"""Background worker for sending scheduled email journey emails.

Runs two async loops:
- Email loop: every 60s, processes due emails with priority ordering
- Inactivity loop: every 3600s, checks for inactive users and schedules retention emails
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import resend
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.email.journey_templates import JourneyTemplates
from infrastructure.config.settings import get_settings
from infrastructure.database import async_session_maker
from infrastructure.database.models.email_journey_event import EmailJourneyEvent
from infrastructure.database.models.user import User
from services.email_journey import EMAIL_JOURNEY_MAP, EmailJourneyService

logger = logging.getLogger(__name__)

# Map email_key (base) -> template method name
_EMAIL_KEY_TO_TEMPLATE = {
    "onboarding.welcome": "welcome",
    "onboarding.first_outline_nudge": "first_outline_nudge",
    "onboarding.outline_to_article": "outline_to_article_nudge",
    "onboarding.outline_reminder": "outline_reminder",
    "onboarding.connect_tools": "connect_tools",
    "onboarding.week_one_recap": "week_one_recap",
    "conversion.usage_80": "usage_80_percent",
    "conversion.usage_100": "usage_100_percent",
    "conversion.power_user": "power_user_features",
    "conversion.audit_upsell": "audit_upsell",
    "retention.inactive_7d": "inactive_7_days",
    "retention.inactive_21d": "inactive_21_days",
    "retention.inactive_45d": "inactive_45_days",
    "ongoing.weekly_digest": "weekly_digest",
    "ongoing.content_decay": "content_decay_alert",
}

# Map base email_key -> extra kwargs to extract from metadata_
_TEMPLATE_KWARGS_MAP = {
    "onboarding.week_one_recap": ("outlines_count", "articles_count"),
    "conversion.usage_80": ("current_usage", "limit", "resource"),
    "conversion.usage_100": ("resource",),
    "conversion.audit_upsell": ("issues_count",),
    "ongoing.weekly_digest": ("articles_generated", "decay_alerts"),
    "ongoing.content_decay": ("article_title", "decay_type"),
}

# Inactivity thresholds -> retention email keys
_INACTIVITY_THRESHOLDS = {
    7: "retention.inactive_7d",
    21: "retention.inactive_21d",
    45: "retention.inactive_45d",
}


class EmailJourneyWorker:
    """Background worker that processes scheduled journey emails."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._templates = JourneyTemplates(self._settings.frontend_url)
        self._running = False

    async def start(self) -> None:
        """Start both background loops."""
        self._running = True
        logger.info("Email journey worker started")
        await asyncio.gather(
            self.run_email_loop(),
            self.run_inactivity_loop(),
        )

    async def stop(self) -> None:
        """Signal the loops to stop."""
        self._running = False

    async def run_email_loop(self) -> None:
        """Process due emails every 60 seconds."""
        while self._running:
            try:
                async with async_session_maker() as db:
                    await self.process_due_emails(db)
            except Exception:
                logger.exception("Error in email loop")
            await asyncio.sleep(60)

    async def run_inactivity_loop(self) -> None:
        """Check for inactive users every hour."""
        while self._running:
            try:
                async with async_session_maker() as db:
                    await self.check_inactive_users(db)
            except Exception:
                logger.exception("Error in inactivity loop")
            await asyncio.sleep(3600)

    async def process_due_emails(self, db: AsyncSession) -> None:
        """Query and process all due scheduled emails."""
        now = datetime.now(UTC)

        result = await db.execute(
            select(EmailJourneyEvent)
            .where(
                EmailJourneyEvent.status == "scheduled",
                EmailJourneyEvent.scheduled_for <= now,
            )
            .order_by(EmailJourneyEvent.user_id, EmailJourneyEvent.scheduled_for)
            .limit(200)
        )
        events = list(result.scalars().all())

        if not events:
            return

        logger.info("Processing %d due email events", len(events))

        # Group by user_id
        events_by_user: dict[str, list[EmailJourneyEvent]] = {}
        for event in events:
            events_by_user.setdefault(event.user_id, []).append(event)

        for user_id, user_events in events_by_user.items():
            await self._process_user_events(db, user_id, user_events)

    async def _process_user_events(
        self,
        db: AsyncSession,
        user_id: str,
        events: list[EmailJourneyEvent],
    ) -> None:
        """Process all due events for a single user."""
        # Fetch user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or user.status != "active":
            # Cancel all events for missing/inactive users
            for event in events:
                event.status = "cancelled"
                event.cancelled_at = datetime.now(UTC)
            await db.commit()
            logger.info(
                "Cancelled %d events for user %s (not found or inactive)",
                len(events),
                user_id,
            )
            return

        # Sort by priority (lower = higher priority)
        def _get_priority(event: EmailJourneyEvent) -> int:
            base_key = event.email_key.split(":")[0]
            entry = EMAIL_JOURNEY_MAP.get(base_key, {})
            return entry.get("priority", 999)

        events.sort(key=_get_priority)

        # Check if we already sent an email to this user today
        already_sent_today = await self._was_email_sent_today(db, user_id)

        for i, event in enumerate(events):
            if i == 0 and not already_sent_today:
                # Send highest priority email
                success = await self._send_journey_email(db, event, user)
                if success:
                    event.status = "sent"
                    event.sent_at = datetime.now(UTC)
                else:
                    event.attempt_count += 1
                    if event.attempt_count >= 3:
                        event.status = "failed"
                        logger.warning(
                            "Email %s for user %s marked as failed after %d attempts",
                            event.email_key,
                            user_id,
                            event.attempt_count,
                        )
                    else:
                        # Reschedule +1 hour
                        event.scheduled_for = datetime.now(UTC) + timedelta(hours=1)
            else:
                # Defer remaining to tomorrow 9am UTC
                tomorrow_9am = (datetime.now(UTC) + timedelta(days=1)).replace(
                    hour=9, minute=0, second=0, microsecond=0
                )
                event.scheduled_for = tomorrow_9am

        await db.commit()

    async def _was_email_sent_today(self, db: AsyncSession, user_id: str) -> bool:
        """Check if any journey email was sent to this user today."""
        today_start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        result = await db.execute(
            select(func.count(EmailJourneyEvent.id)).where(
                EmailJourneyEvent.user_id == user_id,
                EmailJourneyEvent.status == "sent",
                EmailJourneyEvent.sent_at >= today_start,
            )
        )
        count = result.scalar_one()
        return count > 0

    async def _send_journey_email(
        self,
        db: AsyncSession,
        event: EmailJourneyEvent,
        user: User,
    ) -> bool:
        """Build and send a journey email via Resend."""
        base_key = event.email_key.split(":")[0]
        template_method_name = _EMAIL_KEY_TO_TEMPLATE.get(base_key)

        if not template_method_name:
            logger.error("No template mapped for email_key=%s", event.email_key)
            return False

        template_method = getattr(self._templates, template_method_name, None)
        if not template_method:
            logger.error(
                "Template method %s not found on JourneyTemplates",
                template_method_name,
            )
            return False

        # Build kwargs from metadata
        kwargs: dict = {"user_name": user.name or ""}
        extra_keys = _TEMPLATE_KWARGS_MAP.get(base_key, ())
        metadata = event.metadata_ or {}
        for key in extra_keys:
            if key in metadata:
                kwargs[key] = metadata[key]

        try:
            html_body, subject = template_method(**kwargs)
        except Exception:
            logger.exception(
                "Failed to render template %s for user %s",
                template_method_name,
                user.id,
            )
            return False

        # Replace unsubscribe placeholder with actual URL
        # Lazy import — module may not exist yet
        try:
            from services.email_journey_unsubscribe import generate_unsubscribe_token

            unsub_token = generate_unsubscribe_token(user.id, self._settings.secret_key)
            unsub_url = f"{self._settings.frontend_url}/unsubscribe?token={unsub_token}"
        except ImportError:
            logger.warning("Unsubscribe module not available; using placeholder URL")
            unsub_url = f"{self._settings.frontend_url}/dashboard/settings"

        html_body = html_body.replace("{unsubscribe_url}", unsub_url)

        # Send via Resend (or log in dev mode)
        if not self._settings.resend_api_key:
            logger.info(
                "[DEV] Journey email '%s' to %s: subject='%s'",
                event.email_key,
                user.email,
                subject,
            )
            return True

        try:
            await asyncio.to_thread(
                resend.Emails.send,
                {
                    "from": self._settings.resend_from_email,
                    "to": user.email,
                    "subject": subject,
                    "html": html_body,
                    "headers": {
                        "List-Unsubscribe": f"<{unsub_url}>",
                        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                    },
                },
            )
            logger.info(
                "Sent journey email '%s' to %s",
                event.email_key,
                user.email,
            )
            return True
        except Exception:
            logger.exception(
                "Failed to send journey email '%s' to %s",
                event.email_key,
                user.email,
            )
            return False

    async def check_inactive_users(self, db: AsyncSession) -> None:
        """Check for inactive users and schedule retention emails."""
        now = datetime.now(UTC)
        journey_service = EmailJourneyService(db)

        for days, email_key in _INACTIVITY_THRESHOLDS.items():
            cutoff = now - timedelta(days=days)
            # Find next threshold to avoid double-scheduling
            next_cutoff = None
            sorted_thresholds = sorted(_INACTIVITY_THRESHOLDS.keys())
            idx = sorted_thresholds.index(days)
            if idx > 0:
                # Only get users who became inactive AFTER the previous threshold
                prev_days = sorted_thresholds[idx - 1]
                next_cutoff = now - timedelta(days=prev_days)

            query = (
                select(User)
                .where(
                    User.status == "active",
                    User.last_active_at.isnot(None),
                    User.last_active_at <= cutoff,
                )
                .limit(500)
            )
            if next_cutoff is not None:
                query = query.where(User.last_active_at > next_cutoff)

            result = await db.execute(query)
            users = result.scalars().all()

            for user in users:
                try:
                    # Check preferences before scheduling
                    phase = EMAIL_JOURNEY_MAP.get(email_key, {}).get("phase")
                    if phase and not await journey_service._check_preference(user.id, phase):
                        continue
                    await journey_service._schedule_email(
                        user.id, email_key, timedelta(0)
                    )
                except Exception:
                    logger.exception(
                        "Failed to schedule retention email for user %s",
                        user.id,
                    )

            if users:
                logger.info(
                    "Checked %d users inactive for %d+ days",
                    len(list(users)),
                    days,
                )
