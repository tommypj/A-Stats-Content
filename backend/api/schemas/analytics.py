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


# ============================================================================
# Article Performance Schemas
# ============================================================================


class ArticlePerformanceItem(BaseModel):
    """Article with cross-referenced GSC performance data."""

    article_id: str
    title: str
    keyword: str
    published_url: str
    published_at: Optional[datetime] = None
    seo_score: Optional[float] = None
    total_clicks: int = 0
    total_impressions: int = 0
    avg_ctr: float = 0.0
    avg_position: float = 0.0
    clicks_trend: Optional[TrendData] = None
    position_trend: Optional[TrendData] = None
    performance_status: str = Field(
        default="new",
        description="improving, declining, neutral, or new",
    )


class ArticlePerformanceListResponse(BaseModel):
    """Paginated list of articles with GSC performance data."""

    items: List[ArticlePerformanceItem]
    total: int
    page: int
    page_size: int
    pages: int
    total_published_articles: int = 0
    articles_with_data: int = 0


class ArticleDailyPerformance(BaseModel):
    """Single day of performance data for an article."""

    date: date_type
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    position: float = 0.0


class ArticlePerformanceDetailResponse(BaseModel):
    """Detailed performance data for a single article."""

    article_id: str
    title: str
    keyword: str
    published_url: str
    published_at: Optional[datetime] = None
    seo_score: Optional[float] = None
    total_clicks: int = 0
    total_impressions: int = 0
    avg_ctr: float = 0.0
    avg_position: float = 0.0
    clicks_trend: Optional[TrendData] = None
    impressions_trend: Optional[TrendData] = None
    ctr_trend: Optional[TrendData] = None
    position_trend: Optional[TrendData] = None
    daily_data: List[ArticleDailyPerformance] = Field(default_factory=list)
    start_date: date_type
    end_date: date_type


# ============================================================================
# Content Opportunities Schemas
# ============================================================================


class KeywordOpportunity(BaseModel):
    """A keyword opportunity identified from GSC data."""

    keyword: str
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    position: float = 0.0
    opportunity_type: str = Field(
        ..., description="quick_win, content_gap, or rising"
    )
    position_change: float = 0.0
    has_existing_article: bool = False
    existing_article_id: Optional[str] = None


class ContentOpportunitiesResponse(BaseModel):
    """Categorized content opportunities from keyword data."""

    quick_wins: List[KeywordOpportunity] = Field(default_factory=list)
    content_gaps: List[KeywordOpportunity] = Field(default_factory=list)
    rising_keywords: List[KeywordOpportunity] = Field(default_factory=list)
    total_opportunities: int = 0
    start_date: date_type
    end_date: date_type


class ContentSuggestionRequest(BaseModel):
    """Request for AI-generated content suggestions."""

    keywords: List[str] = Field(..., min_length=1, max_length=20)
    max_suggestions: int = Field(default=5, ge=1, le=10)


class ContentSuggestion(BaseModel):
    """AI-generated content suggestion based on keyword data."""

    suggested_title: str
    target_keyword: str
    content_angle: str
    rationale: str
    estimated_difficulty: str = Field(
        ..., description="easy, medium, or hard"
    )
    estimated_word_count: int = 1500


class ContentSuggestionsResponse(BaseModel):
    """Response containing AI-generated content suggestions."""

    suggestions: List[ContentSuggestion] = Field(default_factory=list)
    based_on_keywords: List[str] = Field(default_factory=list)


# ============================================================================
# Content Decay / Content Health Schemas
# ============================================================================


