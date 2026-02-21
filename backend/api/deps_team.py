"""
Team content access dependencies for multi-tenancy.

Provides helper functions to filter content by team ownership and verify access permissions.
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


def get_content_filter(user: User, team_id: Optional[str] = None):
    """
    Returns SQLAlchemy filter for content queries based on ownership.

    This function creates a filter that can be applied to any content query to ensure
    users only access content they own (personal) or their team owns (team content).

    Usage:
        ```python
        # Personal content only
        filter_clause = get_content_filter(current_user, team_id=None)
        stmt = select(Article).where(filter_clause)

        # Team content (user must be verified as team member separately)
        filter_clause = get_content_filter(current_user, team_id=team_uuid)
        stmt = select(Article).where(filter_clause)
        ```

    Args:
        user: The authenticated user making the request
        team_id: Optional team ID. If provided, filters by team_id.
                If None, filters by user_id (personal content).

    Returns:
        SQLAlchemy filter clause that can be used in .where()

    Notes:
        - If team_id is provided, the calling code MUST verify the user is a member
          of that team before calling this function.
        - This function only creates the filter; it doesn't verify permissions.
        - The filter assumes the model has both user_id and team_id columns.
    """
    if team_id:
        # Team content filter
        # NOTE: Caller must verify user is a team member before using this filter
        return and_(
            # Content belongs to the team
            # Using text comparison since team_id is stored as string UUID
            ContentModel.team_id == str(team_id),
        )
    else:
        # Personal content filter
        return and_(
            # Content belongs to user
            ContentModel.user_id == user.id,
            # And is NOT team content (team_id is null)
            ContentModel.team_id.is_(None),
        )


async def verify_team_membership(
    db: AsyncSession,
    user: User,
    team_id: str,
) -> bool:
    """
    Verify that a user is a member of a specific team.

    This function should be called before allowing access to team content.

    Args:
        db: Database session
        user: The user to check
        team_id: The team ID to verify membership for

    Returns:
        True if user is a member of the team, False otherwise

    Notes:
        - This is a placeholder implementation. Replace with actual TeamMember query
          once the Team model and TeamMember model are created.
        - Currently returns False to prevent unauthorized access until teams are implemented.
    """
    # TODO: Replace with actual team membership query once Team model exists
    # Example implementation:
    # from infrastructure.database.models.team import TeamMember
    # stmt = select(TeamMember).where(
    #     and_(
    #         TeamMember.team_id == team_id,
    #         TeamMember.user_id == user.id,
    #         TeamMember.is_active == True,
    #     )
    # )
    # result = await db.execute(stmt)
    # member = result.scalar_one_or_none()
    # return member is not None

    # Placeholder: Always return False until Team model is implemented
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
    - Team content: user is a member of content.team_id

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
    if content.user_id == user.id and content.team_id is None:
        return  # User owns this personal content

    # Team content check
    if content.team_id:
        is_member = await verify_team_membership(db, user, content.team_id)
        if is_member:
            return  # User is a team member

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
    - Team content: user is a MEMBER or higher role in content.team_id

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
        - For team content, MEMBER+ roles can edit (not VIEWER)
        - Once Team roles are implemented, add role checking here
    """
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    # Personal content check
    if content.user_id == user.id and content.team_id is None:
        return  # User owns this personal content

    # Team content check
    if content.team_id:
        is_member = await verify_team_membership(db, user, content.team_id)
        if is_member:
            # TODO: Add role-based permission check once TeamMember model exists
            # For now, all team members can edit (MEMBER+ role)
            # Example:
            # if member.role in (TeamRole.MEMBER, TeamRole.ADMIN, TeamRole.OWNER):
            #     return
            # else:
            #     raise HTTPException(403, "You don't have permission to edit team content")
            return  # User is a team member with edit access

    # If we reach here, user doesn't have edit access
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to edit this content",
    )


def validate_team_content_creation(
    user: User,
    team_id: Optional[str] = None,
) -> None:
    """
    Validate that a user can create content for a specific team.

    This should be called when creating new content with a team_id.

    Args:
        user: The authenticated user
        team_id: The team ID to create content for (None = personal content)

    Raises:
        HTTPException: 400 if team_id is invalid
        HTTPException: 403 if user doesn't have permission to create team content

    Usage:
        ```python
        @router.post("/articles")
        async def create_article(
            data: ArticleCreate,
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
        ):
            validate_team_content_creation(current_user, data.team_id)
            article = Article(
                user_id=current_user.id,
                team_id=data.team_id,
                title=data.title,
                # ...
            )
            db.add(article)
            await db.commit()
        ```

    Notes:
        - Personal content (team_id=None) is always allowed
        - Team content requires MEMBER+ role verification
        - This is a synchronous validation; use verify_team_membership for async checks
    """
    if team_id is None:
        # Personal content - always allowed
        return

    # TODO: Add actual team membership and role verification
    # For now, raise error to prevent team content creation until teams are implemented
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Team content creation is not yet implemented. Please create personal content (omit team_id).",
    )


