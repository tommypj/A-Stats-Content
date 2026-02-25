"""
Admin content moderation API routes.

Provides administrative endpoints for content management across all users.
"""

import logging
from typing import Annotated, Optional, List
from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, delete, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.connection import get_db
from infrastructure.database.models.user import User
from infrastructure.database.models.content import Article, Outline, GeneratedImage
from infrastructure.database.models.social import ScheduledPost, PostTarget
from infrastructure.database.models.admin import AdminAuditLog, AuditAction, AuditTargetType
from api.deps_admin import get_current_admin_user
from api.utils import escape_like
from adapters.storage.image_storage import storage_adapter
from api.schemas.admin_content import (
    AdminArticleListResponse,
    AdminArticleListItem,
    AdminArticleDetail,
    AdminArticleAuthorInfo,
    AdminOutlineListResponse,
    AdminOutlineListItem,
    AdminImageListResponse,
    AdminImageListItem,
    AdminSocialPostListResponse,
    AdminSocialPostListItem,
    BulkDeleteRequest,
    BulkDeleteResponse,
    DeleteResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/content", tags=["Admin - Content"])


# --- Helper Functions ---


def create_author_info(user: User) -> AdminArticleAuthorInfo:
    """Create author info from user model."""
    return AdminArticleAuthorInfo(
        user_id=user.id,
        email=user.email,
        name=user.name,
        subscription_tier=user.subscription_tier,
    )


async def log_audit(
    db: AsyncSession,
    admin_user: User,
    action: AuditAction,
    target_type: AuditTargetType,
    target_id: Optional[str],
    target_user_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Log an admin action to the audit log."""
    audit_log = AdminAuditLog(
        admin_user_id=admin_user.id,
        action=action.value,
        target_type=target_type.value,
        target_id=target_id,
        target_user_id=target_user_id,
        details=details,
    )
    db.add(audit_log)
    await db.commit()


# --- Article Endpoints ---


@router.get("/articles", response_model=AdminArticleListResponse)
async def list_all_articles(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in title and content"),
    sort_by: str = Query("created_at", description="Sort field: created_at, updated_at, seo_score"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all articles across all users.

    Admin-only endpoint for content moderation.
    """
    # Build query
    query = select(Article).options(selectinload(Article.outline))

    # Apply filters
    if user_id:
        query = query.where(Article.user_id == user_id)
    if status:
        query = query.where(Article.status == status)
    if search:
        search_pattern = f"%{escape_like(search)}%"
        query = query.where(
            or_(
                Article.title.ilike(search_pattern),
                Article.content.ilike(search_pattern),
            )
        )

    # Apply sorting
    sort_column = getattr(Article, sort_by, Article.created_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)

    # Get total count
    count_query = select(func.count()).select_from(Article)
    if user_id:
        count_query = count_query.where(Article.user_id == user_id)
    if status:
        count_query = count_query.where(Article.status == status)
    if search:
        search_pattern = f"%{escape_like(search)}%"
        count_query = count_query.where(
            or_(
                Article.title.ilike(search_pattern),
                Article.content.ilike(search_pattern),
            )
        )

    result = await db.execute(count_query)
    total = result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    articles = result.scalars().all()

    # Get user info for each article
    user_ids = list(set(article.user_id for article in articles))
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_dict = {user.id: user for user in users_result.scalars().all()}

    # Build response items
    items = [
        AdminArticleListItem(
            id=article.id,
            title=article.title,
            keyword=article.keyword,
            status=article.status,
            word_count=article.word_count,
            seo_score=article.seo_score,
            created_at=article.created_at,
            updated_at=article.updated_at,
            published_at=article.published_at,
            author=create_author_info(users_dict[article.user_id]),
        )
        for article in articles
    ]

    return AdminArticleListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/articles/{article_id}", response_model=AdminArticleDetail)
async def get_article_detail(
    article_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed article information.

    Includes full content, author info, and associated resources.
    """
    # Get article with relationships
    query = select(Article).options(selectinload(Article.images)).where(Article.id == article_id)
    result = await db.execute(query)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article with ID {article_id} not found",
        )

    # Get author info
    user_result = await db.execute(select(User).where(User.id == article.user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Article author not found",
        )

    return AdminArticleDetail(
        id=article.id,
        title=article.title,
        slug=article.slug,
        keyword=article.keyword,
        meta_description=article.meta_description,
        content=article.content,
        content_html=article.content_html,
        status=article.status,
        word_count=article.word_count,
        read_time=article.read_time,
        seo_score=article.seo_score,
        seo_analysis=article.seo_analysis,
        created_at=article.created_at,
        updated_at=article.updated_at,
        published_at=article.published_at,
        published_url=article.published_url,
        wordpress_post_id=article.wordpress_post_id,
        outline_id=article.outline_id,
        featured_image_id=article.featured_image_id,
        author=create_author_info(user),
        image_count=len(article.images) if article.images else 0,
    )


@router.delete("/articles/{article_id}", response_model=DeleteResponse)
async def delete_article(
    article_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an article.

    Hard delete with cascade. Action is logged to audit trail.
    """
    # Get article to verify it exists and get details for audit
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article with ID {article_id} not found",
        )

    article_title = article.title
    article_user_id = article.user_id

    # Delete article (cascade will handle related records)
    await db.execute(delete(Article).where(Article.id == article_id))
    await db.commit()

    # Log to audit
    await log_audit(
        db=db,
        admin_user=admin_user,
        action=AuditAction.ARTICLE_DELETED,
        target_type=AuditTargetType.ARTICLE,
        target_id=article_id,
        target_user_id=article_user_id,
        details={"title": article_title, "deleted_by_admin": admin_user.email},
    )

    logger.info(f"Admin {admin_user.email} deleted article {article_id} ({article_title})")

    return DeleteResponse(
        success=True,
        message=f"Article '{article_title}' deleted successfully",
        deleted_id=article_id,
    )


# --- Outline Endpoints ---


@router.get("/outlines", response_model=AdminOutlineListResponse)
async def list_all_outlines(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in title"),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all outlines across all users.

    Admin-only endpoint for content moderation.
    """
    # Build query
    query = select(Outline)

    # Apply filters
    if user_id:
        query = query.where(Outline.user_id == user_id)
    if status:
        query = query.where(Outline.status == status)
    if search:
        search_pattern = f"%{escape_like(search)}%"
        query = query.where(Outline.title.ilike(search_pattern))

    # Order by created_at desc
    query = query.order_by(desc(Outline.created_at))

    # Get total count
    count_query = select(func.count()).select_from(Outline)
    if user_id:
        count_query = count_query.where(Outline.user_id == user_id)
    if status:
        count_query = count_query.where(Outline.status == status)
    if search:
        search_pattern = f"%{escape_like(search)}%"
        count_query = count_query.where(Outline.title.ilike(search_pattern))

    result = await db.execute(count_query)
    total = result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    outlines = result.scalars().all()

    # Get user info for each outline
    user_ids = list(set(outline.user_id for outline in outlines))
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_dict = {user.id: user for user in users_result.scalars().all()}

    # Build response items
    items = [
        AdminOutlineListItem(
            id=outline.id,
            title=outline.title,
            keyword=outline.keyword,
            status=outline.status,
            word_count_target=outline.word_count_target,
            section_count=outline.section_count,
            created_at=outline.created_at,
            updated_at=outline.updated_at,
            author=create_author_info(users_dict[outline.user_id]),
        )
        for outline in outlines
    ]

    return AdminOutlineListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.delete("/outlines/{outline_id}", response_model=DeleteResponse)
async def delete_outline(
    outline_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an outline.

    Hard delete with cascade. Action is logged to audit trail.
    """
    # Get outline to verify it exists and get details for audit
    result = await db.execute(select(Outline).where(Outline.id == outline_id))
    outline = result.scalar_one_or_none()

    if not outline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Outline with ID {outline_id} not found",
        )

    outline_title = outline.title
    outline_user_id = outline.user_id

    # Delete outline (cascade will handle related records)
    await db.execute(delete(Outline).where(Outline.id == outline_id))
    await db.commit()

    # Log to audit
    await log_audit(
        db=db,
        admin_user=admin_user,
        action=AuditAction.OUTLINE_DELETED,
        target_type=AuditTargetType.OUTLINE,
        target_id=outline_id,
        target_user_id=outline_user_id,
        details={"title": outline_title, "deleted_by_admin": admin_user.email},
    )

    logger.info(f"Admin {admin_user.email} deleted outline {outline_id} ({outline_title})")

    return DeleteResponse(
        success=True,
        message=f"Outline '{outline_title}' deleted successfully",
        deleted_id=outline_id,
    )


# --- Image Endpoints ---


@router.get("/images", response_model=AdminImageListResponse)
async def list_all_images(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all generated images across all users.

    Admin-only endpoint for content moderation.
    """
    # Build query
    query = select(GeneratedImage)

    # Apply filters
    if user_id:
        query = query.where(GeneratedImage.user_id == user_id)
    if status:
        query = query.where(GeneratedImage.status == status)
    if start_date:
        query = query.where(GeneratedImage.created_at >= start_date)
    if end_date:
        query = query.where(GeneratedImage.created_at <= end_date)

    # Order by created_at desc
    query = query.order_by(desc(GeneratedImage.created_at))

    # Get total count
    count_query = select(func.count()).select_from(GeneratedImage)
    if user_id:
        count_query = count_query.where(GeneratedImage.user_id == user_id)
    if status:
        count_query = count_query.where(GeneratedImage.status == status)
    if start_date:
        count_query = count_query.where(GeneratedImage.created_at >= start_date)
    if end_date:
        count_query = count_query.where(GeneratedImage.created_at <= end_date)

    result = await db.execute(count_query)
    total = result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    images = result.scalars().all()

    # Get user info for each image
    user_ids = list(set(image.user_id for image in images))
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_dict = {user.id: user for user in users_result.scalars().all()}

    # Build response items
    items = [
        AdminImageListItem(
            id=image.id,
            prompt=image.prompt,
            url=image.url,
            alt_text=image.alt_text,
            status=image.status,
            style=image.style,
            model=image.model,
            width=image.width,
            height=image.height,
            created_at=image.created_at,
            article_id=image.article_id,
            author=create_author_info(users_dict[image.user_id]),
        )
        for image in images
    ]

    return AdminImageListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.delete("/images/{image_id}", response_model=DeleteResponse)
async def delete_image(
    image_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a generated image.

    Removes from storage and database. Action is logged to audit trail.
    """
    # Get image to verify it exists and get details for audit
    result = await db.execute(select(GeneratedImage).where(GeneratedImage.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with ID {image_id} not found",
        )

    image_prompt = image.prompt[:50]  # First 50 chars
    image_user_id = image.user_id
    image_url = image.url

    # Remove from local storage if cached
    if image.local_path:
        try:
            await storage_adapter.delete_image(image.local_path)
        except OSError:
            logger.warning("Failed to delete local image file: %s", image.local_path)

    # Delete image from database
    await db.execute(delete(GeneratedImage).where(GeneratedImage.id == image_id))
    await db.commit()

    # Log to audit
    await log_audit(
        db=db,
        admin_user=admin_user,
        action=AuditAction.IMAGE_DELETED,
        target_type=AuditTargetType.IMAGE,
        target_id=image_id,
        target_user_id=image_user_id,
        details={
            "prompt": image_prompt,
            "url": image_url,
            "deleted_by_admin": admin_user.email,
        },
    )

    logger.info(f"Admin {admin_user.email} deleted image {image_id} ({image_prompt})")

    return DeleteResponse(
        success=True,
        message=f"Image deleted successfully",
        deleted_id=image_id,
    )


# --- Social Post Endpoints ---


@router.get("/social-posts", response_model=AdminSocialPostListResponse)
async def list_all_social_posts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all scheduled social posts across all users.

    Admin-only endpoint for content moderation.
    """
    # Build query with platform filter via join if needed
    if platform:
        # Need to join with post_targets and social_accounts to filter by platform
        query = (
            select(ScheduledPost)
            .join(PostTarget, ScheduledPost.id == PostTarget.scheduled_post_id)
        )
    else:
        query = select(ScheduledPost)

    # Apply filters
    if user_id:
        query = query.where(ScheduledPost.user_id == user_id)
    if status:
        query = query.where(ScheduledPost.status == status)

    # Order by created_at desc
    query = query.order_by(desc(ScheduledPost.created_at))

    # Get total count
    if platform:
        count_query = (
            select(func.count(ScheduledPost.id.distinct()))
            .select_from(ScheduledPost)
            .join(PostTarget, ScheduledPost.id == PostTarget.scheduled_post_id)
        )
    else:
        count_query = select(func.count()).select_from(ScheduledPost)

    if user_id:
        count_query = count_query.where(ScheduledPost.user_id == user_id)
    if status:
        count_query = count_query.where(ScheduledPost.status == status)

    result = await db.execute(count_query)
    total = result.scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    posts = result.scalars().all() if not platform else result.unique().scalars().all()

    # Get user info for each post
    user_ids = list(set(post.user_id for post in posts))
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_dict = {user.id: user for user in users_result.scalars().all()}

    # Get platform count for each post
    post_ids = [post.id for post in posts]
    targets_count_result = await db.execute(
        select(PostTarget.scheduled_post_id, func.count(PostTarget.id))
        .where(PostTarget.scheduled_post_id.in_(post_ids))
        .group_by(PostTarget.scheduled_post_id)
    )
    platform_counts = dict(targets_count_result.all())

    # Build response items
    items = [
        AdminSocialPostListItem(
            id=post.id,
            content=post.content[:100] + "..." if len(post.content) > 100 else post.content,
            status=post.status,
            scheduled_at=post.scheduled_at,
            published_at=post.published_at,
            platform_count=platform_counts.get(post.id, 0),
            created_at=post.created_at,
            updated_at=post.updated_at,
            author=create_author_info(users_dict[post.user_id]),
        )
        for post in posts
    ]

    return AdminSocialPostListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.delete("/social-posts/{post_id}", response_model=DeleteResponse)
async def delete_social_post(
    post_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a scheduled social post.

    Hard delete with cascade. Action is logged to audit trail.
    """
    # Get post to verify it exists and get details for audit
    result = await db.execute(select(ScheduledPost).where(ScheduledPost.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheduled post with ID {post_id} not found",
        )

    post_content = post.content[:50]  # First 50 chars
    post_user_id = post.user_id

    # Delete post (cascade will handle related targets)
    await db.execute(delete(ScheduledPost).where(ScheduledPost.id == post_id))
    await db.commit()

    # Log to audit
    await log_audit(
        db=db,
        admin_user=admin_user,
        action=AuditAction.SOCIAL_POST_DELETED,
        target_type=AuditTargetType.SOCIAL_POST,
        target_id=post_id,
        target_user_id=post_user_id,
        details={
            "content_preview": post_content,
            "deleted_by_admin": admin_user.email,
        },
    )

    logger.info(f"Admin {admin_user.email} deleted social post {post_id}")

    return DeleteResponse(
        success=True,
        message="Social post deleted successfully",
        deleted_id=post_id,
    )


# --- Bulk Delete Endpoint ---


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_content(
    request: BulkDeleteRequest,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk delete content items.

    Supports: articles, outlines, images, social posts.
    All deletions are logged to audit trail.
    """
    if not request.ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No IDs provided for deletion",
        )

    # Map content types to models and audit actions
    content_mapping = {
        "article": (Article, AuditAction.ARTICLE_DELETED, AuditTargetType.ARTICLE),
        "outline": (Outline, AuditAction.OUTLINE_DELETED, AuditTargetType.OUTLINE),
        "image": (GeneratedImage, AuditAction.IMAGE_DELETED, AuditTargetType.IMAGE),
        "social_post": (ScheduledPost, AuditAction.SOCIAL_POST_DELETED, AuditTargetType.SOCIAL_POST),
    }

    if request.content_type not in content_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type: {request.content_type}",
        )

    model, audit_action, target_type = content_mapping[request.content_type]

    # Track results
    deleted_count = 0
    failed_ids = []

    # Delete each item
    for item_id in request.ids:
        try:
            # Get item to verify existence
            result = await db.execute(select(model).where(model.id == item_id))
            item = result.scalar_one_or_none()

            if not item:
                failed_ids.append(item_id)
                continue

            # Store user_id before deletion
            item_user_id = item.user_id

            # Delete item
            await db.execute(delete(model).where(model.id == item_id))

            # Log to audit
            await log_audit(
                db=db,
                admin_user=admin_user,
                action=audit_action,
                target_type=target_type,
                target_id=item_id,
                target_user_id=item_user_id,
                details={
                    "bulk_delete": True,
                    "deleted_by_admin": admin_user.email,
                },
            )

            deleted_count += 1

        except Exception as e:
            logger.error(f"Failed to delete {request.content_type} {item_id}: {e}")
            failed_ids.append(item_id)

    # Commit all changes
    await db.commit()

    # Log bulk operation summary
    await log_audit(
        db=db,
        admin_user=admin_user,
        action=AuditAction.BULK_DELETE_CONTENT,
        target_type=target_type,
        target_id=None,
        details={
            "content_type": request.content_type,
            "total_requested": len(request.ids),
            "deleted_count": deleted_count,
            "failed_count": len(failed_ids),
            "deleted_by_admin": admin_user.email,
        },
    )

    logger.info(
        f"Admin {admin_user.email} bulk deleted {deleted_count} {request.content_type}(s), "
        f"{len(failed_ids)} failed"
    )

    return BulkDeleteResponse(
        success=deleted_count > 0,
        deleted_count=deleted_count,
        failed_count=len(failed_ids),
        failed_ids=failed_ids,
        message=f"Deleted {deleted_count} {request.content_type}(s). {len(failed_ids)} failed.",
    )
