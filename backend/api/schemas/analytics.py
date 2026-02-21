"""
Analytics API schemas for Google Search Console integration.
"""

from datetime import date as date_type, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# GSC Connection Schemas
# ============================================================================


class GSCConnectResponse(BaseModel):
    """Response containing OAuth authorization URL."""

    auth_url: str = Field(..., description="Google OAuth authorization URL")
    state: str = Field(..., description="OAuth state parameter for security")


class GSCCallbackRequest(BaseModel):
    """OAuth callback request parameters."""

    code: str = Field(..., description="Authorization code from Google")
    state: str = Field(..., description="State parameter from OAuth flow")


class GSCConnectionStatus(BaseModel):
    """GSC connection status response."""

    connected: bool = Field(..., description="Whether GSC is connected")
    site_url: Optional[str] = Field(None, description="Connected site URL")
    last_sync: Optional[datetime] = Field(None, description="Last sync timestamp")
    connected_at: Optional[datetime] = Field(None, description="Connection timestamp")

    model_config = ConfigDict(from_attributes=True)


class GSCSiteResponse(BaseModel):
    """GSC site verification response."""

    site_url: str = Field(..., description="Site URL")
    permission_level: str = Field(..., description="User's permission level")


class GSCSiteListResponse(BaseModel):
    """List of verified sites from GSC."""

    sites: List[GSCSiteResponse] = Field(default_factory=list)


class GSCSelectSiteRequest(BaseModel):
    """Request to select a site to track."""

    site_url: str = Field(..., min_length=1, max_length=500, description="Site URL to track")


class GSCSyncResponse(BaseModel):
    """Response from triggering a GSC data sync."""

    message: str = Field(..., description="Status message")
    site_url: str = Field(..., description="Site being synced")
    sync_started_at: datetime = Field(..., description="Sync start timestamp")


class GSCDisconnectResponse(BaseModel):
    """Response from disconnecting GSC."""

    message: str = Field(default="GSC disconnected successfully")
    disconnected_at: datetime = Field(..., description="Disconnection timestamp")


# ============================================================================
# Analytics Data Schemas
# ============================================================================


class KeywordRankingResponse(BaseModel):
    """Keyword ranking data response."""

    id: str
    keyword: str
    date: date_type
    clicks: int
    impressions: int
    ctr: float
    position: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KeywordRankingListResponse(BaseModel):
    """List of keyword rankings with pagination."""

    items: List[KeywordRankingResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PagePerformanceResponse(BaseModel):
    """Page performance data response."""

    id: str
    page_url: str
    date: date_type
    clicks: int
    impressions: int
    ctr: float
    position: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PagePerformanceListResponse(BaseModel):
    """List of page performances with pagination."""

    items: List[PagePerformanceResponse]
    total: int
    page: int
    page_size: int
    pages: int


class DailyAnalyticsResponse(BaseModel):
    """Daily analytics data response."""

    id: str
    date: date_type
    total_clicks: int
    total_impressions: int
    avg_ctr: float
    avg_position: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailyAnalyticsListResponse(BaseModel):
    """List of daily analytics with pagination."""

    items: List[DailyAnalyticsResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# Analytics Summary/Dashboard Schemas
# ============================================================================


class TrendData(BaseModel):
    """Trend data for a metric."""

    current: float = Field(..., description="Current period value")
    previous: float = Field(..., description="Previous period value")
    change_percent: float = Field(..., description="Percentage change")
    trend: str = Field(..., description="up, down, or stable")


class AnalyticsSummaryResponse(BaseModel):
    """Analytics overview/dashboard summary response."""

    # Current period totals
    total_clicks: int = Field(default=0, description="Total clicks in period")
    total_impressions: int = Field(default=0, description="Total impressions in period")
    avg_ctr: float = Field(default=0.0, description="Average CTR in period")
    avg_position: float = Field(default=0.0, description="Average position in period")

    # Trends (comparison to previous period)
    clicks_trend: Optional[TrendData] = Field(None, description="Clicks trend")
    impressions_trend: Optional[TrendData] = Field(None, description="Impressions trend")
    ctr_trend: Optional[TrendData] = Field(None, description="CTR trend")
    position_trend: Optional[TrendData] = Field(None, description="Position trend")

    # Top performers
    top_keywords: List[KeywordRankingResponse] = Field(
        default_factory=list,
        description="Top performing keywords",
    )
    top_pages: List[PagePerformanceResponse] = Field(
        default_factory=list,
        description="Top performing pages",
    )

    # Time range
    start_date: date_type = Field(..., description="Start date of data")
    end_date: date_type = Field(..., description="End date of data")
    site_url: str = Field(..., description="Site URL")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Query Parameter Schemas
# ============================================================================


class DateRangeParams(BaseModel):
    """Date range query parameters."""

    start_date: Optional[date_type] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[date_type] = Field(None, description="End date (YYYY-MM-DD)")

    model_config = ConfigDict(from_attributes=True)
