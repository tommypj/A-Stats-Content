"""
Admin blog management API routes.

Provides endpoints for admins to create, edit, publish, and delete blog posts,
categories, and tags. All mutating operations are logged to AdminAuditLog.
"""

import logging
import re
from datetime import UTC, datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from adapters.ai.anthropic_adapter import content_ai_service
from api.deps_admin import get_current_admin_user
from api.middleware.rate_limit import limiter
from api.routes.blog import _post_to_detail as _public_post_to_detail
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
from infrastructure.database.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/blog", tags=["Admin - Blog"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    word_count: int = 800


class BlogGenerateResponse(BaseModel):
    content_html: str


@router.post("/generate-content", response_model=BlogGenerateResponse)
@limiter.limit("10/minute")
async def admin_generate_blog_content(
    request: Request,
    body: BlogGenerateRequest,
    admin_user: User = Depends(get_current_admin_user),
):
    """Generate HTML blog post content using AI given a title and optional keyword."""
    keyword_line = f"Target keyword: {body.keyword}\n" if body.keyword else ""
    audience_line = f"Target audience: {body.target_audience}\n" if body.target_audience else ""

    prompt = f"""Write a high-quality blog post in HTML format.

Title: {body.title}
{keyword_line}{audience_line}Tone: {body.tone}
Approximate word count: {body.word_count}

Requirements:
- Return only valid HTML content (no <html>/<head>/<body> wrapper tags)
- Use <h2> and <h3> for section headings
- Use <p> for paragraphs
- Use <ul>/<ol> and <li> for lists where appropriate
- Use <strong> and <em> for emphasis
- Write in a {body.tone} tone
- Include an introduction, 3-5 main sections, and a conclusion
- Do not include the title as an <h1> (it will be added separately)
- Do not add any markdown, only HTML tags
- Naturally include the keyword throughout if provided

Output only the HTML content, nothing else."""

    content_html = await content_ai_service.generate_text(prompt, max_tokens=4000, temperature=0.7)

    return BlogGenerateResponse(content_html=content_html)
