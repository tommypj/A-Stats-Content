"""
Project invitation API routes.
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
from api.schemas.project import (
    ProjectInvitationAcceptResponse,
    ProjectInvitationCreate,
    ProjectInvitationListResponse,
    ProjectInvitationPublicResponse,
    ProjectInvitationResponse,
)
from infrastructure.config.settings import settings
from infrastructure.database.models import (
    InvitationStatus,
    Project,
    ProjectInvitation,
    ProjectMember,
    ProjectMemberRole,
    User,
)

router = APIRouter(prefix="/projects", tags=["project-invitations"])


# =============================================================================
# Project Admin Endpoints (require project admin role)
# =============================================================================


async def require_project_admin(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """
    Dependency to ensure current user is admin/owner of the project.

    Returns the project if authorized.
    Raises HTTPException 403 if not authorized or 404 if project not found.
    """
    # Get project
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id, Project.deleted_at.is_(None))
        .options(selectinload(Project.members))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check if user is owner
    if project.owner_id == current_user.id:
        return project

    # Check if user is admin member
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id,
            ProjectMember.deleted_at.is_(None),
        )
    )
    member = result.scalar_one_or_none()

    if not member or member.role not in (
        ProjectMemberRole.OWNER.value,
        ProjectMemberRole.ADMIN.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owners and admins can manage invitations",
        )

    return project


@router.get("/{project_id}/invitations", response_model=ProjectInvitationListResponse)
async def list_project_invitations(
    project_id: str,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    project: Project = Depends(require_project_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List pending invitations for a project.

    - Requires ADMIN+ role in the project
    - Filter by status (pending, expired, accepted, revoked)
    - Paginated results
    """
    # Build query
    query = select(ProjectInvitation).where(ProjectInvitation.project_id == project_id)

    # Apply status filter
    if status_filter:
        query = query.where(ProjectInvitation.status == status_filter)

    # Add ordering
    query = query.order_by(ProjectInvitation.created_at.desc())

    # Count total
    count_query = select(func.count()).select_from(ProjectInvitation).where(ProjectInvitation.project_id == project_id)
    if status_filter:
        count_query = count_query.where(ProjectInvitation.status == status_filter)

    result = await db.execute(count_query)
    total = result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Load invitations with relationships
    query = query.options(selectinload(ProjectInvitation.inviter))

    result = await db.execute(query)
    invitations = result.scalars().all()

    # Convert to response schema
    invitation_responses = []
    for inv in invitations:
        invitation_responses.append(
            ProjectInvitationResponse(
                id=inv.id,
                project_id=inv.project_id,
                email=inv.email,
                role=inv.role,
                token=inv.token,
                status=inv.status,
                invited_by_id=inv.invited_by,
                expires_at=inv.expires_at,
                accepted_at=inv.accepted_at,
                created_at=inv.created_at,
                project_name=project.name,
                project_slug=project.slug,
                inviter_name=inv.inviter.name if inv.inviter else None,
                inviter_email=inv.inviter.email if inv.inviter else None,
            )
        )

    total_pages = (total + page_size - 1) // page_size

    return ProjectInvitationListResponse(
        invitations=invitation_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/{project_id}/invitations", response_model=ProjectInvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_project_invitation(
    project_id: str,
    invitation: ProjectInvitationCreate,
    project: Project = Depends(require_project_admin),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a project invitation email.

    - Requires ADMIN+ role
    - Validates email format
    - Checks if user is already a member
    - Generates unique secure token
    - Sets expiration to 7 days from now
    - Sends invitation email
    """
    # Check if project can add more members
    if not project.can_add_member():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project has reached maximum member limit ({project.max_members})",
        )

    # Check if user with this email already exists and is already a member
    result = await db.execute(select(User).where(User.email == invitation.email.lower()))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Check if already a member
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == existing_user.id,
                ProjectMember.deleted_at.is_(None),
            )
        )
        existing_member = result.scalar_one_or_none()

        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this project",
            )

    # Check if there's already a pending invitation for this email
    result = await db.execute(
        select(ProjectInvitation).where(
            ProjectInvitation.project_id == project_id,
            ProjectInvitation.email == invitation.email.lower(),
            ProjectInvitation.status == InvitationStatus.PENDING.value,
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
    new_invitation = ProjectInvitation(
        project_id=project_id,
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
        select(ProjectInvitation)
        .where(ProjectInvitation.id == new_invitation.id)
        .options(selectinload(ProjectInvitation.inviter))
    )
    await db.refresh(new_invitation)

    # Send invitation email
    invitation_url = f"{settings.frontend_url}/invitations/{token}"
    await email_service.send_team_invitation_email(
        to_email=invitation.email,
        inviter_name=current_user.name,
        team_name=project.name,
        role=invitation.role,
        invitation_url=invitation_url,
    )

    return ProjectInvitationResponse(
        id=new_invitation.id,
        project_id=new_invitation.project_id,
        email=new_invitation.email,
        role=new_invitation.role,
        token=new_invitation.token,
        status=new_invitation.status,
        invited_by_id=new_invitation.invited_by,
        expires_at=new_invitation.expires_at,
        accepted_at=new_invitation.accepted_at,
        created_at=new_invitation.created_at,
        project_name=project.name,
        project_slug=project.slug,
        inviter_name=new_invitation.inviter.name if new_invitation.inviter else None,
        inviter_email=new_invitation.inviter.email if new_invitation.inviter else None,
    )


@router.delete("/{project_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_project_invitation(
    project_id: str,
    invitation_id: str,
    project: Project = Depends(require_project_admin),
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
        select(ProjectInvitation).where(
            ProjectInvitation.id == invitation_id,
            ProjectInvitation.project_id == project_id,
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


@router.post("/{project_id}/invitations/{invitation_id}/resend", response_model=ProjectInvitationResponse)
async def resend_project_invitation(
    project_id: str,
    invitation_id: str,
    project: Project = Depends(require_project_admin),
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
        select(ProjectInvitation)
        .where(
            ProjectInvitation.id == invitation_id,
            ProjectInvitation.project_id == project_id,
        )
        .options(selectinload(ProjectInvitation.inviter))
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
        team_name=project.name,
        role=invitation.role,
        invitation_url=invitation_url,
    )

    return ProjectInvitationResponse(
        id=invitation.id,
        project_id=invitation.project_id,
        email=invitation.email,
        role=invitation.role,
        token=invitation.token,
        status=invitation.status,
        invited_by_id=invitation.invited_by,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        created_at=invitation.created_at,
        project_name=project.name,
        project_slug=project.slug,
        inviter_name=invitation.inviter.name if invitation.inviter else None,
        inviter_email=invitation.inviter.email if invitation.inviter else None,
    )


# =============================================================================
# Public Invitation Endpoints (no auth required)
# =============================================================================


@router.get("/invitations/{token}", response_model=ProjectInvitationPublicResponse, tags=["public-invitations"])
async def get_invitation_details(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get invitation details by token (public endpoint).

    - No authentication required
    - Returns project name, inviter name, role, expiration
    - Checks if invitation is expired or already used
    """
    # Get invitation with project and inviter info
    result = await db.execute(
        select(ProjectInvitation)
        .where(ProjectInvitation.token == token)
        .options(
            selectinload(ProjectInvitation.project),
            selectinload(ProjectInvitation.inviter),
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

    return ProjectInvitationPublicResponse(
        project_name=invitation.project.name,
        project_slug=invitation.project.slug,
        project_logo_url=invitation.project.avatar_url,
        inviter_name=invitation.inviter.name,
        role=invitation.role,
        expires_at=invitation.expires_at,
        is_expired=is_expired,
        is_already_member=is_already_member,
    )


@router.post("/invitations/{token}/accept", response_model=ProjectInvitationAcceptResponse, tags=["public-invitations"])
async def accept_invitation(
    token: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a project invitation.

    - If user is logged in: Add them to the project immediately
    - If user is not logged in: Return redirect URL to register/login
    - Validates invitation is still pending and not expired
    """
    # Get invitation
    result = await db.execute(
        select(ProjectInvitation)
        .where(ProjectInvitation.token == token)
        .options(selectinload(ProjectInvitation.project))
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
        return ProjectInvitationAcceptResponse(
            success=False,
            project_id=invitation.project_id,
            project_name=invitation.project.name,
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
        select(ProjectMember).where(
            ProjectMember.project_id == invitation.project_id,
            ProjectMember.user_id == current_user.id,
            ProjectMember.deleted_at.is_(None),
        )
    )
    existing_member = result.scalar_one_or_none()

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this project",
        )

    # Create project member
    new_member = ProjectMember(
        project_id=invitation.project_id,
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

    # Set user's current project to this project if they don't have one
    if not current_user.current_project_id:
        current_user.current_project_id = invitation.project_id

    await db.commit()

    return ProjectInvitationAcceptResponse(
        success=True,
        project_id=invitation.project_id,
        project_name=invitation.project.name,
        redirect_url=None,
    )
