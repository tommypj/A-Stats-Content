"""
Social media scheduling API schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================
# Account Connection Schemas
# ============================================


class ConnectAccountResponse(BaseModel):
    """Response for initiating OAuth connection."""

    authorization_url: str = Field(..., description="OAuth authorization URL")
    state: str = Field(..., description="CSRF state token")


class SocialAccountResponse(BaseModel):
    """Social media account details."""

    id: str
    platform: str
    project_id: str | None = None
    platform_username: str | None = None
    platform_display_name: str | None = None
    profile_image_url: str | None = None
    is_active: bool
    last_verified_at: datetime | None = None
    verification_error: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SocialAccountListResponse(BaseModel):
    """List of connected social accounts."""

    accounts: list[SocialAccountResponse]
    total: int


class DisconnectAccountResponse(BaseModel):
    """Response for disconnecting account."""

    message: str
    disconnected_at: datetime


class VerifyAccountResponse(BaseModel):
    """Response for account verification."""

    is_valid: bool
    last_verified_at: datetime
    error_message: str | None = None


# ============================================
# Post Scheduling Schemas
# ============================================


class PostTargetRequest(BaseModel):
    """Target platform for a post."""

    account_id: str = Field(..., description="Social account ID")
    platform_content: str | None = Field(
        None, description="Custom content for this platform (overrides main content)"
    )
    platform_metadata: dict | None = Field(
        None, description="Platform-specific metadata (hashtags, etc.)"
    )


class CreatePostRequest(BaseModel):
    """Request to create a scheduled post."""

    content: str = Field(..., min_length=1, max_length=10000)
    account_ids: list[str] = Field(..., min_length=1, description="Target account IDs")
    scheduled_at: datetime | None = Field(None, description="When to publish (None = draft)")
    media_urls: list[str] | None = Field(None, max_length=10)
    link_url: str | None = Field(None, max_length=2048)
    article_id: str | None = None
    project_id: str | None = Field(None, description="Project ID for project content")
    targets: list[PostTargetRequest] | None = Field(None, description="Platform-specific overrides")

    # SM-33: Validate media_urls as a list of valid HTTP/HTTPS URL strings
    @field_validator("media_urls")
    @classmethod
    def validate_media_urls(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("media_urls must be a list")
        for url in v:
            if not isinstance(url, str):
                raise ValueError("Each media URL must be a string")
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Invalid media URL: {url}")
        return v


class UpdatePostRequest(BaseModel):
    """Request to update a scheduled post."""

    content: str | None = Field(None, min_length=1, max_length=10000)
    scheduled_at: datetime | None = None
    media_urls: list[str] | None = Field(None, max_length=10)
    link_url: str | None = Field(None, max_length=2048)
    status: str | None = None


class PostTargetResponse(BaseModel):
    """Response for a post target."""

    id: str
    social_account_id: str
    platform: str
    platform_username: str | None = None
    platform_content: str | None = None
    is_published: bool
    published_at: datetime | None = None
    platform_post_id: str | None = None
    platform_post_url: str | None = None
    publish_error: str | None = None
    analytics_data: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class ScheduledPostResponse(BaseModel):
    """Scheduled post details."""

    id: str
    content: str
    project_id: str | None = None
    media_urls: list[str] | None = None
    link_url: str | None = None
    scheduled_at: datetime | None = None
    status: str
    published_at: datetime | None = None
    publish_error: str | None = None
    article_id: str | None = None
    targets: list[PostTargetResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduledPostListResponse(BaseModel):
    """Paginated list of scheduled posts."""

    posts: list[ScheduledPostResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================
# Calendar Schemas
# ============================================


class CalendarDayPost(BaseModel):
    """Post summary for calendar view."""

    id: str
    content_preview: str = Field(..., description="First 100 chars of content")
    scheduled_at: datetime
    status: str
    platforms: list[str] = Field(..., description="List of platform names")


class CalendarDay(BaseModel):
    """Calendar day with posts."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    posts: list[CalendarDayPost]
    post_count: int


class CalendarResponse(BaseModel):
    """Calendar view response."""

    days: list[CalendarDay]
    start_date: str
    end_date: str


# ============================================
# Analytics Schemas
# ============================================


class PlatformAnalytics(BaseModel):
    """Analytics for a single platform."""

    platform: str
    post_id: str
    post_url: str | None = None
    likes: int | None = None
    shares: int | None = None
    comments: int | None = None
    impressions: int | None = None
    clicks: int | None = None
    engagement_rate: float | None = None
    fetched_at: datetime | None = None


class PostAnalyticsResponse(BaseModel):
    """Analytics for a posted content."""

    post_id: str
    published_at: datetime | None = None
    platforms: list[PlatformAnalytics]
    total_likes: int = 0
    total_shares: int = 0
    total_comments: int = 0
    total_impressions: int = 0
    total_clicks: int = 0
    average_engagement_rate: float | None = None


# ============================================
# Utility Schemas
# ============================================


class PreviewRequest(BaseModel):
    """Request to preview a post."""

    content: str
    platform: str


class PlatformLimits(BaseModel):
    """Platform character and media limits."""

    chars: int
    images: int
    video: int


class PreviewResponse(BaseModel):
    """Post preview response."""

    platform: str
    content: str
    char_count: int
    char_limit: int
    is_valid: bool
    warnings: list[str] = []
    limits: PlatformLimits


class BestTimeSlot(BaseModel):
    """Recommended posting time slot."""

    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    engagement_score: float = Field(..., description="Predicted engagement score")
    post_count: int = Field(..., description="Historical posts at this time")


class BestTimesResponse(BaseModel):
    """Best posting times recommendation."""

    platform: str
    time_slots: list[BestTimeSlot]
    timezone: str = "UTC"
