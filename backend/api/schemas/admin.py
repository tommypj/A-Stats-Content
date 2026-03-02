"""
Admin API schemas for platform analytics and management.
"""

from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Time Series Data (Shared)
# ============================================================================


class TimeSeriesData(BaseModel):
    """Time series data point for charts."""

    date: date_type = Field(..., description="Date for this data point")
    value: int = Field(..., description="Value at this date")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Dashboard Stats
# ============================================================================


class UserStats(BaseModel):
    """User statistics for dashboard."""

    total_users: int = Field(..., description="Total number of users")
    new_users_this_week: int = Field(..., description="New users in past 7 days")
    new_users_this_month: int = Field(..., description="New users in past 30 days")
    active_users_this_week: int = Field(..., description="Active users in past 7 days")
    verified_users: int = Field(..., description="Email verified users")
    pending_users: int = Field(..., description="Pending verification users")


class ContentStats(BaseModel):
    """Content statistics for dashboard."""

    total_articles: int = Field(..., description="Total articles created")
    total_outlines: int = Field(..., description="Total outlines created")
    total_images: int = Field(..., description="Total images generated")
    articles_this_month: int = Field(..., description="Articles created this month")
    outlines_this_month: int = Field(..., description="Outlines created this month")
    images_this_month: int = Field(..., description="Images generated this month")


class SubscriptionStats(BaseModel):
    """Subscription statistics for dashboard."""

    free_tier: int = Field(..., description="Users on free tier")
    starter_tier: int = Field(..., description="Users on starter tier")
    professional_tier: int = Field(..., description="Users on professional tier")
    enterprise_tier: int = Field(..., description="Users on enterprise tier")
    active_subscriptions: int = Field(..., description="Active paid subscriptions")
    cancelled_subscriptions: int = Field(..., description="Cancelled subscriptions")


class RevenueStats(BaseModel):
    """Revenue statistics for dashboard."""

    monthly_recurring_revenue: float = Field(..., description="Estimated MRR in USD")
    annual_recurring_revenue: float = Field(..., description="Estimated ARR in USD")
    revenue_this_month: float = Field(..., description="Revenue for current month")


class DashboardStatsResponse(BaseModel):
    """Main dashboard statistics."""

    users: UserStats
    content: ContentStats
    subscriptions: SubscriptionStats
    revenue: RevenueStats
    platform_usage_7d: list[TimeSeriesData] = Field(
        ..., description="Daily active users for past 7 days"
    )
    platform_usage_30d: list[TimeSeriesData] = Field(
        ..., description="Daily active users for past 30 days"
    )

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# User Analytics
# ============================================================================


class SignupTrend(BaseModel):
    """Daily signup trend data."""

    date: date_type
    signups: int
    verified: int = Field(..., description="Users who verified email that day")


class RetentionMetrics(BaseModel):
    """User retention metrics."""

    day_1_retention: float = Field(..., description="% users active after 1 day")
    day_7_retention: float = Field(..., description="% users active after 7 days")
    day_30_retention: float = Field(..., description="% users active after 30 days")


class ConversionMetrics(BaseModel):
    """Subscription conversion metrics."""

    free_to_starter: float = Field(..., description="% free users who upgraded to starter")
    free_to_professional: float = Field(
        ..., description="% free users who upgraded to professional"
    )
    free_to_enterprise: float = Field(..., description="% free users who upgraded to enterprise")
    overall_conversion_rate: float = Field(
        ..., description="% free users who upgraded to any paid tier"
    )


class GeographicDistribution(BaseModel):
    """Geographic distribution data."""

    country_code: str = Field(..., description="ISO country code")
    country_name: str = Field(..., description="Country name")
    user_count: int = Field(..., description="Number of users")
    percentage: float = Field(..., description="Percentage of total users")


class UserAnalyticsResponse(BaseModel):
    """User analytics data."""

    signup_trends: list[SignupTrend] = Field(..., description="Daily signups for past 30 days")
    retention_metrics: RetentionMetrics
    conversion_metrics: ConversionMetrics
    geographic_distribution: list[GeographicDistribution] = Field(
        default_factory=list, description="User distribution by country"
    )
    total_users: int = Field(..., description="Total user count")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Content Analytics
# ============================================================================


class ContentTrend(BaseModel):
    """Daily content creation trend."""

    date: date_type
    articles: int
    outlines: int
    images: int


class TopUser(BaseModel):
    """Top user by content creation."""

    user_id: str
    email: str
    name: str
    articles_count: int
    outlines_count: int
    images_count: int
    total_content: int = Field(..., description="Total content items created")
    subscription_tier: str


class ContentStatusBreakdown(BaseModel):
    """Content by status breakdown."""

    status: str
    count: int
    percentage: float


class ContentAnalyticsResponse(BaseModel):
    """Content analytics data."""

    content_trends: list[ContentTrend] = Field(
        ..., description="Daily content creation for past 30 days"
    )
    top_users: list[TopUser] = Field(..., description="Top 10 users by content created")
    article_status_breakdown: list[ContentStatusBreakdown]
    outline_status_breakdown: list[ContentStatusBreakdown]
    total_articles: int
    total_outlines: int
    total_images: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Revenue Analytics
# ============================================================================


class MonthlyRevenue(BaseModel):
    """Monthly revenue data."""

    month: str = Field(..., description="YYYY-MM format")
    revenue: float = Field(..., description="Revenue for this month")
    new_subscriptions: int = Field(..., description="New subscriptions this month")
    churned_subscriptions: int = Field(..., description="Cancelled subscriptions")


