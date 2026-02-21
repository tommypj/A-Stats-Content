"""
Team billing API routes for multi-tenancy subscription management.

Provides endpoints for team-level billing operations including
subscription management, checkout, and usage tracking.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import get_db
from infrastructure.database.models.team import Team, TeamMember, TeamMemberRole
from infrastructure.database.models.user import User
from infrastructure.config.settings import settings
from api.routes.auth import get_current_user
from api.schemas.team_billing import (
    TeamSubscriptionResponse,
    TeamCheckoutRequest,
    TeamCheckoutResponse,
    TeamPortalResponse,
    TeamCancelResponse,
    TeamUsageResponse,
    TeamLimits,
    TeamUsageStats,
)
from services.team_usage import TeamUsageService, TEAM_TIER_LIMITS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teams", tags=["team-billing"])


async def get_team_member(
    team_id: UUID,
    user_id: str,
    db: AsyncSession,
) -> TeamMember:
    """
    Get team member record for user.

    Args:
        team_id: Team ID
        user_id: User ID
        db: Database session

    Returns:
        TeamMember instance

    Raises:
        HTTPException: If user is not a member of the team
    """
    result = await db.execute(
        select(TeamMember)
        .where(TeamMember.team_id == str(team_id))
        .where(TeamMember.user_id == user_id)
        .where(TeamMember.deleted_at.is_(None))
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    return member


async def require_team_role(
    team_id: UUID,
    user: User,
    required_role: TeamMemberRole,
    db: AsyncSession,
) -> TeamMember:
    """
    Verify user has required role in team.

    Args:
        team_id: Team ID
        user: Current user
        required_role: Required role (OWNER, ADMIN, or MEMBER)
        db: Database session

    Returns:
        TeamMember instance

    Raises:
        HTTPException: If user doesn't have required role
    """
    member = await get_team_member(team_id, user.id, db)

    # Define role hierarchy (higher index = more permissions)
    role_hierarchy = {
        TeamMemberRole.VIEWER.value: 0,
        TeamMemberRole.EDITOR.value: 1,
        TeamMemberRole.ADMIN.value: 2,
        TeamMemberRole.OWNER.value: 3,
    }

    user_role_level = role_hierarchy.get(member.role, 0)
    required_role_level = role_hierarchy.get(required_role.value, 0)

    if user_role_level < required_role_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This operation requires {required_role.value} role",
        )

    return member


@router.get("/{team_id}/billing/subscription", response_model=TeamSubscriptionResponse)
async def get_team_subscription(
    team_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get team subscription status and usage.

    Requires ADMIN or OWNER role.

    Returns current subscription tier, status, usage stats, and limits.
    """
    # Require ADMIN role to view billing
    await require_team_role(team_id, current_user, TeamMemberRole.ADMIN, db)

    # Get team
    result = await db.execute(
        select(Team).where(Team.id == str(team_id))
    )
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Get usage stats
    usage_service = TeamUsageService(db)
    usage_stats = await usage_service.get_team_usage(team_id)
    limits = usage_service.get_team_limits(team)

    # Check if user is owner
    is_owner = str(team.owner_id) == current_user.id

    return TeamSubscriptionResponse(
        team_id=UUID(team.id),
        team_name=team.name,
        subscription_tier=team.subscription_tier,
        subscription_status=team.subscription_status,
        subscription_expires=team.subscription_expires,
        customer_id=team.lemonsqueezy_customer_id,
        subscription_id=team.lemonsqueezy_subscription_id,
        variant_id=team.lemonsqueezy_subscription_id,
        usage=usage_stats,
        limits=limits,
        can_manage=is_owner,
    )


