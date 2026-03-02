"""
Revenue Attribution Service.

Calculates content ROI by cross-referencing GSC organic traffic data with
conversion goals.  All heavy lifting is done in async SQLAlchemy queries so
the service never blocks the event loop.
"""

import logging
import math
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.content import Article
from infrastructure.database.models.revenue import (
    ContentConversion,
    ConversionGoal,
    RevenueReport,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _default_date_range(
    start_date: date | None,
    end_date: date | None,
    days: int = 30,
) -> tuple[date, date]:
    """Return (start, end) defaulting to the last *days* days."""
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=days - 1)
    return start_date, end_date


def _normalize_url(url: str) -> str:
    """ANA-06: Canonicalize a URL for matching against article published_url.

    # ANA-37: Normalizes URL by stripping scheme, www prefix, trailing slash, and query params
    Normalizations applied:
    - Strip query string and fragment
    - Lower-case scheme and host
    - Remove www. prefix
    - Strip trailing slash from path
    - Force https scheme (treat http and https as the same)
    """
    try:
        p = urlparse(url.strip())
        scheme = "https"
        netloc = (p.netloc or "").lower()
        host = netloc[4:] if netloc.startswith("www.") else netloc
        path = p.path.rstrip("/")
        return urlunparse((scheme, host, path, "", "", ""))
    except Exception:
        return url.rstrip("/")


def _safe_rate(numerator: float, denominator: float) -> float:
    """Return numerator/denominator as a percentage, or 0.0 on zero-division."""
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 4)


def _pct_change(current: float, previous: float) -> float | None:
    """Percentage change from previous to current.  None when previous is 0."""
    if not previous:
        return None
    return round(((current - previous) / previous) * 100, 2)


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def get_revenue_overview(
    user_id: str,
    db: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """
    Return a high-level revenue overview for a user over a date range.

    Includes totals, conversion rate, active-goal count, top articles,
    top keywords, and a comparison with the immediately preceding period
    of the same length.

    If no dates are supplied the last 30 days are used.
    """
    start_date, end_date = _default_date_range(start_date, end_date, days=30)
    period_days = (end_date - start_date).days + 1

    # Previous period of equal length for comparison
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days - 1)

    # --- Current period totals -------------------------------------------------
    totals_q = select(
        func.sum(ContentConversion.visits).label("total_visits"),
        func.sum(ContentConversion.conversions).label("total_conversions"),
        func.sum(ContentConversion.revenue).label("total_revenue"),
    ).where(
        and_(
            ContentConversion.user_id == user_id,
            ContentConversion.date >= start_date,
            ContentConversion.date <= end_date,
        )
    )
    totals_row = (await db.execute(totals_q)).one()

    total_visits = int(totals_row.total_visits or 0)
    total_conversions = int(totals_row.total_conversions or 0)
    total_revenue = float(totals_row.total_revenue or 0.0)
    conversion_rate = _safe_rate(total_conversions, total_visits)

    # --- Previous period totals for comparison ---------------------------------
    prev_totals_q = select(
        func.sum(ContentConversion.visits).label("total_visits"),
        func.sum(ContentConversion.conversions).label("total_conversions"),
        func.sum(ContentConversion.revenue).label("total_revenue"),
    ).where(
        and_(
            ContentConversion.user_id == user_id,
            ContentConversion.date >= prev_start,
            ContentConversion.date <= prev_end,
        )
    )
    prev_row = (await db.execute(prev_totals_q)).one()

    prev_visits = int(prev_row.total_visits or 0)
    prev_conversions = int(prev_row.total_conversions or 0)
    prev_revenue = float(prev_row.total_revenue or 0.0)

    # --- Active goals count ----------------------------------------------------
    goals_q = select(func.count(ConversionGoal.id)).where(
        and_(
            ConversionGoal.user_id == user_id,
            ConversionGoal.is_active == True,  # noqa: E712
        )
    )
    active_goals = (await db.execute(goals_q)).scalar() or 0

    # --- Top 5 articles by revenue ---------------------------------------------
    top_articles_q = (
        select(
            ContentConversion.article_id,
            Article.title,
            Article.keyword,
            Article.published_url,
            func.sum(ContentConversion.visits).label("visits"),
            func.sum(ContentConversion.conversions).label("conversions"),
            func.sum(ContentConversion.revenue).label("revenue"),
        )
        .join(Article, Article.id == ContentConversion.article_id, isouter=True)
        .where(
            and_(
                ContentConversion.user_id == user_id,
                ContentConversion.article_id.isnot(None),
                ContentConversion.date >= start_date,
                ContentConversion.date <= end_date,
            )
        )
        .group_by(
            ContentConversion.article_id,
            Article.title,
            Article.keyword,
            Article.published_url,
        )
        .order_by(desc("revenue"))
        .limit(5)
    )
    top_articles_rows = (await db.execute(top_articles_q)).all()

    top_articles = [
        {
            "article_id": row.article_id,
            "title": row.title,
            "keyword": row.keyword,
            "published_url": row.published_url,
            "visits": int(row.visits or 0),
            "conversions": int(row.conversions or 0),
            "revenue": float(row.revenue or 0.0),
            "conversion_rate": _safe_rate(int(row.conversions or 0), int(row.visits or 0)),
        }
        for row in top_articles_rows
    ]

    # --- Top 5 keywords by revenue ---------------------------------------------
    top_kw_q = (
        select(
            ContentConversion.keyword,
            func.sum(ContentConversion.visits).label("visits"),
            func.sum(ContentConversion.conversions).label("conversions"),
            func.sum(ContentConversion.revenue).label("revenue"),
        )
        .where(
            and_(
                ContentConversion.user_id == user_id,
                ContentConversion.keyword.isnot(None),
                ContentConversion.date >= start_date,
                ContentConversion.date <= end_date,
            )
        )
        .group_by(ContentConversion.keyword)
        .order_by(desc("revenue"))
        .limit(5)
    )
    top_kw_rows = (await db.execute(top_kw_q)).all()

    top_keywords = [
        {
            "keyword": row.keyword,
            "visits": int(row.visits or 0),
            "conversions": int(row.conversions or 0),
            "revenue": float(row.revenue or 0.0),
            "conversion_rate": _safe_rate(int(row.conversions or 0), int(row.visits or 0)),
        }
        for row in top_kw_rows
    ]

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": period_days,
        },
        "total_organic_visits": total_visits,
        "total_conversions": total_conversions,
        "total_revenue": round(total_revenue, 2),
        "conversion_rate": conversion_rate,
        "active_goals": int(active_goals),
        "top_articles": top_articles,
        "top_keywords": top_keywords,
        "comparison": {
            "previous_period_start": prev_start.isoformat(),
            "previous_period_end": prev_end.isoformat(),
            "visits_change_pct": _pct_change(total_visits, prev_visits),
            "conversions_change_pct": _pct_change(total_conversions, prev_conversions),
            "revenue_change_pct": _pct_change(total_revenue, prev_revenue),
            "previous_visits": prev_visits,
            "previous_conversions": prev_conversions,
            "previous_revenue": round(prev_revenue, 2),
        },
    }


