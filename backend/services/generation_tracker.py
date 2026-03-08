"""
Generation tracking service.
Logs all generation events, creates admin alerts on failure,
and increments user-level usage counters only on success.
"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.generation import AdminAlert, GenerationLog
from services.error_logger import log_error

logger = logging.getLogger(__name__)


class GenerationTracker:
    """Tracks generation events and manages usage billing."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_start(
        self,
        user_id: str,
        project_id: str | None,
        resource_type: str,
        resource_id: str,
        input_metadata: dict | None = None,
    ) -> GenerationLog:
        """Log the start of a generation. Returns the log entry for later update.

        GEN-35: DB failures here are non-fatal — a warning is logged and a
        detached (unsaved) log object is returned so generation proceeds
        uninterrupted.  Callers (log_success / log_failure) already guard
        against a missing log row via scalar_one_or_none checks.
        """
        log = GenerationLog(
            id=str(uuid4()),
            user_id=user_id,
            project_id=project_id,
            resource_type=resource_type,
            resource_id=resource_id,
            status="started",
            input_metadata=input_metadata,
            cost_credits=0,  # Not charged yet
        )
        try:
            self.db.add(log)
            await self.db.flush()
        except Exception as e:
            logger.warning("Failed to log generation start (non-fatal): %s", e)
            # Do not re-raise — allow generation to proceed even if tracking fails.
            # The log object is returned in a detached/unsaved state; subsequent
            # log_success / log_failure calls will find no matching row and skip
            # their updates silently (they already guard with scalar_one_or_none).
        return log

    async def log_success(
        self,
        log_id: str,
        ai_model: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Mark generation as successful and increment usage."""
        result = await self.db.execute(select(GenerationLog).where(GenerationLog.id == log_id))
        log = result.scalar_one_or_none()
        if not log:
            logger.warning("Generation log %s not found for success update", log_id)
            return

        log.status = "success"
        log.ai_model = ai_model
        log.duration_ms = duration_ms
        log.cost_credits = 1

        # Increment user-level usage counters
        try:
            from infrastructure.database.models.user import User

            user_result = await self.db.execute(select(User).where(User.id == log.user_id))
            user = user_result.scalar_one_or_none()
            if user:
                ALLOWED_USAGE_FIELDS = {
                    "article": "articles_generated_this_month",
                    "outline": "outlines_generated_this_month",
                    "image": "images_generated_this_month",
                    "social_post": "social_posts_generated_this_month",
                }
                usage_field = ALLOWED_USAGE_FIELDS.get(log.resource_type)
                if usage_field:
                    current = getattr(user, usage_field, 0) or 0
                    setattr(user, usage_field, current + 1)
                else:
                    logger.warning(
                        "Unknown resource_type '%s' for usage increment", log.resource_type
                    )
            else:
                logger.warning("User %s not found for usage increment", log.user_id)
        except Exception as e:
            logger.warning("Failed to increment user usage for %s: %s", log.user_id, e)

        await self.db.flush()

    async def log_failure(
        self,
        log_id: str,
        error_message: str,
        user_id: str | None = None,
        project_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Mark generation as failed. Creates an admin alert. Does NOT increment usage."""
        result = await self.db.execute(select(GenerationLog).where(GenerationLog.id == log_id))
        log = result.scalar_one_or_none()
        if not log:
            logger.warning("Generation log %s not found for failure update", log_id)
            return

        log.status = "failed"
        log.error_message = error_message[:2000] if error_message else None
        log.duration_ms = duration_ms
        log.cost_credits = 0  # NOT charged on failure

        # Create admin alert
        alert = AdminAlert(
            id=str(uuid4()),
            alert_type="generation_failed",
            severity="warning",
            title=f"{log.resource_type.capitalize()} generation failed",
            message=(
                f"Failed to generate {log.resource_type} (ID: {log.resource_id}). "
                f"Error: {error_message[:500] if error_message else 'Unknown error'}"
            ),
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            user_id=log.user_id,
            project_id=log.project_id,
        )
        self.db.add(alert)

        # Also log to centralized system error log (no auto-commit — caller manages transaction)
        await log_error(
            self.db,
            error_type=self._extract_error_type(error_message),
            title=f"{log.resource_type.capitalize()} generation failed",
            message=error_message,
            severity="error",
            service=f"{log.resource_type}_generation",
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            user_id=log.user_id,
            project_id=log.project_id,
            auto_commit=False,
        )

    @staticmethod
    def _extract_error_type(error_message: str | None) -> str:
        """Extract a meaningful error type from the error message."""
        if not error_message:
            return "UnknownError"
        msg = error_message.strip()
        # Common provider error patterns
        for prefix in ("ReplicateError", "OpenAIError", "GoogleAPIError",
                        "AnthropicError", "ValidationError", "TimeoutError",
                        "ConnectionError", "HTTPError"):
            if prefix in msg:
                return prefix
        # Check for HTTP status patterns
        if "422" in msg[:20]:
            return "ValidationError"
        if "429" in msg[:20]:
            return "RateLimitError"
        if "500" in msg[:20] or "502" in msg[:20] or "503" in msg[:20]:
            return "ServerError"
        return "GenerationError"

    async def check_limit(
        self,
        project_id: str | None,
        resource_type: str,
        user_id: str | None = None,
    ) -> bool:
        """Check if the user can generate more of this resource type.
        Returns True if allowed, False if limit reached.

        Uses DB-based checks only. Fails CLOSED on error (returns False) to
        protect billing — a transient DB error should not silently grant unlimited
        generation. project_id is accepted for call-site compatibility but ignored;
        all quota enforcement is user-level only.
        """
        if not user_id:
            return False  # No user context — fail closed

        try:
            from infrastructure.database.models.user import User

            user_result = await self.db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                # User row not found — this is an invalid auth state;
                # deny generation rather than silently allowing it.
                logger.warning("User %s not found during limit check — denying", user_id)
                return False

            # Reset monthly counters if we've crossed into a new month
            await self._reset_user_usage_if_needed(user)

            # Get plan limits — treat expired subscriptions as free tier
            from core.plans import PLANS

            now = datetime.now(UTC)
            tier = user.subscription_tier or "free"
            if user.subscription_expires and user.subscription_expires < now:
                tier = "free"
            plan = PLANS.get(tier, PLANS["free"])
            limits = plan.get("limits", {})

            # Map resource_type to limit key
            limit_key = f"{resource_type}s_per_month"
            limit = limits.get(limit_key, 0)

            if limit == -1:
                return True  # unlimited

            # Get current month's usage count for this user
            ALLOWED_USAGE_FIELDS = {
                "article": "articles_generated_this_month",
                "outline": "outlines_generated_this_month",
                "image": "images_generated_this_month",
                "social_post": "social_posts_generated_this_month",
            }
            usage_field = ALLOWED_USAGE_FIELDS.get(resource_type)
            if not usage_field:
                logger.warning(
                    "Unknown resource_type '%s' for limit check — denying", resource_type
                )
                return False  # API-M1: deny unknown resource types (fail closed)
            current_usage = getattr(user, usage_field, 0) or 0

            return current_usage < limit
        except Exception as e:
            logger.error("Failed to check user-level limit for user %s: %s", user_id, e)
            return False  # Fail closed

    async def _reset_user_usage_if_needed(self, user) -> bool:
        """Reset user-level monthly usage counters if the billing period has elapsed.

        Returns True if a reset was performed.
        """
        now = datetime.now(UTC)
        reset_date = user.usage_reset_date

        # If no reset date is set, initialise it to the first of next month
        # and reset counters since we have no record of when they were last reset.
        if reset_date is None:
            user.articles_generated_this_month = 0
            user.outlines_generated_this_month = 0
            user.images_generated_this_month = 0
            user.social_posts_generated_this_month = 0
            if now.month == 12:
                user.usage_reset_date = datetime(now.year + 1, 1, 1, tzinfo=UTC)
            else:
                user.usage_reset_date = datetime(now.year, now.month + 1, 1, tzinfo=UTC)
            # PROJ-13: commit immediately so concurrent requests see the updated reset_date
            await self.db.commit()
            # Re-load expired attributes so check_limit can read them after commit
            await self.db.refresh(user)
            logger.info("Initialized usage reset date and reset counters for user %s", user.id)
            return True

        # Ensure timezone-aware comparison
        if reset_date.tzinfo is None:
            reset_date = reset_date.replace(tzinfo=UTC)

        if now >= reset_date:
            user.articles_generated_this_month = 0
            user.outlines_generated_this_month = 0
            user.images_generated_this_month = 0
            user.social_posts_generated_this_month = 0
            # Set next reset to the first of the month after the current date
            if now.month == 12:
                user.usage_reset_date = datetime(now.year + 1, 1, 1, tzinfo=UTC)
            else:
                user.usage_reset_date = datetime(now.year, now.month + 1, 1, tzinfo=UTC)
            # PROJ-13: commit immediately so concurrent requests see the updated reset_date
            await self.db.commit()
            # Re-load expired attributes so check_limit can read them after commit
            await self.db.refresh(user)
            logger.info("Reset monthly usage counters for user %s", user.id)
            return True

        return False
