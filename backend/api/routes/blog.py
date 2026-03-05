"""
Public blog API routes.

No authentication required — all endpoints serve published content only.
"""

import logging
import re
from datetime import UTC, datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.middleware.rate_limit import limiter
from api.schemas.blog import (
    BlogCategoryOut,
    BlogPostCard,
    BlogPostDetail,
    BlogPostListResponse,
    BlogTagOut,
)
from api.utils import escape_like
from infrastructure.database.connection import get_db
from infrastructure.database.models.blog import (
    BlogCategory,
    BlogPost,
    BlogPostStatus,
    BlogPostTag,
    BlogTag,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blog", tags=["Blog"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _word_count(html: str | None) -> int:
    """Strip HTML tags and count words."""
    if not html:
        return 0
    text = re.sub(r"<[^>]+>", " ", html)
    return len(text.split())


def _reading_time(html: str | None) -> int:
    """Estimate reading time in minutes (200 wpm average)."""
    words = _word_count(html)
    return max(1, round(words / 200))


def _post_to_card(post: BlogPost) -> BlogPostCard:
    tags = [BlogTagOut(id=pt.tag.id, name=pt.tag.name, slug=pt.tag.slug) for pt in (post.post_tags or []) if pt.tag]
    category = None
    if post.category:
        category = BlogCategoryOut(
            id=post.category.id,
            name=post.category.name,
            slug=post.category.slug,
            description=post.category.description,
        )
    return BlogPostCard(
        id=post.id,
        slug=post.slug,
        title=post.title,
        excerpt=post.excerpt,
        meta_description=post.meta_description,
        featured_image_url=post.featured_image_url,
        featured_image_alt=post.featured_image_alt,
        category=category,
        tags=tags,
        author_name=post.author_name,
        published_at=post.published_at,
        reading_time_minutes=_reading_time(post.content_html),
    )


def _post_to_detail(post: BlogPost) -> BlogPostDetail:
    card = _post_to_card(post)
    return BlogPostDetail(
        **card.model_dump(),
        content_html=post.content_html,
        schema_faq=post.schema_faq,
        og_image_url=post.og_image_url,
        meta_title=post.meta_title,
        status=post.status,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------


@router.get("/posts", response_model=BlogPostListResponse)
@limiter.limit("60/minute")
async def list_posts(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    category_slug: str | None = Query(None),
    tag_slug: str | None = Query(None),
    search: str | None = Query(None, max_length=200),
    db: AsyncSession = Depends(get_db),
):
    """List published blog posts (paginated)."""
    base_q = (
        select(BlogPost)
        .where(
            BlogPost.status == BlogPostStatus.PUBLISHED,
            BlogPost.deleted_at.is_(None),
            BlogPost.published_at <= func.now(),
        )
        .options(
            selectinload(BlogPost.post_tags).selectinload(BlogPostTag.tag),
            selectinload(BlogPost.category),
        )
    )

    if category_slug:
        base_q = base_q.join(BlogCategory, BlogPost.category_id == BlogCategory.id).where(
            BlogCategory.slug == category_slug
        )

    if tag_slug:
        base_q = base_q.join(BlogPostTag, BlogPost.id == BlogPostTag.post_id).join(
            BlogTag, BlogPostTag.tag_id == BlogTag.id
        ).where(BlogTag.slug == tag_slug)

    if search:
        term = f"%{escape_like(search)}%"
        base_q = base_q.where(
            or_(
                BlogPost.title.ilike(term),
                BlogPost.excerpt.ilike(term),
                BlogPost.meta_description.ilike(term),
            )
        )

    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    posts_q = base_q.order_by(BlogPost.published_at.desc()).offset((page - 1) * page_size).limit(page_size)
    posts = (await db.execute(posts_q)).scalars().all()

    return BlogPostListResponse(
        items=[_post_to_card(p) for p in posts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 1,
    )


@router.get("/posts/{slug}", response_model=BlogPostDetail)
@limiter.limit("120/minute")
async def get_post(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get a single published blog post by slug."""
    result = await db.execute(
        select(BlogPost)
        .where(
            BlogPost.slug == slug,
            BlogPost.status == BlogPostStatus.PUBLISHED,
            BlogPost.deleted_at.is_(None),
            BlogPost.published_at <= func.now(),
        )
        .options(
            selectinload(BlogPost.post_tags).selectinload(BlogPostTag.tag),
            selectinload(BlogPost.category),
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return _post_to_detail(post)


@router.get("/categories", response_model=list[BlogCategoryOut])
@limiter.limit("60/minute")
async def list_categories(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List all blog categories that have at least one published post."""
    # Subquery: count published posts per category
    post_count_sq = (
        select(BlogPost.category_id, func.count(BlogPost.id).label("post_count"))
        .where(
            BlogPost.status == BlogPostStatus.PUBLISHED,
            BlogPost.deleted_at.is_(None),
            BlogPost.published_at <= func.now(),
        )
        .group_by(BlogPost.category_id)
        .subquery()
    )

    result = await db.execute(
        select(BlogCategory, post_count_sq.c.post_count)
        .join(post_count_sq, BlogCategory.id == post_count_sq.c.category_id)
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


@router.get("/tags", response_model=list[BlogTagOut])
@limiter.limit("60/minute")
async def list_tags(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List all blog tags."""
    result = await db.execute(select(BlogTag).order_by(BlogTag.name))
    return [BlogTagOut(id=t.id, name=t.name, slug=t.slug) for t in result.scalars().all()]


@router.get("/feed.xml")
@limiter.limit("30/minute")
async def rss_feed(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """RSS 2.0 feed of the 20 most recent published blog posts."""
    result = await db.execute(
        select(BlogPost)
        .where(
            BlogPost.status == BlogPostStatus.PUBLISHED,
            BlogPost.deleted_at.is_(None),
            BlogPost.published_at <= func.now(),
        )
        .options(
            selectinload(BlogPost.category),
            selectinload(BlogPost.post_tags).selectinload(BlogPostTag.tag),
        )
        .order_by(BlogPost.published_at.desc())
        .limit(20)
    )
    posts = result.scalars().all()

    base_url = "https://a-stats.app"
    now_rfc822 = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S +0000")

    items_xml = ""
    for post in posts:
        pub_date = (
            post.published_at.strftime("%a, %d %b %Y %H:%M:%S +0000")
            if post.published_at
            else now_rfc822
        )
        desc = post.excerpt or post.meta_description or ""
        # Escape XML special chars
        title_esc = post.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        desc_esc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        author_tag = f"      <author>{post.author_name}</author>\n" if post.author_name else ""
        category_tag = f"      <category>{post.category.name}</category>\n" if post.category else ""
        items_xml += f"""
    <item>
      <title>{title_esc}</title>
      <link>{base_url}/en/blog/{post.slug}</link>
      <guid isPermaLink="true">{base_url}/en/blog/{post.slug}</guid>
      <pubDate>{pub_date}</pubDate>
      <description>{desc_esc}</description>
{author_tag}{category_tag}    </item>"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>A-Stats Blog</title>
    <link>{base_url}/en/blog</link>
    <description>SEO, AEO, and content marketing insights from A-Stats.</description>
    <language>en</language>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
    <atom:link href="{base_url}/api/v1/blog/feed.xml" rel="self" type="application/rss+xml"/>
    {items_xml}
  </channel>
</rss>"""

    return Response(content=rss_xml, media_type="application/rss+xml")