async def get_revenue_by_article(
    user_id: str,
    db: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    Return paginated content conversion data grouped by article.

    Joins with Article for title / keyword / published_url.
    Sorted by revenue descending.  ROI is returned as None until a cost
    tracking model is introduced.
    """
    start_date, end_date = _default_date_range(start_date, end_date, days=30)

    base_where = and_(
        ContentConversion.user_id == user_id,
        ContentConversion.article_id.isnot(None),
        ContentConversion.date >= start_date,
        ContentConversion.date <= end_date,
    )

    # --- Total distinct articles for pagination --------------------------------
    count_q = select(func.count(func.distinct(ContentConversion.article_id))).where(base_where)
    total_items = (await db.execute(count_q)).scalar() or 0
    total_pages = math.ceil(total_items / page_size) if total_items else 1
    offset = (page - 1) * page_size

    # --- Paginated data --------------------------------------------------------
    data_q = (
        select(
            ContentConversion.article_id,
            Article.title,
            Article.keyword,
            Article.published_url,
            func.sum(ContentConversion.visits).label("visits"),
            func.sum(ContentConversion.conversions).label("conversions"),
            func.sum(ContentConversion.revenue).label("revenue"),
        )
        .join(Article, Article.id == ContentConversion.article_id, isouter=True)
        .where(base_where)
        .group_by(
            ContentConversion.article_id,
            Article.title,
            Article.keyword,
            Article.published_url,
        )
        .order_by(desc("revenue"))
        .offset(offset)
        .limit(page_size)
    )
    rows = (await db.execute(data_q)).all()

    items = [
        {
            "article_id": row.article_id,
            "title": row.title,
            "keyword": row.keyword,
            "published_url": row.published_url,
            "visits": int(row.visits or 0),
            "conversions": int(row.conversions or 0),
            "revenue": round(float(row.revenue or 0.0), 2),
            "conversion_rate": _safe_rate(int(row.conversions or 0), int(row.visits or 0)),
            # ROI requires cost data not yet captured in the schema.
            # None signals the frontend to hide the column until cost
            # tracking is introduced.
            "roi": None,
        }
        for row in rows
    ]

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        },
        "items": items,
    }


async def get_revenue_by_keyword(
    user_id: str,
    db: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    Return paginated content conversion data grouped by keyword.

    Sorted by revenue descending.
    """
    start_date, end_date = _default_date_range(start_date, end_date, days=30)

    base_where = and_(
        ContentConversion.user_id == user_id,
        ContentConversion.keyword.isnot(None),
        ContentConversion.date >= start_date,
        ContentConversion.date <= end_date,
    )

    # --- Total distinct keywords for pagination --------------------------------
    count_q = select(func.count(func.distinct(ContentConversion.keyword))).where(base_where)
    total_items = (await db.execute(count_q)).scalar() or 0
    total_pages = math.ceil(total_items / page_size) if total_items else 1
    offset = (page - 1) * page_size

    # --- Paginated data --------------------------------------------------------
    data_q = (
        select(
            ContentConversion.keyword,
            func.sum(ContentConversion.visits).label("visits"),
            func.sum(ContentConversion.conversions).label("conversions"),
            func.sum(ContentConversion.revenue).label("revenue"),
        )
        .where(base_where)
        .group_by(ContentConversion.keyword)
        .order_by(desc("revenue"))
        .offset(offset)
        .limit(page_size)
    )
    rows = (await db.execute(data_q)).all()

    items = [
        {
            "keyword": row.keyword,
            "visits": int(row.visits or 0),
            "conversions": int(row.conversions or 0),
            "revenue": round(float(row.revenue or 0.0), 2),
            "conversion_rate": _safe_rate(int(row.conversions or 0), int(row.visits or 0)),
        }
        for row in rows
    ]

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        },
        "items": items,
    }


