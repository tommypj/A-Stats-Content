"""Admin email journey testing and template override endpoints."""

import asyncio
import logging
from uuid import uuid4

import resend
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.email.journey_templates import JourneyTemplates
from adapters.email.template_resolver import resolve_template
from api.deps_admin import get_current_admin_user
from api.middleware.rate_limit import limiter
from infrastructure.config.settings import get_settings
from infrastructure.database.connection import get_db
from infrastructure.database.models.email_template_override import EmailTemplateOverride
from infrastructure.database.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/emails", tags=["Admin - Emails"])


# ── Valid email keys (used for validation) ─────────────────────────

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


class OverrideUpsertRequest(BaseModel):
    subject: str | None = None
    html: str | None = None


class OverrideResponse(BaseModel):
    id: str
    email_key: str
    subject: str | None
    html: str | None
    updated_by_admin_id: str | None
    created_at: str
    updated_at: str


# ── Helper ──────────────────────────────────────────────────────────


def _render_template(
    templates: JourneyTemplates, email_key: str, user_name: str
) -> tuple[str, str]:
    """Render a template with sample data. Returns (html, subject)."""
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
    db: AsyncSession = Depends(get_db),
) -> EmailPreviewResponse:
    """Render an email template with sample data for preview."""
    settings = get_settings()
    templates = JourneyTemplates(frontend_url=settings.frontend_url)

    html, subject = _render_template(templates, body.email_key, body.user_name)

    # Apply DB overrides if present
    html, subject = await resolve_template(db, body.email_key, html, subject)

    # Replace unsubscribe placeholder with a dummy URL
    html = html.replace("{unsubscribe_url}", "#unsubscribe-preview")

    return EmailPreviewResponse(email_key=body.email_key, subject=subject, html=html)


@router.post("/send-test")
@limiter.limit("20/minute")
async def send_test_email(
    request: Request,
    body: SendTestEmailRequest,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a test email to a specified address."""
    settings = get_settings()
    templates = JourneyTemplates(frontend_url=settings.frontend_url)

    html, subject = _render_template(templates, body.email_key, body.user_name)

    # Apply DB overrides if present
    html, subject = await resolve_template(db, body.email_key, html, subject)

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


# ── Template Override Endpoints ─────────────────────────────────────


@router.get("/overrides")
@limiter.limit("30/minute")
async def list_overrides(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all email template overrides."""
    result = await db.execute(
        select(EmailTemplateOverride).order_by(EmailTemplateOverride.email_key)
    )
    overrides = result.scalars().all()

    return {
        "overrides": [
            {
                "id": o.id,
                "email_key": o.email_key,
                "subject": o.subject,
                "html": o.html,
                "updated_by_admin_id": o.updated_by_admin_id,
                "created_at": o.created_at.isoformat(),
                "updated_at": o.updated_at.isoformat(),
            }
            for o in overrides
        ],
        "total": len(overrides),
    }


@router.put("/overrides/{email_key}")
@limiter.limit("20/minute")
async def upsert_override(
    request: Request,
    email_key: str,
    body: OverrideUpsertRequest,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create or update an email template override."""
    if email_key not in TEMPLATE_MAP:
        raise HTTPException(
            status_code=400, detail=f"Unknown email template: {email_key}"
        )

    if body.subject is None and body.html is None:
        raise HTTPException(
            status_code=400,
            detail="At least one of 'subject' or 'html' must be provided",
        )

    new_id = str(uuid4())
    await db.execute(
        text("""
            INSERT INTO email_template_overrides (id, email_key, subject, html, updated_by_admin_id, created_at, updated_at)
            VALUES (:id, :email_key, :subject, :html, :admin_id, NOW(), NOW())
            ON CONFLICT (email_key) DO UPDATE SET
                subject = COALESCE(:subject, email_template_overrides.subject),
                html = COALESCE(:html, email_template_overrides.html),
                updated_by_admin_id = :admin_id,
                updated_at = NOW()
        """),
        {
            "id": new_id,
            "email_key": email_key,
            "subject": body.subject,
            "html": body.html,
            "admin_id": admin_user.id,
        },
    )
    await db.commit()

    # Fetch the upserted row
    result = await db.execute(
        select(EmailTemplateOverride).where(
            EmailTemplateOverride.email_key == email_key
        )
    )
    override = result.scalar_one()

    return {
        "id": override.id,
        "email_key": override.email_key,
        "subject": override.subject,
        "html": override.html,
        "updated_by_admin_id": override.updated_by_admin_id,
        "created_at": override.created_at.isoformat(),
        "updated_at": override.updated_at.isoformat(),
    }


@router.delete("/overrides/{email_key}")
@limiter.limit("20/minute")
async def delete_override(
    request: Request,
    email_key: str,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an email template override, resetting to code default."""
    result = await db.execute(
        delete(EmailTemplateOverride).where(
            EmailTemplateOverride.email_key == email_key
        )
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No override found for email_key: {email_key}",
        )

    return {"message": f"Override for '{email_key}' deleted, reset to default"}
