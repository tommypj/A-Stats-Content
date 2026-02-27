"""
Content Decay Detection Service.

Compares GSC performance metrics across time periods to detect
declining content and generate alerts with AI-powered recovery suggestions.
"""

import logging
from datetime import date, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.analytics import (
    KeywordRanking,
    PagePerformance,
    ContentDecayAlert,
)
from infrastructure.database.models.content import Article

logger = logging.getLogger(__name__)

# Detection thresholds
POSITION_WARNING_THRESHOLD = 3.0   # position worsened by 3+
POSITION_CRITICAL_THRESHOLD = 5.0  # position worsened by 5+
CLICKS_WARNING_PCT = -20.0         # clicks dropped 20%+
CLICKS_CRITICAL_PCT = -40.0        # clicks dropped 40%+
IMPRESSIONS_WARNING_PCT = -25.0    # impressions dropped 25%+
IMPRESSIONS_CRITICAL_PCT = -50.0   # impressions dropped 50%+
CTR_WARNING_PCT = -20.0
CTR_CRITICAL_PCT = -40.0
MIN_IMPRESSIONS_FOR_ALERT = 50     # minimum impressions to trigger alert


async def detect_keyword_decay(
    db: AsyncSession,
    user_id: str,
    project_id: Optional[str] = None,
    period_days: int = 7,
) -> list[ContentDecayAlert]:
    """
    Compare keyword performance between current and previous period.
    Returns list of new alerts (not yet committed).
    """
    end_date = date.today() - timedelta(days=3)  # GSC has 3-day lag
    start_date = end_date - timedelta(days=period_days - 1)
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days - 1)

    # Current period aggregates
    current_q = (
        select(
            KeywordRanking.keyword,
            func.sum(KeywordRanking.clicks).label("clicks"),
            func.sum(KeywordRanking.impressions).label("impressions"),
            func.avg(KeywordRanking.ctr).label("ctr"),
            func.avg(KeywordRanking.position).label("position"),
        )
        .where(
            and_(
                KeywordRanking.user_id == user_id,
                KeywordRanking.date >= start_date,
                KeywordRanking.date <= end_date,
            )
        )
        .group_by(KeywordRanking.keyword)
    )
    current_result = await db.execute(current_q)
    current_data = {row.keyword: row for row in current_result.all()}

    # Previous period aggregates
    prev_q = (
        select(
            KeywordRanking.keyword,
            func.sum(KeywordRanking.clicks).label("clicks"),
            func.sum(KeywordRanking.impressions).label("impressions"),
            func.avg(KeywordRanking.ctr).label("ctr"),
            func.avg(KeywordRanking.position).label("position"),
        )
        .where(
            and_(
                KeywordRanking.user_id == user_id,
                KeywordRanking.date >= prev_start,
                KeywordRanking.date <= prev_end,
            )
        )
        .group_by(KeywordRanking.keyword)
    )
    prev_result = await db.execute(prev_q)
    prev_data = {row.keyword: row for row in prev_result.all()}

    # ANA-29: No N+1 here — keywords and articles are each loaded in a single batch query.
    # Match articles to keywords
    articles_q = select(Article.id, Article.keyword, Article.project_id, Article.published_url).where(
        Article.user_id == user_id
    )
    articles_result = await db.execute(articles_q)
    article_map = {row.keyword.lower(): (row.id, row.project_id, row.published_url) for row in articles_result.all() if row.keyword}

    alerts: list[ContentDecayAlert] = []

    for keyword, curr in current_data.items():
        # ANA-32: Normalise case for consistent cross-period matching
        prev = prev_data.get(keyword) or prev_data.get(keyword.lower())
        if not prev:
            continue

        prev_impressions = prev.impressions or 0
        if prev_impressions < MIN_IMPRESSIONS_FOR_ALERT:
            continue

        curr_clicks = curr.clicks or 0
        prev_clicks = prev.clicks or 0
        curr_position = float(curr.position or 0)
        prev_position = float(prev.position or 0)
        curr_impressions = curr.impressions or 0
        curr_ctr = float(curr.ctr or 0)
        prev_ctr = float(prev.ctr or 0)

        # ANA-31: Truncate excessively long keywords before any DB or dict operations
        if keyword and len(keyword) > 200:
            keyword = keyword[:200]

        # Look up article
        article_info = article_map.get(keyword.lower())
        article_id = article_info[0] if article_info else None
        art_project_id = article_info[1] if article_info else project_id

        # Position decay (higher number = worse)
        position_change = curr_position - prev_position
        if position_change >= POSITION_WARNING_THRESHOLD:
            severity = "critical" if position_change >= POSITION_CRITICAL_THRESHOLD else "warning"
            pct = (position_change / prev_position * 100) if prev_position > 0 else 0
            alerts.append(ContentDecayAlert(
                id=str(uuid4()),
                user_id=user_id,
                project_id=art_project_id,
                article_id=article_id,
                alert_type="position_drop",
                severity=severity,
                keyword=keyword,
                page_url=article_info[2] if article_info else None,
                metric_name="position",
                metric_before=prev_position,
                metric_after=curr_position,
                period_days=period_days,
                percentage_change=round(pct, 2),
            ))

        # Clicks decay
        if prev_clicks > 0:
            clicks_pct = ((curr_clicks - prev_clicks) / prev_clicks) * 100
            if clicks_pct <= CLICKS_WARNING_PCT:
                severity = "critical" if clicks_pct <= CLICKS_CRITICAL_PCT else "warning"
                alerts.append(ContentDecayAlert(
                    id=str(uuid4()),
                    user_id=user_id,
                    project_id=art_project_id,
                    article_id=article_id,
                    alert_type="traffic_drop",
                    severity=severity,
                    keyword=keyword,
                    page_url=article_info[2] if article_info else None,
                    metric_name="clicks",
                    metric_before=float(prev_clicks),
                    metric_after=float(curr_clicks),
                    period_days=period_days,
                    percentage_change=round(clicks_pct, 2),
                ))

        # Impressions decay
        if prev_impressions > 0:
            impressions_pct = ((curr_impressions - prev_impressions) / prev_impressions) * 100
        else:
            impressions_pct = 0.0
        if impressions_pct <= IMPRESSIONS_WARNING_PCT:
            severity = "critical" if impressions_pct <= IMPRESSIONS_CRITICAL_PCT else "warning"
            alerts.append(ContentDecayAlert(
                id=str(uuid4()),
                user_id=user_id,
                project_id=art_project_id,
                article_id=article_id,
                alert_type="impressions_drop",
                severity=severity,
                keyword=keyword,
                page_url=article_info[2] if article_info else None,
                metric_name="impressions",
                metric_before=float(prev_impressions),
                metric_after=float(curr_impressions),
                period_days=period_days,
                percentage_change=round(impressions_pct, 2),
            ))

        # CTR decay
        if prev_ctr > 0:
            ctr_pct = ((curr_ctr - prev_ctr) / prev_ctr) * 100
            if ctr_pct <= CTR_WARNING_PCT:
                severity = "critical" if ctr_pct <= CTR_CRITICAL_PCT else "warning"
                alerts.append(ContentDecayAlert(
                    id=str(uuid4()),
                    user_id=user_id,
                    project_id=art_project_id,
                    article_id=article_id,
                    alert_type="ctr_drop",
                    severity=severity,
                    keyword=keyword,
                    page_url=article_info[2] if article_info else None,
                    metric_name="ctr",
                    metric_before=prev_ctr,
                    metric_after=curr_ctr,
                    period_days=period_days,
                    percentage_change=round(ctr_pct, 2),
                ))

    return alerts


