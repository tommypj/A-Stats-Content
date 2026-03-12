"""
Project content access dependencies for multi-tenancy.

Provides helper functions to filter content by project ownership and verify access permissions.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db
from infrastructure.database.models.analytics import GSCConnection
from infrastructure.database.models.content import Article, GeneratedImage, Outline
from infrastructure.database.models.knowledge import KnowledgeSource
from infrastructure.database.models.project import ProjectMember, ProjectMemberRole
from infrastructure.database.models.social import ScheduledPost, SocialAccount
from infrastructure.database.models.user import User, UserStatus

# Type alias for content models
ContentModel = (
    Article
    | Outline
    | GeneratedImage
    | SocialAccount
    | ScheduledPost
    | KnowledgeSource
    | GSCConnection
)


async def verify_project_membership(
    db: AsyncSession,
    user: User,
    project_id: str,
) -> bool:
    """
    Verify that a user is a member of a specific project.

    This function should be called before allowing access to project content.

    Args:
        db: Database session
        user: The user to check
        project_id: The project ID to verify membership for

    Returns:
        True if user is a member of the project, False otherwise

    Notes:
        - This is a placeholder implementation. Replace with actual ProjectMember query
          once the Project model and ProjectMember model are created.
        - Currently returns False to prevent unauthorized access until projects are implemented.
    """
    stmt = select(ProjectMember).where(
        and_(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
            ProjectMember.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    return member is not None


async def verify_content_access(
    db: AsyncSession,
    content: ContentModel,
    user: User,
) -> None:
    """
    Verify that a user can access (read) specific content.

    Access is granted if:
    - Personal content: content.user_id matches user.id
    - Project content: user is a member of content.project_id

    Args:
        db: Database session
        content: The content object to verify access for
        user: The authenticated user

    Raises:
        HTTPException: 403 if user doesn't have access
        HTTPException: 404 if content doesn't exist (to avoid info leakage)

    Usage:
        ```python
        article = await db.get(Article, article_id)
        if not article:
            raise HTTPException(404, "Article not found")
        await verify_content_access(db, article, current_user)
        # Now safe to return article data
        ```
    """
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    # Personal content check
    if content.user_id == user.id and content.project_id is None:
        return  # User owns this personal content

    # Project content check
    if content.project_id:
        is_member = await verify_project_membership(db, user, content.project_id)
        if is_member:
            return  # User is a project member

    # If we reach here, user doesn't have access
    # Return 404 instead of 403 to avoid leaking information about content existence
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Content not found",
    )


async def verify_content_edit(
    db: AsyncSession,
    content: ContentModel,
    user: User,
) -> None:
    """
    Verify that a user can edit/delete specific content.

    Edit access is granted if:
    - Personal content: content.user_id matches user.id
    - Project content: user is a MEMBER or higher role in content.project_id

    Args:
        db: Database session
        content: The content object to verify edit access for
        user: The authenticated user

    Raises:
        HTTPException: 403 if user doesn't have edit permission
        HTTPException: 404 if content doesn't exist (to avoid info leakage)

    Usage:
        ```python
        article = await db.get(Article, article_id)
        if not article:
            raise HTTPException(404, "Article not found")
        await verify_content_edit(db, article, current_user)
        # Now safe to modify article
        article.title = "New Title"
        await db.commit()
        ```

    Notes:
        - For personal content, only the owner can edit
        - For project content, MEMBER+ roles can edit (not VIEWER)
        - Once Project roles are implemented, add role checking here
    """
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    # Personal content check
    if content.user_id == user.id and content.project_id is None:
        return  # User owns this personal content

    # Project content check — viewers cannot edit
    if content.project_id:
        stmt = select(ProjectMember).where(
            and_(
                ProjectMember.project_id == content.project_id,
                ProjectMember.user_id == user.id,
                ProjectMember.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        member = result.scalar_one_or_none()
        if member and member.role != ProjectMemberRole.VIEWER.value:
            return  # OWNER, ADMIN, or EDITOR can edit
        if member and member.role == ProjectMemberRole.VIEWER.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewers cannot edit project content",
            )

    # If we reach here, user doesn't have edit access
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to edit this content",
    )


# =============================================================================
# Project Management Dependencies (for project CRUD routes)
# =============================================================================


async def get_project_by_id(
    project_id: str,
    db: AsyncSession,
) -> "Project":  # noqa: F821
    """
    Get a project by ID from database.

    Args:
        project_id: Project UUID
        db: Database session

    Returns:
        Project object

    Raises:
        HTTPException: 404 if project not found or deleted
    """
    from infrastructure.database.models.project import Project

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
            detail="Project not found",
        )

    return project


async def get_project_member(
    project_id: str,
    user_id: str,
    db: AsyncSession,
) -> "ProjectMember":
    """
    Get a project member record.

    Args:
        project_id: Project UUID
        user_id: User UUID
        db: Database session

    Returns:
        ProjectMember object

    Raises:
        HTTPException: 404 if membership not found
    """
    from infrastructure.database.models.project import ProjectMember

    stmt = select(ProjectMember).where(
        and_(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
            ProjectMember.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this project",
        )

    return member


async def require_project_admin(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> "ProjectMember":
    """
    Dependency to require project admin or owner role.

    Args:
        project_id: Project ID from path parameter
        current_user: Current authenticated user
        db: Database session

    Returns:
        ProjectMember object with admin or owner role

    Raises:
        HTTPException: 403 if user is not admin/owner
    """
    # PROJ-48: Reject suspended accounts before granting admin access
    if current_user.status == UserStatus.SUSPENDED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended",
        )

    from infrastructure.database.models.project import ProjectMemberRole

    member = await get_project_member(project_id, current_user.id, db)

    if member.role not in [ProjectMemberRole.OWNER.value, ProjectMemberRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires admin or owner privileges",
        )

    return member


async def require_project_owner(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> "ProjectMember":
    """
    Dependency to require project owner role.

    Args:
        project_id: Project ID from path parameter
        current_user: Current authenticated user
        db: Database session

    Returns:
        ProjectMember object with owner role

    Raises:
        HTTPException: 403 if user is not the owner
    """
    # PROJ-48: Reject suspended accounts before granting owner access
    if current_user.status == UserStatus.SUSPENDED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended",
        )

    from infrastructure.database.models.project import ProjectMemberRole

    member = await get_project_member(project_id, current_user.id, db)

    if member.role != ProjectMemberRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires project owner privileges",
        )

    return member
