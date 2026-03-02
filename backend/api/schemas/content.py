"""
Content API schemas for outlines, articles, and images.
"""

from datetime import datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# Outline Schemas
# ============================================================================


class OutlineSectionSchema(BaseModel):
    """Outline section structure."""

    heading: str = Field(..., description="H2 heading for the section")
    subheadings: list[str] = Field(default_factory=list, description="H3 subheadings")
    notes: str = Field(default="", description="Content notes for this section")
    word_count_target: int = Field(default=200, ge=50, le=2000)


class OutlineCreateRequest(BaseModel):
    """Request to create/generate an outline."""

    keyword: str = Field(..., min_length=2, max_length=255)
    target_audience: str | None = Field(None, max_length=500)
    tone: str = Field(default="professional", max_length=50)
    word_count_target: int = Field(default=1500, ge=500, le=10000)
    language: str | None = Field(
        None, max_length=10, description="Content language code (e.g., 'en', 'ro')"
    )
    auto_generate: bool = Field(default=True, description="Auto-generate with AI")
    project_id: str | None = Field(None, description="Project ID for project content")


class OutlineUpdateRequest(BaseModel):
    """Request to update an outline."""

    title: str | None = Field(None, max_length=500)
    keyword: str | None = Field(None, min_length=2, max_length=255)
    target_audience: str | None = Field(None, max_length=500)
    tone: str | None = Field(None, max_length=50)
    sections: list[OutlineSectionSchema] | None = None
    word_count_target: int | None = Field(None, ge=500, le=10000)


class OutlineResponse(BaseModel):
    """Outline response."""

    id: str
    user_id: str
    project_id: str | None = None
    title: str
    keyword: str
    target_audience: str | None
    tone: str
    sections: list[dict[str, Any]] | None
    status: str
    word_count_target: int
    estimated_read_time: int | None
    ai_model: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutlineListResponse(BaseModel):
    """List of outlines response."""

    items: list[OutlineResponse]
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
    tone: str | None = Field(None, max_length=50)
    target_audience: str | None = Field(None, max_length=500)
    writing_style: str | None = Field(
        None,
        max_length=50,
        description="Writing style: editorial, narrative, listicle, or balanced",
    )
    voice: str | None = Field(
        None,
        max_length=50,
        description="Voice: first_person, second_person, third_person",
    )
    list_usage: str | None = Field(
        None,
        max_length=50,
        description="List usage preference: minimal, balanced, heavy",
    )
    custom_instructions: str | None = Field(
        None,
        max_length=1000,
        description="Custom instructions for the AI writer",
    )
    language: str | None = Field(
        None, max_length=10, description="Content language code (e.g., 'en', 'ro')"
    )

    # GEN-47: Validate enum-like fields against values the AI adapter actually supports
    VALID_WRITING_STYLES: ClassVar[set[str]] = {"editorial", "narrative", "listicle", "balanced"}
    VALID_VOICES: ClassVar[set[str]] = {"first_person", "second_person", "third_person"}
    VALID_LIST_USAGES: ClassVar[set[str]] = {"minimal", "balanced", "heavy"}

    @field_validator("writing_style")
    @classmethod
    def validate_writing_style(cls, v: str | None) -> str | None:
        if v is not None and v not in cls.VALID_WRITING_STYLES:
            raise ValueError(
                f"Invalid writing_style '{v}'. Must be one of: {sorted(cls.VALID_WRITING_STYLES)}"
            )
        return v

    @field_validator("voice")
    @classmethod
    def validate_voice(cls, v: str | None) -> str | None:
        if v is not None and v not in cls.VALID_VOICES:
            raise ValueError(f"Invalid voice '{v}'. Must be one of: {sorted(cls.VALID_VOICES)}")
        return v

    @field_validator("list_usage")
    @classmethod
    def validate_list_usage(cls, v: str | None) -> str | None:
        if v is not None and v not in cls.VALID_LIST_USAGES:
            raise ValueError(
                f"Invalid list_usage '{v}'. Must be one of: {sorted(cls.VALID_LIST_USAGES)}"
            )
        return v