async def run_decay_detection(
    db: AsyncSession,
    user_id: str,
    project_id: Optional[str] = None,
) -> int:
    """
    Run full decay detection and persist new alerts.
    Returns number of new alerts created.
    """
    alerts = await detect_keyword_decay(db, user_id, project_id)

    if not alerts:
        return 0

    # Deduplicate: don't create alert if same type+keyword already exists unresolved
    # ANA-07: scope dedup to current project to avoid cross-project suppression
    dedup_conditions = [
        ContentDecayAlert.user_id == user_id,
        ContentDecayAlert.is_resolved == False,
    ]
    if project_id:
        dedup_conditions.append(ContentDecayAlert.project_id == project_id)
    existing_q = select(
        ContentDecayAlert.keyword, ContentDecayAlert.alert_type
    ).where(and_(*dedup_conditions))
    existing_result = await db.execute(existing_q)
    existing_keys = {(row.keyword, row.alert_type) for row in existing_result.all()}

    new_alerts = [
        a for a in alerts
        if (a.keyword, a.alert_type) not in existing_keys
    ]

    # ANA-30: Catch IntegrityError per-alert to handle concurrent duplicate inserts.
    # Use nested savepoints so only the individual failing INSERT is rolled back,
    # not the entire outer transaction.
    for alert in new_alerts:
        try:
            savepoint = await db.begin_nested()
            db.add(alert)
            await savepoint.commit()
        except IntegrityError:
            await savepoint.rollback()
            # Alert already exists (concurrent insert), skip it
            logger.debug("Skipping duplicate decay alert for keyword=%s type=%s", alert.keyword, alert.alert_type)

    if new_alerts:
        await db.commit()

    logger.info("Content decay: %d new alerts for user %s", len(new_alerts), user_id)
    return len(new_alerts)


