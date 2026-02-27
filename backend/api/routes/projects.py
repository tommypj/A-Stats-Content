"""
Project management API routes for multi-tenancy.
"""

import math
from datetime import datetime, timezone
from typing import Annotated, Optional, List
import re

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_, update as sql_update, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.connection import get_db
from infrastructure.database.models.user import User
from infrastructure.database.models.project import Project, ProjectMember, ProjectMemberRole
from api.routes.auth import get_current_user
from api.deps_project import (
    get_project_by_id,
    get_project_member,
    require_project_membership,
    require_project_admin,
    require_project_owner,
)
from api.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectWithMemberRoleResponse,
    ProjectListResponse,
    ProjectDetailResponse,
    ProjectDeleteResponse,
    SwitchProjectRequest,
    SwitchProjectResponse,
    CurrentProjectResponse,
    ProjectMemberResponse,
    ProjectMembersListResponse,
    AddMemberRequest,
    AddMemberResponse,
    UpdateMemberRoleRequest,
    UpdateMemberRoleResponse,
    RemoveMemberResponse,
    LeaveProjectResponse,
    TransferOwnershipRequest,
    TransferOwnershipResponse,
    BrandVoiceSettings,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


# =============================================================================
# Helper Functions
# =============================================================================

def generate_unique_slug(name: str) -> str:
    """Generate a URL-friendly slug from project name."""
    slug = name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    slug = slug.strip('-')
    slug = slug[:100]
    return slug


async def ensure_unique_slug(db: AsyncSession, slug: str, project_id: Optional[str] = None) -> str:
    """Ensure slug is unique by appending number if necessary."""
    original_slug = slug
    counter = 1
    max_attempts = 100

    while counter <= max_attempts:
        stmt = select(Project).where(Project.slug == slug)
        if project_id:
            stmt = stmt.where(Project.id != project_id)

        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            return slug

        slug = f"{original_slug}-{counter}"
        counter += 1

    # Fallback: append a random suffix to guarantee uniqueness
    import uuid
    return f"{original_slug}-{uuid.uuid4().hex[:8]}"


