"""Health check endpoints."""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database import get_db
from infrastructure.config import get_settings
from api.deps_admin import get_current_admin_user
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
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    """Health check with database connectivity."""
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        db_status = "connected"
    except Exception as e:
        logger.error("Health check DB error: %s", str(e))
        db_status = "error: database check failed"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Kubernetes-style readiness probe."""
    try:
        await db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception:
        return {"ready": False}


@router.get("/health/live")
async def liveness_check():
    """Kubernetes-style liveness probe."""
    return {"alive": True}


@router.get("/health/services")
async def services_check(admin_user: User = Depends(get_current_admin_user)):
    """Check status of external service connections."""
    from adapters.ai.replicate_adapter import image_ai_service
    from adapters.ai.anthropic_adapter import content_ai_service

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
        "timestamp": datetime.utcnow().isoformat(),
    }
