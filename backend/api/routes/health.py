"""Health check endpoints."""

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps_admin import get_current_admin_user
from infrastructure.config import get_settings
from infrastructure.database import get_db
from infrastructure.database.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    """Health check with database connectivity."""
    try:
        # LOW-04: Wrap DB execute in timeout to prevent hanging health checks
        result = await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=5.0)
        result.scalar()
        db_status = "connected"
    except TimeoutError:
        logger.error("Health check DB timeout")
        db_status = "error: database timeout"
    except Exception as e:
        logger.error("Health check DB error: %s", str(e))
        db_status = "error: database check failed"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": db_status,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/redis")
async def health_redis():
    """INFRA-M1: Check Redis connectivity."""
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        await asyncio.wait_for(r.ping(), timeout=3.0)
        await r.aclose()
        return {"status": "healthy", "service": "redis"}
    except TimeoutError:
        raise HTTPException(status_code=503, detail="Redis timeout")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {str(e)}")


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Kubernetes-style readiness probe."""
    db_ok = False
    try:
        # LOW-04: Apply timeout to DB check in readiness probe too
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=5.0)
        db_ok = True
    except Exception:
        db_ok = False

    # INFRA-M1: Check Redis too — app degrades significantly without it (rate limiting breaks)
    redis_ok = False
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        await asyncio.wait_for(r.ping(), timeout=2.0)
        await r.aclose()
        redis_ok = True
    except Exception:
        redis_ok = False

    # DB is required; Redis degraded is tolerated (app still starts, but rate limiting may be per-process)
    return {
        "ready": db_ok,
        "database": "ok" if db_ok else "unavailable",
        "redis": "ok" if redis_ok else "degraded",
    }


@router.get("/health/live")
async def liveness_check():
    """Kubernetes-style liveness probe."""
    return {"alive": True}


@router.get("/health/services")
async def services_check(admin_user: User = Depends(get_current_admin_user)):
    """Check status of external service connections."""
    from adapters.ai.anthropic_adapter import content_ai_service
    from adapters.ai.replicate_adapter import image_ai_service

    services = {}

    # Replicate
    services["replicate"] = {
        "configured": image_ai_service._client is not None,
        "api_token_set": bool(settings.replicate_api_token),
        "model": settings.replicate_model,
    }

    # Anthropic
    services["anthropic"] = {
        "configured": content_ai_service._client is not None,
        "api_key_set": bool(settings.anthropic_api_key),
        "model": settings.anthropic_model,
    }

    all_configured = all(s["configured"] for s in services.values())

    return {
        "status": "healthy" if all_configured else "degraded",
        "services": services,
        "timestamp": datetime.now(UTC).isoformat(),
    }
