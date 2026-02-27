"""
Admin platform analytics API routes for Phase 9.

Provides comprehensive analytics endpoints for admin users to monitor
platform health, user activity, content generation, revenue, and system metrics.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request
from api.middleware.rate_limit import limiter
from sqlalchemy import select, func, and_, or_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps_admin import get_current_admin_user
from api.schemas.admin import (
    DashboardStatsResponse,
    UserStats,
    ContentStats,
    SubscriptionStats,
    RevenueStats,
    TimeSeriesData,
    UserAnalyticsResponse,
    SignupTrend,
    RetentionMetrics,
    ConversionMetrics,
    GeographicDistribution,
    ContentAnalyticsResponse,
    ContentTrend,
    TopUser,
    ContentStatusBreakdown,
    RevenueAnalyticsResponse,
    MonthlyRevenue,
    SubscriptionDistribution,
    ChurnIndicator,
    SystemHealthResponse,
    TableStats,
    StorageStats,
    ErrorRate,
    BackgroundJobStatus,
)
from infrastructure.database.connection import get_db
from infrastructure.database.models import User
from infrastructure.database.models.user import UserStatus, SubscriptionTier
from infrastructure.database.models.content import Article, Outline, GeneratedImage, ContentStatus
from infrastructure.database.models.social import ScheduledPost, PostStatus
from infrastructure.database.models.knowledge import KnowledgeSource, SourceStatus

router = APIRouter(prefix="/admin/analytics", tags=["Admin - Analytics"])


# ============================================================================
# Helper Functions
# ============================================================================


def get_date_range(days: int) -> tuple[datetime, datetime]:
    """Get datetime range for the past N days."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def calculate_percentage(part: int, total: int) -> float:
    """Calculate percentage with safe division."""
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


# Subscription tier pricing (monthly) - matches billing.py configuration
TIER_PRICING = {
    SubscriptionTier.FREE.value: 0,
    SubscriptionTier.STARTER.value: 29,
    SubscriptionTier.PROFESSIONAL.value: 79,
    SubscriptionTier.ENTERPRISE.value: 199,
}


# ============================================================================
# Endpoint 1: Main Dashboard Stats
# ============================================================================


