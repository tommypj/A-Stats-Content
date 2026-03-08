"""
Admin blog management API routes.

Provides endpoints for admins to create, edit, publish, and delete blog posts,
categories, and tags. All mutating operations are logged to AdminAuditLog.
"""

import logging
import markdown
import re
from datetime import UTC, datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps_admin import get_current_admin_user
from api.middleware.rate_limit import limiter
from api.routes.blog import _post_to_detail as _public_post_to_detail
from adapters.storage.image_storage import download_image, get_storage_adapter
from api.schemas.blog import (
    AdminBlogCategoryCreate,
    AdminBlogCategoryUpdate,
    AdminBlogPostCreate,
    AdminBlogPostListItem,
    AdminBlogPostListResponse,
    AdminBlogPostUpdate,
    AdminBlogTagCreate,
    BlogCategoryOut,
    BlogPostDetail,
    BlogTagOut,
)
from api.utils import escape_like
from infrastructure.database.connection import get_db
from infrastructure.database.models.admin import AdminAuditLog
from infrastructure.database.models.blog import (
    BlogCategory,
    BlogPost,
    BlogPostStatus,
    BlogPostTag,
    BlogTag,
)
from infrastructure.database.models.content import Article, GeneratedImage
from infrastructure.database.models.user import User
from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/blog", tags=["Admin - Blog"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_permanent_image_url(image: GeneratedImage) -> str | None:
    """Get a permanent URL for a GeneratedImage, preferring local storage over Replicate."""
    if image.local_path:
        return f"{settings.api_base_url.rstrip('/')}/uploads/{image.local_path}"
    return image.url  # fallback to external URL (may expire)


def _slugify(text: str) -> str:
    """Generate a URL-safe slug from text."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _post_to_list_item(post: BlogPost) -> AdminBlogPostListItem:
    return AdminBlogPostListItem(
        id=post.id,
        slug=post.slug,
        title=post.title,
        status=post.status,
        category_name=post.category.name if post.category else None,
        author_name=post.author_name,
        published_at=post.published_at,
        created_at=post.created_at,
    )


def _post_to_detail(post: BlogPost) -> BlogPostDetail:
    return _public_post_to_detail(post)


async def _log_audit(
    db: AsyncSession,
    admin_user: User,
    action: str,
    target_id: str | None,
    details: dict | None = None,
) -> None:
    try:
        audit = AdminAuditLog(
            admin_user_id=admin_user.id,
            action=action,
            target_type="blog_post",
            target_id=target_id,
            details=details,
        )
        db.add(audit)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to log audit action %s: %s", action, exc)


async def _sync_tags(db: AsyncSession, post: BlogPost, tag_ids: list[str]) -> None:
    """Replace the post's tag associations with the given tag_ids."""
    await db.execute(delete(BlogPostTag).where(BlogPostTag.post_id == post.id))
    for tag_id in tag_ids:
        db.add(BlogPostTag(post_id=post.id, tag_id=tag_id))


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------