async def import_conversions(
    user_id: str,
    db: AsyncSession,
    goal_id: str,
    conversions_data: list[dict],
) -> dict:
    """
    Import a batch of daily conversion records for a specific goal.

    Each item in *conversions_data* must contain:
        page_url    (str)
        date        (str ISO-8601 or date object)
        visits      (int)
        conversions (int)
        revenue     (float)

    Matching against Article.published_url uses exact-match after stripping
    trailing slashes to handle the most common URL normalisation mismatch.
    """
    if not conversions_data:
        return {"imported_count": 0, "matched_articles": 0}

    # Verify the goal belongs to this user
    goal_q = select(ConversionGoal.id).where(
        and_(
            ConversionGoal.id == goal_id,
            ConversionGoal.user_id == user_id,
        )
    )
    goal_exists = (await db.execute(goal_q)).scalar()
    if not goal_exists:
        logger.warning("import_conversions: goal %s not found for user %s", goal_id, user_id)
        return {"imported_count": 0, "matched_articles": 0, "error": "goal_not_found"}

    # Build a normalised URL -> article_id lookup
    articles_q = select(Article.id, Article.published_url).where(
        and_(
            Article.user_id == user_id,
            Article.published_url.isnot(None),
        )
    )
    article_rows = (await db.execute(articles_q)).all()
    url_to_article: dict[str, str] = {
        _normalize_url(row.published_url): row.id for row in article_rows if row.published_url
    }

    imported_count = 0
    matched_article_ids: set[str] = set()

    for item in conversions_data:
        page_url: str = str(item.get("page_url", "")).strip()
        if not page_url:
            logger.debug("import_conversions: skipping item with empty page_url")
            continue

        # Parse date
        raw_date = item.get("date")
        if isinstance(raw_date, date) and not isinstance(raw_date, datetime):
            conv_date = raw_date
        elif isinstance(raw_date, datetime):
            conv_date = raw_date.date()
        elif isinstance(raw_date, str):
            try:
                conv_date = date.fromisoformat(raw_date[:10])
            except ValueError:
                logger.warning("import_conversions: unparseable date %r – skipping", raw_date)
                continue
        else:
            logger.warning("import_conversions: missing date field – skipping")
            continue

        visits = int(item.get("visits", 0))
        conversions_count = int(item.get("conversions", 0))
        revenue = float(item.get("revenue", 0.0))

        # Match article by normalised URL (ANA-06: full normalization)
        normalised_url = _normalize_url(page_url)
        article_id = url_to_article.get(normalised_url)
        if article_id:
            matched_article_ids.add(article_id)

        record = ContentConversion(
            id=str(uuid4()),
            user_id=user_id,
            goal_id=goal_id,
            article_id=article_id,
            page_url=page_url,
            date=conv_date,
            visits=visits,
            conversions=conversions_count,
            revenue=revenue,
        )
        db.add(record)
        imported_count += 1

    if imported_count:
        # ANA-27: Use commit() not flush() to ensure data is persisted even on interrupt
        await db.commit()

    return {
        "imported_count": imported_count,
        "matched_articles": len(matched_article_ids),
    }