# Helper function to build content list query with team filtering
def apply_content_filters(
    stmt: Any,
    user: User,
    team_id: Optional[str] = None,
) -> Any:
    """
    Apply content ownership filters to a SQLAlchemy statement.

    This is a convenience function that applies get_content_filter to an existing query.

    Args:
        stmt: SQLAlchemy select statement
        user: The authenticated user
        team_id: Optional team ID to filter by

    Returns:
        Modified statement with filters applied

    Usage:
        ```python
        stmt = select(Article)
        stmt = apply_content_filters(stmt, current_user, team_id=request.args.team_id)
        results = await db.execute(stmt)
        ```
    """
    content_filter = get_content_filter(user, team_id)
    return stmt.where(content_filter)


# =============================================================================
# Team Management Dependencies (for team CRUD routes)
# =============================================================================

async def get_team_by_id(
    team_id: str,
    db: AsyncSession,
) -> "Team":
    """
    Get a team by ID from database.

    Args:
        team_id: Team UUID
        db: Database session

    Returns:
        Team object

    Raises:
        HTTPException: 404 if team not found or deleted
    """
    from infrastructure.database.models.team import Team

    stmt = select(Team).where(
        and_(
            Team.id == team_id,
            Team.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    return team


async def get_team_member(
    team_id: str,
    user_id: str,
    db: AsyncSession,
) -> "TeamMember":
    """
    Get a team member record.

    Args:
        team_id: Team UUID
        user_id: User UUID
        db: Database session

    Returns:
        TeamMember object

    Raises:
        HTTPException: 404 if membership not found
    """
    from infrastructure.database.models.team import TeamMember

    stmt = select(TeamMember).where(
        and_(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    return member


async def require_team_membership(
    team_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> "TeamMember":
    """
    Dependency to require team membership.

    Args:
        team_id: Team ID from path parameter
        current_user: Current authenticated user
        db: Database session

    Returns:
        TeamMember object

    Raises:
        HTTPException: 403 if user is not a member

    Usage:
        @router.get("/teams/{team_id}/something")
        async def get_something(
            member: Annotated[TeamMember, Depends(require_team_membership)],
        ):
            # member is guaranteed to exist
            return {"team_id": member.team_id, "role": member.role}
    """
    return await get_team_member(team_id, current_user.id, db)


async def require_team_role(
    team_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    required_roles: List[str] = None,
) -> "TeamMember":
    """
    Dependency to require specific team role.

    Args:
        team_id: Team ID from path parameter
        current_user: Current authenticated user
        db: Database session
        required_roles: List of allowed roles (e.g., ["owner", "admin"])

    Returns:
        TeamMember object

    Raises:
        HTTPException: 403 if user doesn't have required role

    Usage:
        @router.put("/teams/{team_id}/settings")
        async def update_settings(
            team_id: str,
            member: Annotated[TeamMember, Depends(require_team_role)],
        ):
            # Check role manually if needed
            if member.role not in [TeamMemberRole.OWNER.value, TeamMemberRole.ADMIN.value]:
                raise HTTPException(403, "Admin access required")
            # ...
    """
    member = await get_team_member(team_id, current_user.id, db)

    if required_roles and member.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires one of the following roles: {', '.join(required_roles)}",
        )

    return member


async def require_team_admin(
    team_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> "TeamMember":
    """
    Dependency to require team admin or owner role.

    Args:
        team_id: Team ID from path parameter
        current_user: Current authenticated user
        db: Database session

    Returns:
        TeamMember object with admin or owner role

    Raises:
        HTTPException: 403 if user is not admin/owner
    """
    member = await get_team_member(team_id, current_user.id, db)

    if member.role not in [TeamMemberRole.OWNER.value, TeamMemberRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires admin or owner privileges",
        )

    return member


async def require_team_owner(
    team_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> "TeamMember":
    """
    Dependency to require team owner role.

    Args:
        team_id: Team ID from path parameter
        current_user: Current authenticated user
        db: Database session

    Returns:
        TeamMember object with owner role

    Raises:
        HTTPException: 403 if user is not the owner
    """
    member = await get_team_member(team_id, current_user.id, db)

    if member.role != TeamMemberRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires team owner privileges",
        )

    return member
