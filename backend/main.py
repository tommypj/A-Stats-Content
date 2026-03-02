"""A-Stats Engine - Main FastAPI Application."""

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.middleware.rate_limit import limiter
from api.routes import api_router
from infrastructure.config import get_settings
from infrastructure.database import close_db, init_db
from infrastructure.logging_config import setup_logging
from services.post_queue import post_queue
from services.social_scheduler import scheduler_service
from services.task_queue import task_queue

settings = get_settings()
logger = logging.getLogger(__name__)

# Sentry error tracking — initialised at module level so startup errors are captured too
if settings.sentry_dsn:
    import logging as _logging

    # LOW-12: Validate DSN format before initializing to surface misconfiguration early
    _dsn = settings.sentry_dsn
    if not _dsn.startswith("https://") or "@sentry.io" not in _dsn:
        logger.warning(
            "LOW-12: SENTRY_DSN appears malformed: %s. Sentry will not be initialized.",
            _dsn[:30],
        )
    else:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=_dsn,
            environment=settings.environment,
            integrations=[
                FastApiIntegration(transaction_style="url"),
                SqlalchemyIntegration(),
                RedisIntegration(),
                LoggingIntegration(level=_logging.INFO, event_level=_logging.ERROR),
            ],
            traces_sample_rate=0.1 if settings.is_production else 1.0,
            profiles_sample_rate=0.05 if settings.is_production else 0.0,
            send_default_pii=False,
        )
        logger.info("Sentry error tracking initialised (env=%s)", settings.environment)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Configure logging before anything else so all startup messages use the
    # correct format: JSON in production/staging, human-readable in development.
    setup_logging(
        json_output=not settings.debug and settings.is_production,
        level="DEBUG" if settings.debug else "INFO",
    )

    # Startup
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    logger.info("Environment: %s", settings.environment)
    logger.info("CORS origins raw: %r", settings.cors_origins)
    logger.info("CORS origins list: %r", settings.cors_origins_list)

    settings.validate_production_secrets()

    # Recover articles, outlines, and images stuck in "generating" status from previous shutdown
    from sqlalchemy import update

    from infrastructure.database.connection import async_session_maker
    from infrastructure.database.models.content import (
        Article,
        ContentStatus,
        GeneratedImage,
        Outline,
    )

    async with async_session_maker() as recovery_db:
        stale_articles = await recovery_db.execute(
            update(Article)
            .where(Article.status == ContentStatus.GENERATING.value)
            .values(
                status=ContentStatus.FAILED.value,
                generation_error="Server restarted during generation",
            )
        )
        stale_outlines = await recovery_db.execute(
            update(Outline)
            .where(Outline.status == ContentStatus.GENERATING.value)
            .values(
                status=ContentStatus.FAILED.value,
                generation_error="Server restarted during generation",
            )
        )
        stale_images = await recovery_db.execute(
            update(GeneratedImage)
            .where(GeneratedImage.status == "generating")
            .values(status="failed")
        )
        await recovery_db.commit()
        if stale_articles.rowcount > 0:
            logger.warning(
                "Recovered %d articles stuck in generating status", stale_articles.rowcount
            )
        if stale_outlines.rowcount > 0:
            logger.warning(
                "Recovered %d outlines stuck in generating status", stale_outlines.rowcount
            )
        if stale_images.rowcount > 0:
            logger.warning("Recovered %d images stuck in generating status", stale_images.rowcount)

    if settings.is_development:
        logger.info("Development mode - initializing database...")
        await init_db()

    # INFRA-08: In production, validate Redis is reachable — rate limiter falls
    # back to per-process in-memory storage which is ineffective in multi-instance.
    if settings.environment == "production":
        try:
            import redis.asyncio as aioredis

            # INFRA-02: Configure connection pool to cap max connections and prevent exhaustion
            _redis_check = aioredis.from_url(
                settings.redis_url,
                max_connections=20,
            )
            await _redis_check.ping()
            await _redis_check.aclose()
            logger.info("Redis connectivity confirmed for rate limiter")
        except Exception as _redis_err:
            logger.critical(
                "INFRA-08: Redis is unreachable in production (%s). "
                "Rate limiting will use per-process in-memory storage — "
                "this is insecure in multi-instance deployments.",
                _redis_err,
            )
            # Do not raise — allow startup to proceed, but alert loudly

    # INFRA-C2: Validate CORS origins match FRONTEND_URL to prevent credential leakage
    from urllib.parse import urlparse as _urlparse

    _frontend_host = _urlparse(settings.frontend_url).netloc if settings.frontend_url else None
    if _frontend_host and settings.environment == "production":
        for _origin in settings.cors_origins_list:
            _origin_host = _urlparse(_origin).netloc
            if (
                _origin_host
                and _origin_host != _frontend_host
                and not _origin_host.endswith("." + _frontend_host)
            ):
                logger.warning(
                    "INFRA-C2: CORS origin '%s' does not match FRONTEND_URL host '%s'. "
                    "This may allow credential leakage to unintended origins.",
                    _origin,
                    _frontend_host,
                )

    # Initialize Redis post queue (optional)
    logger.info("Connecting to Redis for post queue...")
    await post_queue.connect()

    # Start social media scheduler in background
    logger.info("Starting social media scheduler...")
    scheduler_task = asyncio.create_task(scheduler_service.start())

    # Start periodic task-queue cleanup (runs every 30 minutes, removes tasks >1h old)
    async def _task_queue_cleanup_loop():
        while True:
            await asyncio.sleep(1800)  # 30 minutes
            removed = task_queue.cleanup_old(max_age_seconds=3600)
            if removed:
                logger.info("task_queue cleanup: removed %d old tasks", removed)

    cleanup_task = asyncio.create_task(_task_queue_cleanup_loop(), name="tq-cleanup")

    # LOW-08: Start daily cleanup of ContentDecayAlert records older than 90 days.
    # Runs once at startup (to clear any backlog), then every 24 hours thereafter.
    async def _decay_alert_cleanup_loop():
        from datetime import datetime, timedelta

        from sqlalchemy import delete as _sa_delete

        from infrastructure.database.models.analytics import ContentDecayAlert

        async def _run_cleanup():
            try:
                async with async_session_maker() as _db:
                    cutoff = datetime.now(UTC) - timedelta(days=90)
                    result = await _db.execute(
                        _sa_delete(ContentDecayAlert).where(ContentDecayAlert.created_at < cutoff)
                    )
                    await _db.commit()
                    deleted = result.rowcount
                    if deleted:
                        logger.info(
                            "LOW-08: Cleaned up %d ContentDecayAlert records older than 90 days",
                            deleted,
                        )
            except Exception as _cleanup_err:
                logger.warning("LOW-08: decay alert cleanup failed: %s", _cleanup_err)

        # Run once at startup to clear any backlog
        await _run_cleanup()

        while True:
            await asyncio.sleep(86400)  # 24 hours
            await _run_cleanup()

    decay_alert_cleanup_task = asyncio.create_task(
        _decay_alert_cleanup_loop(), name="decay-alert-cleanup"
    )

    logger.info("Application started successfully!")

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Stop task-queue cleanup loop
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    # Stop decay alert cleanup loop
    decay_alert_cleanup_task.cancel()
    try:
        await decay_alert_cleanup_task
    except asyncio.CancelledError:
        pass

    # Stop scheduler — INFRA-07: wait up to 30 s for in-flight publishes to complete
    logger.info("Stopping social media scheduler...")
    await scheduler_service.stop()
    scheduler_task.cancel()

    try:
        await asyncio.wait_for(asyncio.shield(scheduler_task), timeout=30.0)
    except (TimeoutError, asyncio.CancelledError):
        pass

    # Disconnect Redis
    await post_queue.disconnect()

    await close_db()
    logger.info("Application stopped.")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="AI-Powered Content Generation & SEO Platform",
    version=settings.app_version,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# Rate limiting — wire the slowapi limiter so that:
# 1. app.state.limiter is set (required by SlowAPIMiddleware and @limiter.limit decorators)
# 2. SlowAPIMiddleware intercepts every request and applies the default 100/minute
#    global limit; per-endpoint @limiter.limit decorators override this automatically
# 3. The RateLimitExceeded exception handler returns a proper 429 response
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# INFRA-13: reject request bodies larger than 5MB to prevent memory exhaustion
_MAX_BODY_SIZE = 5 * 1024 * 1024  # 5MB


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH"):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large (max 5MB)"},
            )
    return await call_next(request)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # INFRA-05: Log full stack trace in dev only — production logs only type+message to avoid leaking internals.
    # INFRA-06: Truncate exc message to 200 chars to prevent leaking DB connection strings or secrets.
    if settings.environment == "production":
        logger.error("Unhandled exception: %s: %s", type(exc).__name__, str(exc)[:200])
    else:
        logger.error("Unhandled exception: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"

    # Skip logging for health check endpoints to avoid log noise
    path = request.url.path
    if not path.startswith("/api/v1/health"):
        logger.info(
            "%s %s %s %.1fms",
            request.method,
            path,
            response.status_code,
            round(duration_ms, 1),
            extra={
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 1),
            },
        )
    return response


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    incoming = request.headers.get("X-Request-ID")
    # INFRA-09: Only accept the caller's ID if it is a valid UUID to prevent log injection.
    if incoming:
        try:
            uuid.UUID(incoming)
            request_id = incoming
        except ValueError:
            request_id = str(uuid.uuid4())
    else:
        request_id = str(uuid.uuid4())
    # INFRA-04: Store in request.state so log handlers and dependencies can correlate logs.
    request.state.request_id = request_id
    # INFRA-17: TODO — Propagate X-Request-ID header to outbound Anthropic/email API calls for tracing
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # INFRA-03: TODO — Add Content-Security-Policy header once frontend inline styles/scripts are audited
    # Suggested: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # IMG-09: Generated images are immutable (content-addressed by ID) — cache aggressively
    if request.url.path.startswith("/uploads/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Serve uploaded files (images, etc.)
uploads_path = os.path.join(os.path.dirname(__file__), "data", "uploads")
os.makedirs(uploads_path, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.is_development else "disabled",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        workers=settings.workers if not settings.is_development else 1,
    )
