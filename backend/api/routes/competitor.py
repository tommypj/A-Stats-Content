"""
Competitor Analysis API routes.
"""

import asyncio
import logging
import math
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.middleware.rate_limit import limiter
from api.dependencies import require_tier
from api.routes.auth import get_current_user
from api.schemas.competitor import (
    AnalyzeCompetitorRequest,
    CompetitorAnalysisResponse,
    CompetitorAnalysisDetailResponse,
    CompetitorAnalysisListResponse,
    CompetitorArticleResponse,
    KeywordAggregation,
    KeywordAggregationListResponse,
    KeywordArticle,
    KeywordGapItem,
    KeywordGapResponse,
)
from infrastructure.database.connection import get_db
from infrastructure.database.models.competitor import CompetitorAnalysis, CompetitorArticle
from infrastructure.database.models.user import User
from services.competitor_analyzer import run_competitor_analysis, compute_keyword_gaps

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/competitors", tags=["competitors"])


@router.post("/analyze", response_model=CompetitorAnalysisResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def analyze_competitor(
    request: Request,
    body: AnalyzeCompetitorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a competitor analysis for the given domain.
    Returns cached result if a non-expired analysis exists.
    """
    require_tier("professional")(current_user)
    domain = body.domain
    project_id = body.project_id

    # Check for cached (non-expired) analysis
    cached_result = await db.execute(
        select(CompetitorAnalysis).where(
            CompetitorAnalysis.user_id == current_user.id,
            CompetitorAnalysis.domain == domain,
            CompetitorAnalysis.expires_at > datetime.now(timezone.utc),
            CompetitorAnalysis.status.in_(["completed", "crawling", "scraping", "extracting", "pending"]),
        ).order_by(CompetitorAnalysis.created_at.desc()).limit(1)
    )
    cached = cached_result.scalar_one_or_none()
    if cached:
        return cached

    # Create new analysis
    analysis = CompetitorAnalysis(
        id=str(uuid4()),
        user_id=current_user.id,
        project_id=project_id,
        domain=domain,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Launch background task
    asyncio.create_task(run_competitor_analysis(analysis.id))
    logger.info("Started competitor analysis %s for domain %s (user: %s)", analysis.id, domain, current_user.id)

    return analysis


@router.get("/analyses", response_model=CompetitorAnalysisListResponse)
async def list_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's competitor analyses, newest first."""
    require_tier("professional")(current_user)
    base_query = select(CompetitorAnalysis).where(
        CompetitorAnalysis.user_id == current_user.id
    )

    # Count
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    # Fetch page
    items_result = await db.execute(
        base_query.order_by(CompetitorAnalysis.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = items_result.scalars().all()

    return CompetitorAnalysisListResponse(
        items=[CompetitorAnalysisResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/analyses/{analysis_id}", response_model=CompetitorAnalysisDetailResponse)
async def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get analysis detail with all articles."""
    require_tier("professional")(current_user)
    result = await db.execute(
        select(CompetitorAnalysis)
        .options(selectinload(CompetitorAnalysis.articles))
        .where(
            CompetitorAnalysis.id == analysis_id,
            CompetitorAnalysis.user_id == current_user.id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return CompetitorAnalysisDetailResponse(
        **CompetitorAnalysisResponse.model_validate(analysis).model_dump(),
        articles=[CompetitorArticleResponse.model_validate(a) for a in analysis.articles],
    )


@router.delete("/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_analysis(
    request: Request,
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a competitor analysis and all its articles."""
    require_tier("professional")(current_user)
    result = await db.execute(
        select(CompetitorAnalysis).where(
            CompetitorAnalysis.id == analysis_id,
            CompetitorAnalysis.user_id == current_user.id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    await db.execute(
        delete(CompetitorArticle).where(CompetitorArticle.analysis_id == analysis_id)
    )
    await db.delete(analysis)
    await db.commit()


@router.get("/analyses/{analysis_id}/keywords", response_model=KeywordAggregationListResponse)
async def get_keywords(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated keywords from a completed analysis."""
    require_tier("professional")(current_user)
    # Verify ownership
    analysis = await db.execute(
        select(CompetitorAnalysis).where(
            CompetitorAnalysis.id == analysis_id,
            CompetitorAnalysis.user_id == current_user.id,
        )
    )
    if not analysis.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Aggregate keywords
    result = await db.execute(
        select(CompetitorArticle)
        .where(
            CompetitorArticle.analysis_id == analysis_id,
            CompetitorArticle.extracted_keyword.isnot(None),
        )
        .order_by(CompetitorArticle.extracted_keyword)
    )
    articles = result.scalars().all()

    # Group by keyword
    keyword_map: dict[str, list] = {}
    for art in articles:
        kw = art.extracted_keyword.lower().strip()
        if kw not in keyword_map:
            keyword_map[kw] = []
        keyword_map[kw].append(KeywordArticle(url=art.url, title=art.title))

    keywords = sorted(
        [
            KeywordAggregation(keyword=kw, article_count=len(arts), articles=arts)
            for kw, arts in keyword_map.items()
        ],
        key=lambda x: x.article_count,
        reverse=True,
    )

    return KeywordAggregationListResponse(keywords=keywords, total=len(keywords))


@router.get("/analyses/{analysis_id}/gaps", response_model=KeywordGapResponse)
async def get_keyword_gaps(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get keyword gap analysis — keywords the competitor covers but user does not."""
    require_tier("professional")(current_user)
    # Verify ownership
    result = await db.execute(
        select(CompetitorAnalysis).where(
            CompetitorAnalysis.id == analysis_id,
            CompetitorAnalysis.user_id == current_user.id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    gap_data = await compute_keyword_gaps(
        db=db,
        analysis_id=analysis_id,
        user_id=current_user.id,
        project_id=analysis.project_id,
    )

    return KeywordGapResponse(
        gaps=[KeywordGapItem(**g) for g in gap_data["gaps"]],
        total_competitor_keywords=gap_data["total_competitor_keywords"],
        total_your_keywords=gap_data["total_your_keywords"],
        total_gaps=gap_data["total_gaps"],
    )
