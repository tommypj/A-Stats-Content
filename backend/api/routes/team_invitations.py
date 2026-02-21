"""
Team invitation API routes.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from adapters.email.resend_adapter import email_service
from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db
from api.schemas.team import (
    TeamInvitationAcceptResponse,
    TeamInvitationCreate,
    TeamInvitationListResponse,
    TeamInvitationPublicResponse,
    TeamInvitationResponse,
)
from infrastructure.config.settings import settings
from infrastructure.database.models import (
    InvitationStatus,
    Team,
    TeamInvitation,
    TeamMember,
    TeamMemberRole,
    User,
)

router = APIRouter(prefix="/teams", tags=["team-invitations"])


# =============================================================================
# Team Admin Endpoints (require team admin role)
# =============================================================================


async def require_team_admin(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Team:
    """
    Dependency to ensure current user is admin/owner of the team.

    Returns the team if authorized.
    Raises HTTPException 403 if not authorized or 404 if team not found.
    """
    # Get team
    result = await db.execute(
        select(Team)
        .where(Team.id == team_id, Team.deleted_at.is_(None))
        .options(selectinload(Team.members))
    )
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check if user is owner
    if team.owner_id == current_user.id:
        return team

    # Check if user is admin member
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.deleted_at.is_(None),
        )
    )
    member = result.scalar_one_or_none()

    if not member or member.role not in (
        TeamMemberRole.OWNER.value,
        TeamMemberRole.ADMIN.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owners and admins can manage invitations",
        )

    return team


@router.get("/{team_id}/invitations", response_model=TeamInvitationListResponse)
async def list_team_invitations(
    team_id: str,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    team: Team = Depends(require_team_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List pending invitations for a team.

    - Requires ADMIN+ role in the team
    - Filter by status (pending, expired, accepted, revoked)
    - Paginated results
    """
    # Build query
    query = select(TeamInvitation).where(TeamInvitation.team_id == team_id)

    # Apply status filter
    if status_filter:
        query = query.where(TeamInvitation.status == status_filter)

    # Add ordering
    query = query.order_by(TeamInvitation.created_at.desc())

    # Count total
    count_query = select(func.count()).select_from(TeamInvitation).where(TeamInvitation.team_id == team_id)
    if status_filter:
        count_query = count_query.where(TeamInvitation.status == status_filter)

    result = await db.execute(count_query)
    total = result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Load invitations with relationships
    query = query.options(selectinload(TeamInvitation.inviter))

    result = await db.execute(query)
    invitations = result.scalars().all()

    # Convert to response schema
    invitation_responses = []
    for inv in invitations:
        invitation_responses.append(
            TeamInvitationResponse(
                id=inv.id,
                team_id=inv.team_id,
                email=inv.email,
                role=inv.role,
                token=inv.token,
                status=inv.status,
                invited_by_id=inv.invited_by,
                expires_at=inv.expires_at,
                accepted_at=inv.accepted_at,
                created_at=inv.created_at,
                team_name=team.name,
                team_slug=team.slug,
                inviter_name=inv.inviter.name if inv.inviter else None,
                inviter_email=inv.inviter.email if inv.inviter else None,
            )
        )

    total_pages = (total + page_size - 1) // page_size

    return TeamInvitationListResponse(
        invitations=invitation_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/{team_id}/invitations", response_model=TeamInvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_team_invitation(
    team_id: str,
    invitation: TeamInvitationCreate,
    team: Team = Depends(require_team_admin),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a team invitation email.

    - Requires ADMIN+ role
    - Validates email format
    - Checks if user is already a member
    - Generates unique secure token
    - Sets expiration to 7 days from now
    - Sends invitation email
    """
    # Check if team can add more members
    if not team.can_add_member():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team has reached maximum member limit ({team.max_members})",
        )

    # Check if user with this email already exists and is already a member
    result = await db.execute(select(User).where(User.email == invitation.email.lower()))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Check if already a member
        result = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == existing_user.id,
                TeamMember.deleted_at.is_(None),
            )
        )
        existing_member = result.scalar_one_or_none()

        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this team",
            )

    # Check if there's already a pending invitation for this email
    result = await db.execute(
        select(TeamInvitation).where(
            TeamInvitation.team_id == team_id,
            TeamInvitation.email == invitation.email.lower(),
            TeamInvitation.status == InvitationStatus.PENDING.value,
        )
    )
    existing_invitation = result.scalar_one_or_none()

    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending invitation already exists for this email",
        )

    # Generate secure token
    token = secrets.token_urlsafe(32)

    # Create invitation
    new_invitation = TeamInvitation(
        team_id=team_id,
        invited_by=current_user.id,
        email=invitation.email.lower(),
        role=invitation.role,
        token=token,
        status=InvitationStatus.PENDING.value,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )

    db.add(new_invitation)
    await db.commit()
    await db.refresh(new_invitation)

    # Load relationships for response
    await db.execute(
        select(TeamInvitation)
        .where(TeamInvitation.id == new_invitation.id)
        .options(selectinload(TeamInvitation.inviter))
    )
    await db.refresh(new_invitation)

    # Send invitation email
    invitation_url = f"{settings.frontend_url}/invitations/{token}"
    await email_service.send_team_invitation_email(
        to_email=invitation.email,
        inviter_name=current_user.name,
        team_name=team.name,
        role=invitation.role,
        invitation_url=invitation_url,
    )

    return TeamInvitationResponse(
        id=new_invitation.id,
        team_id=new_invitation.team_id,
        email=new_invitation.email,
        role=new_invitation.role,
        token=new_invitation.token,
        status=new_invitation.status,
        invited_by_id=new_invitation.invited_by,
        expires_at=new_invitation.expires_at,
        accepted_at=new_invitation.accepted_at,
        created_at=new_invitation.created_at,
        team_name=team.name,
        team_slug=team.slug,
        inviter_name=new_invitation.inviter.name if new_invitation.inviter else None,
        inviter_email=new_invitation.inviter.email if new_invitation.inviter else None,
    )


@router.delete("/{team_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_team_invitation(
    team_id: str,
    invitation_id: str,
    team: Team = Depends(require_team_admin),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke a pending invitation.

    - Requires ADMIN+ role
    - Sets status to REVOKED
    - Only works for PENDING invitations
    """
    # Get invitation
    result = await db.execute(
        select(TeamInvitation).where(
            TeamInvitation.id == invitation_id,
            TeamInvitation.team_id == team_id,
        )
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.status != InvitationStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot revoke invitation with status: {invitation.status}",
        )

    # Update invitation
    invitation.status = InvitationStatus.REVOKED.value
    invitation.revoked_at = datetime.utcnow()
    invitation.revoked_by = current_user.id

    await db.commit()

    return None


@router.post("/{team_id}/invitations/{invitation_id}/resend", response_model=TeamInvitationResponse)
async def resend_team_invitation(
    team_id: str,
    invitation_id: str,
    team: Team = Depends(require_team_admin),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resend an invitation email.

    - Requires ADMIN+ role
    - Only works for PENDING invitations
    - Resets expires_at to 7 days from now
    - Sends new email with same token
    """
    # Get invitation
    result = await db.execute(
        select(TeamInvitation)
        .where(
            TeamInvitation.id == invitation_id,
            TeamInvitation.team_id == team_id,
        )
        .options(selectinload(TeamInvitation.inviter))
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.status != InvitationStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resend invitation with status: {invitation.status}",
        )

    # Reset expiration
    invitation.expires_at = datetime.utcnow() + timedelta(days=7)
    await db.commit()
    await db.refresh(invitation)

    # Resend invitation email
    invitation_url = f"{settings.frontend_url}/invitations/{invitation.token}"
    await email_service.send_team_invitation_email(
        to_email=invitation.email,
        inviter_name=current_user.name,
        team_name=team.name,
        role=invitation.role,
        invitation_url=invitation_url,
    )

    return TeamInvitationResponse(
        id=invitation.id,
        team_id=invitation.team_id,
        email=invitation.email,
        role=invitation.role,
        token=invitation.token,
        status=invitation.status,
        invited_by_id=invitation.invited_by,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        created_at=invitation.created_at,
        team_name=team.name,
        team_slug=team.slug,
        inviter_name=invitation.inviter.name if invitation.inviter else None,
        inviter_email=invitation.inviter.email if invitation.inviter else None,
    )


# =============================================================================
# Public Invitation Endpoints (no auth required)
# =============================================================================


@router.get("/invitations/{token}", response_model=TeamInvitationPublicResponse, tags=["public-invitations"])
async def get_invitation_details(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get invitation details by token (public endpoint).

    - No authentication required
    - Returns team name, inviter name, role, expiration
    - Checks if invitation is expired or already used
    """
    # Get invitation with team and inviter info
    result = await db.execute(
        select(TeamInvitation)
        .where(TeamInvitation.token == token)
        .options(
            selectinload(TeamInvitation.team),
            selectinload(TeamInvitation.inviter),
        )
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    # Check if expired
    is_expired = invitation.is_expired

    # Check if already accepted
    is_already_member = invitation.status == InvitationStatus.ACCEPTED.value

    return TeamInvitationPublicResponse(
        team_name=invitation.team.name,
        team_slug=invitation.team.slug,
        team_logo_url=invitation.team.avatar_url,
        inviter_name=invitation.inviter.name,
        role=invitation.role,
        expires_at=invitation.expires_at,
        is_expired=is_expired,
        is_already_member=is_already_member,
    )


@router.post("/invitations/{token}/accept", response_model=TeamInvitationAcceptResponse, tags=["public-invitations"])
async def accept_invitation(
    token: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a team invitation.

    - If user is logged in: Add them to the team immediately
    - If user is not logged in: Return redirect URL to register/login
    - Validates invitation is still pending and not expired
    """
    # Get invitation
    result = await db.execute(
        select(TeamInvitation)
        .where(TeamInvitation.token == token)
        .options(selectinload(TeamInvitation.team))
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    # Check if can accept
    if not invitation.can_accept():
        if invitation.is_expired:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired",
            )
        elif invitation.status == InvitationStatus.ACCEPTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has already been accepted",
            )
        elif invitation.status == InvitationStatus.REVOKED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has been revoked",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot accept invitation with status: {invitation.status}",
            )

    # If user is not logged in, return redirect URL
    if not current_user:
        redirect_url = f"{settings.frontend_url}/register?invitation={token}"
        return TeamInvitationAcceptResponse(
            success=False,
            team_id=invitation.team_id,
            team_name=invitation.team.name,
            redirect_url=redirect_url,
        )

    # Check if user email matches invitation email
    if current_user.email.lower() != invitation.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation is for a different email address",
        )

    # Check if user is already a member
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == invitation.team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.deleted_at.is_(None),
        )
    )
    existing_member = result.scalar_one_or_none()

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this team",
        )

    # Create team member
    new_member = TeamMember(
        team_id=invitation.team_id,
        user_id=current_user.id,
        role=invitation.role,
        invited_by=invitation.invited_by,
        joined_at=datetime.utcnow(),
    )

    db.add(new_member)

    # Update invitation status
    invitation.status = InvitationStatus.ACCEPTED.value
    invitation.accepted_at = datetime.utcnow()
    invitation.accepted_by_user_id = current_user.id

    # Set user's current team to this team if they don't have one
    if not current_user.current_team_id:
        current_user.current_team_id = invitation.team_id

    await db.commit()

    return TeamInvitationAcceptResponse(
        success=True,
        team_id=invitation.team_id,
        team_name=invitation.team.name,
        redirect_url=None,
    )
