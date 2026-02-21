"""
Admin content moderation schemas.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# --- Article Schemas ---


class AdminArticleAuthorInfo(BaseModel):
    """Author information for admin article view."""

    user_id: str
    email: str
    name: str
    subscription_tier: str


class AdminArticleListItem(BaseModel):
    """Article list item for admin view."""

    id: str
    title: str
    keyword: str
    status: str
    word_count: int
    seo_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    author: AdminArticleAuthorInfo

    model_config = ConfigDict(from_attributes=True)


class AdminArticleListResponse(BaseModel):
    """Paginated article list response."""

    items: List[AdminArticleListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminArticleDetail(BaseModel):
    """Detailed article view for admin."""

    id: str
    title: str
    slug: Optional[str] = None
    keyword: str
    meta_description: Optional[str] = None
    content: Optional[str] = None
    content_html: Optional[str] = None
    status: str
    word_count: int
    read_time: Optional[int] = None
    seo_score: Optional[float] = None
    seo_analysis: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    published_url: Optional[str] = None
    wordpress_post_id: Optional[int] = None
    outline_id: Optional[str] = None
    featured_image_id: Optional[str] = None
    author: AdminArticleAuthorInfo
    image_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# --- Outline Schemas ---


class AdminOutlineListItem(BaseModel):
    """Outline list item for admin view."""

    id: str
    title: str
    keyword: str
    status: str
    word_count_target: int
    section_count: int
    created_at: datetime
    updated_at: datetime
    author: AdminArticleAuthorInfo

    model_config = ConfigDict(from_attributes=True)


class AdminOutlineListResponse(BaseModel):
    """Paginated outline list response."""

    items: List[AdminOutlineListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Image Schemas ---


class AdminImageListItem(BaseModel):
    """Image list item for admin view."""

    id: str
    prompt: str
    url: str
    alt_text: Optional[str] = None
    status: str
    style: Optional[str] = None
    model: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: datetime
    article_id: Optional[str] = None
    author: AdminArticleAuthorInfo

    model_config = ConfigDict(from_attributes=True)


class AdminImageListResponse(BaseModel):
    """Paginated image list response."""

    items: List[AdminImageListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Social Post Schemas ---


class AdminSocialPostListItem(BaseModel):
    """Social post list item for admin view."""

    id: str
    content: str
    status: str
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    platform_count: int = 0
    created_at: datetime
    updated_at: datetime
    author: AdminArticleAuthorInfo

    model_config = ConfigDict(from_attributes=True)


class AdminSocialPostListResponse(BaseModel):
    """Paginated social post list response."""

    items: List[AdminSocialPostListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Bulk Delete Schemas ---


class BulkDeleteRequest(BaseModel):
    """Request to bulk delete content."""

    content_type: str = Field(
        ...,
        description="Type of content to delete",
        pattern="^(article|outline|image|social_post)$",
    )
    ids: List[str] = Field(..., min_items=1, description="List of content IDs to delete")


class BulkDeleteResponse(BaseModel):
    """Response from bulk delete operation."""

    success: bool
    deleted_count: int
    failed_count: int = 0
    failed_ids: List[str] = Field(default_factory=list)
    message: str


# --- Common Responses ---


class DeleteResponse(BaseModel):
    """Standard delete response."""

    success: bool
    message: str
    deleted_id: str
