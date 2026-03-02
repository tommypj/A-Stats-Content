"""
Admin content moderation schemas.
"""

from datetime import datetime

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
    seo_score: float | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    author: AdminArticleAuthorInfo

    model_config = ConfigDict(from_attributes=True)


class AdminArticleListResponse(BaseModel):
    """Paginated article list response."""

    items: list[AdminArticleListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminArticleDetail(BaseModel):
    """Detailed article view for admin."""

    id: str
    title: str
    slug: str | None = None
    keyword: str
    meta_description: str | None = None
    content: str | None = None
    content_html: str | None = None
    status: str
    word_count: int
    read_time: int | None = None
    seo_score: float | None = None
    seo_analysis: dict | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    published_url: str | None = None
    wordpress_post_id: int | None = None
    outline_id: str | None = None
    featured_image_id: str | None = None
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

    items: list[AdminOutlineListItem]
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
    alt_text: str | None = None
    status: str
    style: str | None = None
    model: str | None = None
    width: int | None = None
    height: int | None = None
    created_at: datetime
    article_id: str | None = None
    author: AdminArticleAuthorInfo

    model_config = ConfigDict(from_attributes=True)


class AdminImageListResponse(BaseModel):
    """Paginated image list response."""

    items: list[AdminImageListItem]
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
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    platform_count: int = 0
    created_at: datetime
    updated_at: datetime
    author: AdminArticleAuthorInfo

    model_config = ConfigDict(from_attributes=True)


class AdminSocialPostListResponse(BaseModel):
    """Paginated social post list response."""

    items: list[AdminSocialPostListItem]
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
    ids: list[str] = Field(
        ..., min_length=1, max_length=100, description="List of content IDs to delete (max 100)"
    )


class BulkDeleteResponse(BaseModel):
    """Response from bulk delete operation."""

    success: bool
    deleted_count: int
    failed_count: int = 0
    failed_ids: list[str] = Field(default_factory=list)
    message: str


# --- Common Responses ---


class DeleteResponse(BaseModel):
    """Standard delete response."""

    success: bool
    message: str
    deleted_id: str
