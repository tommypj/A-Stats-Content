"""
Social media scheduling API schemas.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


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
    team_id: Optional[str] = None
    platform_username: Optional[str] = None
    platform_display_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: bool
    last_verified_at: Optional[datetime] = None
    verification_error: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SocialAccountListResponse(BaseModel):
    """List of connected social accounts."""

    accounts: List[SocialAccountResponse]
    total: int


class DisconnectAccountResponse(BaseModel):
    """Response for disconnecting account."""

    message: str
    disconnected_at: datetime


class VerifyAccountResponse(BaseModel):
    """Response for account verification."""

    is_valid: bool
    last_verified_at: datetime
    error_message: Optional[str] = None


# ============================================
# Post Scheduling Schemas
# ============================================


class PostTargetRequest(BaseModel):
    """Target platform for a post."""

    account_id: str = Field(..., description="Social account ID")
    platform_content: Optional[str] = Field(
        None, description="Custom content for this platform (overrides main content)"
    )
    platform_metadata: Optional[dict] = Field(
        None, description="Platform-specific metadata (hashtags, etc.)"
    )


class CreatePostRequest(BaseModel):
    """Request to create a scheduled post."""

    content: str = Field(..., min_length=1, max_length=10000)
    account_ids: List[str] = Field(..., min_items=1, description="Target account IDs")
    scheduled_at: Optional[datetime] = Field(None, description="When to publish (None = draft)")
    media_urls: Optional[List[str]] = Field(None, max_items=10)
    link_url: Optional[str] = Field(None, max_length=2048)
    article_id: Optional[str] = None
    team_id: Optional[str] = Field(None, description="Team ID for team content")
    targets: Optional[List[PostTargetRequest]] = Field(
        None, description="Platform-specific overrides"
    )


class UpdatePostRequest(BaseModel):
    """Request to update a scheduled post."""

    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    scheduled_at: Optional[datetime] = None
    media_urls: Optional[List[str]] = Field(None, max_items=10)
    link_url: Optional[str] = Field(None, max_length=2048)
    status: Optional[str] = None


class PostTargetResponse(BaseModel):
    """Response for a post target."""

    id: str
    social_account_id: str
    platform: str
    platform_username: Optional[str] = None
    platform_content: Optional[str] = None
    is_published: bool
    published_at: Optional[datetime] = None
    platform_post_id: Optional[str] = None
    platform_post_url: Optional[str] = None
    publish_error: Optional[str] = None
    analytics_data: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduledPostResponse(BaseModel):
    """Scheduled post details."""

    id: str
    content: str
    team_id: Optional[str] = None
    media_urls: Optional[List[str]] = None
    link_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: str
    published_at: Optional[datetime] = None
    publish_error: Optional[str] = None
    article_id: Optional[str] = None
    targets: List[PostTargetResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduledPostListResponse(BaseModel):
    """Paginated list of scheduled posts."""

    posts: List[ScheduledPostResponse]
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
    platforms: List[str] = Field(..., description="List of platform names")


class CalendarDay(BaseModel):
    """Calendar day with posts."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    posts: List[CalendarDayPost]
    post_count: int


class CalendarResponse(BaseModel):
    """Calendar view response."""

    days: List[CalendarDay]
    start_date: str
    end_date: str


# ============================================
# Analytics Schemas
# ============================================


class PlatformAnalytics(BaseModel):
    """Analytics for a single platform."""

    platform: str
    post_id: str
    post_url: Optional[str] = None
    likes: Optional[int] = None
    shares: Optional[int] = None
    comments: Optional[int] = None
    impressions: Optional[int] = None
    clicks: Optional[int] = None
    engagement_rate: Optional[float] = None
    fetched_at: Optional[datetime] = None


class PostAnalyticsResponse(BaseModel):
    """Analytics for a posted content."""

    post_id: str
    published_at: Optional[datetime] = None
    platforms: List[PlatformAnalytics]
    total_likes: int = 0
    total_shares: int = 0
    total_comments: int = 0
    total_impressions: int = 0
    total_clicks: int = 0
    average_engagement_rate: Optional[float] = None


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
    warnings: List[str] = []
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
    time_slots: List[BestTimeSlot]
    timezone: str = "UTC"
