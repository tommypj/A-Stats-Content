"""
Generation tracking service.
Logs all generation events, creates admin alerts on failure,
and increments project usage counters only on success.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.config.settings import settings
from infrastructure.database.models.generation import GenerationLog, AdminAlert
from infrastructure.database.models.project import Project
from services.project_usage import ProjectUsageService

logger = logging.getLogger(__name__)


class GenerationTracker:
    """Tracks generation events and manages usage billing."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_start(
        self,
        user_id: str,
        project_id: Optional[str],
        resource_type: str,
        resource_id: str,
        input_metadata: Optional[dict] = None,
    ) -> GenerationLog:
        """Log the start of a generation. Returns the log entry for later update."""
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
        self.db.add(log)
        await self.db.flush()
        return log

    async def log_success(
        self,
        log_id: str,
        ai_model: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Mark generation as successful and increment usage."""
        result = await self.db.execute(
            select(GenerationLog).where(GenerationLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            logger.warning("Generation log %s not found for success update", log_id)
            return

        log.status = "success"
        log.ai_model = ai_model
        log.duration_ms = duration_ms
        log.cost_credits = 1

        # Increment project usage counter if project exists
        if log.project_id:
            try:
                usage_service = ProjectUsageService(self.db)
                await usage_service.increment_usage(log.project_id, log.resource_type + "s")
            except Exception as e:
                logger.warning("Failed to increment usage for project %s: %s", log.project_id, e)

        await self.db.flush()

    async def log_failure(
        self,
        log_id: str,
        error_message: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Mark generation as failed. Creates an admin alert. Does NOT increment usage."""
        result = await self.db.execute(
            select(GenerationLog).where(GenerationLog.id == log_id)
        )
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
        await self.db.flush()

    async def check_limit(
        self,
        project_id: Optional[str],
        resource_type: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Check if the project (or user) can generate more of this resource type.
        Returns True if allowed. False if limit reached.

        NOTE: Temporarily bypassed while usage counter reset logic is
        being stabilised.  Re-enable once billing is fully wired up.
        """
        return True  # TODO: re-enable after billing integration

        entity_id = project_id or user_id

        # Redis-based atomic counter check to prevent race conditions.
        # If Redis is configured, use an atomic increment to verify the quota
        # before falling through to the slower DB-based check.
        if settings.redis_url and entity_id:
            try:
                import redis.asyncio as aioredis
                r = aioredis.from_url(settings.redis_url)
                key = (
                    f"gen_limit:{entity_id}:{resource_type}:"
                    f"{datetime.now(timezone.utc).strftime('%Y-%m')}"
                )
                current = await r.incr(key)
                if current == 1:
                    await r.expire(key, 86400 * 35)  # expire after 35 days
                await r.aclose()

                # We need the plan limit to compare against.
                # Derive it from the project or user record.
                limit = await self._get_limit(project_id, user_id, resource_type)
                if limit is not None:
                    if limit == -1:
                        return True  # unlimited
                    if current > limit:
                        return False
                    return True
                # If we couldn't determine the limit, fall through to DB check.
            except Exception as e:
                logger.warning(
                    "Redis quota check failed for %s, falling back to DB: %s",
                    entity_id,
                    e,
                )
                # Fall through to DB-based check below.

        if not project_id:
            # Check user-level limits for personal workspace
            if not user_id:
                return True  # No user context — fail open

            try:
                from infrastructure.database.models.user import User
                user_result = await self.db.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    return False

                # Reset monthly counters if we've crossed into a new month
                await self._reset_user_usage_if_needed(user)

                # Get plan limits
                from core.plans import PLANS
                plan = PLANS.get(user.subscription_tier or "free", PLANS["free"])
                limits = plan.get("limits", {})

                # Map resource_type to limit key
                limit_key = f"{resource_type}s_per_month"
                limit = limits.get(limit_key, 0)

                if limit == -1:
                    return True  # unlimited

                # Get current month's usage count for this user
                usage_field = f"{resource_type}s_generated_this_month"
                current_usage = getattr(user, usage_field, 0) or 0

                return current_usage < limit
            except Exception as e:
                logger.error("Failed to check user-level limit for user %s: %s", user_id, e)
                return True  # Fail open — don't block generation if limit check fails

        try:
            usage_service = ProjectUsageService(self.db)
            # Reset usage if needed
            await usage_service.reset_project_usage_if_needed(project_id)
            # Check limit — resource_type should be plural: 'articles', 'outlines', 'images'
            return await usage_service.check_project_limit(project_id, resource_type + "s")
        except Exception as e:
            logger.error("Failed to check project usage limit: %s", str(e))
            return False  # fail closed — deny generation when limits can't be verified

    async def _reset_user_usage_if_needed(self, user) -> bool:
        """Reset user-level monthly usage counters if the billing period has elapsed.

        Returns True if a reset was performed.
        """
        now = datetime.now(timezone.utc)
        reset_date = user.usage_reset_date

        # If no reset date is set, initialise it to the first of next month
        # and reset counters since we have no record of when they were last reset.
        if reset_date is None:
            user.articles_generated_this_month = 0
            user.outlines_generated_this_month = 0
            user.images_generated_this_month = 0
            if now.month == 12:
                user.usage_reset_date = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                user.usage_reset_date = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
            await self.db.flush()
            logger.info("Initialized usage reset date and reset counters for user %s", user.id)
            return True

        # Ensure timezone-aware comparison
        if reset_date.tzinfo is None:
            reset_date = reset_date.replace(tzinfo=timezone.utc)

        if now >= reset_date:
            user.articles_generated_this_month = 0
            user.outlines_generated_this_month = 0
            user.images_generated_this_month = 0
            # Set next reset to the first of the month after the current date
            if now.month == 12:
                user.usage_reset_date = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                user.usage_reset_date = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
            await self.db.flush()
            logger.info("Reset monthly usage counters for user %s", user.id)
            return True

        return False

    async def _get_limit(
        self,
        project_id: Optional[str],
        user_id: Optional[str],
        resource_type: str,
    ) -> Optional[int]:
        """Return the numeric generation limit for the given context, or None if unknown.

        Returns -1 for unlimited, a non-negative int for a fixed cap, or None if the
        limit cannot be determined (caller should fall back to DB-based check).
        """
        try:
            if project_id:
                from services.project_usage import ProjectUsageService, PROJECT_TIER_LIMITS
                result = await self.db.execute(
                    select(Project).where(Project.id == project_id)
                )
                project = result.scalar_one_or_none()
                if not project:
                    return None
                tier = project.subscription_tier or "free"
                tier_limits = PROJECT_TIER_LIMITS.get(tier, PROJECT_TIER_LIMITS["free"])
                resource_key = resource_type + "s_per_month"
                return tier_limits.get(resource_key)
            elif user_id:
                from infrastructure.database.models.user import User
                from core.plans import PLANS
                user_result = await self.db.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    return None
                plan = PLANS.get(user.subscription_tier or "free", PLANS["free"])
                limits = plan.get("limits", {})
                limit_key = f"{resource_type}s_per_month"
                return limits.get(limit_key)
        except Exception as e:
            logger.warning("Failed to determine limit for Redis check: %s", e)
        return None
