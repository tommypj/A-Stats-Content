"""
Project billing API routes for multi-tenancy subscription management.

Provides endpoints for project-level billing operations including
subscription management, checkout, and usage tracking.
"""

import logging
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import get_db
from infrastructure.database.models.project import Project, ProjectMember, ProjectMemberRole
from infrastructure.database.models.user import User
from infrastructure.config.settings import settings
from api.routes.auth import get_current_user
from api.schemas.project_billing import (
    ProjectSubscriptionResponse,
    ProjectCheckoutRequest,
    ProjectCheckoutResponse,
    ProjectPortalResponse,
    ProjectCancelResponse,
    ProjectUsageResponse,
    ProjectLimits,
    ProjectUsageStats,
)
from services.project_usage import ProjectUsageService, PROJECT_TIER_LIMITS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["project-billing"])


async def get_project_member(
    project_id: UUID,
    user_id: str,
    db: AsyncSession,
) -> ProjectMember:
    """
    Get project member record for user.

    Args:
        project_id: Project ID
        user_id: User ID
        db: Database session

    Returns:
        ProjectMember instance

    Raises:
        HTTPException: If user is not a member of the project
    """
    result = await db.execute(
        select(ProjectMember)
        .where(ProjectMember.project_id == str(project_id))
        .where(ProjectMember.user_id == user_id)
        .where(ProjectMember.deleted_at.is_(None))
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this project",
        )

    return member


async def require_project_role(
    project_id: UUID,
    user: User,
    required_role: ProjectMemberRole,
    db: AsyncSession,
) -> ProjectMember:
    """
    Verify user has required role in project.

    Args:
        project_id: Project ID
        user: Current user
        required_role: Required role (OWNER, ADMIN, or MEMBER)
        db: Database session

    Returns:
        ProjectMember instance

    Raises:
        HTTPException: If user doesn't have required role
    """
    member = await get_project_member(project_id, user.id, db)

    # Define role hierarchy (higher index = more permissions)
    role_hierarchy = {
        ProjectMemberRole.VIEWER.value: 0,
        ProjectMemberRole.EDITOR.value: 1,
        ProjectMemberRole.ADMIN.value: 2,
        ProjectMemberRole.OWNER.value: 3,
    }

    user_role_level = role_hierarchy.get(member.role, 0)
    required_role_level = role_hierarchy.get(required_role.value, 0)

    if user_role_level < required_role_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This operation requires {required_role.value} role",
        )

    return member