class ContentDecayAlertResponse(BaseModel):
    """Single content decay alert."""

    id: str
    user_id: str
    project_id: Optional[str] = None
    article_id: Optional[str] = None
    alert_type: str = Field(..., description="position_drop, traffic_drop, ctr_drop, impressions_drop")
    severity: str = Field(..., description="warning or critical")
    keyword: Optional[str] = None
    page_url: Optional[str] = None
    metric_name: str
    metric_before: float
    metric_after: float
    period_days: int
    percentage_change: float
    suggested_actions: Optional[dict] = None
    is_read: bool = False
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    created_at: datetime
    article_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ContentDecayAlertListResponse(BaseModel):
    """Paginated list of content decay alerts."""

    items: list[ContentDecayAlertResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ContentHealthSummaryResponse(BaseModel):
    """Overall content health metrics."""

    health_score: int = Field(..., description="0-100 health score")
    total_published_articles: int = 0
    declining_articles: int = 0
    active_warnings: int = 0
    active_criticals: int = 0
    total_active_alerts: int = 0
    recent_alerts: list[ContentDecayAlertResponse] = Field(default_factory=list)


class DecayRecoverySuggestionsResponse(BaseModel):
    """AI-generated recovery suggestions for a decay alert."""

    suggestions: list[dict] = Field(default_factory=list)


class RunDecayDetectionResponse(BaseModel):
    """Response from triggering decay detection."""

    message: str
    new_alerts: int


# ============================================================================
# AEO (Answer Engine Optimization) Schemas
# ============================================================================


class AEOScoreBreakdown(BaseModel):
    """Breakdown of AEO score components."""

    structure_score: int = 0
    faq_score: int = 0
    entity_score: int = 0
    conciseness_score: int = 0
    schema_score: int = 0
    citation_readiness: int = 0


class AEOScoreResponse(BaseModel):
    """AEO score for a single article."""

    id: str
    article_id: str
    aeo_score: int = Field(..., description="0-100 AEO score")
    score_breakdown: Optional[AEOScoreBreakdown] = None
    suggestions: Optional[list] = None
    previous_score: Optional[int] = None
    scored_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AEOArticleSummary(BaseModel):
    """Article summary with AEO score for overview lists."""

    article_id: str
    title: str
    keyword: str
    aeo_score: int
    score_breakdown: Optional[dict] = None


class AEOOverviewResponse(BaseModel):
    """AEO overview for all user articles."""

    total_scored: int = 0
    average_score: int = 0
    excellent_count: int = 0
    good_count: int = 0
    needs_work_count: int = 0
    score_distribution: dict = Field(default_factory=dict)
    top_articles: list[AEOArticleSummary] = Field(default_factory=list)
    bottom_articles: list[AEOArticleSummary] = Field(default_factory=list)


class AEOSuggestionsResponse(BaseModel):
    """AI-generated AEO improvement suggestions."""

    suggestions: list[dict] = Field(default_factory=list)


# ============================================================================
# Revenue Attribution Schemas
# ============================================================================


class ConversionGoalResponse(BaseModel):
    """Conversion goal configuration."""

    id: str
    user_id: str
    project_id: Optional[str] = None
    name: str
    goal_type: str = Field(..., description="page_visit, form_submit, purchase, or custom")
    goal_config: Optional[dict] = None
    is_active: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversionGoalListResponse(BaseModel):
    """List of conversion goals."""

    items: list[ConversionGoalResponse]
    total: int


class CreateConversionGoalRequest(BaseModel):
    """Request to create a conversion goal."""

    name: str = Field(..., min_length=1, max_length=200)
    goal_type: str = Field(..., description="page_visit, form_submit, purchase, or custom")
    goal_config: Optional[dict] = None


class UpdateConversionGoalRequest(BaseModel):
    """Request to update a conversion goal."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    goal_type: Optional[str] = None
    goal_config: Optional[dict] = None
    is_active: Optional[bool] = None


class ContentConversionResponse(BaseModel):
    """Single content conversion record."""

    id: str
    article_id: Optional[str] = None
    goal_id: str
    page_url: Optional[str] = None
    keyword: Optional[str] = None
    date: date_type
    visits: int = 0
    conversions: int = 0
    conversion_rate: float = 0.0
    revenue: float = 0.0
    attribution_model: str = "last_touch"

    model_config = ConfigDict(from_attributes=True)


class RevenueOverviewResponse(BaseModel):
    """Revenue attribution dashboard overview."""

    total_organic_visits: int = 0
    total_conversions: int = 0
    total_revenue: float = 0.0
    conversion_rate: float = 0.0
    active_goals: int = 0
    top_articles: list[dict] = Field(default_factory=list)
    top_keywords: list[dict] = Field(default_factory=list)
    visits_trend: Optional[TrendData] = None
    conversions_trend: Optional[TrendData] = None
    revenue_trend: Optional[TrendData] = None
    start_date: date_type
    end_date: date_type


class RevenueByArticleItem(BaseModel):
    """Revenue data for a single article."""

    article_id: str
    title: str
    keyword: str
    published_url: Optional[str] = None
    visits: int = 0
    conversions: int = 0
    revenue: float = 0.0
    conversion_rate: float = 0.0


class RevenueByArticleListResponse(BaseModel):
    """Paginated list of articles with revenue data."""

    items: list[RevenueByArticleItem]
    total: int
    page: int
    page_size: int
    pages: int


class RevenueByKeywordItem(BaseModel):
    """Revenue data for a single keyword."""

    keyword: str
    visits: int = 0
    conversions: int = 0
    revenue: float = 0.0
    conversion_rate: float = 0.0


class RevenueByKeywordListResponse(BaseModel):
    """Paginated list of keywords with revenue data."""

    items: list[RevenueByKeywordItem]
    total: int
    page: int
    page_size: int
    pages: int


class ImportConversionsRequest(BaseModel):
    """Request to import conversion data."""

    goal_id: str = Field(..., description="Conversion goal ID")
    conversions: list[dict] = Field(..., min_length=1, max_length=1000, description="List of conversion records")


class ImportConversionsResponse(BaseModel):
    """Response from importing conversion data."""

    imported_count: int = 0
    matched_articles: int = 0
    message: str = "Import completed"


class RevenueReportResponse(BaseModel):
    """Generated revenue report."""

    id: str
    report_type: str
    period_start: date_type
    period_end: date_type
    total_organic_visits: int = 0
    total_conversions: int = 0
    total_revenue: float = 0.0
    top_articles: Optional[list] = None
    top_keywords: Optional[list] = None
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Device / Country Breakdown Schemas
# ============================================================================


class DeviceBreakdownItem(BaseModel):
    """Performance data for a single device type."""

    device: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class DeviceBreakdownResponse(BaseModel):
    """Response containing device breakdown items."""

    items: list[DeviceBreakdownItem]


class CountryBreakdownItem(BaseModel):
    """Performance data for a single country."""

    country: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class CountryBreakdownResponse(BaseModel):
    """Response containing country breakdown items with a total count."""

    items: list[CountryBreakdownItem]
    total: int