@router.get("/dashboard", response_model=DashboardStatsResponse)
@limiter.limit("10/minute")
async def get_dashboard_stats(
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get main admin dashboard statistics.

    Returns comprehensive platform metrics including:
    - Total users and new user signups (week/month)
    - Total content (articles, outlines, images)
    - Active subscriptions by tier
    - Revenue estimates (MRR/ARR)
    - Platform usage trends (7-day, 30-day)

    **Admin access required.**
    """
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # ========== USER STATS ==========
    # Total users
    total_users_result = await db.execute(
        select(func.count(User.id))
    )
    total_users = total_users_result.scalar() or 0

    # New users this week
    new_users_week_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    )
    new_users_week = new_users_week_result.scalar() or 0

    # New users this month
    new_users_month_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= month_ago)
    )
    new_users_month = new_users_month_result.scalar() or 0

    # Active users this week (users who logged in, excluding suspended users)
    # ADM-26: Exclude SUSPENDED users from active user count
    active_users_week_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.last_login >= week_ago,
                User.status == UserStatus.ACTIVE.value,
                User.status != UserStatus.SUSPENDED.value,
            )
        )
    )
    active_users_week = active_users_week_result.scalar() or 0

    # Verified users
    verified_users_result = await db.execute(
        select(func.count(User.id)).where(User.email_verified == True)
    )
    verified_users = verified_users_result.scalar() or 0

    # Pending users
    pending_users_result = await db.execute(
        select(func.count(User.id)).where(User.status == UserStatus.PENDING.value)
    )
    pending_users = pending_users_result.scalar() or 0

    user_stats = UserStats(
        total_users=total_users,
        new_users_this_week=new_users_week,
        new_users_this_month=new_users_month,
        active_users_this_week=active_users_week,
        verified_users=verified_users,
        pending_users=pending_users,
    )

    # ========== CONTENT STATS ==========
    # Total articles
    total_articles_result = await db.execute(select(func.count(Article.id)))
    total_articles = total_articles_result.scalar() or 0

    # Total outlines
    total_outlines_result = await db.execute(select(func.count(Outline.id)))
    total_outlines = total_outlines_result.scalar() or 0

    # Total images
    total_images_result = await db.execute(select(func.count(GeneratedImage.id)))
    total_images = total_images_result.scalar() or 0

    # Articles this month
    articles_month_result = await db.execute(
        select(func.count(Article.id)).where(Article.created_at >= month_ago)
    )
    articles_month = articles_month_result.scalar() or 0

    # Outlines this month
    outlines_month_result = await db.execute(
        select(func.count(Outline.id)).where(Outline.created_at >= month_ago)
    )
    outlines_month = outlines_month_result.scalar() or 0

    # Images this month
    images_month_result = await db.execute(
        select(func.count(GeneratedImage.id)).where(GeneratedImage.created_at >= month_ago)
    )
    images_month = images_month_result.scalar() or 0

    content_stats = ContentStats(
        total_articles=total_articles,
        total_outlines=total_outlines,
        total_images=total_images,
        articles_this_month=articles_month,
        outlines_this_month=outlines_month,
        images_this_month=images_month,
    )

    # ========== SUBSCRIPTION STATS ==========
    # Count users by subscription tier
    subscription_counts_result = await db.execute(
        select(
            User.subscription_tier,
            func.count(User.id)
        ).group_by(User.subscription_tier)
    )
    subscription_counts = {tier: count for tier, count in subscription_counts_result.all()}

    free_tier = subscription_counts.get(SubscriptionTier.FREE.value, 0)
    starter_tier = subscription_counts.get(SubscriptionTier.STARTER.value, 0)
    professional_tier = subscription_counts.get(SubscriptionTier.PROFESSIONAL.value, 0)
    enterprise_tier = subscription_counts.get(SubscriptionTier.ENTERPRISE.value, 0)

    # Active paid subscriptions
    active_subscriptions = starter_tier + professional_tier + enterprise_tier

    # Cancelled subscriptions (users with cancelled status but still on paid tier)
    cancelled_subs_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.subscription_status == "cancelled",
                User.subscription_tier.in_([
                    SubscriptionTier.STARTER.value,
                    SubscriptionTier.PROFESSIONAL.value,
                    SubscriptionTier.ENTERPRISE.value
                ])
            )
        )
    )
    cancelled_subscriptions = cancelled_subs_result.scalar() or 0

    subscription_stats = SubscriptionStats(
        free_tier=free_tier,
        starter_tier=starter_tier,
        professional_tier=professional_tier,
        enterprise_tier=enterprise_tier,
        active_subscriptions=active_subscriptions,
        cancelled_subscriptions=cancelled_subscriptions,
    )

    # ========== REVENUE STATS ==========
    # Calculate MRR (Monthly Recurring Revenue)
    mrr = (
        starter_tier * TIER_PRICING[SubscriptionTier.STARTER.value] +
        professional_tier * TIER_PRICING[SubscriptionTier.PROFESSIONAL.value] +
        enterprise_tier * TIER_PRICING[SubscriptionTier.ENTERPRISE.value]
    )

    # Calculate ARR (Annual Recurring Revenue)
    arr = mrr * 12

    # Revenue this month (same as MRR for subscription model)
    revenue_this_month = mrr

    revenue_stats = RevenueStats(
        monthly_recurring_revenue=float(mrr),
        annual_recurring_revenue=float(arr),
        revenue_this_month=float(revenue_this_month),
    )

    # ========== PLATFORM USAGE TRENDS ==========
    # Single GROUP BY query for active users per day over last 30 days
    start_30d = now - timedelta(days=30)
    usage_daily_result = await db.execute(
        select(
            func.date(User.last_login).label("day"),
            func.count(User.id).label("count"),
        )
        .where(User.last_login >= start_30d)
        .group_by(func.date(User.last_login))
    )
    usage_daily_counts = {row.day: row.count for row in usage_daily_result}

    # Build 7-day list from the cached daily counts
    usage_7d = []
    for i in range(6, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        usage_7d.append(TimeSeriesData(date=day_date, value=usage_daily_counts.get(day_date, 0)))

    # Build 30-day list from the cached daily counts
    usage_30d = []
    for i in range(29, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        usage_30d.append(TimeSeriesData(date=day_date, value=usage_daily_counts.get(day_date, 0)))

    return DashboardStatsResponse(
        users=user_stats,
        content=content_stats,
        subscriptions=subscription_stats,
        revenue=revenue_stats,
        platform_usage_7d=usage_7d,
        platform_usage_30d=usage_30d,
    )


# ============================================================================
# Endpoint 2: User Analytics
# ============================================================================


@router.get("/users", response_model=UserAnalyticsResponse)
@limiter.limit("10/minute")
async def get_user_analytics(
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed user analytics.

    Returns:
    - New user signups over time (daily for last 30 days)
    - User retention metrics (1-day, 7-day, 30-day)
    - Subscription conversion rates (free to paid)
    - Geographic distribution (placeholder - requires additional data)

    **Admin access required.**

    **Note:** Cache recommended for this endpoint (heavy queries).
    """
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # ========== SIGNUP TRENDS ==========
    # Single GROUP BY query for total signups per day
    signups_daily_result = await db.execute(
        select(
            func.date(User.created_at).label("day"),
            func.count(User.id).label("count"),
        )
        .where(User.created_at >= thirty_days_ago)
        .group_by(func.date(User.created_at))
    )
    signups_daily_counts = {row.day: row.count for row in signups_daily_result}

    # Single GROUP BY query for verified signups per day
    verified_daily_result = await db.execute(
        select(
            func.date(User.created_at).label("day"),
            func.count(User.id).label("count"),
        )
        .where(
            and_(
                User.created_at >= thirty_days_ago,
                User.email_verified == True,
            )
        )
        .group_by(func.date(User.created_at))
    )
    verified_daily_counts = {row.day: row.count for row in verified_daily_result}

    signup_trends = []
    for i in range(29, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        signup_trends.append(
            SignupTrend(
                date=day_date,
                signups=signups_daily_counts.get(day_date, 0),
                verified=verified_daily_counts.get(day_date, 0),
            )
        )

    # ========== RETENTION METRICS ==========
    # Day 1 retention: % of users who logged in 1 day after signup
    # Simplified: users who have last_login > created_at + 1 day
    one_day_ago = now - timedelta(days=1)
    users_created_1d_result = await db.execute(
        select(func.count(User.id)).where(
            User.created_at <= one_day_ago,
            User.deleted_at.is_(None),  # ADM-28: exclude deleted users
            User.status != "suspended",  # ADM-28: exclude suspended users
        )
    )
    users_created_1d = users_created_1d_result.scalar() or 1  # Avoid division by zero

    users_active_after_1d_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.created_at <= one_day_ago,
                User.last_login >= User.created_at + timedelta(days=1),
                User.deleted_at.is_(None),  # ADM-28: exclude deleted users
                User.status != "suspended",  # ADM-28: exclude suspended users
            )
        )
    )
    users_active_after_1d = users_active_after_1d_result.scalar() or 0
    day_1_retention = calculate_percentage(users_active_after_1d, users_created_1d)

    # Day 7 retention
    seven_days_ago = now - timedelta(days=7)
    users_created_7d_result = await db.execute(
        select(func.count(User.id)).where(
            User.created_at <= seven_days_ago,
            User.deleted_at.is_(None),  # ADM-28: exclude deleted users
            User.status != "suspended",  # ADM-28: exclude suspended users
        )
    )
    users_created_7d = users_created_7d_result.scalar() or 1

    users_active_after_7d_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.created_at <= seven_days_ago,
                User.last_login >= User.created_at + timedelta(days=7),
                User.deleted_at.is_(None),  # ADM-28: exclude deleted users
                User.status != "suspended",  # ADM-28: exclude suspended users
            )
        )
    )
    users_active_after_7d = users_active_after_7d_result.scalar() or 0
    day_7_retention = calculate_percentage(users_active_after_7d, users_created_7d)

    # Day 30 retention
    users_created_30d_result = await db.execute(
        select(func.count(User.id)).where(
            User.created_at <= thirty_days_ago,
            User.deleted_at.is_(None),  # ADM-28: exclude deleted users
            User.status != "suspended",  # ADM-28: exclude suspended users
        )
    )
    users_created_30d = users_created_30d_result.scalar() or 1

    users_active_after_30d_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.created_at <= thirty_days_ago,
                User.last_login >= User.created_at + timedelta(days=30),
                User.deleted_at.is_(None),  # ADM-28: exclude deleted users
                User.status != "suspended",  # ADM-28: exclude suspended users
            )
        )
    )
    users_active_after_30d = users_active_after_30d_result.scalar() or 0
    day_30_retention = calculate_percentage(users_active_after_30d, users_created_30d)

    retention_metrics = RetentionMetrics(
        day_1_retention=day_1_retention,
        day_7_retention=day_7_retention,
        day_30_retention=day_30_retention,
    )

    # ========== CONVERSION METRICS ==========
    # Total free users (ever)
    total_free_result = await db.execute(
        select(func.count(User.id))
    )
    total_free = total_free_result.scalar() or 1

    # Users who upgraded to starter
    starter_count_result = await db.execute(
        select(func.count(User.id)).where(
            User.subscription_tier == SubscriptionTier.STARTER.value
        )
    )
    starter_count = starter_count_result.scalar() or 0
    free_to_starter = calculate_percentage(starter_count, total_free)

    # Users who upgraded to professional
    pro_count_result = await db.execute(
        select(func.count(User.id)).where(
            User.subscription_tier == SubscriptionTier.PROFESSIONAL.value
        )
    )
    pro_count = pro_count_result.scalar() or 0
    free_to_professional = calculate_percentage(pro_count, total_free)

    # Users who upgraded to enterprise
    enterprise_count_result = await db.execute(
        select(func.count(User.id)).where(
            User.subscription_tier == SubscriptionTier.ENTERPRISE.value
        )
    )
    enterprise_count = enterprise_count_result.scalar() or 0
    free_to_enterprise = calculate_percentage(enterprise_count, total_free)

    # Overall conversion rate
    paid_count = starter_count + pro_count + enterprise_count
    overall_conversion_rate = calculate_percentage(paid_count, total_free)

    conversion_metrics = ConversionMetrics(
        free_to_starter=free_to_starter,
        free_to_professional=free_to_professional,
        free_to_enterprise=free_to_enterprise,
        overall_conversion_rate=overall_conversion_rate,
    )

    # ========== GEOGRAPHIC DISTRIBUTION ==========
    # Placeholder: Would require additional user metadata (IP geolocation, country field)
    # For now, return empty list
    geographic_distribution = []

    # Total users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    return UserAnalyticsResponse(
        signup_trends=signup_trends,
        retention_metrics=retention_metrics,
        conversion_metrics=conversion_metrics,
        geographic_distribution=geographic_distribution,
        total_users=total_users,
    )


