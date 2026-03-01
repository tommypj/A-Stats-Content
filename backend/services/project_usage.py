"""
Project usage service for tracking and enforcing project subscription limits.

Handles project-level usage limits for content generation based on
subscription tier, separate from individual user limits.
"""

import logging
from datetime import datetime, timezone
from typing import Dict
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.project import Project, ProjectMember
from infrastructure.database.models.user import SubscriptionTier
from api.schemas.project_billing import ProjectLimits, ProjectUsageStats

logger = logging.getLogger(__name__)


# Project tier limits configuration
# Project plans have higher limits than individual plans
PROJECT_TIER_LIMITS: Dict[str, Dict[str, int]] = {
    SubscriptionTier.FREE.value: {
        "articles_per_month": 3,
        "outlines_per_month": 3,
        "images_per_month": 3,
        "social_posts_per_month": 5,
        "max_members": 1,
    },
    SubscriptionTier.STARTER.value: {
        "articles_per_month": 30,
        "outlines_per_month": 30,
        "images_per_month": 10,
        "social_posts_per_month": 20,
        "max_members": 3,
    },
    SubscriptionTier.PROFESSIONAL.value: {
        "articles_per_month": 100,
        "outlines_per_month": 100,
        "images_per_month": 50,
        "social_posts_per_month": 100,
        "max_members": 10,
    },
    SubscriptionTier.ENTERPRISE.value: {
        "articles_per_month": 300,
        "outlines_per_month": 300,
        "images_per_month": 200,
        "social_posts_per_month": 300,
        "max_members": -1,  # unlimited members
    },
}


