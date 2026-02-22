"""
Analytics API routes for Google Search Console integration.
"""

import math
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.analytics import (
    GSCConnectResponse,
    GSCCallbackRequest,
    GSCConnectionStatus,
    GSCSiteResponse,
    GSCSiteListResponse,
    GSCSelectSiteRequest,
    GSCSyncResponse,
    GSCDisconnectResponse,
    KeywordRankingResponse,
    KeywordRankingListResponse,
    PagePerformanceResponse,
    PagePerformanceListResponse,
    DailyAnalyticsResponse,
    DailyAnalyticsListResponse,
    AnalyticsSummaryResponse,
    TrendData,
    ArticlePerformanceItem,
    ArticlePerformanceListResponse,
    ArticleDailyPerformance,
    ArticlePerformanceDetailResponse,
    KeywordOpportunity,
    ContentOpportunitiesResponse,
    ContentSuggestionRequest,
    ContentSuggestion,
    ContentSuggestionsResponse,
)
from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db
from infrastructure.database.models import User
from infrastructure.database.models.analytics import (
    GSCConnection,
    KeywordRanking,
    PagePerformance,
    DailyAnalytics,
)
from infrastructure.database.models.content import Article
from infrastructure.config.settings import settings

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ============================================================================
# Helper Functions
# ============================================================================


def calculate_trend(current: float, previous: float) -> TrendData:
    """Calculate trend data between current and previous values."""
    if previous == 0:
        change_percent = 100.0 if current > 0 else 0.0
    else:
        change_percent = ((current - previous) / previous) * 100

    if abs(change_percent) < 1:
        trend = "stable"
    elif change_percent > 0:
        trend = "up"
    else:
        trend = "down"

    return TrendData(
        current=current,
        previous=previous,
        change_percent=round(change_percent, 2),
        trend=trend,
    )


async def get_gsc_connection(
    user_id: str, db: AsyncSession
) -> Optional[GSCConnection]:
    """Get user's GSC connection."""
    result = await db.execute(
        select(GSCConnection).where(
            GSCConnection.user_id == user_id,
            GSCConnection.is_active == True,
        )
    )
    return result.scalar_one_or_none()


# ============================================================================
# GSC Connection Management Endpoints
# ============================================================================


@router.get("/gsc/auth-url", response_model=GSCConnectResponse)
async def get_gsc_auth_url(
    current_user: User = Depends(get_current_user),
):
    """
    Get Google OAuth authorization URL for GSC connection.
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured",
        )

    # Generate state for CSRF protection
    state = str(uuid4())

    # Build OAuth URL with proper URL encoding
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    return GSCConnectResponse(auth_url=auth_url, state=state)


@router.get("/gsc/callback")
async def gsc_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter from OAuth flow"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth callback handler for GSC connection.
    This endpoint exchanges the authorization code for tokens.
    """
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter",
        )

    try:
        # Import encryption and GSC adapter
        from adapters.search.gsc_adapter import GSCAdapter
        from core.security.encryption import encrypt_credential

        # Initialize GSC adapter
        gsc_adapter = GSCAdapter()

        # Exchange authorization code for tokens
        credentials = gsc_adapter.exchange_code(code)

        # Encrypt the tokens before storing
        encrypted_access_token = encrypt_credential(
            credentials.access_token, settings.secret_key
        )
        encrypted_refresh_token = encrypt_credential(
            credentials.refresh_token, settings.secret_key
        )

        # Check if connection already exists (including inactive ones)
        result = await db.execute(
            select(GSCConnection).where(GSCConnection.user_id == current_user.id)
        )
        existing_connection = result.scalar_one_or_none()

        if existing_connection:
            # Update existing connection
            existing_connection.access_token = encrypted_access_token
            existing_connection.refresh_token = encrypted_refresh_token
            existing_connection.token_expiry = credentials.token_expiry
            existing_connection.is_active = True
            existing_connection.connected_at = datetime.now(timezone.utc)
            connection = existing_connection
        else:
            # Create new connection
            connection = GSCConnection(
                user_id=current_user.id,
                site_url="",  # Will be set when user selects a site
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                token_expiry=credentials.token_expiry,
                connected_at=datetime.now(timezone.utc),
                is_active=True,
            )
            db.add(connection)

        await db.commit()
        await db.refresh(connection)

        return {
            "message": "GSC connected successfully",
            "connected_at": connection.connected_at,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect GSC: {str(e)}",
        )