async def generate_revenue_report(
    user_id: str,
    db: AsyncSession,
    report_type: str = "monthly",
) -> dict:
    """
    Aggregate conversion data for the requested period, persist a
    RevenueReport record, and return the full report payload.

    Supported report_type values:
        "weekly"  – last 7 days
        "monthly" – last 30 days  (default for unknown values)
    """
    today = date.today()

    if report_type == "weekly":
        period_days = 7
    else:
        report_type = "monthly"
        period_days = 30

    end_date = today
    start_date = today - timedelta(days=period_days - 1)

    # --- Aggregate totals ------------------------------------------------------
    totals_q = select(
        func.sum(ContentConversion.visits).label("total_visits"),
        func.sum(ContentConversion.conversions).label("total_conversions"),
        func.sum(ContentConversion.revenue).label("total_revenue"),
    ).where(
        and_(
            ContentConversion.user_id == user_id,
            ContentConversion.date >= start_date,
            ContentConversion.date <= end_date,
        )
    )
    totals_row = (await db.execute(totals_q)).one()

    total_visits = int(totals_row.total_visits or 0)
    total_conversions = int(totals_row.total_conversions or 0)
    total_revenue = float(totals_row.total_revenue or 0.0)
    conversion_rate = _safe_rate(total_conversions, total_visits)

    # --- Top 10 articles -------------------------------------------------------
    top_articles_q = (
        select(
            ContentConversion.article_id,
            Article.title,
            Article.keyword,
            Article.published_url,
            func.sum(ContentConversion.visits).label("visits"),
            func.sum(ContentConversion.conversions).label("conversions"),
            func.sum(ContentConversion.revenue).label("revenue"),
        )
        .join(Article, Article.id == ContentConversion.article_id, isouter=True)
        .where(
            and_(
                ContentConversion.user_id == user_id,
                ContentConversion.article_id.isnot(None),
                ContentConversion.date >= start_date,
                ContentConversion.date <= end_date,
            )
        )
        .group_by(
            ContentConversion.article_id,
            Article.title,
            Article.keyword,
            Article.published_url,
        )
        .order_by(desc("revenue"))
        .limit(10)
    )
    top_articles_rows = (await db.execute(top_articles_q)).all()

    top_articles = [
        {
            "article_id": row.article_id,
            "title": row.title,
            "keyword": row.keyword,
            "published_url": row.published_url,
            "visits": int(row.visits or 0),
            "conversions": int(row.conversions or 0),
            "revenue": round(float(row.revenue or 0.0), 2),
            "conversion_rate": _safe_rate(int(row.conversions or 0), int(row.visits or 0)),
        }
        for row in top_articles_rows
    ]

    # --- Top 10 keywords -------------------------------------------------------
    top_kw_q = (
        select(
            ContentConversion.keyword,
            func.sum(ContentConversion.visits).label("visits"),
            func.sum(ContentConversion.conversions).label("conversions"),
            func.sum(ContentConversion.revenue).label("revenue"),
        )
        .where(
            and_(
                ContentConversion.user_id == user_id,
                ContentConversion.keyword.isnot(None),
                ContentConversion.date >= start_date,
                ContentConversion.date <= end_date,
            )
        )
        .group_by(ContentConversion.keyword)
        .order_by(desc("revenue"))
        .limit(10)
    )
    top_kw_rows = (await db.execute(top_kw_q)).all()

    top_keywords = [
        {
            "keyword": row.keyword,
            "visits": int(row.visits or 0),
            "conversions": int(row.conversions or 0),
            "revenue": round(float(row.revenue or 0.0), 2),
            "conversion_rate": _safe_rate(int(row.conversions or 0), int(row.visits or 0)),
        }
        for row in top_kw_rows
    ]

    # --- Persist report record -------------------------------------------------
    report = RevenueReport(
        id=str(uuid4()),
        user_id=user_id,
        report_type=report_type,
        period_start=start_date,
        period_end=end_date,
        total_organic_visits=total_visits,
        total_conversions=total_conversions,
        total_revenue=round(total_revenue, 2),
        top_articles=top_articles,
        top_keywords=top_keywords,
        generated_at=datetime.now(UTC),
    )
    db.add(report)
    await db.flush()

    return {
        "report_id": report.id,
        "report_type": report_type,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": period_days,
        },
        "total_organic_visits": total_visits,
        "total_conversions": total_conversions,
        "total_revenue": round(total_revenue, 2),
        "conversion_rate": conversion_rate,
        "top_articles": top_articles,
        "top_keywords": top_keywords,
        "generated_at": report.generated_at.isoformat(),
    }