@router.get("/posts", response_model=AdminBlogPostListResponse)
@limiter.limit("60/minute")
async def admin_list_posts(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    category_id: str | None = Query(None),
    search: str | None = Query(None),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all blog posts (any status)."""
    base_q = (
        select(BlogPost)
        .where(BlogPost.deleted_at.is_(None))
        .options(selectinload(BlogPost.category))
    )

    if status_filter:
        base_q = base_q.where(BlogPost.status == status_filter)

    if category_id:
        base_q = base_q.where(BlogPost.category_id == category_id)

    if search:
        term = f"%{escape_like(search)}%"
        base_q = base_q.where(
            or_(BlogPost.title.ilike(term), BlogPost.excerpt.ilike(term))
        )

    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    posts_q = base_q.order_by(BlogPost.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    posts = (await db.execute(posts_q)).scalars().all()

    return AdminBlogPostListResponse(
        items=[_post_to_list_item(p) for p in posts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 1,
    )


@router.post("/posts", response_model=BlogPostDetail, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def admin_create_post(
    request: Request,
    body: AdminBlogPostCreate,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new blog post (draft)."""
    slug = body.slug or _slugify(body.title)
    # Ensure slug uniqueness
    existing = (await db.execute(select(BlogPost).where(BlogPost.slug == slug))).scalar_one_or_none()
    if existing:
        slug = f"{slug}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

    post = BlogPost(
        slug=slug,
        title=body.title,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        excerpt=body.excerpt,
        content_html=body.content_html,
        status=BlogPostStatus.DRAFT,
        featured_image_url=body.featured_image_url,
        featured_image_alt=body.featured_image_alt,
        og_image_url=body.og_image_url,
        author_id=admin_user.id,
        author_name=admin_user.name or admin_user.email,
        category_id=body.category_id,
        schema_faq=body.schema_faq,
    )
    db.add(post)
    await db.flush()  # get post.id before sync_tags

    if body.tag_ids:
        await _sync_tags(db, post, body.tag_ids)

    await db.commit()
    await db.refresh(post)

    # Re-load relationships for response
    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.id == post.id)
        .options(
            selectinload(BlogPost.post_tags).selectinload(BlogPostTag.tag),
            selectinload(BlogPost.category),
        )
    )
    post = result.scalar_one()

    await _log_audit(db, admin_user, "blog_post_created", post.id, {"title": post.title})
    return _post_to_detail(post)