async def generate_recovery_suggestions(
    db: AsyncSession,
    alert_id: str,
    user_id: str,
) -> dict:
    """
    Generate AI-powered recovery suggestions for a decay alert.
    Returns a dict with suggestions list.
    """
    alert_result = await db.execute(
        select(ContentDecayAlert).where(
            and_(
                ContentDecayAlert.id == alert_id,
                ContentDecayAlert.user_id == user_id,
            )
        )
    )
    alert = alert_result.scalar_one_or_none()
    if not alert:
        return {"suggestions": []}

    # Get article context if available
    article_title = ""
    article_keyword = ""
    if alert.article_id:
        article_q = await db.execute(
            select(Article.title, Article.keyword).where(Article.id == alert.article_id)
        )
        article_row = article_q.first()
        if article_row:
            article_title = article_row.title
            article_keyword = article_row.keyword

    from adapters.ai.anthropic_adapter import content_ai_service

    prompt = f"""Analyze this content performance decline and suggest specific recovery actions:

Alert Type: {alert.alert_type}
Severity: {alert.severity}
Keyword: {alert.keyword or article_keyword}
Page URL: {alert.page_url or "N/A"}
Article Title: {article_title or "N/A"}
Metric: {alert.metric_name}
Previous Value: {alert.metric_before}
Current Value: {alert.metric_after}
Change: {alert.percentage_change}%
Period: {alert.period_days} days

Provide 3-5 specific, actionable recovery suggestions. For each suggestion include:
- action: A concise title (e.g., "Update content with fresh data")
- description: Detailed explanation of what to do
- priority: "high", "medium", or "low"
- estimated_impact: "high", "medium", or "low"

Return as JSON array of objects with keys: action, description, priority, estimated_impact"""

    try:
        response = await content_ai_service.generate_text(prompt, max_tokens=1500)
        import json
        # ANA-34: Cap AI response size before parsing to prevent memory/CPU abuse
        if len(response) > 50000:
            response = response[:50000]
        # Try to parse JSON from the response
        # Strip markdown code fences if present
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        suggestions = json.loads(text)
        if not isinstance(suggestions, list):
            suggestions = suggestions.get("suggestions", []) if isinstance(suggestions, dict) else []

        # Store on the alert
        alert.suggested_actions = {"suggestions": suggestions}
        await db.commit()

        return {"suggestions": suggestions}
    except Exception as e:
        logger.error("Failed to generate recovery suggestions: %s", str(e))
        return {"suggestions": [
            {
                "action": "Review and update content",
                "description": f"Your {alert.metric_name} has declined by {alert.percentage_change}%. Review the content for freshness and relevance.",
                "priority": "high",
                "estimated_impact": "medium",
            },
            {
                "action": "Analyze competitor content",
                "description": "Check what competitors are ranking for this keyword and identify gaps in your content.",
                "priority": "medium",
                "estimated_impact": "high",
            },
            {
                "action": "Improve on-page SEO",
                "description": "Update meta title, description, and heading structure to better target the keyword.",
                "priority": "medium",
                "estimated_impact": "medium",
            },
        ]}


async def get_content_health_score(
    db: AsyncSession,
    user_id: str,
) -> dict:
    """
    Calculate an overall content health score based on decay alerts.
    Returns health metrics.

    # ANA-39: TODO — add Redis caching for content health scores (recomputed on every call)
    """
    # Count active (unresolved) alerts by severity
    alerts_q = (
        select(
            ContentDecayAlert.severity,
            func.count(ContentDecayAlert.id).label("count"),
        )
        .where(
            and_(
                ContentDecayAlert.user_id == user_id,
                ContentDecayAlert.is_resolved == False,
            )
        )
        .group_by(ContentDecayAlert.severity)
    )
    alerts_result = await db.execute(alerts_q)
    severity_counts = {row.severity: row.count for row in alerts_result.all()}

    warnings = severity_counts.get("warning", 0)
    criticals = severity_counts.get("critical", 0)
    total_active = warnings + criticals

    # Count total published articles
    total_articles_q = select(func.count(Article.id)).where(
        and_(
            Article.user_id == user_id,
            Article.published_url.isnot(None),
            Article.published_url != "",
        )
    )
    total_articles = (await db.execute(total_articles_q)).scalar() or 0

    # Count unique articles with active alerts
    declining_q = select(func.count(func.distinct(ContentDecayAlert.article_id))).where(
        and_(
            ContentDecayAlert.user_id == user_id,
            ContentDecayAlert.is_resolved == False,
            ContentDecayAlert.article_id.isnot(None),
        )
    )
    declining_articles = (await db.execute(declining_q)).scalar() or 0

    # Health score: 100 minus penalties
    if total_articles == 0:
        health_score = 100
    else:
        penalty = (criticals * 10 + warnings * 3) / total_articles * 10
        health_score = max(0, min(100, round(100 - penalty)))

    # Recent alerts (last 10)
    recent_q = (
        select(ContentDecayAlert)
        .where(ContentDecayAlert.user_id == user_id)
        .order_by(ContentDecayAlert.created_at.desc())
        .limit(10)
    )
    recent_result = await db.execute(recent_q)
    recent_alerts = recent_result.scalars().all()

    return {
        "health_score": health_score,
        "total_published_articles": total_articles,
        "declining_articles": declining_articles,
        "active_warnings": warnings,
        "active_criticals": criticals,
        "total_active_alerts": total_active,
        "recent_alerts": recent_alerts,
    }