# ============================================================================
# Endpoint 3: Content Analytics
# ============================================================================


@router.get("/content", response_model=ContentAnalyticsResponse)
@limiter.limit("10/minute")
async def get_content_analytics(
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed content analytics.

    Returns:
    - Articles, outlines, images created over time (daily for last 30 days)
    - Most active users (top 10 by content created)
    - Content by status breakdown (draft, completed, published, etc.)

    **Admin access required.**

    **Note:** Cache recommended for this endpoint (heavy queries).
    """
    now = datetime.now(timezone.utc)

    # ========== CONTENT TRENDS ==========
    thirty_days_ago = now - timedelta(days=30)

    # Single GROUP BY query per content type, then merge
    articles_daily_result = await db.execute(
        select(
            func.date(Article.created_at).label("day"),
            func.count(Article.id).label("count"),
        )
        .where(Article.created_at >= thirty_days_ago)
        .group_by(func.date(Article.created_at))
    )
    articles_daily = {row.day: row.count for row in articles_daily_result}

    outlines_daily_result = await db.execute(
        select(
            func.date(Outline.created_at).label("day"),
            func.count(Outline.id).label("count"),
        )
        .where(Outline.created_at >= thirty_days_ago)
        .group_by(func.date(Outline.created_at))
    )
    outlines_daily = {row.day: row.count for row in outlines_daily_result}

    images_daily_result = await db.execute(
        select(
            func.date(GeneratedImage.created_at).label("day"),
            func.count(GeneratedImage.id).label("count"),
        )
        .where(GeneratedImage.created_at >= thirty_days_ago)
        .group_by(func.date(GeneratedImage.created_at))
    )
    images_daily = {row.day: row.count for row in images_daily_result}

    content_trends = []
    for i in range(29, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        content_trends.append(
            ContentTrend(
                date=day_date,
                articles=articles_daily.get(day_date, 0),
                outlines=outlines_daily.get(day_date, 0),
                images=images_daily.get(day_date, 0),
            )
        )

    # ========== TOP USERS BY CONTENT ==========
    # Use subqueries to count content per user
    # Top 10 users by total content (articles + outlines + images)
    top_users_result = await db.execute(
        select(
            User.id,
            User.email,
            User.name,
            User.subscription_tier,
            func.count(Article.id).label("articles_count"),
        )
        .outerjoin(Article, Article.user_id == User.id)
        .group_by(User.id)
        .order_by(desc("articles_count"))
        .limit(10)
    )
    top_users_articles = {row.id: row for row in top_users_result.all()}

    # Get outline counts for these users
    if top_users_articles:
        user_ids = list(top_users_articles.keys())
        outlines_counts_result = await db.execute(
            select(
                Outline.user_id,
                func.count(Outline.id).label("outlines_count")
            )
            .where(Outline.user_id.in_(user_ids))
            .group_by(Outline.user_id)
        )
        outlines_counts = {row.user_id: row.outlines_count for row in outlines_counts_result.all()}

        # Get image counts for these users
        images_counts_result = await db.execute(
            select(
                GeneratedImage.user_id,
                func.count(GeneratedImage.id).label("images_count")
            )
            .where(GeneratedImage.user_id.in_(user_ids))
            .group_by(GeneratedImage.user_id)
        )
        images_counts = {row.user_id: row.images_count for row in images_counts_result.all()}

        # Build top users list
        top_users = []
        for user_id, row in top_users_articles.items():
            articles_count = row.articles_count
            outlines_count = outlines_counts.get(user_id, 0)
            images_count = images_counts.get(user_id, 0)
            total_content = articles_count + outlines_count + images_count

            top_users.append(
                TopUser(
                    user_id=user_id,
                    email=row.email,
                    name=row.name,
                    articles_count=articles_count,
                    outlines_count=outlines_count,
                    images_count=images_count,
                    total_content=total_content,
                    subscription_tier=row.subscription_tier,
                )
            )

        # Sort by total content
        top_users.sort(key=lambda x: x.total_content, reverse=True)
    else:
        top_users = []

    # ========== CONTENT STATUS BREAKDOWN ==========
    # Articles by status
    articles_status_result = await db.execute(
        select(
            Article.status,
            func.count(Article.id)
        ).group_by(Article.status)
    )
    articles_status_data = {status: count for status, count in articles_status_result.all()}
    total_articles_count = sum(articles_status_data.values()) or 1

    article_status_breakdown = [
        ContentStatusBreakdown(
            status=status,
            count=count,
            percentage=calculate_percentage(count, total_articles_count)
        )
        for status, count in articles_status_data.items()
    ]

    # Outlines by status
    outlines_status_result = await db.execute(
        select(
            Outline.status,
            func.count(Outline.id)
        ).group_by(Outline.status)
    )
    outlines_status_data = {status: count for status, count in outlines_status_result.all()}
    total_outlines_count = sum(outlines_status_data.values()) or 1

    outline_status_breakdown = [
        ContentStatusBreakdown(
            status=status,
            count=count,
            percentage=calculate_percentage(count, total_outlines_count)
        )
        for status, count in outlines_status_data.items()
    ]

    # ========== TOTALS ==========
    total_articles_result = await db.execute(select(func.count(Article.id)))
    total_articles = total_articles_result.scalar() or 0

    total_outlines_result = await db.execute(select(func.count(Outline.id)))
    total_outlines = total_outlines_result.scalar() or 0

    total_images_result = await db.execute(select(func.count(GeneratedImage.id)))
    total_images = total_images_result.scalar() or 0

    return ContentAnalyticsResponse(
        content_trends=content_trends,
        top_users=top_users,
        article_status_breakdown=article_status_breakdown,
        outline_status_breakdown=outline_status_breakdown,
        total_articles=total_articles,
        total_outlines=total_outlines,
        total_images=total_images,
    )


# ============================================================================
# Endpoint 4: Revenue Analytics
# ============================================================================


@router.get("/revenue", response_model=RevenueAnalyticsResponse)
@limiter.limit("10/minute")
async def get_revenue_analytics(
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed revenue analytics.

    Returns:
    - Monthly recurring revenue estimate (last 12 months)
    - Subscription distribution pie chart data
    - Churn indicators (cancelled subscriptions)
    - Revenue growth trend

    **Admin access required.**

    **Note:** Revenue is estimated based on subscription tier pricing.
    Actual payment data would require LemonSqueezy webhook integration.
    """
    now = datetime.now(timezone.utc)

    # ========== MONTHLY REVENUE (Last 12 months) ==========
    # NOTE: This is a simplified estimation. In production, you would track
    # actual subscription events (created, cancelled) with timestamps.
    # For now, we'll use user creation dates as proxy for "new subscriptions"
    monthly_revenue = []

    for i in range(12):
        # Calculate month range
        month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1)

        month_str = month_start.strftime("%Y-%m")

        # Count new paid subscriptions this month (users created on paid tier)
        new_subs_result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.created_at >= month_start,
                    User.created_at < month_end,
                    User.subscription_tier.in_([
                        SubscriptionTier.STARTER.value,
                        SubscriptionTier.PROFESSIONAL.value,
                        SubscriptionTier.ENTERPRISE.value
                    ])
                )
            )
        )
        new_subscriptions = new_subs_result.scalar() or 0

        # Count churned subscriptions (users who cancelled)
        # Simplified: users with subscription_status = 'cancelled' in this month
        # In production, track actual cancellation timestamp
        churned_subs_result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.subscription_status == "cancelled",
                    User.updated_at >= month_start,
                    User.updated_at < month_end
                )
            )
        )
        churned_subscriptions = churned_subs_result.scalar() or 0

        # Estimate revenue: count active subscriptions at end of month
        # Simplified: current subscriptions (doesn't account for historical changes)
        active_subs_result = await db.execute(
            select(
                User.subscription_tier,
                func.count(User.id)
            )
            .where(
                and_(
                    User.subscription_tier.in_([
                        SubscriptionTier.STARTER.value,
                        SubscriptionTier.PROFESSIONAL.value,
                        SubscriptionTier.ENTERPRISE.value
                    ]),
                    User.subscription_status == "active"
                )
            )
            .group_by(User.subscription_tier)
        )
        active_subs = {tier: count for tier, count in active_subs_result.all()}

        revenue = (
            active_subs.get(SubscriptionTier.STARTER.value, 0) * TIER_PRICING[SubscriptionTier.STARTER.value] +
            active_subs.get(SubscriptionTier.PROFESSIONAL.value, 0) * TIER_PRICING[SubscriptionTier.PROFESSIONAL.value] +
            active_subs.get(SubscriptionTier.ENTERPRISE.value, 0) * TIER_PRICING[SubscriptionTier.ENTERPRISE.value]
        )

        monthly_revenue.append(
            MonthlyRevenue(
                month=month_str,
                revenue=float(revenue),
                new_subscriptions=new_subscriptions,
                churned_subscriptions=churned_subscriptions,
            )
        )

    monthly_revenue.reverse()  # Chronological order

    # ========== SUBSCRIPTION DISTRIBUTION ==========
    subscription_counts_result = await db.execute(
        select(
            User.subscription_tier,
            func.count(User.id)
        )
        .where(User.subscription_status == "active")
        .group_by(User.subscription_tier)
    )
    subscription_counts = {tier: count for tier, count in subscription_counts_result.all()}

    total_active_subs = sum(subscription_counts.values()) or 1

    subscription_distribution = []
    for tier, pricing in TIER_PRICING.items():
        count = subscription_counts.get(tier, 0)
        percentage = calculate_percentage(count, total_active_subs)
        monthly_value = count * pricing

        subscription_distribution.append(
            SubscriptionDistribution(
                tier=tier,
                count=count,
                percentage=percentage,
                monthly_value=float(monthly_value),
            )
        )

    # ========== CHURN INDICATORS (Last 6 months) ==========
    churn_indicators = []

    for i in range(6):
        month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1)

        month_str = month_start.strftime("%Y-%m")

        # Count churned subscriptions
        churned_count_result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.subscription_status == "cancelled",
                    User.updated_at >= month_start,
                    User.updated_at < month_end
                )
            )
        )
        churned_count = churned_count_result.scalar() or 0

        # Calculate churn rate: churned / active at start of month
        # Simplified: use current active count
        active_count_result = await db.execute(
            select(func.count(User.id)).where(
                User.subscription_status == "active"
            )
        )
        active_count = active_count_result.scalar() or 1

        churn_rate = calculate_percentage(churned_count, active_count)

        churn_indicators.append(
            ChurnIndicator(
                month=month_str,
                churned_count=churned_count,
                churn_rate=churn_rate,
            )
        )

    churn_indicators.reverse()  # Chronological order

    # ========== CURRENT MRR & ARR ==========
    current_mrr = (
        subscription_counts.get(SubscriptionTier.STARTER.value, 0) * TIER_PRICING[SubscriptionTier.STARTER.value] +
        subscription_counts.get(SubscriptionTier.PROFESSIONAL.value, 0) * TIER_PRICING[SubscriptionTier.PROFESSIONAL.value] +
        subscription_counts.get(SubscriptionTier.ENTERPRISE.value, 0) * TIER_PRICING[SubscriptionTier.ENTERPRISE.value]
    )
    current_arr = current_mrr * 12

    # ========== REVENUE GROWTH RATE ==========
    # Compare current month revenue to previous month
    if len(monthly_revenue) >= 2:
        current_month_revenue = monthly_revenue[-1].revenue
        previous_month_revenue = monthly_revenue[-2].revenue or 1  # Avoid division by zero

        revenue_growth_rate = (
            ((current_month_revenue - previous_month_revenue) / previous_month_revenue) * 100
            if previous_month_revenue > 0
            else 0.0
        )
    else:
        revenue_growth_rate = 0.0

    return RevenueAnalyticsResponse(
        monthly_revenue=monthly_revenue,
        subscription_distribution=subscription_distribution,
        churn_indicators=churn_indicators,
        current_mrr=float(current_mrr),
        current_arr=float(current_arr),
        revenue_growth_rate=round(revenue_growth_rate, 2),
    )