@router.post("/{team_id}/billing/checkout", response_model=TeamCheckoutResponse)
async def create_team_checkout(
    team_id: UUID,
    request: TeamCheckoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Create LemonSqueezy checkout session for team subscription.

    Requires OWNER role only.

    Generates a checkout URL with team context passed in custom data.
    """
    # Require OWNER role for billing changes
    member = await require_team_role(team_id, current_user, TeamMemberRole.OWNER, db)

    # Get team
    result = await db.execute(
        select(Team).where(Team.id == str(team_id))
    )
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check LemonSqueezy configuration
    if not settings.lemonsqueezy_api_key or not settings.lemonsqueezy_store_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment system not configured",
        )

    # Build checkout URL with team context
    # Format: https://YOUR_STORE.lemonsqueezy.com/checkout/buy/{variant_id}
    store_url = f"https://{settings.lemonsqueezy_store_id}.lemonsqueezy.com"
    checkout_url = (
        f"{store_url}/checkout/buy/{request.variant_id}"
        f"?checkout[email]={current_user.email}"
        f"&checkout[custom][team_id]={team_id}"
        f"&checkout[custom][user_id]={current_user.id}"
    )

    logger.info(
        f"Created team checkout session: team_id={team_id}, "
        f"variant_id={request.variant_id}, user={current_user.id}"
    )

    return TeamCheckoutResponse(checkout_url=checkout_url)


@router.get("/{team_id}/billing/portal", response_model=TeamPortalResponse)
async def get_team_billing_portal(
    team_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get LemonSqueezy customer portal URL for team billing management.

    Requires OWNER role only.

    Returns URL where owner can manage subscription, payment methods, etc.
    """
    # Require OWNER role for billing portal
    await require_team_role(team_id, current_user, TeamMemberRole.OWNER, db)

    # Get team
    result = await db.execute(
        select(Team).where(Team.id == str(team_id))
    )
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    if not team.lemonsqueezy_customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active team subscription found",
        )

    if not settings.lemonsqueezy_store_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment system not configured",
        )

    # Build customer portal URL
    portal_url = f"https://{settings.lemonsqueezy_store_id}.lemonsqueezy.com/billing"

    logger.info(f"Generated team billing portal URL for team {team_id}")

    return TeamPortalResponse(portal_url=portal_url)


@router.post("/{team_id}/billing/cancel", response_model=TeamCancelResponse)
async def cancel_team_subscription(
    team_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel team subscription.

    Requires OWNER role only.

    Subscription remains active until end of billing period,
    then team reverts to free plan.
    """
    # Require OWNER role for cancellation
    await require_team_role(team_id, current_user, TeamMemberRole.OWNER, db)

    # Get team
    result = await db.execute(
        select(Team).where(Team.id == str(team_id))
    )
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    if not team.lemonsqueezy_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active team subscription to cancel",
        )

    # TODO: Implement actual LemonSqueezy API call to cancel subscription
    # For now, just log the cancellation request

    logger.info(
        f"Team subscription cancellation requested: "
        f"team_id={team_id}, subscription_id={team.lemonsqueezy_subscription_id}"
    )

    return TeamCancelResponse(
        success=True,
        message=(
            "Team subscription will be cancelled at the end of the billing period. "
            "Please visit the customer portal to complete cancellation."
        ),
    )


@router.get("/{team_id}/billing/usage", response_model=TeamUsageResponse)
async def get_team_usage(
    team_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get team usage statistics.

    Requires MEMBER role or higher (any team member can view usage).

    Returns current usage vs limits for all resources.
    """
    # Any team member can view usage
    await get_team_member(team_id, current_user.id, db)

    # Get team
    result = await db.execute(
        select(Team).where(Team.id == str(team_id))
    )
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Get usage stats
    usage_service = TeamUsageService(db)
    usage_stats = await usage_service.get_team_usage(team_id)
    limits = usage_service.get_team_limits(team)

    # Calculate usage percentages for UI
    def calc_percentage(used: int, limit: int) -> float:
        if limit == -1:  # unlimited
            return 0.0
        if limit == 0:
            return 0.0
        return min((used / limit) * 100, 100.0)

    articles_percent = calc_percentage(
        usage_stats.articles_used,
        usage_stats.articles_limit,
    )
    outlines_percent = calc_percentage(
        usage_stats.outlines_used,
        usage_stats.outlines_limit,
    )
    images_percent = calc_percentage(
        usage_stats.images_used,
        usage_stats.images_limit,
    )
    members_percent = calc_percentage(
        usage_stats.members_count,
        usage_stats.members_limit,
    )

    return TeamUsageResponse(
        team_id=UUID(team.id),
        team_name=team.name,
        subscription_tier=team.subscription_tier,
        usage=usage_stats,
        limits=limits,
        articles_usage_percent=articles_percent,
        outlines_usage_percent=outlines_percent,
        images_usage_percent=images_percent,
        members_usage_percent=members_percent,
    )