@router.post("/gsc/disconnect", response_model=GSCDisconnectResponse)
async def disconnect_gsc(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect Google Search Console integration.
    """
    connection = await get_gsc_connection(current_user.id, db)

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No GSC connection found",
        )

    connection.is_active = False
    await db.commit()

    return GSCDisconnectResponse(disconnected_at=datetime.now(timezone.utc))


@router.get("/gsc/status", response_model=GSCConnectionStatus)
async def get_gsc_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current GSC connection status.
    """
    connection = await get_gsc_connection(current_user.id, db)

    if not connection:
        return GSCConnectionStatus(connected=False)

    return GSCConnectionStatus(
        connected=True,
        site_url=connection.site_url,
        last_sync=connection.last_sync,
        connected_at=connection.connected_at,
    )


@router.get("/gsc/sites", response_model=GSCSiteListResponse)
async def get_gsc_sites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List verified sites from Google Search Console.
    """
    import logging
    logger = logging.getLogger(__name__)

    connection = await get_gsc_connection(current_user.id, db)

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GSC not connected. Please connect first.",
        )

    try:
        # Import required modules
        from adapters.search.gsc_adapter import GSCAdapter, GSCCredentials
        from core.security.encryption import decrypt_credential, encrypt_credential

        # Decrypt the stored tokens
        decrypted_access_token = decrypt_credential(
            connection.access_token, settings.secret_key
        )
        decrypted_refresh_token = decrypt_credential(
            connection.refresh_token, settings.secret_key
        )

        logger.info(
            f"GSC list_sites: token starts with '{decrypted_access_token[:10]}...', "
            f"refresh starts with '{decrypted_refresh_token[:10]}...', "
            f"token_expiry={connection.token_expiry}"
        )

        # Create credentials object
        credentials = GSCCredentials(
            access_token=decrypted_access_token,
            refresh_token=decrypted_refresh_token,
            token_expiry=connection.token_expiry,
            site_url=connection.site_url,
        )

        # Initialize GSC adapter and fetch sites
        gsc_adapter = GSCAdapter()
        sites_data, updated_creds = gsc_adapter.list_sites(credentials)

        # If tokens were refreshed, save them back to the database
        if updated_creds.access_token != decrypted_access_token:
            logger.info("GSC tokens were refreshed, saving back to database")
            connection.access_token = encrypt_credential(
                updated_creds.access_token, settings.secret_key
            )
            connection.token_expiry = updated_creds.token_expiry
            await db.commit()

        logger.info(f"GSC list_sites: returning {len(sites_data)} sites")

        # Transform to response format
        sites = [
            GSCSiteResponse(
                site_url=site["siteUrl"],
                permission_level=site.get("permissionLevel", "owner"),
            )
            for site in sites_data
        ]

        return GSCSiteListResponse(sites=sites)

    except Exception as e:
        logger.error(f"GSC list_sites failed: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch GSC sites: {str(e)}",
        )


@router.post("/gsc/select-site", response_model=GSCConnectionStatus)
async def select_gsc_site(
    request: GSCSelectSiteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Select a site to track from verified GSC sites.
    """
    connection = await get_gsc_connection(current_user.id, db)

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GSC not connected. Please connect first.",
        )

    connection.site_url = request.site_url
    await db.commit()
    await db.refresh(connection)

    return GSCConnectionStatus(
        connected=True,
        site_url=connection.site_url,
        last_sync=connection.last_sync,
        connected_at=connection.connected_at,
    )


