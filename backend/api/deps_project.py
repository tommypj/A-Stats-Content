"""
Project content access dependencies for multi-tenancy.

Provides helper functions to filter content by project ownership and verify access permissions.
"""

from typing import Annotated, Any, List, Optional, Union
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db
from infrastructure.database.models.user import User
from infrastructure.database.models.content import Article, Outline, GeneratedImage
from infrastructure.database.models.social import SocialAccount, ScheduledPost
from infrastructure.database.models.knowledge import KnowledgeSource
from infrastructure.database.models.analytics import GSCConnection


# Type alias for content models
ContentModel = Union[
    Article,
    Outline,
    GeneratedImage,
    SocialAccount,
    ScheduledPost,
    KnowledgeSource,
    GSCConnection,
]


def get_content_filter(user: User, project_id: Optional[str] = None):
    """
    Returns SQLAlchemy filter for content queries based on ownership.

    This function creates a filter that can be applied to any content query to ensure
    users only access content they own (personal) or their project owns (project content).

    Usage:
        ```python
        # Personal content only
        filter_clause = get_content_filter(current_user, project_id=None)
        stmt = select(Article).where(filter_clause)

        # Project content (user must be verified as project member separately)
        filter_clause = get_content_filter(current_user, project_id=project_uuid)
        stmt = select(Article).where(filter_clause)
        ```

    Args:
        user: The authenticated user making the request
        project_id: Optional project ID. If provided, filters by project_id.
                If None, filters by user_id (personal content).

    Returns:
        SQLAlchemy filter clause that can be used in .where()

    Notes:
        - If project_id is provided, the calling code MUST verify the user is a member
          of that project before calling this function.
        - This function only creates the filter; it doesn't verify permissions.
        - The filter assumes the model has both user_id and project_id columns.
    """
    if project_id:
        # Project content filter
        # NOTE: Caller must verify user is a project member before using this filter
        return and_(
            # Content belongs to the project
            # Using text comparison since project_id is stored as string UUID
            ContentModel.project_id == str(project_id),
        )
    else:
        # Personal content filter
        return and_(
            # Content belongs to user
            ContentModel.user_id == user.id,
            # And is NOT project content (project_id is null)
            ContentModel.project_id.is_(None),
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
    # TODO: Replace with actual project membership query once Project model exists
    # Example implementation:
    # from infrastructure.database.models.project import ProjectMember
    # stmt = select(ProjectMember).where(
    #     and_(
    #         ProjectMember.project_id == project_id,
    #         ProjectMember.user_id == user.id,
    #         ProjectMember.is_active == True,
    #     )
    # )
    # result = await db.execute(stmt)
    # member = result.scalar_one_or_none()
    # return member is not None

    # Placeholder: Always return False until Project model is implemented
    return False


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

    # Project content check
    if content.project_id:
        is_member = await verify_project_membership(db, user, content.project_id)
        if is_member:
            # TODO: Add role-based permission check once ProjectMember model exists
            # For now, all project members can edit (MEMBER+ role)
            # Example:
            # if member.role in (ProjectRole.MEMBER, ProjectRole.ADMIN, ProjectRole.OWNER):
            #     return
            # else:
            #     raise HTTPException(403, "You don't have permission to edit project content")
            return  # User is a project member with edit access

    # If we reach here, user doesn't have edit access
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to edit this content",
    )


def validate_project_content_creation(
    user: User,
    project_id: Optional[str] = None,
) -> None:
    """
    Validate that a user can create content for a specific project.

    This should be called when creating new content with a project_id.

    Args:
        user: The authenticated user
        project_id: The project ID to create content for (None = personal content)

    Raises:
        HTTPException: 400 if project_id is invalid
        HTTPException: 403 if user doesn't have permission to create project content

    Usage:
        ```python
        @router.post("/articles")
        async def create_article(
            data: ArticleCreate,
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
        ):
            validate_project_content_creation(current_user, data.project_id)
            article = Article(
                user_id=current_user.id,
                project_id=data.project_id,
                title=data.title,
                # ...
            )
            db.add(article)
            await db.commit()
        ```

    Notes:
        - Personal content (project_id=None) is always allowed
        - Project content requires MEMBER+ role verification
        - This is a synchronous validation; use verify_project_membership for async checks
    """
    if project_id is None:
        # Personal content - always allowed
        return

    # TODO: Add actual project membership and role verification
    # For now, raise error to prevent project content creation until projects are implemented
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Project content creation is not yet implemented. Please create personal content (omit project_id).",
    )


# Helper function to build content list query with project filtering
def apply_content_filters(
    stmt: Any,
    user: User,
    project_id: Optional[str] = None,
) -> Any:
    """
    Apply content ownership filters to a SQLAlchemy statement.

    This is a convenience function that applies get_content_filter to an existing query.

    Args:
        stmt: SQLAlchemy select statement
        user: The authenticated user
        project_id: Optional project ID to filter by

    Returns:
        Modified statement with filters applied

    Usage:
        ```python
        stmt = select(Article)
        stmt = apply_content_filters(stmt, current_user, project_id=request.args.project_id)
        results = await db.execute(stmt)
        ```
    """
    content_filter = get_content_filter(user, project_id)
    return stmt.where(content_filter)


# =============================================================================
# Project Management Dependencies (for project CRUD routes)
# =============================================================================

async def get_project_by_id(
    project_id: str,
    db: AsyncSession,
) -> "Project":
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


async def require_project_membership(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> "ProjectMember":
    """
    Dependency to require project membership.

    Args:
        project_id: Project ID from path parameter
        current_user: Current authenticated user
        db: Database session

    Returns:
        ProjectMember object

    Raises:
        HTTPException: 403 if user is not a member

    Usage:
        @router.get("/projects/{project_id}/something")
        async def get_something(
            member: Annotated[ProjectMember, Depends(require_project_membership)],
        ):
            # member is guaranteed to exist
            return {"project_id": member.project_id, "role": member.role}
    """
    return await get_project_member(project_id, current_user.id, db)


async def require_project_role(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    required_roles: List[str] = None,
) -> "ProjectMember":
    """
    Dependency to require specific project role.

    Args:
        project_id: Project ID from path parameter
        current_user: Current authenticated user
        db: Database session
        required_roles: List of allowed roles (e.g., ["owner", "admin"])

    Returns:
        ProjectMember object

    Raises:
        HTTPException: 403 if user doesn't have required role

    Usage:
        @router.put("/projects/{project_id}/settings")
        async def update_settings(
            project_id: str,
            member: Annotated[ProjectMember, Depends(require_project_role)],
        ):
            # Check role manually if needed
            if member.role not in [ProjectMemberRole.OWNER.value, ProjectMemberRole.ADMIN.value]:
                raise HTTPException(403, "Admin access required")
            # ...
    """
    member = await get_project_member(project_id, current_user.id, db)

    if required_roles and member.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires one of the following roles: {', '.join(required_roles)}",
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
    from infrastructure.database.models.project import ProjectMemberRole
    member = await get_project_member(project_id, current_user.id, db)

    if member.role != ProjectMemberRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires project owner privileges",
        )

    return member
