"""Admin email journey testing endpoints."""

import asyncio
import logging

import resend
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from adapters.email.journey_templates import JourneyTemplates
from api.deps_admin import get_current_admin_user
from api.middleware.rate_limit import limiter
from infrastructure.config.settings import get_settings
from infrastructure.database.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/emails", tags=["Admin - Emails"])


# ── Request / Response models ───────────────────────────────────────


class EmailPreviewRequest(BaseModel):
    email_key: str
    user_name: str = "Test User"


class EmailPreviewResponse(BaseModel):
    email_key: str
    subject: str
    html: str


class SendTestEmailRequest(BaseModel):
    email_key: str
    recipient_email: EmailStr
    user_name: str = "Test User"


# ── Helper ──────────────────────────────────────────────────────────


def _render_template(
    templates: JourneyTemplates, email_key: str, user_name: str
) -> tuple[str, str]:
    """Render a template with sample data. Returns (html, subject)."""
    TEMPLATE_MAP: dict[str, tuple[str, dict]] = {
        "onboarding.welcome": ("welcome", {}),
        "onboarding.first_outline_nudge": ("first_outline_nudge", {}),
        "onboarding.outline_to_article": ("outline_to_article_nudge", {}),
        "onboarding.outline_reminder": ("outline_reminder", {}),
        "onboarding.connect_tools": ("connect_tools", {}),
        "onboarding.week_one_recap": (
            "week_one_recap",
            {"outlines_count": 3, "articles_count": 1},
        ),
        "conversion.usage_80": (
            "usage_80_percent",
            {"current_usage": 8, "limit": 10, "resource": "articles"},
        ),
        "conversion.usage_100": ("usage_100_percent", {"resource": "articles"}),
        "conversion.power_user": ("power_user_features", {}),
        "conversion.audit_upsell": ("audit_upsell", {"issues_count": 12}),
        "retention.inactive_7d": ("inactive_7_days", {}),
        "retention.inactive_21d": ("inactive_21_days", {}),
        "retention.inactive_45d": ("inactive_45_days", {}),
        "ongoing.weekly_digest": (
            "weekly_digest",
            {"articles_generated": 5, "decay_alerts": 2},
        ),
        "ongoing.content_decay": (
            "content_decay_alert",
            {"article_title": "Best SEO Tips 2026", "decay_type": "position_drop"},
        ),
        "system.unsubscribe_confirmation": ("unsubscribe_confirmation", {}),
        "system.resubscribe_confirmation": ("resubscribe_confirmation", {}),
    }

    entry = TEMPLATE_MAP.get(email_key)
    if not entry:
        raise HTTPException(
            status_code=400, detail=f"Unknown email template: {email_key}"
        )

    method_name, extra_kwargs = entry
    method = getattr(templates, method_name)
    return method(user_name=user_name, **extra_kwargs)


# ── Endpoints ───────────────────────────────────────────────────────


@router.get("/templates")
async def list_email_templates(
    admin_user: User = Depends(get_current_admin_user),
) -> dict:
    """List all available email journey templates."""
    from services.email_journey import EMAIL_JOURNEY_MAP

    templates = []
    for key, meta in EMAIL_JOURNEY_MAP.items():
        templates.append(
            {
                "email_key": key,
                "phase": meta["phase"],
                "priority": meta["priority"],
            }
        )
    # Add system templates (not part of the journey map)
    templates.append(
        {"email_key": "system.unsubscribe_confirmation", "phase": "system", "priority": 99}
    )
    templates.append(
        {"email_key": "system.resubscribe_confirmation", "phase": "system", "priority": 99}
    )

    return {"templates": templates, "total": len(templates)}


@router.post("/preview", response_model=EmailPreviewResponse)
@limiter.limit("20/minute")
async def preview_email_template(
    request: Request,
    body: EmailPreviewRequest,
    admin_user: User = Depends(get_current_admin_user),
) -> EmailPreviewResponse:
    """Render an email template with sample data for preview."""
    settings = get_settings()
    templates = JourneyTemplates(frontend_url=settings.frontend_url)

    html, subject = _render_template(templates, body.email_key, body.user_name)

    # Replace unsubscribe placeholder with a dummy URL
    html = html.replace("{unsubscribe_url}", "#unsubscribe-preview")

    return EmailPreviewResponse(email_key=body.email_key, subject=subject, html=html)


@router.post("/send-test")
@limiter.limit("20/minute")
async def send_test_email(
    request: Request,
    body: SendTestEmailRequest,
    admin_user: User = Depends(get_current_admin_user),
) -> dict:
    """Send a test email to a specified address."""
    settings = get_settings()
    templates = JourneyTemplates(frontend_url=settings.frontend_url)

    html, subject = _render_template(templates, body.email_key, body.user_name)
    html = html.replace(
        "{unsubscribe_url}",
        f"{settings.frontend_url}/settings?tab=notifications",
    )

    # Prefix subject to indicate test
    subject = f"[TEST] {subject}"

    if not settings.resend_api_key:
        logger.info(
            "DEV: Would send test email '%s' to %s",
            body.email_key,
            body.recipient_email,
        )
        return {
            "message": f"DEV MODE: Email '{body.email_key}' logged (no API key)",
            "sent": False,
        }

    try:
        resend.api_key = settings.resend_api_key
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": settings.resend_from_email,
                "to": str(body.recipient_email),
                "subject": subject,
                "html": html,
            },
        )
        return {"message": f"Test email sent to {body.recipient_email}", "sent": True}
    except Exception as e:
        logger.exception("Failed to send test email")
        raise HTTPException(status_code=500, detail=f"Failed to send: {str(e)}")
