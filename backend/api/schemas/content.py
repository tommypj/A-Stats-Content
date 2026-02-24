"""
Content API schemas for outlines, articles, and images.
"""

from datetime import datetime
from typing import Literal, Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Outline Schemas
# ============================================================================


class OutlineSectionSchema(BaseModel):
    """Outline section structure."""

    heading: str = Field(..., description="H2 heading for the section")
    subheadings: List[str] = Field(default_factory=list, description="H3 subheadings")
    notes: str = Field(default="", description="Content notes for this section")
    word_count_target: int = Field(default=200, ge=50, le=2000)


class OutlineCreateRequest(BaseModel):
    """Request to create/generate an outline."""

    keyword: str = Field(..., min_length=2, max_length=255)
    target_audience: Optional[str] = Field(None, max_length=500)
    tone: str = Field(default="professional", max_length=50)
    word_count_target: int = Field(default=1500, ge=500, le=10000)
    language: Optional[str] = Field(None, max_length=10, description="Content language code (e.g., 'en', 'ro')")
    auto_generate: bool = Field(default=True, description="Auto-generate with AI")
    project_id: Optional[str] = Field(None, description="Project ID for project content")


class OutlineUpdateRequest(BaseModel):
    """Request to update an outline."""

    title: Optional[str] = Field(None, max_length=500)
    keyword: Optional[str] = Field(None, min_length=2, max_length=255)
    target_audience: Optional[str] = Field(None, max_length=500)
    tone: Optional[str] = Field(None, max_length=50)
    sections: Optional[List[OutlineSectionSchema]] = None
    word_count_target: Optional[int] = Field(None, ge=500, le=10000)


