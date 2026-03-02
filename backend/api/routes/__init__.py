"""API Routes."""

from fastapi import APIRouter

from .admin_alerts import router as admin_alerts_router
from .admin_analytics import router as admin_analytics_router
from .admin_content import router as admin_content_router
from .admin_generations import router as admin_generations_router
from .admin_users import router as admin_users_router
from .agency import router as agency_router
from .analytics import router as analytics_router
from .articles import router as articles_router
from .auth import router as auth_router
from .billing import router as billing_router
from .bulk import router as bulk_router
from .health import router as health_router
from .images import router as images_router
from .knowledge import router as knowledge_router
from .notifications import router as notifications_router
from .outlines import router as outlines_router
from .project_billing import router as project_billing_router
from .project_invitations import router as project_invitations_router
from .projects import router as projects_router
from .social import router as social_router
from .wordpress import router as wordpress_router

# Create main API router
api_router = APIRouter()

# Include route modules
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router)
api_router.include_router(outlines_router)
api_router.include_router(articles_router)
api_router.include_router(images_router)
api_router.include_router(wordpress_router)
api_router.include_router(analytics_router)
api_router.include_router(billing_router)
api_router.include_router(project_billing_router)
api_router.include_router(knowledge_router)
api_router.include_router(social_router)
api_router.include_router(admin_analytics_router)
api_router.include_router(admin_content_router)
api_router.include_router(admin_users_router)
api_router.include_router(admin_generations_router)
api_router.include_router(admin_alerts_router)
api_router.include_router(project_invitations_router)
api_router.include_router(projects_router)
api_router.include_router(notifications_router)
api_router.include_router(bulk_router)
api_router.include_router(agency_router)

# Future routes will be added here:
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
