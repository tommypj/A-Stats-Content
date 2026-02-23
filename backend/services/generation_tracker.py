"""
Generation tracking service.
Logs all generation events, creates admin alerts on failure,
and increments project usage counters only on success.
"""

import logging
import time
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    ) -> bool:
        """Check if the project can generate more of this resource type.
        Returns True if allowed (or no project context). False if limit reached."""
        if not project_id:
            return True  # No project = no limit enforcement (personal workspace)

        try:
            usage_service = ProjectUsageService(self.db)
            # Reset usage if needed
            await usage_service.reset_project_usage_if_needed(project_id)
            # Check limit — resource_type should be plural: 'articles', 'outlines', 'images'
            return await usage_service.check_project_limit(project_id, resource_type + "s")
        except Exception as e:
            logger.warning("Failed to check limit for project %s: %s", project_id, e)
            return True  # Fail open — don't block generation if limit check fails