@router.post("/gsc/sync", response_model=GSCSyncResponse)
async def sync_gsc_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a data sync from Google Search Console.
    Fetches keyword rankings, page performance, and daily stats for the last 28 days.
    """
    connection = await get_gsc_connection(current_user.id, db)

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GSC not connected. Please connect first.",
        )

    if not connection.site_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No site selected. Please select a site first.",
        )

    try:
        # Import required modules
        from adapters.search.gsc_adapter import GSCAdapter, GSCCredentials
        from core.security.encryption import decrypt_credential, encrypt_credential
        from datetime import date as date_type
        from sqlalchemy.dialects.postgresql import insert

        # Decrypt the stored tokens
        decrypted_access_token = decrypt_credential(
            connection.access_token, settings.secret_key
        )
        decrypted_refresh_token = decrypt_credential(
            connection.refresh_token, settings.secret_key
        )

        # Create credentials object
        credentials = GSCCredentials(
            access_token=decrypted_access_token,
            refresh_token=decrypted_refresh_token,
            token_expiry=connection.token_expiry,
            site_url=connection.site_url,
        )

        # Initialize GSC adapter
        gsc_adapter = GSCAdapter()

        # Fetch keyword rankings (last 28 days)
        keywords_data = gsc_adapter.get_keyword_rankings(
            credentials=credentials,
            site_url=connection.site_url,
            days=28,
        )

        # Fetch page performance (last 28 days)
        pages_data = gsc_adapter.get_page_performance(
            credentials=credentials,
            site_url=connection.site_url,
            days=28,
        )

        # Fetch daily stats (last 28 days)
        daily_data = gsc_adapter.get_daily_stats(
            credentials=credentials,
            site_url=connection.site_url,
            days=28,
        )

        # Sync keyword rankings (upsert to avoid duplicates)
        for keyword_item in keywords_data:
            # Get the date from the data (GSC returns data with 2-3 day delay)
            end_date = date_type.today() - timedelta(days=3)

            stmt = insert(KeywordRanking).values(
                user_id=current_user.id,
                site_url=connection.site_url,
                keyword=keyword_item["query"],
                date=end_date,
                clicks=keyword_item["clicks"],
                impressions=keyword_item["impressions"],
                ctr=keyword_item["ctr"],
                position=keyword_item["position"],
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_keyword_ranking_user_site_keyword_date",
                set_={
                    "clicks": stmt.excluded.clicks,
                    "impressions": stmt.excluded.impressions,
                    "ctr": stmt.excluded.ctr,
                    "position": stmt.excluded.position,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            await db.execute(stmt)

        # Sync page performance (upsert to avoid duplicates)
        for page_item in pages_data:
            end_date = date_type.today() - timedelta(days=3)

            stmt = insert(PagePerformance).values(
                user_id=current_user.id,
                site_url=connection.site_url,
                page_url=page_item["page"],
                date=end_date,
                clicks=page_item["clicks"],
                impressions=page_item["impressions"],
                ctr=page_item["ctr"],
                position=page_item["position"],
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_page_performance_user_site_page_date",
                set_={
                    "clicks": stmt.excluded.clicks,
                    "impressions": stmt.excluded.impressions,
                    "ctr": stmt.excluded.ctr,
                    "position": stmt.excluded.position,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            await db.execute(stmt)

        # Sync daily stats (upsert to avoid duplicates)
        for daily_item in daily_data:
            # Parse the date string (format: YYYY-MM-DD)
            daily_date = date_type.fromisoformat(daily_item["date"])

            stmt = insert(DailyAnalytics).values(
                user_id=current_user.id,
                site_url=connection.site_url,
                date=daily_date,
                total_clicks=daily_item["clicks"],
                total_impressions=daily_item["impressions"],
                avg_ctr=daily_item["ctr"],
                avg_position=daily_item["position"],
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_daily_analytics_user_site_date",
                set_={
                    "total_clicks": stmt.excluded.total_clicks,
                    "total_impressions": stmt.excluded.total_impressions,
                    "avg_ctr": stmt.excluded.avg_ctr,
                    "avg_position": stmt.excluded.avg_position,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            await db.execute(stmt)

        # Update last_sync timestamp
        sync_completed_at = datetime.now(timezone.utc)
        connection.last_sync = sync_completed_at
        await db.commit()

        return GSCSyncResponse(
            message=f"Successfully synced {len(keywords_data)} keywords, {len(pages_data)} pages, and {len(daily_data)} days of data",
            site_url=connection.site_url,
            sync_started_at=sync_completed_at,
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync GSC data: {str(e)}",
        )


# ============================================================================
# Analytics Data Endpoints
# ============================================================================


@router.get("/keywords", response_model=KeywordRankingListResponse)
async def get_keyword_rankings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get keyword ranking data with pagination and date filtering.
    """
    connection = await get_gsc_connection(current_user.id, db)

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GSC not connected",
        )

    query = select(KeywordRanking).where(KeywordRanking.user_id == current_user.id)

    if start_date:
        query = query.where(KeywordRanking.date >= start_date)
    if end_date:
        query = query.where(KeywordRanking.date <= end_date)
    if keyword:
        query = query.where(KeywordRanking.keyword.ilike(f"%{keyword}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Order by date desc, then clicks desc
    query = query.order_by(desc(KeywordRanking.date), desc(KeywordRanking.clicks))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    keywords = result.scalars().all()

    return KeywordRankingListResponse(
        items=keywords,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/pages", response_model=PagePerformanceListResponse)
async def get_page_performances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page_url: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get page performance data with pagination and date filtering.
    """
    connection = await get_gsc_connection(current_user.id, db)

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GSC not connected",
        )

    query = select(PagePerformance).where(PagePerformance.user_id == current_user.id)

    if start_date:
        query = query.where(PagePerformance.date >= start_date)
    if end_date:
        query = query.where(PagePerformance.date <= end_date)
    if page_url:
        query = query.where(PagePerformance.page_url.ilike(f"%{page_url}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Order by date desc, then clicks desc
    query = query.order_by(desc(PagePerformance.date), desc(PagePerformance.clicks))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    pages = result.scalars().all()

    return PagePerformanceListResponse(
        items=pages,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/daily", response_model=DailyAnalyticsListResponse)
async def get_daily_analytics(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=365),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get daily aggregated analytics data with pagination and date filtering.
    """
    connection = await get_gsc_connection(current_user.id, db)

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GSC not connected",
        )

    query = select(DailyAnalytics).where(DailyAnalytics.user_id == current_user.id)

    if start_date:
        query = query.where(DailyAnalytics.date >= start_date)
    if end_date:
        query = query.where(DailyAnalytics.date <= end_date)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Order by date desc
    query = query.order_by(desc(DailyAnalytics.date))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    daily_data = result.scalars().all()

    return DailyAnalyticsListResponse(
        items=daily_data,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get analytics overview/dashboard summary with trends and top performers.
    """
    connection = await get_gsc_connection(current_user.id, db)

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GSC not connected",
        )

    # Default to last 30 days if not specified
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Calculate previous period for trends
    period_length = (end_date - start_date).days
    previous_start = start_date - timedelta(days=period_length)
    previous_end = start_date - timedelta(days=1)

    # Get current period aggregates
    current_query = select(
        func.sum(DailyAnalytics.total_clicks).label("total_clicks"),
        func.sum(DailyAnalytics.total_impressions).label("total_impressions"),
        func.avg(DailyAnalytics.avg_ctr).label("avg_ctr"),
        func.avg(DailyAnalytics.avg_position).label("avg_position"),
    ).where(
        and_(
            DailyAnalytics.user_id == current_user.id,
            DailyAnalytics.date >= start_date,
            DailyAnalytics.date <= end_date,
        )
    )

    current_result = await db.execute(current_query)
    current_data = current_result.first()

    # Get previous period aggregates
    previous_query = select(
        func.sum(DailyAnalytics.total_clicks).label("total_clicks"),
        func.sum(DailyAnalytics.total_impressions).label("total_impressions"),
        func.avg(DailyAnalytics.avg_ctr).label("avg_ctr"),
        func.avg(DailyAnalytics.avg_position).label("avg_position"),
    ).where(
        and_(
            DailyAnalytics.user_id == current_user.id,
            DailyAnalytics.date >= previous_start,
            DailyAnalytics.date <= previous_end,
        )
    )

    previous_result = await db.execute(previous_query)
    previous_data = previous_result.first()

    # Calculate trends
    current_clicks = current_data.total_clicks or 0
    current_impressions = current_data.total_impressions or 0
    current_ctr = current_data.avg_ctr or 0.0
    current_position = current_data.avg_position or 0.0

    previous_clicks = previous_data.total_clicks or 0
    previous_impressions = previous_data.total_impressions or 0
    previous_ctr = previous_data.avg_ctr or 0.0
    previous_position = previous_data.avg_position or 0.0

    # Get top keywords (top 10 by clicks in period)
    top_keywords_query = (
        select(KeywordRanking)
        .where(
            and_(
                KeywordRanking.user_id == current_user.id,
                KeywordRanking.date >= start_date,
                KeywordRanking.date <= end_date,
            )
        )
        .order_by(desc(KeywordRanking.clicks))
        .limit(10)
    )

    top_keywords_result = await db.execute(top_keywords_query)
    top_keywords = top_keywords_result.scalars().all()

    # Get top pages (top 10 by clicks in period)
    top_pages_query = (
        select(PagePerformance)
        .where(
            and_(
                PagePerformance.user_id == current_user.id,
                PagePerformance.date >= start_date,
                PagePerformance.date <= end_date,
            )
        )
        .order_by(desc(PagePerformance.clicks))
        .limit(10)
    )

    top_pages_result = await db.execute(top_pages_query)
    top_pages = top_pages_result.scalars().all()

    return AnalyticsSummaryResponse(
        total_clicks=current_clicks,
        total_impressions=current_impressions,
        avg_ctr=round(current_ctr, 4),
        avg_position=round(current_position, 2),
        clicks_trend=calculate_trend(current_clicks, previous_clicks),
        impressions_trend=calculate_trend(current_impressions, previous_impressions),
        ctr_trend=calculate_trend(current_ctr, previous_ctr),
        position_trend=calculate_trend(current_position, previous_position),
        top_keywords=top_keywords,
        top_pages=top_pages,
        start_date=start_date,
        end_date=end_date,
        site_url=connection.site_url,
    )


# ============================================================================
# Article Performance Endpoints
# ============================================================================


def normalize_url(url: str) -> str:
    """Normalize a URL for comparison by stripping protocol, www, and trailing slash."""
    url = url.lower().strip().rstrip("/")
    for prefix in ("https://", "http://"):
        if url.startswith(prefix):
            url = url[len(prefix):]
            break
    if url.startswith("www."):
        url = url[4:]
    return url


@router.get("/article-performance", response_model=ArticlePerformanceListResponse)
async def get_article_performance(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_by: str = Query("total_clicks", regex="^(total_clicks|total_impressions|avg_position|avg_ctr|published_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List published articles cross-referenced with GSC page performance data.
    """
    connection = await get_gsc_connection(current_user.id, db)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GSC not connected",
        )

    # Default date range: last 30 days
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Previous period for trend calculation
    period_length = (end_date - start_date).days
    previous_start = start_date - timedelta(days=period_length)
    previous_end = start_date - timedelta(days=1)

    # Fetch all published articles for this user
    articles_query = select(Article).where(
        and_(
            Article.user_id == current_user.id,
            Article.published_url.isnot(None),
            Article.published_url != "",
        )
    )
    articles_result = await db.execute(articles_query)
    articles = articles_result.scalars().all()

    total_published = len(articles)

    # Fetch all page performance rows in the current period
    current_perf_query = select(PagePerformance).where(
        and_(
            PagePerformance.user_id == current_user.id,
            PagePerformance.date >= start_date,
            PagePerformance.date <= end_date,
        )
    )
    current_perf_result = await db.execute(current_perf_query)
    current_perf_rows = current_perf_result.scalars().all()

    # Fetch previous period performance
    previous_perf_query = select(PagePerformance).where(
        and_(
            PagePerformance.user_id == current_user.id,
            PagePerformance.date >= previous_start,
            PagePerformance.date <= previous_end,
        )
    )
    previous_perf_result = await db.execute(previous_perf_query)
    previous_perf_rows = previous_perf_result.scalars().all()

    # Build lookup maps by normalized URL
    current_by_url: dict[str, list] = {}
    for row in current_perf_rows:
        key = normalize_url(row.page_url)
        current_by_url.setdefault(key, []).append(row)

    previous_by_url: dict[str, list] = {}
    for row in previous_perf_rows:
        key = normalize_url(row.page_url)
        previous_by_url.setdefault(key, []).append(row)

    # Cross-reference articles with performance data
    items: list[ArticlePerformanceItem] = []
    articles_with_data = 0

    for article in articles:
        norm_url = normalize_url(article.published_url)
        current_rows = current_by_url.get(norm_url, [])
        previous_rows = previous_by_url.get(norm_url, [])

        total_clicks = sum(r.clicks for r in current_rows)
        total_impressions = sum(r.impressions for r in current_rows)
        avg_ctr = (
            sum(r.ctr for r in current_rows) / len(current_rows)
            if current_rows
            else 0.0
        )
        avg_position = (
            sum(r.position for r in current_rows) / len(current_rows)
            if current_rows
            else 0.0
        )

        prev_clicks = sum(r.clicks for r in previous_rows)
        prev_position = (
            sum(r.position for r in previous_rows) / len(previous_rows)
            if previous_rows
            else 0.0
        )

        clicks_trend = calculate_trend(total_clicks, prev_clicks) if current_rows or previous_rows else None
        position_trend = calculate_trend(avg_position, prev_position) if current_rows or previous_rows else None

        # Determine performance status
        if not current_rows and not previous_rows:
            perf_status = "new"
        elif clicks_trend and clicks_trend.change_percent > 5:
            perf_status = "improving"
        elif clicks_trend and clicks_trend.change_percent < -5:
            perf_status = "declining"
        else:
            perf_status = "neutral"

        if current_rows:
            articles_with_data += 1

        items.append(
            ArticlePerformanceItem(
                article_id=article.id,
                title=article.title,
                keyword=article.keyword,
                published_url=article.published_url,
                published_at=article.published_at,
                seo_score=article.seo_score,
                total_clicks=total_clicks,
                total_impressions=total_impressions,
                avg_ctr=round(avg_ctr, 4),
                avg_position=round(avg_position, 2),
                clicks_trend=clicks_trend,
                position_trend=position_trend,
                performance_status=perf_status,
            )
        )

    # Sort
    reverse = sort_order == "desc"
    sort_key_map = {
        "total_clicks": lambda x: x.total_clicks,
        "total_impressions": lambda x: x.total_impressions,
        "avg_position": lambda x: x.avg_position,
        "avg_ctr": lambda x: x.avg_ctr,
        "published_at": lambda x: x.published_at or datetime.min.replace(tzinfo=timezone.utc),
    }
    items.sort(key=sort_key_map.get(sort_by, sort_key_map["total_clicks"]), reverse=reverse)

    total = len(items)
    pages_count = math.ceil(total / page_size) if total > 0 else 0
    paginated = items[(page - 1) * page_size : page * page_size]

    return ArticlePerformanceListResponse(
        items=paginated,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages_count,
        total_published_articles=total_published,
        articles_with_data=articles_with_data,
    )


@router.get("/article-performance/{article_id}", response_model=ArticlePerformanceDetailResponse)
async def get_article_performance_detail(
    article_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed performance data for a single article.
    """
    connection = await get_gsc_connection(current_user.id, db)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GSC not connected",
        )

    # Fetch the article
    article_result = await db.execute(
        select(Article).where(
            and_(
                Article.id == article_id,
                Article.user_id == current_user.id,
            )
        )
    )
    article = article_result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    if not article.published_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Article has no published URL")

    # Default date range
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    period_length = (end_date - start_date).days
    previous_start = start_date - timedelta(days=period_length)
    previous_end = start_date - timedelta(days=1)

    norm_url = normalize_url(article.published_url)

    # Fetch all page performance for this URL in date range
    all_perf_query = select(PagePerformance).where(
        and_(
            PagePerformance.user_id == current_user.id,
            PagePerformance.date >= start_date,
            PagePerformance.date <= end_date,
        )
    ).order_by(PagePerformance.date)
    all_perf_result = await db.execute(all_perf_query)
    all_rows = all_perf_result.scalars().all()

    # Filter by normalized URL
    current_rows = [r for r in all_rows if normalize_url(r.page_url) == norm_url]

    # Previous period
    prev_perf_query = select(PagePerformance).where(
        and_(
            PagePerformance.user_id == current_user.id,
            PagePerformance.date >= previous_start,
            PagePerformance.date <= previous_end,
        )
    )
    prev_perf_result = await db.execute(prev_perf_query)
    prev_rows = [r for r in prev_perf_result.scalars().all() if normalize_url(r.page_url) == norm_url]

    # Build daily data
    daily_data = [
        ArticleDailyPerformance(
            date=r.date,
            clicks=r.clicks,
            impressions=r.impressions,
            ctr=round(r.ctr, 4),
            position=round(r.position, 2),
        )
        for r in current_rows
    ]

    # Aggregates
    total_clicks = sum(r.clicks for r in current_rows)
    total_impressions = sum(r.impressions for r in current_rows)
    avg_ctr = sum(r.ctr for r in current_rows) / len(current_rows) if current_rows else 0.0
    avg_position = sum(r.position for r in current_rows) / len(current_rows) if current_rows else 0.0

    prev_clicks = sum(r.clicks for r in prev_rows)
    prev_impressions = sum(r.impressions for r in prev_rows)
    prev_ctr = sum(r.ctr for r in prev_rows) / len(prev_rows) if prev_rows else 0.0
    prev_position = sum(r.position for r in prev_rows) / len(prev_rows) if prev_rows else 0.0

    return ArticlePerformanceDetailResponse(
        article_id=article.id,
        title=article.title,
        keyword=article.keyword,
        published_url=article.published_url,
        published_at=article.published_at,
        seo_score=article.seo_score,
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        avg_ctr=round(avg_ctr, 4),
        avg_position=round(avg_position, 2),
        clicks_trend=calculate_trend(total_clicks, prev_clicks),
        impressions_trend=calculate_trend(total_impressions, prev_impressions),
        ctr_trend=calculate_trend(avg_ctr, prev_ctr),
        position_trend=calculate_trend(avg_position, prev_position),
        daily_data=daily_data,
        start_date=start_date,
        end_date=end_date,
    )


# ============================================================================
# Content Opportunities Endpoints
# ============================================================================


@router.get("/opportunities", response_model=ContentOpportunitiesResponse)
async def get_content_opportunities(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze keyword data to surface content opportunities.
    Categories: quick wins (positions 5-20), content gaps (high impressions, low CTR),
    rising keywords (improved position).
    """
    connection = await get_gsc_connection(current_user.id, db)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GSC not connected",
        )

    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    period_length = (end_date - start_date).days
    previous_start = start_date - timedelta(days=period_length)
    previous_end = start_date - timedelta(days=1)

    # Fetch current period keywords aggregated
    current_kw_query = (
        select(
            KeywordRanking.keyword,
            func.sum(KeywordRanking.clicks).label("clicks"),
            func.sum(KeywordRanking.impressions).label("impressions"),
            func.avg(KeywordRanking.ctr).label("ctr"),
            func.avg(KeywordRanking.position).label("position"),
        )
        .where(
            and_(
                KeywordRanking.user_id == current_user.id,
                KeywordRanking.date >= start_date,
                KeywordRanking.date <= end_date,
            )
        )
        .group_by(KeywordRanking.keyword)
    )
    current_result = await db.execute(current_kw_query)
    current_keywords = {row.keyword: row for row in current_result.all()}

    # Fetch previous period for comparison
    prev_kw_query = (
        select(
            KeywordRanking.keyword,
            func.avg(KeywordRanking.position).label("position"),
        )
        .where(
            and_(
                KeywordRanking.user_id == current_user.id,
                KeywordRanking.date >= previous_start,
                KeywordRanking.date <= previous_end,
            )
        )
        .group_by(KeywordRanking.keyword)
    )
    prev_result = await db.execute(prev_kw_query)
    prev_positions = {row.keyword: row.position for row in prev_result.all()}

    # Fetch existing articles to cross-reference
    articles_query = select(Article.id, Article.keyword).where(
        Article.user_id == current_user.id
    )
    articles_result = await db.execute(articles_query)
    article_keywords = {row.keyword.lower(): row.id for row in articles_result.all()}

    quick_wins = []
    content_gaps = []
    rising_keywords = []

    for keyword, data in current_keywords.items():
        clicks = data.clicks or 0
        impressions = data.impressions or 0
        ctr = data.ctr or 0.0
        position = data.position or 0.0
        prev_pos = prev_positions.get(keyword, position)
        position_change = prev_pos - position  # positive = improved (lower position number)

        has_article = keyword.lower() in article_keywords
        article_id = article_keywords.get(keyword.lower())

        # Quick Wins: positions 5-20 with decent impressions
        if 5 <= position <= 20 and impressions >= 50:
            quick_wins.append(
                KeywordOpportunity(
                    keyword=keyword,
                    clicks=clicks,
                    impressions=impressions,
                    ctr=round(ctr, 4),
                    position=round(position, 2),
                    opportunity_type="quick_win",
                    position_change=round(position_change, 2),
                    has_existing_article=has_article,
                    existing_article_id=article_id,
                )
            )

        # Content Gaps: high impressions but very low CTR
        if impressions >= 100 and ctr < 0.02:
            content_gaps.append(
                KeywordOpportunity(
                    keyword=keyword,
                    clicks=clicks,
                    impressions=impressions,
                    ctr=round(ctr, 4),
                    position=round(position, 2),
                    opportunity_type="content_gap",
                    position_change=round(position_change, 2),
                    has_existing_article=has_article,
                    existing_article_id=article_id,
                )
            )

        # Rising Keywords: position improved by > 3
        if position_change > 3:
            rising_keywords.append(
                KeywordOpportunity(
                    keyword=keyword,
                    clicks=clicks,
                    impressions=impressions,
                    ctr=round(ctr, 4),
                    position=round(position, 2),
                    opportunity_type="rising",
                    position_change=round(position_change, 2),
                    has_existing_article=has_article,
                    existing_article_id=article_id,
                )
            )

    # Sort each category
    quick_wins.sort(key=lambda x: x.impressions, reverse=True)
    content_gaps.sort(key=lambda x: x.impressions, reverse=True)
    rising_keywords.sort(key=lambda x: x.position_change, reverse=True)

    total = len(quick_wins) + len(content_gaps) + len(rising_keywords)

    return ContentOpportunitiesResponse(
        quick_wins=quick_wins[:50],
        content_gaps=content_gaps[:50],
        rising_keywords=rising_keywords[:50],
        total_opportunities=total,
        start_date=start_date,
        end_date=end_date,
    )


@router.post("/opportunities/suggest", response_model=ContentSuggestionsResponse)
async def suggest_content(
    request: ContentSuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate AI-powered content suggestions based on selected keywords.
    """
    connection = await get_gsc_connection(current_user.id, db)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GSC not connected",
        )

    # Fetch keyword data for the requested keywords
    kw_query = (
        select(
            KeywordRanking.keyword,
            func.sum(KeywordRanking.clicks).label("clicks"),
            func.sum(KeywordRanking.impressions).label("impressions"),
            func.avg(KeywordRanking.ctr).label("ctr"),
            func.avg(KeywordRanking.position).label("position"),
        )
        .where(
            and_(
                KeywordRanking.user_id == current_user.id,
                KeywordRanking.keyword.in_(request.keywords),
            )
        )
        .group_by(KeywordRanking.keyword)
    )
    kw_result = await db.execute(kw_query)
    keyword_data = [
        {
            "keyword": row.keyword,
            "clicks": row.clicks or 0,
            "impressions": row.impressions or 0,
            "ctr": row.ctr or 0.0,
            "position": row.position or 0.0,
        }
        for row in kw_result.all()
    ]

    # Include any keywords that weren't found in the DB with default values
    found_kws = {kd["keyword"] for kd in keyword_data}
    for kw in request.keywords:
        if kw not in found_kws:
            keyword_data.append({
                "keyword": kw,
                "clicks": 0,
                "impressions": 0,
                "ctr": 0.0,
                "position": 0.0,
            })

    # Fetch existing article titles
    articles_query = select(Article.title).where(
        Article.user_id == current_user.id
    )
    articles_result = await db.execute(articles_query)
    existing_titles = [row[0] for row in articles_result.all()]

    # Get user language preference
    user_result = await db.execute(
        select(User.language).where(User.id == current_user.id)
    )
    user_lang = user_result.scalar() or "en"

    # Call AI adapter
    from adapters.ai.anthropic_adapter import content_ai_service

    try:
        suggestions_data = await content_ai_service.generate_content_suggestions(
            keywords=keyword_data,
            existing_articles=existing_titles,
            language=user_lang,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate suggestions: {str(e)}",
        )

    suggestions = [
        ContentSuggestion(
            suggested_title=s.get("suggested_title", ""),
            target_keyword=s.get("target_keyword", ""),
            content_angle=s.get("content_angle", ""),
            rationale=s.get("rationale", ""),
            estimated_difficulty=s.get("estimated_difficulty", "medium"),
            estimated_word_count=s.get("estimated_word_count", 1500),
        )
        for s in suggestions_data[:request.max_suggestions]
    ]

    return ContentSuggestionsResponse(
        suggestions=suggestions,
        based_on_keywords=request.keywords,
    )
