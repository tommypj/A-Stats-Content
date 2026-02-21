"""
Team management API routes for multi-tenancy.
"""

from datetime import datetime
from typing import Annotated, Optional, List
import re

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_, update as sql_update, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.connection import get_db
from infrastructure.database.models.user import User
from infrastructure.database.models.team import Team, TeamMember, TeamMemberRole
from api.routes.auth import get_current_user
from api.deps_team import (
    get_team_by_id,
    get_team_member,
    require_team_membership,
    require_team_admin,
    require_team_owner,
)
from api.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamWithMemberRoleResponse,
    TeamListResponse,
    TeamDetailResponse,
    TeamDeleteResponse,
    SwitchTeamRequest,
    SwitchTeamResponse,
    CurrentTeamResponse,
    TeamMemberResponse,
    TeamMembersListResponse,
    AddMemberRequest,
    AddMemberResponse,
    UpdateMemberRoleRequest,
    UpdateMemberRoleResponse,
    RemoveMemberResponse,
    LeaveTeamResponse,
    TransferOwnershipRequest,
    TransferOwnershipResponse,
)

router = APIRouter(prefix="/teams", tags=["Teams"])


# =============================================================================
# Helper Functions
# =============================================================================

def generate_unique_slug(name: str) -> str:
    """Generate a URL-friendly slug from team name."""
    slug = name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    slug = slug.strip('-')
    slug = slug[:100]
    return slug


async def ensure_unique_slug(db: AsyncSession, slug: str, team_id: Optional[str] = None) -> str:
    """Ensure slug is unique by appending number if necessary."""
    original_slug = slug
    counter = 1

    while True:
        stmt = select(Team).where(Team.slug == slug)
        if team_id:
            stmt = stmt.where(Team.id != team_id)

        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            return slug

        slug = f"{original_slug}-{counter}"
        counter += 1


# =============================================================================
# Team CRUD
# =============================================================================

@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    data: TeamCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new team.

    The current user becomes the owner of the team.
    Team is initialized with free tier subscription.
    """
    # Generate slug if not provided
    slug = data.slug or generate_unique_slug(data.name)

    # Ensure slug is unique
    slug = await ensure_unique_slug(db, slug)

    # Create team
    team = Team(
        name=data.name,
        slug=slug,
        description=data.description,
        avatar_url=getattr(data, 'logo_url', None),
        owner_id=current_user.id,
        subscription_tier="free",
        subscription_status="active",
        max_members=5,  # Free tier default
    )

    db.add(team)
    await db.flush()  # Get team ID

    # Add owner as team member
    member = TeamMember(
        team_id=team.id,
        user_id=current_user.id,
        role=TeamMemberRole.OWNER.value,
        invited_by=None,  # Self-created
        joined_at=datetime.now(),
    )

    db.add(member)
    await db.commit()
    await db.refresh(team)

    # Calculate member count
    stmt = select(func.count()).select_from(TeamMember).where(
        and_(
            TeamMember.team_id == team.id,
            TeamMember.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    member_count = result.scalar()

    # Build response
    response_data = TeamResponse.model_validate(team)
    response_data.member_count = member_count

    return response_data


@router.get("", response_model=TeamListResponse)
async def list_teams(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    List all teams the current user is a member of.

    Returns teams with the user's role in each team.
    """
    # Get all team memberships for user
    stmt = (
        select(TeamMember)
        .where(
            and_(
                TeamMember.user_id == current_user.id,
                TeamMember.deleted_at.is_(None),
            )
        )
        .options(selectinload(TeamMember.team))
    )

    result = await db.execute(stmt)
    memberships = result.scalars().all()

    teams_with_roles = []
    for membership in memberships:
        team = membership.team

        # Skip deleted teams
        if team.deleted_at is not None:
            continue

        # Count members
        count_stmt = select(func.count()).select_from(TeamMember).where(
            and_(
                TeamMember.team_id == team.id,
                TeamMember.deleted_at.is_(None),
            )
        )
        count_result = await db.execute(count_stmt)
        member_count = count_result.scalar()

        teams_with_roles.append({
            "id": team.id,
            "name": team.name,
            "slug": team.slug,
            "description": team.description,
            "avatar_url": team.avatar_url,
            "owner_id": team.owner_id,
            "subscription_tier": team.subscription_tier,
            "subscription_status": team.subscription_status,
            "member_count": member_count,
            "current_user_role": membership.role,
            "created_at": team.created_at,
        })

    return TeamListResponse(
        teams=teams_with_roles,
        total=len(teams_with_roles),
    )