@router.get("/posts/{post_id}", response_model=BlogPostDetail)
@limiter.limit("60/minute")
async def admin_get_post(
    post_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single blog post (any status)."""
    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.id == post_id, BlogPost.deleted_at.is_(None))
        .options(
            selectinload(BlogPost.post_tags).selectinload(BlogPostTag.tag),
            selectinload(BlogPost.category),
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return _post_to_detail(post)


@router.patch("/posts/{post_id}", response_model=BlogPostDetail)
@limiter.limit("30/minute")
async def admin_update_post(
    post_id: str,
    request: Request,
    body: AdminBlogPostUpdate,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update blog post fields."""
    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.id == post_id, BlogPost.deleted_at.is_(None))
        .options(
            selectinload(BlogPost.post_tags).selectinload(BlogPostTag.tag),
            selectinload(BlogPost.category),
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    update_data = body.model_dump(exclude_unset=True)
    tag_ids = update_data.pop("tag_ids", None)

    for field, value in update_data.items():
        setattr(post, field, value)

    if tag_ids is not None:
        await _sync_tags(db, post, tag_ids)

    await db.commit()
    await db.refresh(post)

    # Re-load relationships
    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.id == post.id)
        .options(
            selectinload(BlogPost.post_tags).selectinload(BlogPostTag.tag),
            selectinload(BlogPost.category),
        )
    )
    post = result.scalar_one()

    await _log_audit(db, admin_user, "blog_post_updated", post.id, {"title": post.title})
    return _post_to_detail(post)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def admin_delete_post(
    post_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Hard delete a blog post."""
    result = await db.execute(
        select(BlogPost).where(BlogPost.id == post_id, BlogPost.deleted_at.is_(None))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    title = post.title
    await db.execute(delete(BlogPostTag).where(BlogPostTag.post_id == post_id))
    await db.delete(post)
    await db.commit()

    await _log_audit(db, admin_user, "blog_post_deleted", post_id, {"title": title})


@router.post("/posts/{post_id}/publish", response_model=BlogPostDetail)
@limiter.limit("20/minute")
async def admin_publish_post(
    post_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish a draft blog post."""
    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.id == post_id, BlogPost.deleted_at.is_(None))
        .options(
            selectinload(BlogPost.post_tags).selectinload(BlogPostTag.tag),
            selectinload(BlogPost.category),
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = BlogPostStatus.PUBLISHED
    if not post.published_at:
        post.published_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(post)

    await _log_audit(db, admin_user, "blog_post_published", post.id, {"slug": post.slug})
    return _post_to_detail(post)


@router.post("/posts/{post_id}/unpublish", response_model=BlogPostDetail)
@limiter.limit("20/minute")
async def admin_unpublish_post(
    post_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Revert a published post back to draft."""
    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.id == post_id, BlogPost.deleted_at.is_(None))
        .options(
            selectinload(BlogPost.post_tags).selectinload(BlogPostTag.tag),
            selectinload(BlogPost.category),
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = BlogPostStatus.DRAFT
    await db.commit()
    await db.refresh(post)

    await _log_audit(db, admin_user, "blog_post_unpublished", post.id, {"slug": post.slug})
    return _post_to_detail(post)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


@router.get("/categories", response_model=list[BlogCategoryOut])
@limiter.limit("60/minute")
async def admin_list_categories(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all blog categories with post counts."""
    post_count_sq = (
        select(BlogPost.category_id, func.count(BlogPost.id).label("post_count"))
        .where(BlogPost.deleted_at.is_(None))
        .group_by(BlogPost.category_id)
        .subquery()
    )

    result = await db.execute(
        select(BlogCategory, func.coalesce(post_count_sq.c.post_count, 0).label("post_count"))
        .outerjoin(post_count_sq, BlogCategory.id == post_count_sq.c.category_id)
        .order_by(BlogCategory.name)
    )
    rows = result.all()

    return [
        BlogCategoryOut(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            post_count=count or 0,
        )
        for cat, count in rows
    ]


@router.post("/categories", response_model=BlogCategoryOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def admin_create_category(
    request: Request,
    body: AdminBlogCategoryCreate,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new blog category."""
    slug = body.slug or _slugify(body.name)
    cat = BlogCategory(name=body.name, slug=slug, description=body.description)
    db.add(cat)
    try:
        await db.commit()
        await db.refresh(cat)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Category name or slug already exists")

    return BlogCategoryOut(id=cat.id, name=cat.name, slug=cat.slug, description=cat.description, post_count=0)


@router.patch("/categories/{cat_id}", response_model=BlogCategoryOut)
@limiter.limit("20/minute")
async def admin_update_category(
    cat_id: str,
    request: Request,
    body: AdminBlogCategoryUpdate,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a blog category."""
    result = await db.execute(select(BlogCategory).where(BlogCategory.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cat, field, value)

    try:
        await db.commit()
        await db.refresh(cat)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Category name or slug already exists")

    # Get post count
    count_result = await db.execute(
        select(func.count(BlogPost.id))
        .where(BlogPost.category_id == cat.id, BlogPost.deleted_at.is_(None))
    )
    post_count = count_result.scalar_one()

    return BlogCategoryOut(id=cat.id, name=cat.name, slug=cat.slug, description=cat.description, post_count=post_count)


@router.delete("/categories/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def admin_delete_category(
    cat_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a category (blocked if posts reference it)."""
    result = await db.execute(select(BlogCategory).where(BlogCategory.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    post_count_result = await db.execute(
        select(func.count(BlogPost.id))
        .where(BlogPost.category_id == cat_id, BlogPost.deleted_at.is_(None))
    )
    if post_count_result.scalar_one() > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete category with existing posts. Reassign or delete posts first.",
        )

    await db.delete(cat)
    await db.commit()


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


@router.get("/tags", response_model=list[BlogTagOut])
@limiter.limit("60/minute")
async def admin_list_tags(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all blog tags."""
    result = await db.execute(select(BlogTag).order_by(BlogTag.name))
    return [BlogTagOut(id=t.id, name=t.name, slug=t.slug) for t in result.scalars().all()]


@router.post("/tags", response_model=BlogTagOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def admin_create_tag(
    request: Request,
    body: AdminBlogTagCreate,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new blog tag."""
    slug = body.slug or _slugify(body.name)
    tag = BlogTag(name=body.name, slug=slug)
    db.add(tag)
    try:
        await db.commit()
        await db.refresh(tag)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Tag name or slug already exists")

    return BlogTagOut(id=tag.id, name=tag.name, slug=tag.slug)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def admin_delete_tag(
    tag_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a blog tag (removes all associations)."""
    result = await db.execute(select(BlogTag).where(BlogTag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    await db.execute(delete(BlogPostTag).where(BlogPostTag.tag_id == tag_id))
    await db.delete(tag)
    await db.commit()


# ---------------------------------------------------------------------------
# AI Content Generation
# ---------------------------------------------------------------------------


class BlogGenerateRequest(BaseModel):
    title: str
    keyword: str | None = None
    tone: str = "professional"
    target_audience: str | None = None
    word_count: int = 1200
    writing_style: str = "balanced"
    voice: str = "second_person"
    list_usage: str = "balanced"
    custom_instructions: str | None = None
    language: str = "en"
    secondary_keywords: list[str] = []
    entities: list[str] = []


class BlogGenerateResponse(BaseModel):
    content_html: str
    meta_description: str | None = None
    suggested_title: str | None = None
    image_prompt: str | None = None
    flagged_stats: list[str] = []
    url_slug: str | None = None


@router.post("/generate-content", response_model=BlogGenerateResponse)
@limiter.limit("10/minute")
async def admin_generate_blog_content(
    request: Request,
    body: BlogGenerateRequest,
    admin_user: User = Depends(get_current_admin_user),
):
    """Generate full-quality blog post content using the multi-model article generation pipeline."""
    from services.content_pipeline import content_pipeline

    keyword = body.keyword or body.title

    pipeline_result = await content_pipeline.run_full_pipeline(
        keyword=keyword,
        title=body.title,
        tone=body.tone,
        target_audience=body.target_audience,
        word_count_target=body.word_count,
        language=body.language,
        writing_style=body.writing_style,
        voice=body.voice,
        list_usage=body.list_usage,
        custom_instructions=body.custom_instructions,
        secondary_keywords=body.secondary_keywords or None,
        entities=body.entities or None,
    )

    # Convert markdown to HTML
    content_html = markdown.markdown(
        pipeline_result.article.content,
        extensions=["extra", "toc"],
    )

    # Normalize: demote any <h1> to <h2> — the page already has an <h1> (the post title)
    content_html = re.sub(r"<h1(\s[^>]*)?>", r"<h2\1>", content_html)
    content_html = content_html.replace("</h1>", "</h2>")

    return BlogGenerateResponse(
        content_html=content_html,
        meta_description=pipeline_result.outline.meta_description or None,
        suggested_title=pipeline_result.outline.title or None,
        image_prompt=pipeline_result.image_prompt,
        flagged_stats=pipeline_result.flagged_stats,
        url_slug=pipeline_result.url_slug or None,
    )


# ---------------------------------------------------------------------------
# Push Article to Blog
# ---------------------------------------------------------------------------


class FromArticleRequest(BaseModel):
    article_id: str
    category_id: str | None = None
    tag_ids: list[str] = []
    featured_image_url: str | None = None
    featured_image_alt: str | None = None


@router.post("/posts/from-article", response_model=BlogPostDetail, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def admin_post_from_article(
    request: Request,
    body: FromArticleRequest,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a blog post draft from an existing user-generated article."""
    # Fetch article
    result = await db.execute(
        select(Article).where(Article.id == body.article_id, Article.deleted_at.is_(None))
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if not article.content_html:
        raise HTTPException(status_code=422, detail="Article has no generated content yet")

    # Resolve featured image: prefer explicitly passed URL, then article's featured image
    featured_img_url = body.featured_image_url
    featured_img_alt = body.featured_image_alt
    if not featured_img_url and article.featured_image_id:
        img_result = await db.execute(
            select(GeneratedImage).where(
                GeneratedImage.id == article.featured_image_id,
                GeneratedImage.status == "completed",
            )
        )
        img = img_result.scalar_one_or_none()
        if img:
            featured_img_url = _get_permanent_image_url(img)
            featured_img_alt = img.alt_text or article.title

    # Generate unique slug
    slug = _slugify(article.title)
    existing = (await db.execute(select(BlogPost).where(BlogPost.slug == slug))).scalar_one_or_none()
    if existing:
        slug = f"{slug}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

    post = BlogPost(
        slug=slug,
        title=article.title,
        meta_description=article.meta_description,
        content_html=article.content_html,
        status=BlogPostStatus.DRAFT,
        featured_image_url=featured_img_url,
        featured_image_alt=featured_img_alt,
        author_id=admin_user.id,
        author_name=admin_user.name or admin_user.email,
        category_id=body.category_id,
    )
    db.add(post)
    await db.flush()

    if body.tag_ids:
        await _sync_tags(db, post, body.tag_ids)

    await db.commit()
    await db.refresh(post)

    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.id == post.id)
        .options(
            selectinload(BlogPost.post_tags).selectinload(BlogPostTag.tag),
            selectinload(BlogPost.category),
        )
    )
    post = result.scalar_one()

    await _log_audit(db, admin_user, "blog_post_from_article", post.id, {
        "title": post.title,
        "article_id": body.article_id,
    })
    return _post_to_detail(post)


# ---------------------------------------------------------------------------
# Persist Blog Images (fix expired Replicate URLs)
# ---------------------------------------------------------------------------


@router.post("/posts/persist-images")
@limiter.limit("5/minute")
async def admin_persist_blog_images(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download and permanently store all blog post featured images that use
    temporary external URLs (e.g. Replicate). Updates the blog post records
    to point to the permanent backend-hosted URL.
    """
    storage = get_storage_adapter()
    api_base = settings.api_base_url.rstrip("/")

    # Find blog posts with external featured_image_url (not already on our backend)
    result = await db.execute(
        select(BlogPost).where(
            BlogPost.featured_image_url.isnot(None),
            BlogPost.featured_image_url != "",
            ~BlogPost.featured_image_url.startswith(api_base),
            BlogPost.deleted_at.is_(None),
        )
    )
    posts = result.scalars().all()

    persisted = 0
    failed = 0
    already_local = 0

    for post in posts:
        url = post.featured_image_url
        if not url:
            continue

        # Check if there's already a local copy via GeneratedImage
        # (search by the same Replicate URL)
        img_result = await db.execute(
            select(GeneratedImage).where(
                GeneratedImage.url == url,
                GeneratedImage.local_path.isnot(None),
            ).limit(1)
        )
        existing_img = img_result.scalar_one_or_none()

        if existing_img and existing_img.local_path:
            # Use existing permanent copy
            post.featured_image_url = f"{api_base}/uploads/{existing_img.local_path}"
            persisted += 1
            already_local += 1
            continue

        # Try to download and store permanently
        try:
            image_data = await download_image(url)
            slug_part = (post.slug or "blog")[:40]
            filename = f"blog_{slug_part}.png"
            local_path = await storage.save_image(image_data, filename)
            post.featured_image_url = f"{api_base}/uploads/{local_path}"
            persisted += 1
        except Exception as e:
            logger.warning("Failed to persist image for blog post %s: %s", post.id, str(e)[:200])
            failed += 1

    await db.commit()

    await _log_audit(db, admin_user, "blog_persist_images", None, {
        "total_found": len(posts),
        "persisted": persisted,
        "already_local": already_local,
        "failed": failed,
    })

    return {
        "total_found": len(posts),
        "persisted": persisted,
        "already_local": already_local,
        "failed": failed,
    }
