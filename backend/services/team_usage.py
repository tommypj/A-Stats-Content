"""
Team usage service for tracking and enforcing team subscription limits.

Handles team-level usage limits for content generation based on
subscription tier, separate from individual user limits.
"""

import logging
from datetime import datetime, timezone
from typing import Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.team import Team
from infrastructure.database.models.user import SubscriptionTier
from api.schemas.team_billing import TeamLimits, TeamUsageStats

logger = logging.getLogger(__name__)


# Team tier limits configuration
# Team plans have higher limits than individual plans
TEAM_TIER_LIMITS: Dict[str, Dict[str, int]] = {
    SubscriptionTier.FREE.value: {
        "articles_per_month": 10,
        "outlines_per_month": 20,
        "images_per_month": 5,
        "max_members": 3,
    },
    SubscriptionTier.STARTER.value: {
        "articles_per_month": 50,
        "outlines_per_month": 100,
        "images_per_month": 25,
        "max_members": 5,
    },
    SubscriptionTier.PROFESSIONAL.value: {
        "articles_per_month": 200,
        "outlines_per_month": 400,
        "images_per_month": 100,
        "max_members": 15,
    },
    SubscriptionTier.ENTERPRISE.value: {
        "articles_per_month": -1,  # -1 = unlimited
        "outlines_per_month": -1,
        "images_per_month": -1,
        "max_members": -1,  # unlimited members
    },
}


class TeamUsageService:
    """
    Service for managing team usage tracking and limits.

    Provides methods to check limits, increment usage, and retrieve
    usage statistics for teams.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize team usage service.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_team(self, team_id: UUID) -> Team:
        """
        Get team by ID.

        Args:
            team_id: Team ID

        Returns:
            Team model instance

        Raises:
            ValueError: If team not found
        """
        result = await self.db.execute(
            select(Team).where(Team.id == str(team_id))
        )
        team = result.scalar_one_or_none()

        if not team:
            raise ValueError(f"Team {team_id} not found")

        return team

    def get_team_limits(self, team: Team) -> TeamLimits:
        """
        Get usage limits for a team based on subscription tier.

        Args:
            team: Team model instance

        Returns:
            TeamLimits schema with limits for current tier
        """
        tier = team.subscription_tier
        limits = TEAM_TIER_LIMITS.get(tier, TEAM_TIER_LIMITS[SubscriptionTier.FREE.value])

        return TeamLimits(
            articles_per_month=limits["articles_per_month"],
            outlines_per_month=limits["outlines_per_month"],
            images_per_month=limits["images_per_month"],
            max_members=limits["max_members"],
        )

    async def get_team_usage(self, team_id: UUID) -> TeamUsageStats:
        """
        Get current usage statistics for a team.

        Args:
            team_id: Team ID

        Returns:
            TeamUsageStats with current usage and limits
        """
        team = await self.get_team(team_id)
        limits = self.get_team_limits(team)

        # Count active members
        active_members_count = len([m for m in team.members if m.deleted_at is None])

        return TeamUsageStats(
            articles_used=team.articles_generated_this_month,
            articles_limit=limits.articles_per_month,
            outlines_used=team.outlines_generated_this_month,
            outlines_limit=limits.outlines_per_month,
            images_used=team.images_generated_this_month,
            images_limit=limits.images_per_month,
            members_count=active_members_count,
            members_limit=limits.max_members,
            usage_reset_date=team.usage_reset_date,
        )

    async def check_team_limit(self, team_id: UUID, resource: str) -> bool:
        """
        Check if team can create more of a resource type.

        Args:
            team_id: Team ID
            resource: Resource type ('articles', 'outlines', 'images', 'members')

        Returns:
            True if team is within limits, False if limit reached

        Raises:
            ValueError: If resource type is invalid or team not found
        """
        team = await self.get_team(team_id)
        limits = self.get_team_limits(team)

        # Map resource type to usage field and limit
        resource_map = {
            "articles": (
                team.articles_generated_this_month,
                limits.articles_per_month,
            ),
            "outlines": (
                team.outlines_generated_this_month,
                limits.outlines_per_month,
            ),
            "images": (
                team.images_generated_this_month,
                limits.images_per_month,
            ),
            "members": (
                len([m for m in team.members if m.deleted_at is None]),
                limits.max_members,
            ),
        }

        if resource not in resource_map:
            raise ValueError(
                f"Invalid resource type: {resource}. "
                f"Must be one of: {', '.join(resource_map.keys())}"
            )

        current_usage, limit = resource_map[resource]

        # -1 means unlimited
        if limit == -1:
            return True

        # Check if within limit
        can_create = current_usage < limit

        if not can_create:
            logger.warning(
                f"Team {team_id} has reached limit for {resource}: "
                f"{current_usage}/{limit}"
            )

        return can_create

    async def increment_usage(self, team_id: UUID, resource: str) -> None:
        """
        Increment team usage counter for a resource.

        Args:
            team_id: Team ID
            resource: Resource type ('articles', 'outlines', 'images')

        Raises:
            ValueError: If resource type is invalid or team not found
        """
        team = await self.get_team(team_id)

        # Map resource type to usage field
        if resource == "articles":
            team.articles_generated_this_month += 1
        elif resource == "outlines":
            team.outlines_generated_this_month += 1
        elif resource == "images":
            team.images_generated_this_month += 1
        else:
            raise ValueError(
                f"Invalid resource type: {resource}. "
                f"Must be one of: articles, outlines, images"
            )

        # Set usage reset date if not set (first day of next month)
        if not team.usage_reset_date:
            now = datetime.now(timezone.utc)
            # Calculate first day of next month
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_month = now.replace(month=now.month + 1, day=1)
            team.usage_reset_date = next_month

        await self.db.commit()
        await self.db.refresh(team)

        logger.info(
            f"Incremented {resource} usage for team {team_id}: "
            f"{getattr(team, f'{resource}_generated_this_month')}"
        )

    async def reset_team_usage_if_needed(self, team_id: UUID) -> bool:
        """
        Reset team usage counters if reset date has passed.

        This should be called by a background job or at the start of
        operations to ensure usage is reset monthly.

        Args:
            team_id: Team ID

        Returns:
            True if usage was reset, False otherwise
        """
        team = await self.get_team(team_id)

        # Check if reset is needed
        if not team.usage_reset_date:
            return False

        now = datetime.now(timezone.utc)
        if now < team.usage_reset_date:
            return False

        # Reset usage counters
        team.articles_generated_this_month = 0
        team.outlines_generated_this_month = 0
        team.images_generated_this_month = 0

        # Calculate next reset date (first day of next month)
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        team.usage_reset_date = next_month

        await self.db.commit()
        await self.db.refresh(team)

        logger.info(f"Reset usage counters for team {team_id}")
        return True
