"""A-Stats Engine - Main FastAPI Application."""
import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

from infrastructure.config import get_settings
from infrastructure.logging_config import setup_logging
from infrastructure.database import init_db, close_db
from api.routes import api_router
from api.middleware.rate_limit import limiter
from services.social_scheduler import scheduler_service
from services.post_queue import post_queue
from services.task_queue import task_queue

settings = get_settings()


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

    # Recover articles and outlines stuck in "generating" status from previous shutdown
    from infrastructure.database.connection import async_session_maker
    from infrastructure.database.models.content import Article, Outline, ContentStatus
    from sqlalchemy import update

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
        await recovery_db.commit()
        if stale_articles.rowcount > 0:
            logger.warning(
                "Recovered %d articles stuck in generating status", stale_articles.rowcount
            )
        if stale_outlines.rowcount > 0:
            logger.warning(
                "Recovered %d outlines stuck in generating status", stale_outlines.rowcount
            )

    if settings.is_development:
        logger.info("Development mode - initializing database...")
        await init_db()

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

    # Stop scheduler
    logger.info("Stopping social media scheduler...")
    await scheduler_service.stop()
    scheduler_task.cancel()

    try:
        await scheduler_task
    except asyncio.CancelledError:
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

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
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
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
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
