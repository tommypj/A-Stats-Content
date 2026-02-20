"""API Routes."""
from fastapi import APIRouter

from .health import router as health_router

# Create main API router
api_router = APIRouter()

# Include route modules
api_router.include_router(health_router, tags=["Health"])

# Future routes will be added here:
# api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(content_router, prefix="/content", tags=["Content"])
# api_router.include_router(social_router, prefix="/social", tags=["Social"])
# api_router.include_router(images_router, prefix="/images", tags=["Images"])
# api_router.include_router(gsc_router, prefix="/gsc", tags=["Google Search Console"])
# api_router.include_router(wordpress_router, prefix="/wordpress", tags=["WordPress"])
# api_router.include_router(knowledge_router, prefix="/knowledge", tags=["Knowledge Vault"])
# api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
# api_router.include_router(billing_router, prefix="/billing", tags=["Billing"])
# api_router.include_router(settings_router, prefix="/settings", tags=["Settings"])
# api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