class ProjectUsageService:
    """
    Service for managing project usage tracking and limits.

    Provides methods to check limits, increment usage, and retrieve
    usage statistics for projects.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize project usage service.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_project(self, project_id: UUID) -> Project:
        """
        Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project model instance

        Raises:
            ValueError: If project not found
        """
        result = await self.db.execute(
            select(Project).where(Project.id == str(project_id))
        )
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        return project

    def get_project_limits(self, project: Project) -> ProjectLimits:
        """
        Get usage limits for a project based on subscription tier.

        Args:
            project: Project model instance

        Returns:
            ProjectLimits schema with limits for current tier
        """
        tier = project.subscription_tier
        # Treat expired subscriptions as free tier
        now = datetime.now(timezone.utc)
        if project.subscription_expires and project.subscription_expires < now:
            tier = SubscriptionTier.FREE.value
        limits = PROJECT_TIER_LIMITS.get(tier, PROJECT_TIER_LIMITS[SubscriptionTier.FREE.value])

        return ProjectLimits(
            articles_per_month=limits["articles_per_month"],
            outlines_per_month=limits["outlines_per_month"],
            images_per_month=limits["images_per_month"],
            social_posts_per_month=limits["social_posts_per_month"],
            max_members=limits["max_members"],
        )

    async def get_project_usage(self, project_id: UUID) -> ProjectUsageStats:
        """
        Get current usage statistics for a project.

        Args:
            project_id: Project ID

        Returns:
            ProjectUsageStats with current usage and limits
        """
        project = await self.get_project(project_id)
        limits = self.get_project_limits(project)

        # Count active members via SQL instead of loading all into memory
        count_result = await self.db.execute(
            select(func.count()).select_from(ProjectMember).where(
                ProjectMember.project_id == str(project_id),
                ProjectMember.deleted_at.is_(None),
            )
        )
        _raw_count = count_result.scalar()
        active_members_count = int(_raw_count) if _raw_count is not None else 0  # GEN-36: explicit int conversion

        return ProjectUsageStats(
            articles_used=project.articles_generated_this_month,
            articles_limit=limits.articles_per_month,
            outlines_used=project.outlines_generated_this_month,
            outlines_limit=limits.outlines_per_month,
            images_used=project.images_generated_this_month,
            images_limit=limits.images_per_month,
            social_posts_used=project.social_posts_generated_this_month,
            social_posts_limit=limits.social_posts_per_month,
            members_count=active_members_count,
            members_limit=limits.max_members,
            usage_reset_date=project.usage_reset_date,
        )

    async def check_project_limit(self, project_id: UUID, resource: str) -> bool:
        """
        Check if project can create more of a resource type.

        Args:
            project_id: Project ID
            resource: Resource type ('articles', 'outlines', 'images', 'members')

        Returns:
            True if project is within limits, False if limit reached

        Raises:
            ValueError: If resource type is invalid or project not found
        """
        # GEN-30: Use with_for_update(of=Project) to prevent TOCTOU — concurrent improve_article
        # requests that both pass the check before either increments the counter.
        # of=Project generates "FOR UPDATE OF projects" which locks only that table;
        # plain FOR UPDATE fails on LEFT OUTER JOINs that SQLAlchemy adds for eager loads.
        result = await self.db.execute(
            select(Project).where(Project.id == str(project_id)).with_for_update(of=Project)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        limits = self.get_project_limits(project)

        # Map resource type to (current_usage, limit).
        # Members count is computed lazily to avoid triggering a
        # relationship lazy-load inside an async session context.
        resource_map: dict[str, tuple[int, int]] = {
            "articles": (
                project.articles_generated_this_month,
                limits.articles_per_month,
            ),
            "outlines": (
                project.outlines_generated_this_month,
                limits.outlines_per_month,
            ),
            "images": (
                project.images_generated_this_month,
                limits.images_per_month,
            ),
            "social_posts": (
                project.social_posts_generated_this_month,
                limits.social_posts_per_month,
            ),
        }

        valid_resources = list(resource_map.keys()) + ["members"]
        if resource not in valid_resources:
            raise ValueError(
                f"Invalid resource type: {resource}. "
                f"Must be one of: {', '.join(valid_resources)}"
            )

        # For members, query the count explicitly to avoid async lazy-load issues
        if resource == "members":
            from infrastructure.database.models.project import ProjectMember
            count_result = await self.db.execute(
                select(func.count()).select_from(ProjectMember).where(
                    ProjectMember.project_id == str(project_id),
                    ProjectMember.deleted_at.is_(None),
                )
            )
            _raw_members = count_result.scalar()
            current_members = int(_raw_members) if _raw_members is not None else 0  # GEN-36: explicit int conversion
            resource_map["members"] = (current_members, limits.max_members)

        current_usage, limit = resource_map[resource]

        # -1 means unlimited
        if limit == -1:
            return True

        # Check if within limit
        can_create = current_usage < limit

        if not can_create:
            logger.warning(
                f"Project {project_id} has reached limit for {resource}: "
                f"{current_usage}/{limit}"
            )

        return can_create

    async def increment_usage(self, project_id: UUID, resource: str) -> None:
        """
        Atomically increment project usage counter for a resource.

        Uses SQL-level increment to avoid read-modify-write race conditions
        under concurrent requests.

        Args:
            project_id: Project ID
            resource: Resource type ('articles', 'outlines', 'images')

        Raises:
            ValueError: If resource type is invalid or project not found
        """
        # Map resource type to column
        column_map = {
            "articles": Project.articles_generated_this_month,
            "outlines": Project.outlines_generated_this_month,
            "images": Project.images_generated_this_month,
            "social_posts": Project.social_posts_generated_this_month,
        }
        column = column_map.get(resource)
        if column is None:
            raise ValueError(
                f"Invalid resource type: {resource}. "
                f"Must be one of: articles, outlines, images, social_posts"
            )

        # Atomic SQL increment — no read-modify-write race
        values = {column.key: column + 1}

        # Set usage reset date if not already set
        now = datetime.now(timezone.utc)
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)

        result = await self.db.execute(
            update(Project)
            .where(Project.id == str(project_id))
            .where(Project.usage_reset_date.is_(None))
            .values(**values, usage_reset_date=next_month)
        )

        if result.rowcount == 0:
            # usage_reset_date was already set — just increment the counter
            await self.db.execute(
                update(Project)
                .where(Project.id == str(project_id))
                .values(**values)
            )

        await self.db.flush()

        logger.info(f"Incremented {resource} usage for project {project_id}")

    async def reset_project_usage_if_needed(self, project_id: UUID) -> bool:
        """
        Reset project usage counters if reset date has passed.

        This should be called by a background job or at the start of
        operations to ensure usage is reset monthly.

        Args:
            project_id: Project ID

        Returns:
            True if usage was reset, False otherwise
        """
        # GEN-24: Use with_for_update(of=_Project) to prevent race condition where two concurrent
        # requests both read stale usage_reset_date and both attempt to reset counters.
        # of=_Project generates "FOR UPDATE OF projects" — safe with the LEFT OUTER JOIN
        # that SQLAlchemy adds when eager-loading the owner relationship.
        from infrastructure.database.models.project import Project as _Project
        result = await self.db.execute(
            select(_Project).where(_Project.id == str(project_id)).with_for_update(of=_Project)
        )
        project = result.scalar_one_or_none()
        if not project:
            return False

        # Check if reset is needed
        if not project.usage_reset_date:
            return False

        now = datetime.now(timezone.utc)
        if now < project.usage_reset_date:
            return False

        # Reset usage counters
        project.articles_generated_this_month = 0
        project.outlines_generated_this_month = 0
        project.images_generated_this_month = 0
        project.social_posts_generated_this_month = 0

        # Calculate next reset date (first day of next month)
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        project.usage_reset_date = next_month

        await self.db.flush()

        logger.info(f"Reset usage counters for project {project_id}")
        return True