@router.get("/{project_id}/billing/subscription", response_model=ProjectSubscriptionResponse)
async def get_project_subscription(
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get project subscription status and usage.

    Requires ADMIN or OWNER role.

    Returns current subscription tier, status, usage stats, and limits.
    """
    # Require ADMIN role to view billing
    await require_project_role(project_id, current_user, ProjectMemberRole.ADMIN, db)

    # Get project
    result = await db.execute(
        select(Project).where(Project.id == str(project_id))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get usage stats
    usage_service = ProjectUsageService(db)
    usage_stats = await usage_service.get_project_usage(project_id)
    limits = usage_service.get_project_limits(project)

    # Check if user is owner
    is_owner = str(project.owner_id) == current_user.id

    return ProjectSubscriptionResponse(
        project_id=UUID(project.id),
        project_name=project.name,
        subscription_tier=project.subscription_tier,
        subscription_status=project.subscription_status,
        subscription_expires=project.subscription_expires,
        customer_id=project.lemonsqueezy_customer_id,
        subscription_id=project.lemonsqueezy_subscription_id,
        variant_id=project.lemonsqueezy_subscription_id,
        usage=usage_stats,
        limits=limits,
        can_manage=is_owner,
    )


@router.post("/{project_id}/billing/checkout", response_model=ProjectCheckoutResponse)
async def create_project_checkout(
    project_id: UUID,
    request: ProjectCheckoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Create LemonSqueezy checkout session for project subscription.

    Requires OWNER role only.

    Generates a checkout URL with project context passed in custom data.
    """
    # Require OWNER role for billing changes
    member = await require_project_role(project_id, current_user, ProjectMemberRole.OWNER, db)

    # Get project
    result = await db.execute(
        select(Project).where(Project.id == str(project_id))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check LemonSqueezy configuration
    if not settings.lemonsqueezy_api_key or not settings.lemonsqueezy_store_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment system not configured",
        )

    # Build checkout URL with project context
    # Format: https://YOUR_STORE.lemonsqueezy.com/checkout/buy/{variant_id}
    store_url = f"https://{settings.lemonsqueezy_store_id}.lemonsqueezy.com"
    checkout_url = (
        f"{store_url}/checkout/buy/{request.variant_id}"
        f"?checkout[email]={current_user.email}"
        f"&checkout[custom][project_id]={project_id}"
        f"&checkout[custom][user_id]={current_user.id}"
    )

    logger.info(
        f"Created project checkout session: project_id={project_id}, "
        f"variant_id={request.variant_id}, user={current_user.id}"
    )

    return ProjectCheckoutResponse(checkout_url=checkout_url)


@router.get("/{project_id}/billing/portal", response_model=ProjectPortalResponse)
async def get_project_billing_portal(
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get LemonSqueezy customer portal URL for project billing management.

    Requires OWNER role only.

    Returns URL where owner can manage subscription, payment methods, etc.
    """
    # Require OWNER role for billing portal
    await require_project_role(project_id, current_user, ProjectMemberRole.OWNER, db)

    # Get project
    result = await db.execute(
        select(Project).where(Project.id == str(project_id))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not project.lemonsqueezy_customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active project subscription found",
        )

    if not settings.lemonsqueezy_store_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment system not configured",
        )

    # Build customer portal URL
    portal_url = f"https://{settings.lemonsqueezy_store_id}.lemonsqueezy.com/billing"

    logger.info(f"Generated project billing portal URL for project {project_id}")

    return ProjectPortalResponse(portal_url=portal_url)


@router.post("/{project_id}/billing/cancel", response_model=ProjectCancelResponse)
async def cancel_project_subscription(
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel project subscription.

    Requires OWNER role only.

    Subscription remains active until end of billing period,
    then project reverts to free plan.
    """
    # Require OWNER role for cancellation
    await require_project_role(project_id, current_user, ProjectMemberRole.OWNER, db)

    # Get project
    result = await db.execute(
        select(Project).where(Project.id == str(project_id))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not project.lemonsqueezy_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active project subscription to cancel",
        )

    logger.info(
        f"Project subscription cancellation requested: "
        f"project_id={project_id}, subscription_id={project.lemonsqueezy_subscription_id}"
    )

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"https://api.lemonsqueezy.com/v1/subscriptions/{project.lemonsqueezy_subscription_id}",
            headers={
                "Authorization": f"Bearer {settings.lemonsqueezy_api_key}",
                "Accept": "application/vnd.api+json",
            },
        )
        if response.status_code not in (200, 204):
            logger.error(
                "LemonSqueezy cancel failed for project %s: %s %s",
                project_id,
                response.status_code,
                response.text,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to cancel project subscription. Please try again or contact support.",
            )

    return ProjectCancelResponse(
        success=True,
        message="Project subscription will be cancelled at the end of the billing period.",
    )


@router.get("/{project_id}/billing/usage", response_model=ProjectUsageResponse)
async def get_project_usage(
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get project usage statistics.

    Requires MEMBER role or higher (any project member can view usage).

    Returns current usage vs limits for all resources.
    """
    # Any project member can view usage
    await get_project_member(project_id, current_user.id, db)

    # Get project
    result = await db.execute(
        select(Project).where(Project.id == str(project_id))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get usage stats
    usage_service = ProjectUsageService(db)
    usage_stats = await usage_service.get_project_usage(project_id)
    limits = usage_service.get_project_limits(project)

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

    return ProjectUsageResponse(
        project_id=UUID(project.id),
        project_name=project.name,
        subscription_tier=project.subscription_tier,
        usage=usage_stats,
        limits=limits,
        articles_usage_percent=articles_percent,
        outlines_usage_percent=outlines_percent,
        images_usage_percent=images_percent,
        members_usage_percent=members_percent,
    )