# ============================================================================
# Endpoint 5: System Health
# ============================================================================


@router.get("/system", response_model=SystemHealthResponse)
@limiter.limit("10/minute")
async def get_system_health(
    request: Request,
    current_admin: Annotated[User, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get system health metrics.

    Returns:
    - Total database records per table
    - Storage usage estimate (images)
    - Recent error rates (placeholder - requires error logging)
    - Background job status (pending/failed social posts, etc.)

    **Admin access required.**
    """

    # ========== TABLE STATS ==========
    table_stats = []

    # Users
    users_count_result = await db.execute(select(func.count(User.id)))
    users_count = users_count_result.scalar() or 0
    table_stats.append(TableStats(table_name="users", record_count=users_count))

    # Articles
    articles_count_result = await db.execute(select(func.count(Article.id)))
    articles_count = articles_count_result.scalar() or 0
    table_stats.append(TableStats(table_name="articles", record_count=articles_count))

    # Outlines
    outlines_count_result = await db.execute(select(func.count(Outline.id)))
    outlines_count = outlines_count_result.scalar() or 0
    table_stats.append(TableStats(table_name="outlines", record_count=outlines_count))

    # Generated Images
    images_count_result = await db.execute(select(func.count(GeneratedImage.id)))
    images_count = images_count_result.scalar() or 0
    table_stats.append(TableStats(table_name="generated_images", record_count=images_count))

    # Scheduled Posts
    posts_count_result = await db.execute(select(func.count(ScheduledPost.id)))
    posts_count = posts_count_result.scalar() or 0
    table_stats.append(TableStats(table_name="scheduled_posts", record_count=posts_count))

    # Knowledge Sources
    sources_count_result = await db.execute(select(func.count(KnowledgeSource.id)))
    sources_count = sources_count_result.scalar() or 0
    table_stats.append(TableStats(table_name="knowledge_sources", record_count=sources_count))

    # ========== STORAGE STATS ==========
    # Calculate total storage from images
    # Assuming average image size (can improve with actual file_size tracking)
    total_images = images_count
    average_image_size_kb = 250.0  # Estimate: 250KB per image
    total_storage_mb = (total_images * average_image_size_kb) / 1024

    storage_stats = StorageStats(
        total_images=total_images,
        total_storage_mb=round(total_storage_mb, 2),
        average_image_size_kb=average_image_size_kb,
    )

    # ========== RECENT ERROR RATES ==========
    # Placeholder: Would require error logging table
    # For now, return empty list
    recent_error_rates = []

    # ========== BACKGROUND JOB STATUS ==========
    background_jobs = []

    # Scheduled social posts
    pending_posts_result = await db.execute(
        select(func.count(ScheduledPost.id)).where(
            ScheduledPost.status == PostStatus.SCHEDULED.value
        )
    )
    pending_posts = pending_posts_result.scalar() or 0

    failed_posts_result = await db.execute(
        select(func.count(ScheduledPost.id)).where(
            ScheduledPost.status == PostStatus.FAILED.value
        )
    )
    failed_posts = failed_posts_result.scalar() or 0

    background_jobs.append(
        BackgroundJobStatus(
            job_type="social_posts",
            pending_count=pending_posts,
            failed_count=failed_posts,
        )
    )

    # Knowledge source processing
    pending_sources_result = await db.execute(
        select(func.count(KnowledgeSource.id)).where(
            KnowledgeSource.status.in_([
                SourceStatus.PENDING.value,
                SourceStatus.PROCESSING.value
            ])
        )
    )
    pending_sources = pending_sources_result.scalar() or 0

    failed_sources_result = await db.execute(
        select(func.count(KnowledgeSource.id)).where(
            KnowledgeSource.status == SourceStatus.FAILED.value
        )
    )
    failed_sources = failed_sources_result.scalar() or 0

    background_jobs.append(
        BackgroundJobStatus(
            job_type="knowledge_processing",
            pending_count=pending_sources,
            failed_count=failed_sources,
        )
    )

    # ========== DATABASE SIZE ==========
    # Placeholder: Would require PostgreSQL-specific query
    # For now, return 0
    database_size_mb = 0.0

    return SystemHealthResponse(
        table_stats=table_stats,
        storage_stats=storage_stats,
        recent_error_rates=recent_error_rates,
        background_jobs=background_jobs,
        database_size_mb=database_size_mb,
    )
