"""Email journey orchestrator.

Receives events from application code, decides which emails to schedule
or cancel, and persists scheduling decisions to the database. The actual
sending is handled by the background worker (email_journey_worker.py).
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.email_journey_event import EmailJourneyEvent
from infrastructure.database.models.notification_preferences import NotificationPreferences

logger = logging.getLogger(__name__)

# Map of email_key -> metadata
# phase: which notification preference column gates this email
# priority: for same-day conflict resolution (lower number = higher priority)
EMAIL_JOURNEY_MAP = {
    # Phase 1: Onboarding
    "onboarding.welcome": {"phase": "onboarding", "priority": 20},
    "onboarding.first_outline_nudge": {"phase": "onboarding", "priority": 21},
    "onboarding.outline_to_article": {"phase": "onboarding", "priority": 22},
    "onboarding.outline_reminder": {"phase": "onboarding", "priority": 23},
    "onboarding.connect_tools": {"phase": "onboarding", "priority": 24},
    "onboarding.week_one_recap": {"phase": "onboarding", "priority": 25},
    # Phase 2: Conversion
    "conversion.usage_80": {"phase": "usage", "priority": 10},
    "conversion.usage_100": {"phase": "usage", "priority": 11},
    "conversion.power_user": {"phase": "conversion_tips", "priority": 12},
    "conversion.audit_upsell": {"phase": "conversion_tips", "priority": 13},
    # Phase 3: Retention
    "retention.inactive_7d": {"phase": "reengagement", "priority": 30},
    "retention.inactive_21d": {"phase": "reengagement", "priority": 31},
    "retention.inactive_45d": {"phase": "reengagement", "priority": 32},
    # Phase 4: Ongoing
    "ongoing.weekly_digest": {"phase": "weekly_digest", "priority": 40},
    "ongoing.content_decay": {"phase": "content_decay", "priority": 41},
}

# Map phase -> notification_preferences column name
PHASE_TO_PREF_COLUMN = {
    "onboarding": "email_onboarding",
    "usage": None,  # Uses existing email_usage_80_percent / email_usage_limit_reached
    "conversion_tips": "email_conversion_tips",
    "reengagement": "email_reengagement",
    "weekly_digest": "email_weekly_digest",
    "content_decay": "email_content_decay",
}


class EmailJourneyService:
    """Orchestrates email journey scheduling based on user events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def emit(self, event: str, *, user_id: str, metadata: dict | None = None) -> None:
        """Handle an event and schedule/cancel appropriate emails.

        This is fire-and-forget — exceptions are caught and logged.
        """
        try:
            await self._handle_event(event, user_id, metadata or {})
        except Exception:
            logger.exception("Email journey error handling event=%s user=%s", event, user_id)

    async def _handle_event(self, event: str, user_id: str, metadata: dict) -> None:
        handlers = {
            "user.verified": self._on_user_verified,
            "outline.created": self._on_outline_created,
            "article.generated": self._on_article_generated,
            "integration.connected": self._on_integration_connected,
            "audit.completed": self._on_audit_completed,
            "usage.threshold_reached": self._on_usage_threshold,
            "content.decay_detected": self._on_content_decay,
            "user.tier_changed": self._on_tier_changed,
        }
        handler = handlers.get(event)
        if handler:
            await handler(user_id, metadata)

    async def _on_user_verified(self, user_id: str, metadata: dict) -> None:
        if not await self._check_preference(user_id, "onboarding"):
            return
        await self._schedule_email(user_id, "onboarding.welcome", timedelta(0))
        await self._schedule_email(user_id, "onboarding.first_outline_nudge", timedelta(days=1))
        await self._schedule_email(user_id, "onboarding.connect_tools", timedelta(days=5))
        await self._schedule_email(user_id, "onboarding.week_one_recap", timedelta(days=7))

    async def _on_outline_created(self, user_id: str, metadata: dict) -> None:
        await self._cancel_email(user_id, "onboarding.first_outline_nudge")
        await self._cancel_email(user_id, "onboarding.outline_reminder")
        if await self._check_preference(user_id, "onboarding"):
            await self._schedule_email(user_id, "onboarding.outline_to_article", timedelta(0))
            await self._schedule_email(user_id, "onboarding.outline_reminder", timedelta(days=2))

    async def _on_article_generated(self, user_id: str, metadata: dict) -> None:
        await self._cancel_email(user_id, "onboarding.outline_to_article")
        await self._cancel_email(user_id, "onboarding.outline_reminder")
        article_count = metadata.get("article_count", 0)
        if article_count >= 5 and await self._check_preference(user_id, "conversion_tips"):
            await self._schedule_email(user_id, "conversion.power_user", timedelta(hours=2))

    async def _on_integration_connected(self, user_id: str, metadata: dict) -> None:
        await self._cancel_email(user_id, "onboarding.connect_tools")

    async def _on_audit_completed(self, user_id: str, metadata: dict) -> None:
        issues_count = metadata.get("issues_count", 0)
        if issues_count > 0 and await self._check_preference(user_id, "conversion_tips"):
            await self._schedule_email(
                user_id, "conversion.audit_upsell", timedelta(hours=4),
                extra_data={"issues_count": issues_count},
            )

    async def _on_usage_threshold(self, user_id: str, metadata: dict) -> None:
        percentage = metadata.get("percentage", 0)
        if percentage >= 100:
            pref_col = "email_usage_limit_reached"
            email_key = "conversion.usage_100"
        elif percentage >= 80:
            pref_col = "email_usage_80_percent"
            email_key = "conversion.usage_80"
        else:
            return
        if await self._check_preference_column(user_id, pref_col):
            await self._schedule_email(user_id, email_key, timedelta(0), extra_data=metadata)

    async def _on_content_decay(self, user_id: str, metadata: dict) -> None:
        if await self._check_preference(user_id, "content_decay"):
            # Use article-specific email_key so decay emails are per-article
            article_id = metadata.get("article_id", "unknown")
            email_key = f"ongoing.content_decay:{article_id}"
            await self._schedule_email(user_id, email_key, timedelta(0), extra_data=metadata)

    async def _on_tier_changed(self, user_id: str, metadata: dict) -> None:
        await self._cancel_email(user_id, "conversion.usage_80")
        await self._cancel_email(user_id, "conversion.usage_100")

    async def _schedule_email(
        self,
        user_id: str,
        email_key: str,
        delay: timedelta,
        *,
        extra_data: dict | None = None,
    ) -> None:
        """Schedule an email, skipping if already sent or already scheduled."""
        # Check for existing active record (the partial unique index only covers scheduled/sent)
        result = await self.db.execute(
            select(EmailJourneyEvent).where(
                EmailJourneyEvent.user_id == user_id,
                EmailJourneyEvent.email_key == email_key,
                EmailJourneyEvent.status.in_(["scheduled", "sent"]),
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return  # Already scheduled or sent

        # Check for recent failure that can be retried
        result = await self.db.execute(
            select(EmailJourneyEvent).where(
                EmailJourneyEvent.user_id == user_id,
                EmailJourneyEvent.email_key == email_key,
                EmailJourneyEvent.status == "failed",
            ).order_by(EmailJourneyEvent.created_at.desc()).limit(1)
        )
        failed = result.scalar_one_or_none()
        if failed and failed.attempt_count < 3:
            failed.status = "scheduled"
            failed.scheduled_for = datetime.now(UTC) + delay
            if extra_data:
                failed.metadata_ = extra_data
            await self.db.commit()
            return

        event = EmailJourneyEvent(
            id=str(uuid4()),
            user_id=user_id,
            email_key=email_key,
            status="scheduled",
            scheduled_for=datetime.now(UTC) + delay,
            metadata_=extra_data,
        )
        self.db.add(event)
        await self.db.commit()

    async def _cancel_email(self, user_id: str, email_key: str) -> None:
        """Cancel a scheduled email if it hasn't been sent yet."""
        await self.db.execute(
            update(EmailJourneyEvent)
            .where(
                EmailJourneyEvent.user_id == user_id,
                EmailJourneyEvent.email_key == email_key,
                EmailJourneyEvent.status == "scheduled",
            )
            .values(status="cancelled", cancelled_at=datetime.now(UTC))
        )
        await self.db.commit()

    async def _check_preference(self, user_id: str, phase: str) -> bool:
        """Check if user has the relevant notification preference enabled."""
        pref_col = PHASE_TO_PREF_COLUMN.get(phase)
        if pref_col is None:
            return True
        return await self._check_preference_column(user_id, pref_col)

    async def _check_preference_column(self, user_id: str, column_name: str) -> bool:
        """Check a specific notification_preferences column."""
        result = await self.db.execute(
            select(NotificationPreferences).where(
                NotificationPreferences.user_id == user_id
            )
        )
        prefs = result.scalar_one_or_none()
        if prefs is None:
            return True  # Default: all enabled
        return getattr(prefs, column_name, True)