class ArticleCreateRequest(BaseModel):
    """Request to create an article manually."""

    title: str = Field(..., min_length=5, max_length=500)
    keyword: str = Field(..., min_length=2, max_length=255)
    content: str | None = None
    meta_description: str | None = Field(
        None, max_length=160
    )  # GEN-39: SEO meta descriptions should not exceed 160 chars
    outline_id: str | None = None
    project_id: str | None = Field(None, description="Project ID for project content")


class ArticleUpdateRequest(BaseModel):
    """Request to update an article."""

    title: str | None = Field(None, min_length=5, max_length=500)
    keyword: str | None = Field(None, min_length=2, max_length=255)
    meta_description: str | None = Field(
        None, max_length=160
    )  # GEN-39: SEO meta descriptions should not exceed 160 chars
    content: str | None = None
    status: Literal["draft", "completed", "published"] | None = None


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
    suggestions: list[str]


class ArticleResponse(BaseModel):
    """Article response."""

    id: str
    user_id: str
    project_id: str | None = None
    outline_id: str | None
    title: str
    slug: str | None
    keyword: str
    meta_description: str | None
    content: str | None
    content_html: str | None
    status: str
    word_count: int
    read_time: int | None
    seo_score: float | None
    seo_analysis: dict[str, Any] | None
    ai_model: str | None
    image_prompt: str | None = None
    published_at: datetime | None
    published_url: str | None
    featured_image_id: str | None
    social_posts: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArticleListItemResponse(BaseModel):
    """Article response for list endpoints (excludes heavy content fields)."""

    id: str
    user_id: str
    project_id: str | None = None
    outline_id: str | None
    title: str
    slug: str | None
    keyword: str
    meta_description: str | None
    status: str
    word_count: int
    read_time: int | None
    seo_score: float | None
    seo_analysis: dict[str, Any] | None
    ai_model: str | None
    image_prompt: str | None = None
    published_at: datetime | None
    published_url: str | None
    featured_image_id: str | None
    social_posts: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArticleListResponse(BaseModel):
    """List of articles response."""

    items: list[ArticleListItemResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SocialPostContent(BaseModel):
    """Social post content for a single platform."""

    text: str
    generated_at: datetime | None = None


class SocialPostsResponse(BaseModel):
    """Social posts for all platforms."""

    twitter: SocialPostContent | None = None
    linkedin: SocialPostContent | None = None
    facebook: SocialPostContent | None = None
    instagram: SocialPostContent | None = None


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

    ids: list[str] = Field(
        ..., min_length=1, max_length=100, description="List of resource IDs to delete (max 100)"
    )


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

    content: str | None = None
    content_html: str | None = None
    title: str
    meta_description: str | None = None


class ArticleRevisionListResponse(BaseModel):
    """Paginated list of revisions."""

    items: list[ArticleRevisionResponse]
    total: int


# ============================================================================
# Generated Image Schemas
# ============================================================================


class ImageGenerateRequest(BaseModel):
    """Request to generate an image."""

    prompt: str = Field(..., min_length=10, max_length=1000)
    style: str | None = Field(None, max_length=50)
    article_id: str | None = None
    project_id: str | None = Field(None, description="Project ID for project content")
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)


class ImageSetFeaturedRequest(BaseModel):
    """Request to set an image as featured for an article."""

    article_id: str = Field(..., description="ID of the article to set the featured image for")


class ImageResponse(BaseModel):
    """Generated image response."""

    id: str
    user_id: str
    project_id: str | None = None
    article_id: str | None
    prompt: str
    url: str
    local_path: str | None
    alt_text: str | None
    style: str | None
    model: str | None
    width: int | None
    height: int | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImageListResponse(BaseModel):
    """List of images response."""

    items: list[ImageResponse]
    total: int
    page: int
    page_size: int
    pages: int