class OutlineResponse(BaseModel):
    """Outline response."""

    id: str
    user_id: str
    project_id: Optional[str] = None
    title: str
    keyword: str
    target_audience: Optional[str]
    tone: str
    sections: Optional[List[Dict[str, Any]]]
    status: str
    word_count_target: int
    estimated_read_time: Optional[int]
    ai_model: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutlineListResponse(BaseModel):
    """List of outlines response."""

    items: List[OutlineResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# Article Schemas
# ============================================================================


class ArticleGenerateRequest(BaseModel):
    """Request to generate an article from an outline."""

    outline_id: str = Field(..., description="UUID of the outline to use")
    tone: Optional[str] = Field(None, max_length=50)
    target_audience: Optional[str] = Field(None, max_length=500)
    writing_style: Optional[str] = Field(
        None,
        max_length=50,
        description="Writing style: editorial, narrative, listicle, or balanced",
    )
    voice: Optional[str] = Field(
        None,
        max_length=50,
        description="Voice: first_person, second_person, third_person",
    )
    list_usage: Optional[str] = Field(
        None,
        max_length=50,
        description="List usage preference: minimal, balanced, heavy",
    )
    custom_instructions: Optional[str] = Field(
        None,
        max_length=1000,
        description="Custom instructions for the AI writer",
    )
    language: Optional[str] = Field(None, max_length=10, description="Content language code (e.g., 'en', 'ro')")


class ArticleCreateRequest(BaseModel):
    """Request to create an article manually."""

    title: str = Field(..., min_length=5, max_length=500)
    keyword: str = Field(..., min_length=2, max_length=255)
    content: Optional[str] = None
    meta_description: Optional[str] = Field(None, max_length=320)
    outline_id: Optional[str] = None
    project_id: Optional[str] = Field(None, description="Project ID for project content")


class ArticleUpdateRequest(BaseModel):
    """Request to update an article."""

    title: Optional[str] = Field(None, min_length=5, max_length=500)
    keyword: Optional[str] = Field(None, min_length=2, max_length=255)
    meta_description: Optional[str] = Field(None, max_length=320)
    content: Optional[str] = None
    status: Optional[Literal["draft", "completed", "published"]] = None


class ArticleSEOAnalysis(BaseModel):
    """SEO analysis result."""

    keyword_density: float
    title_has_keyword: bool
    meta_description_length: int
    headings_structure: str
    internal_links: int
    external_links: int
    image_alt_texts: bool
    readability_score: float
    suggestions: List[str]


class ArticleResponse(BaseModel):
    """Article response."""

    id: str
    user_id: str
    project_id: Optional[str] = None
    outline_id: Optional[str]
    title: str
    slug: Optional[str]
    keyword: str
    meta_description: Optional[str]
    content: Optional[str]
    content_html: Optional[str]
    status: str
    word_count: int
    read_time: Optional[int]
    seo_score: Optional[float]
    seo_analysis: Optional[Dict[str, Any]]
    ai_model: Optional[str]
    image_prompt: Optional[str] = None
    published_at: Optional[datetime]
    published_url: Optional[str]
    featured_image_id: Optional[str]
    social_posts: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArticleListItemResponse(BaseModel):
    """Article response for list endpoints (excludes heavy content fields)."""

    id: str
    user_id: str
    project_id: Optional[str] = None
    outline_id: Optional[str]
    title: str
    slug: Optional[str]
    keyword: str
    meta_description: Optional[str]
    status: str
    word_count: int
    read_time: Optional[int]
    seo_score: Optional[float]
    seo_analysis: Optional[Dict[str, Any]]
    ai_model: Optional[str]
    image_prompt: Optional[str] = None
    published_at: Optional[datetime]
    published_url: Optional[str]
    featured_image_id: Optional[str]
    social_posts: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArticleListResponse(BaseModel):
    """List of articles response."""

    items: List[ArticleListItemResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SocialPostContent(BaseModel):
    """Social post content for a single platform."""

    text: str
    generated_at: Optional[datetime] = None


class SocialPostsResponse(BaseModel):
    """Social posts for all platforms."""

    twitter: Optional[SocialPostContent] = None
    linkedin: Optional[SocialPostContent] = None
    facebook: Optional[SocialPostContent] = None
    instagram: Optional[SocialPostContent] = None


class SocialPostUpdateRequest(BaseModel):
    """Request to update a single platform's social post text."""

    platform: str = Field(..., pattern="^(twitter|linkedin|facebook|instagram)$")
    text: str = Field(..., min_length=1, max_length=5000)


class ArticleImproveRequest(BaseModel):
    """Request to improve article content."""

    improvement_type: Literal["seo", "readability", "engagement", "grammar"] = Field(
        default="seo",
        description="Type: seo, readability, engagement, grammar",
    )


# ============================================================================
# Bulk Operation Schemas
# ============================================================================


class BulkDeleteRequest(BaseModel):
    """Request body for bulk-delete endpoints."""

    ids: List[str] = Field(..., min_length=1, description="List of resource IDs to delete")


class BulkDeleteResponse(BaseModel):
    """Response returned by bulk-delete endpoints."""

    deleted: int


# ============================================================================
# Article Revision Schemas
# ============================================================================


class ArticleRevisionResponse(BaseModel):
    """Lightweight revision item — for list endpoints (no heavy content fields)."""

    id: str
    article_id: str
    revision_type: str
    word_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArticleRevisionDetailResponse(ArticleRevisionResponse):
    """Full revision with content — for single-revision fetch and restore preview."""

    content: Optional[str] = None
    content_html: Optional[str] = None
    title: str
    meta_description: Optional[str] = None


class ArticleRevisionListResponse(BaseModel):
    """Paginated list of revisions."""

    items: List[ArticleRevisionResponse]
    total: int


# ============================================================================
# Generated Image Schemas
# ============================================================================


class ImageGenerateRequest(BaseModel):
    """Request to generate an image."""

    prompt: str = Field(..., min_length=10, max_length=1000)
    style: Optional[str] = Field(None, max_length=50)
    article_id: Optional[str] = None
    project_id: Optional[str] = Field(None, description="Project ID for project content")
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)


class ImageSetFeaturedRequest(BaseModel):
    """Request to set an image as featured for an article."""

    article_id: str = Field(..., description="ID of the article to set the featured image for")


class ImageResponse(BaseModel):
    """Generated image response."""

    id: str
    user_id: str
    project_id: Optional[str] = None
    article_id: Optional[str]
    prompt: str
    url: str
    local_path: Optional[str]
    alt_text: Optional[str]
    style: Optional[str]
    model: Optional[str]
    width: Optional[int]
    height: Optional[int]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImageListResponse(BaseModel):
    """List of images response."""

    items: List[ImageResponse]
    total: int
    page: int
    page_size: int
    pages: int