@router.get("/current", response_model=CurrentTeamResponse)
async def get_current_team(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get the user's currently selected team.

    Returns null if using personal workspace.
    """
    if not hasattr(current_user, 'current_team_id') or not current_user.current_team_id:
        return CurrentTeamResponse(
            team=None,
            is_personal_workspace=True,
        )

    # Get team
    stmt = select(Team).where(
        and_(
            Team.id == current_user.current_team_id,
            Team.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        return CurrentTeamResponse(
            team=None,
            is_personal_workspace=True,
        )

    # Count members
    count_stmt = select(func.count()).select_from(TeamMember).where(
        and_(
            TeamMember.team_id == team.id,
            TeamMember.deleted_at.is_(None),
        )
    )
    count_result = await db.execute(count_stmt)
    member_count = count_result.scalar()

    response = TeamResponse.model_validate(team)
    response.member_count = member_count

    return CurrentTeamResponse(
        team=response,
        is_personal_workspace=False,
    )


@router.get("/{team_id}", response_model=TeamDetailResponse)
async def get_team(
    team_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get team details including members.

    Requires team membership to access.
    """
    # Verify membership
    membership = await get_team_member(team_id, current_user.id, db)

    # Get team with members
    stmt = (
        select(Team)
        .where(Team.id == team_id)
        .options(selectinload(Team.members))
    )
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team or team.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Count active members
    member_count = len([m for m in team.members if m.deleted_at is None])

    # Get member details with user info
    members_info = []
    for member in team.members:
        if member.deleted_at is not None:
            continue

        # Get user info
        user_stmt = select(User).where(User.id == member.user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if user:
            members_info.append({
                "id": member.id,
                "user_id": member.user_id,
                "role": member.role,
                "joined_at": member.joined_at,
                "invited_by": member.invited_by,
            })

    return {
        "id": team.id,
        "name": team.name,
        "slug": team.slug,
        "description": team.description,
        "avatar_url": team.avatar_url,
        "owner_id": team.owner_id,
        "subscription_tier": team.subscription_tier,
        "subscription_status": team.subscription_status,
        "subscription_expires": team.subscription_expires,
        "max_members": team.max_members,
        "member_count": member_count,
        "members": members_info,
        "current_user_role": membership.role,
        "created_at": team.created_at,
        "updated_at": team.updated_at,
    }


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    data: TeamUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update team information.

    Requires owner or admin role.
    """
    # Verify admin access
    membership = await require_team_admin(team_id, current_user, db)

    # Get team
    team = await get_team_by_id(team_id, db)

    # Update fields
    if data.name is not None:
        team.name = data.name
    if data.description is not None:
        team.description = data.description
    if data.logo_url is not None:
        team.avatar_url = data.logo_url
    if data.settings is not None:
        team.settings = data.settings

    team.updated_at = datetime.now()

    await db.commit()
    await db.refresh(team)

    # Count members
    count_stmt = select(func.count()).select_from(TeamMember).where(
        and_(
            TeamMember.team_id == team.id,
            TeamMember.deleted_at.is_(None),
        )
    )
    count_result = await db.execute(count_stmt)
    member_count = count_result.scalar()

    response = TeamResponse.model_validate(team)
    response.member_count = member_count

    return response


@router.delete("/{team_id}", response_model=TeamDeleteResponse)
async def delete_team(
    team_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a team (soft delete).

    Only the team owner can delete the team.
    """
    # Verify owner access
    membership = await require_team_owner(team_id, current_user, db)

    # Get team
    team = await get_team_by_id(team_id, db)

    # Soft delete team
    team.deleted_at = datetime.now()

    # Soft delete all memberships
    stmt = (
        sql_update(TeamMember)
        .where(TeamMember.team_id == team_id)
        .values(deleted_at=datetime.now())
    )
    await db.execute(stmt)

    await db.commit()

    return TeamDeleteResponse(
        message="Team deleted successfully",
        team_id=team_id,
    )


# =============================================================================
# Team Switching
# =============================================================================

@router.post("/{team_id}/switch", response_model=SwitchTeamResponse)
async def switch_team(
    team_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Switch to a different team.

    Updates the user's current_team_id.
    Must be a member of the team to switch to it.
    """
    # Verify membership
    membership = await get_team_member(team_id, current_user.id, db)

    # Update user's current team
    current_user.current_team_id = team_id
    await db.commit()

    return SwitchTeamResponse(
        message="Switched to team successfully",
        current_team_id=team_id,
    )