class SubscriptionDistribution(BaseModel):
    """Subscription tier distribution for pie chart."""

    tier: str
    count: int
    percentage: float
    monthly_value: float = Field(..., description="Monthly revenue from this tier")


class ChurnIndicator(BaseModel):
    """Churn indicator data."""

    month: str = Field(..., description="YYYY-MM format")
    churned_count: int = Field(..., description="Number of cancellations")
    churn_rate: float = Field(..., description="Churn rate percentage")


class RevenueAnalyticsResponse(BaseModel):
    """Revenue analytics data."""

    monthly_revenue: list[MonthlyRevenue] = Field(
        ..., description="Monthly revenue for past 12 months"
    )
    subscription_distribution: list[SubscriptionDistribution]
    churn_indicators: list[ChurnIndicator] = Field(..., description="Churn data for past 6 months")
    current_mrr: float = Field(..., description="Current monthly recurring revenue")
    current_arr: float = Field(..., description="Current annual recurring revenue")
    revenue_growth_rate: float = Field(..., description="Revenue growth rate (month over month %)")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# System Health
# ============================================================================


class TableStats(BaseModel):
    """Database table statistics."""

    table_name: str
    record_count: int


class StorageStats(BaseModel):
    """Storage usage statistics."""

    total_images: int
    total_storage_mb: float = Field(..., description="Total storage in megabytes")
    average_image_size_kb: float = Field(..., description="Average image size in kilobytes")


class ErrorRate(BaseModel):
    """Error rate data."""

    date: date_type
    error_count: int
    total_requests: int = Field(default=0, description="Total API requests")
    error_rate: float = Field(..., description="Error rate percentage")


class BackgroundJobStatus(BaseModel):
    """Background job status."""

    job_type: str = Field(..., description="Type of background job")
    pending_count: int = Field(..., description="Number of pending jobs")
    failed_count: int = Field(..., description="Number of failed jobs")


class SystemHealthResponse(BaseModel):
    """System health metrics."""

    table_stats: list[TableStats] = Field(..., description="Records per table")
    storage_stats: StorageStats
    recent_error_rates: list[ErrorRate] = Field(
        default_factory=list, description="Error rates for past 7 days"
    )
    background_jobs: list[BackgroundJobStatus] = Field(
        default_factory=list, description="Background job queue status"
    )
    database_size_mb: float = Field(default=0.0, description="Total database size in MB")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# User Management Schemas
# ============================================================================


class UserUpdateRequest(BaseModel):
    """Request to update user details."""

    role: str | None = Field(None, pattern="^(user|admin|super_admin)$")
    subscription_tier: str | None = Field(None, pattern="^(free|starter|professional|enterprise)$")
    is_suspended: bool | None = None
    suspended_reason: str | None = Field(None, max_length=500)


class SuspendUserRequest(BaseModel):
    """Request to suspend a user."""

    reason: str = Field(..., min_length=1, max_length=500)


class UnsuspendUserRequest(BaseModel):
    """Request to unsuspend a user."""

    reason: str | None = Field(None, max_length=500)


class PasswordResetRequest(BaseModel):
    """Request to force password reset for a user."""

    send_email: bool = Field(default=True, description="Send reset email to user")


# ============================================================================
# User Response Schemas
# ============================================================================


class UsageStatsResponse(BaseModel):
    """User usage statistics."""

    articles_generated: int
    outlines_generated: int
    images_generated: int
    usage_reset_date: datetime | None = None


class UserDetailResponse(BaseModel):
    """Detailed user information for admin."""

    id: str
    email: str
    name: str
    avatar_url: str | None = None
    role: str
    status: str
    subscription_tier: str
    subscription_status: str
    subscription_expires: datetime | None = None
    lemonsqueezy_customer_id: str | None = None
    lemonsqueezy_subscription_id: str | None = None
    email_verified: bool
    language: str
    timezone: str
    usage_stats: UsageStatsResponse
    last_login: datetime | None = None
    login_count: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserListItemResponse(BaseModel):
    """User list item for admin."""

    id: str
    email: str
    name: str
    role: str
    status: str
    subscription_tier: str
    email_verified: bool
    last_login: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Paginated user list response."""

    users: list[UserListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Audit Log Schemas
# ============================================================================


class AdminUserInfo(BaseModel):
    """Admin user information in audit log."""

    id: str
    email: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    """Audit log entry response."""

    id: str
    admin_user_id: str | None = None
    admin_user: AdminUserInfo | None = None
    action: str
    target_type: str
    target_id: str | None = None
    description: str
    metadata: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response."""

    logs: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Filter Schemas
# ============================================================================


class UserListFilters(BaseModel):
    """Filters for user list."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = Field(None, description="Search by email or name")
    role: str | None = Field(None, pattern="^(user|admin|super_admin)$")
    subscription_tier: str | None = Field(None, pattern="^(free|starter|professional|enterprise)$")
    status: str | None = Field(None, pattern="^(pending|active|suspended|deleted)$")
    email_verified: bool | None = None
    sort_by: str = Field(
        default="created_at", pattern="^(created_at|email|subscription_tier|last_login)$"
    )
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class AuditLogFilters(BaseModel):
    """Filters for audit log list."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    admin_user_id: str | None = None
    target_type: str | None = None
    action: str | None = None
    target_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# ============================================================================
# Action Response Schemas
# ============================================================================


class UserActionResponse(BaseModel):
    """Generic response for user actions."""

    success: bool
    message: str
    user: UserDetailResponse | None = None


class DeleteUserResponse(BaseModel):
    """Response for user deletion."""

    success: bool
    message: str
    user_id: str
    deleted_at: datetime
