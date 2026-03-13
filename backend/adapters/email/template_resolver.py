"""Resolve email templates with optional DB overrides."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.email_template_override import EmailTemplateOverride

logger = logging.getLogger(__name__)


async def resolve_template(
    db: AsyncSession,
    email_key: str,
    code_html: str,
    code_subject: str,
) -> tuple[str, str]:
    """Return DB-overridden (html, subject) if an override exists, else code defaults."""
    try:
        result = await db.execute(
            select(EmailTemplateOverride).where(
                EmailTemplateOverride.email_key == email_key
            )
        )
        override = result.scalar_one_or_none()
    except Exception:
        logger.exception("Failed to query email template override for %s", email_key)
        return code_html, code_subject

    if override is None:
        return code_html, code_subject

    html = override.html if override.html is not None else code_html
    subject = override.subject if override.subject is not None else code_subject

    return html, subject