# =============================================================================
# Project CRUD
# =============================================================================

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new project.

    The current user becomes the owner of the project.
    Project is initialized with free tier subscription.
    """
    # Generate slug if not provided
    slug = data.slug or generate_unique_slug(data.name)

    # Ensure slug is unique
    slug = await ensure_unique_slug(db, slug)

    # Create project
    project = Project(
        name=data.name,
        slug=slug,
        description=data.description,
        avatar_url=getattr(data, 'logo_url', None),
        owner_id=current_user.id,
        subscription_tier="free",
        subscription_status="active",
        max_members=5,  # Free tier default
    )

    db.add(project)
    await db.flush()  # Get project ID

    # Add owner as project member
    member = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role=ProjectMemberRole.OWNER.value,
        invited_by=None,  # Self-created
        joined_at=datetime.now(timezone.utc),
    )

    db.add(member)
    await db.commit()
    await db.refresh(project)

    # Calculate member count
    stmt = select(func.count()).select_from(ProjectMember).where(
        and_(
            ProjectMember.project_id == project.id,
            ProjectMember.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    member_count = result.scalar()

    # Build response
    response_data = ProjectResponse.model_validate(project)
    response_data.member_count = member_count

    return response_data


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """
    List all projects the current user is a member of.

    Returns projects with the user's role in each project.
    """
    # Get all project memberships for user
    stmt = (
        select(ProjectMember)
        .where(
            and_(
                ProjectMember.user_id == current_user.id,
                ProjectMember.deleted_at.is_(None),
            )
        )
        .options(selectinload(ProjectMember.project))
    )

    result = await db.execute(stmt)
    memberships = result.scalars().all()

    # Batch-fetch member counts for all projects in one query
    project_ids = [m.project_id for m in memberships]
    counts: dict = {}
    if project_ids:
        count_stmt = (
            select(ProjectMember.project_id, func.count().label("cnt"))
            .where(
                ProjectMember.project_id.in_(project_ids),
                ProjectMember.deleted_at.is_(None),
            )
            .group_by(ProjectMember.project_id)
        )
        count_result = await db.execute(count_stmt)
        counts = {row.project_id: row.cnt for row in count_result}

    all_projects_with_roles = []
    for membership in memberships:
        project = membership.project

        # Skip deleted projects
        if project.deleted_at is not None:
            continue

        member_count = counts.get(project.id, 0)

        all_projects_with_roles.append({
            "id": project.id,
            "name": project.name,
            "slug": project.slug,
            "description": project.description,
            "avatar_url": project.avatar_url,
            "logo_url": project.avatar_url,
            "owner_id": project.owner_id,
            "is_personal": getattr(project, 'is_personal', False),
            "subscription_tier": project.subscription_tier,
            "subscription_status": project.subscription_status,
            "member_count": member_count,
            "current_user_role": membership.role,
            "my_role": membership.role,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        })

    total = len(all_projects_with_roles)
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    paginated = all_projects_with_roles[offset: offset + page_size]

    return ProjectListResponse(
        projects=paginated,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/current", response_model=CurrentProjectResponse)
async def get_current_project(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get the user's currently selected project.

    Returns null if using personal workspace.
    """
    if not hasattr(current_user, 'current_project_id') or not current_user.current_project_id:
        return CurrentProjectResponse(
            project=None,
            is_personal_workspace=True,
        )

    # Get project
    stmt = select(Project).where(
        and_(
            Project.id == current_user.current_project_id,
            Project.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        return CurrentProjectResponse(
            project=None,
            is_personal_workspace=True,
        )

    # Count members
    count_stmt = select(func.count()).select_from(ProjectMember).where(
        and_(
            ProjectMember.project_id == project.id,
            ProjectMember.deleted_at.is_(None),
        )
    )
    count_result = await db.execute(count_stmt)
    member_count = count_result.scalar()

    # Get user's role in this project
    role_stmt = select(ProjectMember.role).where(
        and_(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == current_user.id,
            ProjectMember.deleted_at.is_(None),
        )
    )
    role_result = await db.execute(role_stmt)
    user_role = role_result.scalar()

    response = ProjectResponse.model_validate(project)
    response.member_count = member_count
    response.current_user_role = user_role
    response.my_role = user_role
    response.logo_url = project.avatar_url

    return CurrentProjectResponse(
        project=response,
        is_personal_workspace=getattr(project, 'is_personal', False),
    )


# =============================================================================
# Brand Voice
# =============================================================================

@router.get("/current/brand-voice", response_model=BrandVoiceSettings)
async def get_brand_voice(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get the brand voice settings for the current project.

    Returns empty defaults if no project is selected or brand voice is not set.
    """
    project_id = getattr(current_user, 'current_project_id', None)
    if not project_id:
        return BrandVoiceSettings()

    stmt = select(Project).where(
        and_(
            Project.id == project_id,
            Project.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project or not project.brand_voice:
        return BrandVoiceSettings()

    return BrandVoiceSettings(**project.brand_voice)


@router.put("/current/brand-voice", response_model=BrandVoiceSettings)
async def update_brand_voice(
    data: BrandVoiceSettings,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update the brand voice settings for the current project.

    Requires an active project to be selected and ADMIN or OWNER role.
    """
    project_id = getattr(current_user, 'current_project_id', None)
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No project selected. Switch to a project before updating brand voice.",
        )

    # AUTH-06: Require admin/owner role to modify brand voice.
    await require_project_admin(project_id, current_user, db)

    stmt = select(Project).where(
        and_(
            Project.id == project_id,
            Project.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current project not found.",
        )

    project.brand_voice = data.model_dump(exclude_none=True)
    project.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(project)

    return BrandVoiceSettings(**(project.brand_voice or {}))


@router.post("/switch", response_model=SwitchProjectResponse)
async def switch_project_by_body(
    request: SwitchProjectRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Switch to a different project or back to personal workspace.

    Accepts project_id in the request body. Pass null to switch to personal workspace.
    """
    if request.project_id is None:
        # Switch to personal workspace — find the user's personal project
        personal_result = await db.execute(
            select(Project).where(
                Project.owner_id == current_user.id,
                Project.is_personal == True,
                Project.deleted_at.is_(None),
            )
        )
        personal_project = personal_result.scalar_one_or_none()
        if personal_project:
            current_user.current_project_id = personal_project.id
        else:
            current_user.current_project_id = None
        await db.commit()
        return SwitchProjectResponse(
            message="Switched to personal workspace",
            current_project_id=current_user.current_project_id,
        )

    # Verify membership before switching
    membership = await get_project_member(request.project_id, current_user.id, db)

    # Update user's current project
    current_user.current_project_id = request.project_id
    await db.commit()

    return SwitchProjectResponse(
        message="Switched to project successfully",
        current_project_id=request.project_id,
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get project details including members.

    Requires project membership to access.
    """
    # Verify membership
    membership = await get_project_member(project_id, current_user.id, db)

    # Get project with members
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.members))
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project or project.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Count active members
    member_count = len([m for m in project.members if m.deleted_at is None])

    # Batch-fetch all user records for active members in one query
    active_members = [m for m in project.members if m.deleted_at is None]
    users_dict: dict = {}
    user_ids = [m.user_id for m in active_members]
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_dict = {u.id: u for u in users_result.scalars().all()}

    # Get member details with user info
    members_info = []
    for member in active_members:
        user = users_dict.get(member.user_id)

        if user:
            members_info.append({
                "id": member.id,
                "user_id": member.user_id,
                "role": member.role,
                "joined_at": member.joined_at,
                "invited_by": member.invited_by,
            })

    return {
        "id": project.id,
        "name": project.name,
        "slug": project.slug,
        "description": project.description,
        "avatar_url": project.avatar_url,
        "owner_id": project.owner_id,
        "subscription_tier": project.subscription_tier,
        "subscription_status": project.subscription_status,
        "subscription_expires": project.subscription_expires,
        "max_members": project.max_members,
        "member_count": member_count,
        "members": members_info,
        "current_user_role": membership.role,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update project information.

    Requires owner or admin role.
    """
    # Verify admin access
    membership = await require_project_admin(project_id, current_user, db)

    # Get project
    project = await get_project_by_id(project_id, db)

    # Update fields
    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    if data.logo_url is not None:
        project.avatar_url = data.logo_url
    if data.settings is not None:
        project.settings = data.settings

    project.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(project)

    # Count members
    count_stmt = select(func.count()).select_from(ProjectMember).where(
        and_(
            ProjectMember.project_id == project.id,
            ProjectMember.deleted_at.is_(None),
        )
    )
    count_result = await db.execute(count_stmt)
    member_count = count_result.scalar()

    response = ProjectResponse.model_validate(project)
    response.member_count = member_count

    return response


@router.delete("/{project_id}", response_model=ProjectDeleteResponse)
async def delete_project(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a project (soft delete).

    Only the project owner can delete the project.
    """
    # Verify owner access
    membership = await require_project_owner(project_id, current_user, db)

    # Get project
    project = await get_project_by_id(project_id, db)

    # Guard: cannot delete personal workspace (PROJ-10: use 403, not 400)
    if getattr(project, 'is_personal', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete personal workspace",
        )

    # Soft delete project
    project.deleted_at = datetime.now(timezone.utc)

    # Soft delete all memberships
    stmt = (
        sql_update(ProjectMember)
        .where(ProjectMember.project_id == project_id)
        .values(deleted_at=datetime.now(timezone.utc))
    )
    await db.execute(stmt)

    await db.commit()

    return ProjectDeleteResponse(
        message="Project deleted successfully",
        project_id=project_id,
    )


# =============================================================================
# Project Switching
# =============================================================================

# =============================================================================
# Member Management Endpoints (PROJ-04)
# =============================================================================


@router.patch("/{project_id}/members/{member_user_id}", response_model=UpdateMemberRoleResponse)
async def update_member_role(
    project_id: str,
    member_user_id: str,
    data: UpdateMemberRoleRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a project member's role. Requires admin or owner."""
    # Verify caller is admin/owner
    caller = await require_project_admin(project_id, current_user, db)

    # Only owner can assign/change owner role
    if data.role == ProjectMemberRole.OWNER.value and caller.role != ProjectMemberRole.OWNER.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the project owner can assign the owner role")

    # Get target member
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_user_id,
            ProjectMember.deleted_at.is_(None),
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Cannot demote the project owner unless you ARE the owner reassigning it
    if member.role == ProjectMemberRole.OWNER.value and caller.role != ProjectMemberRole.OWNER.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change the owner's role")

    old_role = member.role
    member.role = data.role
    await db.commit()
    await db.refresh(member)

    return UpdateMemberRoleResponse(
        success=True,
        message=f"Role updated from {old_role} to {data.role}",
        member=ProjectMemberResponse.model_validate(member),
    )


@router.delete("/{project_id}/members/{member_user_id}", response_model=RemoveMemberResponse)
async def remove_member(
    project_id: str,
    member_user_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove a member from the project. Requires admin or owner. Cannot remove owner."""
    await require_project_admin(project_id, current_user, db)

    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_user_id,
            ProjectMember.deleted_at.is_(None),
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if member.role == ProjectMemberRole.OWNER.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot remove the project owner. Transfer ownership first.")

    member.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return RemoveMemberResponse(success=True, message="Member removed from project")


@router.post("/{project_id}/leave", response_model=LeaveProjectResponse)
async def leave_project(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Leave a project. The owner cannot leave — transfer ownership first."""
    membership = await get_project_member(project_id, current_user.id, db)

    if membership.role == ProjectMemberRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project owner cannot leave. Transfer ownership to another member first.",
        )

    membership.deleted_at = datetime.now(timezone.utc)

    # Clear current_project_id if they were in this project
    if current_user.current_project_id == project_id:
        current_user.current_project_id = None

    await db.commit()

    return LeaveProjectResponse(success=True, message="You have left the project")


@router.post("/{project_id}/transfer-ownership", response_model=TransferOwnershipResponse)
async def transfer_ownership(
    project_id: str,
    data: TransferOwnershipRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Transfer project ownership to another member. Only the current owner can do this."""
    await require_project_owner(project_id, current_user, db)

    # Get new owner's membership
    new_owner_result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == data.new_owner_id,
            ProjectMember.deleted_at.is_(None),
        )
    )
    new_owner_member = new_owner_result.scalar_one_or_none()
    if not new_owner_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="New owner must already be a project member")

    # Demote current owner to admin, promote new owner
    caller_member = await get_project_member(project_id, current_user.id, db)
    caller_member.role = ProjectMemberRole.ADMIN.value
    new_owner_member.role = ProjectMemberRole.OWNER.value

    # Update project owner_id
    project = await get_project_by_id(project_id, db)
    project.owner_id = data.new_owner_id

    await db.commit()

    return TransferOwnershipResponse(
        success=True,
        message="Ownership transferred successfully",
        new_owner_id=data.new_owner_id,
        previous_owner_role=ProjectMemberRole.ADMIN.value,
    )


@router.post("/{project_id}/switch", response_model=SwitchProjectResponse)
async def switch_project(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Switch to a different project.

    Updates the user's current_project_id.
    Must be a member of the project to switch to it.
    """
    # Verify membership
    membership = await get_project_member(project_id, current_user.id, db)

    # Update user's current project
    current_user.current_project_id = project_id
    await db.commit()

    return SwitchProjectResponse(
        message="Switched to project successfully",
        current_project_id=project_id,
    )
