"""
Blog API schemas.

Covers both public-facing and admin endpoints.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared / Public
# ---------------------------------------------------------------------------


class BlogCategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    post_count: int = 0

    model_config = {"from_attributes": True}


class BlogTagOut(BaseModel):
    id: str
    name: str
    slug: str

    model_config = {"from_attributes": True}


class BlogPostCard(BaseModel):
    """Lightweight card used in list views."""

    id: str
    slug: str
    title: str
    excerpt: str | None = None
    meta_description: str | None = None
    featured_image_url: str | None = None
    featured_image_alt: str | None = None
    category: BlogCategoryOut | None = None
    tags: list[BlogTagOut] = []
    author_name: str | None = None
    published_at: datetime | None = None
    reading_time_minutes: int = 0

    model_config = {"from_attributes": True}


class BlogPostDetail(BlogPostCard):
    """Full post detail including body and SEO metadata."""

    content_html: str | None = None
    schema_faq: dict[str, Any] | None = None
    og_image_url: str | None = None
    meta_title: str | None = None
    status: str = "draft"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class BlogPostListResponse(BaseModel):
    items: list[BlogPostCard]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


class AdminBlogPostCreate(BaseModel):
    title: str = Field(..., max_length=500)
    slug: str | None = Field(None, max_length=300)
    meta_title: str | None = Field(None, max_length=200)
    meta_description: str | None = Field(None, max_length=500)
    excerpt: str | None = None
    content_html: str | None = None
    featured_image_url: str | None = Field(None, max_length=2000)
    featured_image_alt: str | None = Field(None, max_length=500)
    og_image_url: str | None = Field(None, max_length=2000)
    category_id: str | None = None
    tag_ids: list[str] = []
    schema_faq: dict[str, Any] | None = None


class AdminBlogPostUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    slug: str | None = Field(None, max_length=300)
    meta_title: str | None = Field(None, max_length=200)
    meta_description: str | None = Field(None, max_length=500)
    excerpt: str | None = None
    content_html: str | None = None
    featured_image_url: str | None = Field(None, max_length=2000)
    featured_image_alt: str | None = Field(None, max_length=500)
    og_image_url: str | None = Field(None, max_length=2000)
    category_id: str | None = None
    tag_ids: list[str] | None = None
    schema_faq: dict[str, Any] | None = None


class AdminBlogPostListItem(BaseModel):
    id: str
    slug: str
    title: str
    status: str
    category_name: str | None = None
    author_name: str | None = None
    published_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminBlogPostListResponse(BaseModel):
    items: list[AdminBlogPostListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminBlogCategoryCreate(BaseModel):
    name: str = Field(..., max_length=200)
    slug: str | None = Field(None, max_length=200)
    description: str | None = None


class AdminBlogCategoryUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    slug: str | None = Field(None, max_length=200)
    description: str | None = None


class AdminBlogTagCreate(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str | None = Field(None, max_length=100)
