"""
Article API routes.
"""

import asyncio
import csv
import io
import logging
import math
import re
import time
import markdown
import json
import redis.asyncio as aioredis
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.responses import StreamingResponse
from api.middleware.rate_limit import limiter
from sqlalchemy import select, func, delete, case, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from api.schemas.content import (
    ArticleCreateRequest,
    ArticleGenerateRequest,
    ArticleUpdateRequest,
    ArticleResponse,
    ArticleListResponse,
    ArticleImproveRequest,
    SocialPostsResponse,
    SocialPostUpdateRequest,
    ArticleRevisionResponse,
    ArticleRevisionDetailResponse,
    ArticleRevisionListResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
)
from api.routes.auth import get_current_user
from api.utils import escape_like
from infrastructure.database.connection import get_db, async_session_maker
from infrastructure.database.models import Article, ArticleRevision, Outline, User, ContentStatus
from infrastructure.database.models.project import Project
from infrastructure.database.models.keyword_cache import KeywordResearchCache
from adapters.ai.anthropic_adapter import content_ai_service, GeneratedArticle
from infrastructure.config.settings import settings
from services.generation_tracker import GenerationTracker
from core.plans import ARTICLE_IMPROVE_LIMIT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["articles"])

# Timeout (seconds) for the grammar proofread pass — sourced from settings so it can be
# overridden via environment variable (GEN-31)
PROOFREAD_TIMEOUT_SECONDS = getattr(settings, "ai_request_timeout", 60)

# Limit concurrent AI generation tasks to prevent resource exhaustion
_generation_semaphore = asyncio.Semaphore(5)

# Track active generation tasks so they are not garbage-collected mid-flight
_active_generation_tasks: dict[str, asyncio.Task] = {}

# Maximum revisions kept per article (oldest are pruned beyond this limit)
_MAX_REVISIONS_PER_ARTICLE = 20


async def _save_revision(
    db: AsyncSession,
    article: Article,
    revision_type: str,
    user_id: str,
) -> None:
    """
    Snapshot the article's current content as a new ArticleRevision.
    If the article already has _MAX_REVISIONS_PER_ARTICLE revisions,
    the oldest one is deleted before inserting the new one so the table
    stays bounded.
    """
    # Skip if there is nothing meaningful to save
    if not article.content and not article.title:
        return

    revision = ArticleRevision(
        id=str(uuid4()),
        article_id=article.id,
        created_by=user_id,
        content=article.content,
        content_html=article.content_html,
        title=article.title,
        meta_description=article.meta_description,
        word_count=article.word_count or 0,
        revision_type=revision_type,
    )
    db.add(revision)

    # Prune oldest revisions if the article exceeds the limit
    count_result = await db.execute(
        select(func.count()).where(ArticleRevision.article_id == article.id)
    )
    existing_count = count_result.scalar() or 0

    if existing_count >= _MAX_REVISIONS_PER_ARTICLE:
        # Find and delete the oldest revision(s)
        oldest_result = await db.execute(
            select(ArticleRevision)
            .where(ArticleRevision.article_id == article.id)
            .order_by(ArticleRevision.created_at.asc())
            .limit(existing_count - _MAX_REVISIONS_PER_ARTICLE + 1)
        )
        for old_rev in oldest_result.scalars().all():
            await db.delete(old_rev)


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text[:200]


def calculate_read_time(content: str) -> int:
    """Calculate estimated read time in minutes (200 wpm)."""
    word_count = len(content.split())
    return max(1, round(word_count / 200))


def analyze_seo(content: str, keyword: str, title: str, meta_description: str) -> dict:
    """
    Analyse content for SEO and AEO (Answer Engine Optimisation) metrics.
    Scoring updated 2025-2026 to reflect GEO/AEO best practices: FAQ sections,
    external citations, structured lists, content depth, and Quick Answer blocks.
    """
    content_lower = content.lower()
    keyword_lower = keyword.lower()
    # SEO-08: normalize whitespace for consistent word count across backend/frontend
    words = re.split(r'\s+', content.strip())
    word_count = len(words) if words and words[0] else 0

    # Keyword density (whole-word matches only to avoid substring false positives)
    keyword_count = len(re.findall(r'\b' + re.escape(keyword_lower) + r'\b', content_lower))
    keyword_density = (keyword_count / word_count * 100) if word_count > 0 else 0

    # Title keyword check
    title_has_keyword = bool(re.search(r'\b' + re.escape(keyword_lower) + r'\b', title.lower()))

    # Keyword in opening (first 300 chars — covers HPPP hook + problem)
    keyword_in_opening = bool(re.search(r'\b' + re.escape(keyword_lower) + r'\b', content_lower[:300]))

    # Headings: H2 count (## but not ###)
    h2_count = len(re.findall(r"^## ", content, re.MULTILINE))
    h3_count = len(re.findall(r"^### ", content, re.MULTILINE))
    headings_structure = "good" if h2_count >= 3 else "needs_improvement"

    # Links
    internal_links = len(re.findall(r"\[.*?\]\(/", content))
    external_links = len(re.findall(r"\[.*?\]\(https?://", content))

    # FAQ section (H2 titled "Frequently Asked Questions" or "FAQ")
    has_faq = bool(re.search(r"^## .*(frequently asked questions|faq)", content, re.MULTILINE | re.IGNORECASE))

    # Structured lists (bullet or numbered)
    has_lists = bool(re.search(r"^(\s*[-*+]|\s*\d+\.)\s", content, re.MULTILINE))

    # Quick Answer / TL;DR block (> **Quick Answer:** or similar blockquote pattern)
    has_quick_answer = bool(re.search(r">\s*\*\*(quick answer|tl;?dr|summary|key takeaway)", content, re.IGNORECASE))

    # Image alt texts
    images = re.findall(r"!\[(.*?)\]\(", content)
    image_alt_texts = bool(images) and all(alt.strip() for alt in images)

    # Basic readability (average sentence length)
    sentences = [s for s in re.split(r"[.!?]+", content) if s.strip()]
    avg_sentence_length = word_count / len(sentences) if sentences else 0
    readability_score = min(100, max(0, 100 - (avg_sentence_length - 15) * 2))

    # ----------------------------------------------------------------
    # Generate actionable suggestions
    # ----------------------------------------------------------------
    suggestions = []
    if keyword_density < 1:
        suggestions.append(f"Increase keyword '{keyword}' usage (currently {keyword_density:.1f}%)")
    elif keyword_density > 3:
        suggestions.append(f"Reduce keyword stuffing (currently {keyword_density:.1f}%)")
    if not title_has_keyword:
        suggestions.append("Add target keyword to the title")
    if not keyword_in_opening:
        suggestions.append(f"Mention '{keyword}' in the opening paragraph (first 300 characters)")
    if not meta_description:
        suggestions.append("Add a meta description (150-160 characters including the keyword)")
    elif len(meta_description) < 120:
        suggestions.append("Expand meta description to at least 120 characters")
    elif len(meta_description) > 160:
        suggestions.append("Shorten meta description to under 160 characters")
    if h2_count < 3:
        suggestions.append("Add more H2 headings (## Section) — aim for at least 3 modular sections")
    if word_count < 1500:
        suggestions.append(f"Expand content to 1500+ words (currently {word_count}) — articles 1500+ words average significantly more AI citations")
    if not has_faq:
        suggestions.append("Add a '## Frequently Asked Questions' section — the highest-citation format for Google AI Overviews and Perplexity")
    if external_links < 1:
        suggestions.append("Add at least one external link to an authoritative source (study, official docs, industry report)")
    if not has_lists:
        suggestions.append("Add bullet points or a numbered list — structured lists are among the most-cited formats by AI answer engines")
    if not has_quick_answer:
        suggestions.append("Add a Quick Answer block near the top: > **Quick Answer:** [40-70 word standalone answer]")

    # ----------------------------------------------------------------
    # Score (0-100) — updated weights for GEO/AEO 2025-2026
    # ----------------------------------------------------------------
    score = 0
    score += 15 if 1 <= keyword_density <= 3 else 0          # Keyword density
    score += 15 if title_has_keyword else 0                    # Keyword in title
    score += 10 if meta_description and 120 <= len(meta_description) <= 160 else 0  # Meta desc
    score += 15 if headings_structure == "good" else 0         # 3+ H2s
    score += 15 if has_faq else 0                              # FAQ section (AEO signal)
    score += 10 if external_links >= 1 else 0                  # External citation
    score += 10 if has_lists else 0                            # Structured lists
    score += 5 if has_quick_answer else 0                      # Quick Answer / TL;DR block
    score += 5 if image_alt_texts else 0                       # Image alt texts (when images exist)

    return {
        "score": min(100, score),
        "keyword_density": round(keyword_density, 2),
        "title_has_keyword": title_has_keyword,
        "keyword_in_opening": keyword_in_opening,
        "meta_description_length": len(meta_description) if meta_description else 0,
        "headings_structure": headings_structure,
        "h2_count": h2_count,
        "h3_count": h3_count,
        "internal_links": internal_links,
        "external_links": external_links,
        "has_faq": has_faq,
        "has_lists": has_lists,
        "has_quick_answer": has_quick_answer,
        "image_alt_texts": image_alt_texts,
        "readability_score": round(readability_score, 1),
        "word_count": word_count,
        "suggestions": suggestions,
    }


@router.post("", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    request: ArticleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new article manually.
    """
    article_id = str(uuid4())
    slug = slugify(request.title)

    # Check slug uniqueness
    existing = await db.execute(select(Article).where(Article.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{article_id[:8]}"

    word_count = len(request.content.split()) if request.content else 0
    content_html = markdown.markdown(request.content) if request.content else None

    project_id = getattr(current_user, 'current_project_id', None)

    article = Article(
        id=article_id,
        user_id=current_user.id,
        project_id=project_id,
        outline_id=request.outline_id,
        title=request.title,
        slug=slug,
        keyword=request.keyword,
        meta_description=request.meta_description,
        content=request.content,
        content_html=content_html,
        word_count=word_count,
        read_time=calculate_read_time(request.content) if request.content else None,
        status=ContentStatus.DRAFT.value,
    )

    # Run SEO analysis if content exists
    if request.content:
        seo_result = analyze_seo(
            request.content,
            request.keyword,
            request.title,
            request.meta_description or "",
        )
        article.seo_score = seo_result["score"]
        article.seo_analysis = seo_result

    db.add(article)
    await db.commit()
    await db.refresh(article)

    return article


async def _generate_article_background(
    article_id: str,
    user_id: str,
    project_id: Optional[str],
    outline_title: str,
    outline_keyword: str,
    outline_sections: list,
    outline_tone: str,
    outline_target_audience: Optional[str],
    writing_style: str,
    voice: str,
    list_usage: str,
    custom_instructions: Optional[str],
    word_count_target: int = 1500,
    language: str = "en",
):
    """Background task that generates article content and updates the DB."""
    # GEN-41: TODO — add per-user generation semaphore to limit concurrent AI calls per user
    # (currently a global semaphore of 5 is used — 100 users x 5 concurrent = 500 AI API calls)
    async with _generation_semaphore:
        await _run_article_generation(
            article_id=article_id,
            user_id=user_id,
            project_id=project_id,
            outline_title=outline_title,
            outline_keyword=outline_keyword,
            outline_sections=outline_sections,
            outline_tone=outline_tone,
            outline_target_audience=outline_target_audience,
            writing_style=writing_style,
            voice=voice,
            list_usage=list_usage,
            custom_instructions=custom_instructions,
            word_count_target=word_count_target,
            language=language,
        )


async def _run_article_generation(
    article_id: str,
    user_id: str,
    project_id: Optional[str],
    outline_title: str,
    outline_keyword: str,
    outline_sections: list,
    outline_tone: str,
    outline_target_audience: Optional[str],
    writing_style: str,
    voice: str,
    list_usage: str,
    custom_instructions: Optional[str],
    word_count_target: int = 1500,
    language: str = "en",
):
    """Inner implementation of background article generation (called under semaphore)."""
    start_time = time.time()
    gen_log = None
    tracker = None
    async with async_session_maker() as db:
        try:
            result = await db.execute(
                select(Article).where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()
            if not article:
                logger.error("Background generation: article %s not found", article_id)
                return

            # Log the generation start
            tracker = GenerationTracker(db)
            gen_log = await tracker.log_start(
                user_id=user_id,
                project_id=project_id,
                resource_type="article",
                resource_id=article_id,
                input_metadata={
                    "keyword": outline_keyword,
                    "word_count_target": word_count_target,
                    "language": language,
                },
            )
            await db.commit()  # Commit the log entry

            generated = await asyncio.wait_for(
                content_ai_service.generate_article(
                    title=outline_title,
                    keyword=outline_keyword,
                    sections=outline_sections,
                    tone=outline_tone,
                    target_audience=outline_target_audience,
                    writing_style=writing_style,
                    voice=voice,
                    list_usage=list_usage,
                    custom_instructions=custom_instructions,
                    word_count_target=word_count_target,
                    language=language,
                ),
                timeout=540.0,  # 9 min hard limit — non-English articles generate 7000+ tokens and can take 8+ min
            )

            # Grammar proofreading pass
            is_proofread = False
            try:
                proofread_content = await asyncio.wait_for(
                    content_ai_service.proofread_grammar(
                        content=generated.content,
                        language=language,
                    ),
                    timeout=PROOFREAD_TIMEOUT_SECONDS,
                )
                # Update generated content with proofread version
                generated = GeneratedArticle(
                    title=generated.title,
                    content=proofread_content,
                    meta_description=generated.meta_description,
                    word_count=len(proofread_content.split()),
                )
                is_proofread = True
                logger.info("Grammar proofread completed for article %s", article_id)
            except asyncio.TimeoutError:
                logger.warning(
                    "Grammar proofread timed out for article %s, using original content",
                    article_id,
                )
            except Exception as proof_err:
                logger.warning(
                    "Grammar proofread failed for article %s, using original: %s",
                    article_id, proof_err,
                )

            article.content = generated.content
            article.content_html = markdown.markdown(generated.content)
            article.meta_description = generated.meta_description
            article.word_count = generated.word_count
            article.read_time = calculate_read_time(generated.content)
            article.ai_model = settings.anthropic_model
            article.status = ContentStatus.COMPLETED.value

            # Run SEO analysis
            try:
                seo_result = analyze_seo(
                    generated.content,
                    outline_keyword,
                    outline_title,
                    generated.meta_description,
                )
                seo_result["is_proofread"] = is_proofread
                article.seo_score = seo_result["score"]
                article.seo_analysis = seo_result
            except Exception as seo_err:
                logger.warning("SEO analysis failed for article %s: %s", article_id, seo_err)
                article.seo_analysis = {"is_proofread": is_proofread}

            # Generate image prompt (with 30s timeout)
            try:
                image_prompt = await asyncio.wait_for(
                    content_ai_service.generate_image_prompt(
                        title=outline_title,
                        content=generated.content,
                        keyword=outline_keyword,
                    ),
                    timeout=30.0,
                )
                article.image_prompt = image_prompt
            except (asyncio.TimeoutError, Exception) as img_err:
                logger.warning(
                    "Failed to generate image prompt for article %s: %s",
                    article_id, img_err,
                )

            # Log successful generation and increment usage (single commit)
            duration_ms = int((time.time() - start_time) * 1000)
            if gen_log is not None:
                await tracker.log_success(
                    log_id=gen_log.id,
                    ai_model=settings.anthropic_model,
                    duration_ms=duration_ms,
                )
            await db.commit()
            logger.info("Article %s generated successfully", article_id)

        except Exception as e:
            logger.error("Background generation failed for article %s: %s", article_id, e, exc_info=True)
            try:
                await db.rollback()
            except Exception:
                pass
            # Use a fresh session to mark as failed (original session may be broken)
            try:
                async with async_session_maker() as err_db:
                    result = await err_db.execute(
                        select(Article).where(Article.id == article_id)
                    )
                    article = result.scalar_one_or_none()
                    if article:
                        article.status = ContentStatus.FAILED.value
                        article.generation_error = str(e)[:500]
                        await err_db.commit()
                        logger.info("Marked article %s as failed", article_id)
            except Exception:
                logger.error("Failed to mark article %s as failed", article_id, exc_info=True)

            # Log failure in a separate session (original session may be broken)
            if gen_log is not None:
                duration_ms = int((time.time() - start_time) * 1000)
                try:
                    async with async_session_maker() as tracker_db:
                        failure_tracker = GenerationTracker(tracker_db)
                        await failure_tracker.log_failure(
                            log_id=gen_log.id,
                            error_message=str(e),
                            duration_ms=duration_ms,
                        )
                        await tracker_db.commit()
                except Exception:
                    logger.error("Failed to log generation failure for article %s", article_id, exc_info=True)


@router.post("/generate", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def generate_article(
    request: Request,
    body: ArticleGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an article from an outline using AI.
    Returns immediately with status 'generating'; the frontend polls for completion.
    """
    # Get the outline — scoped to project or personal workspace
    project_id = getattr(current_user, 'current_project_id', None)
    if project_id:
        outline_query = select(Outline).where(
            Outline.id == body.outline_id,
            Outline.project_id == project_id,
        )
    else:
        outline_query = select(Outline).where(
            Outline.id == body.outline_id,
            Outline.user_id == current_user.id,
            Outline.project_id.is_(None),
        )
    result = await db.execute(outline_query)
    outline = result.scalar_one_or_none()

    if not outline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outline not found",
        )

    if outline.sections is None or not isinstance(outline.sections, list) or len(outline.sections) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Outline has no sections to generate from",
        )

    # Check usage limit
    tracker = GenerationTracker(db)
    if not await tracker.check_limit(project_id, "article", user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly article generation limit reached. Please upgrade your plan.",
        )

    # Create article in generating status
    article_id = str(uuid4())
    slug = slugify(outline.title)

    existing = await db.execute(select(Article).where(Article.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{article_id[:8]}"

    article = Article(
        id=article_id,
        user_id=current_user.id,
        project_id=project_id,
        outline_id=outline.id,
        title=outline.title,
        slug=slug,
        keyword=outline.keyword,
        status=ContentStatus.GENERATING.value,
    )

    db.add(article)
    await db.commit()
    await db.refresh(article)

    # PROJ-07: Load brand_voice from current project to apply as defaults.
    brand_voice: dict = {}
    if project_id:
        proj_result = await db.execute(
            select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
        )
        proj = proj_result.scalar_one_or_none()
        if proj and isinstance(proj.brand_voice, dict):
            brand_voice = proj.brand_voice

    # GEN-47: Validate generation style params against allowed enum values.
    # Brand voice values come from user-editable JSON — sanitize to defaults on invalid input.
    _VALID_WRITING_STYLES = {"editorial", "conversational", "formal", "technical", "simplified", "balanced"}
    _VALID_VOICES = {"first_person", "second_person", "third_person"}
    _VALID_LIST_USAGES = {"heavy", "light", "balanced"}

    resolved_writing_style = body.writing_style or brand_voice.get("writing_style") or "balanced"
    if resolved_writing_style not in _VALID_WRITING_STYLES:
        resolved_writing_style = "balanced"

    resolved_voice = body.voice or brand_voice.get("voice") or "second_person"
    if resolved_voice not in _VALID_VOICES:
        resolved_voice = "second_person"

    resolved_list_usage = body.list_usage or brand_voice.get("list_usage") or "balanced"
    if resolved_list_usage not in _VALID_LIST_USAGES:
        resolved_list_usage = "balanced"

    # Kick off generation as an asyncio task on the event loop
    # (more reliable than BackgroundTasks for long-running async work)
    task = asyncio.create_task(
        _generate_article_background(
            article_id=article_id,
            user_id=current_user.id,
            project_id=project_id,
            outline_title=outline.title,
            outline_keyword=outline.keyword,
            outline_sections=outline.sections,
            outline_tone=body.tone or outline.tone,
            outline_target_audience=body.target_audience or outline.target_audience,
            writing_style=resolved_writing_style,
            voice=resolved_voice,
            list_usage=resolved_list_usage,
            custom_instructions=body.custom_instructions or brand_voice.get("custom_instructions"),
            word_count_target=outline.word_count_target or 1500,
            language=body.language or brand_voice.get("language") or current_user.language or "en",
        )
    )
    _active_generation_tasks[article_id] = task
    task.add_done_callback(lambda t: _active_generation_tasks.pop(article_id, None))

    return article


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List user's articles with pagination and filtering.
    """
    if current_user.current_project_id:
        query = select(Article).options(
            defer(Article.content), defer(Article.content_html)
        ).where(
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        query = select(Article).options(
            defer(Article.content), defer(Article.content_html)
        ).where(
            Article.user_id == current_user.id,
            Article.project_id.is_(None),
            Article.deleted_at.is_(None),
        )

    if status:
        status = status.lower()
        VALID_STATUSES = {s.value for s in ContentStatus}
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}")
        query = query.where(Article.status == status)
    if keyword:
        query = query.where(Article.keyword.ilike(f"%{escape_like(keyword)}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Article.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    articles = result.scalars().all()

    return ArticleListResponse(
        items=articles,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/health-summary")
async def get_content_health(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get content health summary for the current user/project.

    ART-02: Uses SQL aggregates instead of loading all articles into memory.
    """
    # Build base filter conditions
    status_filter = Article.status.in_([ContentStatus.COMPLETED.value, ContentStatus.PUBLISHED.value])
    if current_user.current_project_id:
        base_filter = and_(
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
            status_filter,
        )
    else:
        base_filter = and_(
            Article.user_id == current_user.id,
            Article.project_id.is_(None),
            Article.deleted_at.is_(None),
            status_filter,
        )

    # Single aggregate query — no full article load
    agg_result = await db.execute(
        select(
            func.count().label("total"),
            func.avg(Article.seo_score).label("avg_score"),
            func.count(case((Article.seo_score >= 80, 1))).label("excellent_count"),
            func.count(case((and_(Article.seo_score >= 60, Article.seo_score < 80), 1))).label("good_count"),
            func.count(case((and_(Article.seo_score.is_not(None), Article.seo_score < 60), 1))).label("needs_work_count"),
            func.count(case((Article.seo_score.is_(None), 1))).label("no_score_count"),
        ).where(base_filter)
    )
    agg = agg_result.one()

    # Top 10 worst articles (needs_work) — targeted query, not full load
    needs_work_rows = await db.execute(
        select(Article.id, Article.title, Article.seo_score, Article.keyword)
        .where(base_filter, Article.seo_score.is_not(None), Article.seo_score < 60)
        .order_by(Article.seo_score.asc())
        .limit(10)
    )
    needs_work = [
        {"id": str(r.id), "title": r.title, "seo_score": r.seo_score, "keyword": r.keyword}
        for r in needs_work_rows
    ]

    # Top 10 articles without a score
    no_score_rows = await db.execute(
        select(Article.id, Article.title, Article.keyword)
        .where(base_filter, Article.seo_score.is_(None))
        .limit(10)
    )
    no_score = [
        {"id": str(r.id), "title": r.title, "keyword": r.keyword}
        for r in no_score_rows
    ]

    avg_score = float(agg.avg_score) if agg.avg_score is not None else None
    return {
        "total_articles": agg.total,
        "avg_seo_score": round(avg_score, 1) if avg_score is not None else None,
        "excellent_count": agg.excellent_count,
        "good_count": agg.good_count,
        "needs_work_count": agg.needs_work_count,
        "no_score_count": agg.no_score_count,
        "needs_work": needs_work,
        "no_score": no_score,
    }


class KeywordSuggestionRequest(BaseModel):
    seed_keyword: str = Field(..., min_length=1, max_length=200)
    count: int = Field(10, ge=5, le=20)


KEYWORD_CACHE_TTL_DAYS = 30
REDIS_KW_TTL = 60 * 60 * 24 * 30  # 30 days in seconds


@router.post("/keyword-suggestions")
@limiter.limit("5/minute")
async def get_keyword_suggestions(
    request: Request,
    body: KeywordSuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-powered keyword suggestions based on a seed keyword."""
    normalized = body.seed_keyword.strip().lower()
    redis_key = f"kw_research:{current_user.id}:{normalized}"

    # 1. Redis fast-path
    redis_client = None
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        cached_raw = await redis_client.get(redis_key)
        if cached_raw:
            result = json.loads(cached_raw)
            result["cached"] = True
            return result
    except Exception as redis_err:
        logger.warning("Redis keyword cache read failed: %s", redis_err)
    finally:
        if redis_client:
            await redis_client.aclose()

    # 2. DB fallback
    now = datetime.now(timezone.utc)
    db_result = await db.execute(
        select(KeywordResearchCache)
        .where(KeywordResearchCache.user_id == current_user.id)
        .where(KeywordResearchCache.seed_keyword_normalized == normalized)
        .where(KeywordResearchCache.expires_at > now)
        .order_by(KeywordResearchCache.created_at.desc())
        .limit(1)
    )
    cached_row = db_result.scalar_one_or_none()
    if cached_row:
        result = json.loads(cached_row.result_json)
        result["cached"] = True
        # Backfill Redis
        redis_client = None
        try:
            redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
            ttl = int((cached_row.expires_at - now).total_seconds())
            if ttl > 0:
                await redis_client.setex(redis_key, ttl, cached_row.result_json)
        except Exception:
            pass
        finally:
            if redis_client:
                await redis_client.aclose()
        return result

    # 3. Check monthly keyword research limit (only real AI calls count; cache hits above are free)
    from core.plans import PLANS as _PLANS
    _now = datetime.now(timezone.utc)
    _tier = current_user.subscription_tier or "free"
    if current_user.subscription_expires and current_user.subscription_expires < _now:
        _tier = "free"
    _monthly_limit = _PLANS.get(_tier, _PLANS["free"])["limits"].get("keyword_researches_per_month", 3)
    _count_key = f"kw_count:{current_user.id}:{_now.year}:{_now.month}"
    redis_client = None
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        _current_count = int(await redis_client.get(_count_key) or 0)
        if _current_count >= _monthly_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly keyword research limit reached ({_monthly_limit}/month). Upgrade your plan for more.",
            )
    except HTTPException:
        raise
    except Exception as _limit_err:
        logger.warning("Keyword research limit check failed (fail open): %s", _limit_err)
    finally:
        if redis_client:
            await redis_client.aclose()

    # 4. Call AI (existing logic)
    prompt = f"""Given the seed keyword "{body.seed_keyword}", suggest {body.count} related keywords for SEO content creation.

For each keyword, provide:
1. The keyword phrase
2. Estimated search intent (informational, commercial, transactional, navigational)
3. Estimated difficulty (low, medium, high)
4. A brief content angle suggestion (1 sentence)

Return as a JSON array with objects having: keyword, intent, difficulty, content_angle

Only return the JSON array, no other text."""

    try:
        from adapters.ai.anthropic_adapter import content_ai_service

        client = content_ai_service._client
        if not client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service not configured",
            )

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        if not response.content:
            raise HTTPException(status_code=502, detail="AI returned empty response — please try again")
        text = response.content[0].text
        # Extract JSON from response (handle markdown code blocks)
        parts = text.split("```")
        if len(parts) >= 3:
            # Standard ```json...``` block — extract the middle part
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
        elif len(parts) == 2:
            # Single opening ``` with no closing — take the rest
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]

        try:
            suggestions = json.loads(text.strip())
        except (json.JSONDecodeError, ValueError):
            logger.warning("AI returned invalid JSON for keyword suggestions: %s", text[:200])
            raise HTTPException(status_code=502, detail="AI returned invalid response — please try again")

        result = {"seed_keyword": body.seed_keyword, "suggestions": suggestions}
        result_str = json.dumps(result)
        expires_at = now + timedelta(days=KEYWORD_CACHE_TTL_DAYS)

        # Increment monthly usage counter (TTL = 35 days, safely covers any month)
        redis_client = None
        try:
            redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
            _count_key = f"kw_count:{current_user.id}:{now.year}:{now.month}"
            await redis_client.incr(_count_key)
            await redis_client.expire(_count_key, 35 * 86400)
        except Exception as _inc_err:
            logger.warning("Failed to increment keyword research counter: %s", _inc_err)
        finally:
            if redis_client:
                await redis_client.aclose()

        # Store in DB
        try:
            # Remove expired entries for this user+keyword first
            await db.execute(
                delete(KeywordResearchCache)
                .where(KeywordResearchCache.user_id == current_user.id)
                .where(KeywordResearchCache.seed_keyword_normalized == normalized)
            )
            cache_entry = KeywordResearchCache(
                user_id=current_user.id,
                seed_keyword_normalized=normalized,
                seed_keyword_original=body.seed_keyword.strip(),
                result_json=result_str,
                expires_at=expires_at,
            )
            db.add(cache_entry)
            await db.commit()
        except Exception as db_err:
            logger.warning("Failed to store keyword research in DB cache: %s", db_err)
            await db.rollback()

        # Store in Redis
        redis_client = None
        try:
            redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
            await redis_client.setex(redis_key, REDIS_KW_TTL, result_str)
        except Exception as redis_err:
            logger.warning("Failed to store keyword research in Redis: %s", redis_err)
        finally:
            if redis_client:
                await redis_client.aclose()

        result["cached"] = False
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Keyword suggestion failed: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate keyword suggestions")


@router.get("/keyword-history")
async def get_keyword_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
):
    """Return the user's recent keyword research history (non-expired entries only)."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(KeywordResearchCache)
        .where(KeywordResearchCache.user_id == current_user.id)
        .where(KeywordResearchCache.expires_at > now)
        .order_by(KeywordResearchCache.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return {
        "history": [
            {
                "seed_keyword": row.seed_keyword_original,
                "searched_at": row.created_at.isoformat(),
                "expires_at": row.expires_at.isoformat(),
                "result": json.loads(row.result_json),
            }
            for row in rows
        ]
    }


@router.get("/export")
@limiter.limit("10/hour")  # ART-01: bulk export is expensive; hard cap per hour
async def export_all_articles(
    request: Request,
    format: str = Query("csv", pattern="^(csv)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export all articles for the current project as CSV.
    """
    if current_user.current_project_id:
        query = select(Article).where(
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        query = select(Article).where(
            Article.user_id == current_user.id,
            Article.project_id.is_(None),
            Article.deleted_at.is_(None),
        )
    query = query.order_by(Article.created_at.desc()).limit(5000)  # ART-01: cap at 5000 rows
    result = await db.execute(query)
    articles = result.scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "title", "status", "keyword", "word_count", "created_at", "updated_at"])
    for a in articles:
        writer.writerow([
            a.id,
            a.title,
            a.status,
            a.keyword,
            a.word_count or 0,
            a.created_at.isoformat() if a.created_at else "",
            a.updated_at.isoformat() if a.updated_at else "",
        ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=articles.csv"},
    )


@router.get("/{article_id}/export")
async def export_article(
    article_id: str,
    format: str = Query("markdown", pattern="^(markdown|html|csv)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export a single article in the requested format (markdown, html, or csv).
    """
    if current_user.current_project_id:
        query = select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        query = select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
            Article.deleted_at.is_(None),
        )
    result = await db.execute(query)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    safe_title = re.sub(r"[^\w\-]", "_", article.title or "article")[:80]

    if format == "markdown":
        content = article.content or ""
        return StreamingResponse(
            iter([content]),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.md"'},
        )

    if format == "html":
        content = article.content_html or ""
        return StreamingResponse(
            iter([content]),
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.html"'},
        )

    # csv
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "title", "status", "keyword", "word_count", "created_at", "updated_at"])
    writer.writerow([
        article.id,
        article.title,
        article.status,
        article.keyword,
        article.word_count or 0,
        article.created_at.isoformat() if article.created_at else "",
        article.updated_at.isoformat() if article.updated_at else "",
    ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.csv"'},
    )


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_articles(
    body: BulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete multiple articles in a single request.

    All supplied IDs must belong to the current user's active project scope.
    Only articles that pass the ownership check are deleted; IDs that do not
    exist or belong to a different project are silently ignored.
    Returns the number of rows actually deleted.
    """
    if not body.ids:
        return BulkDeleteResponse(deleted=0)

    if current_user.current_project_id:
        stmt = (
            delete(Article)
            .where(
                Article.id.in_(body.ids),
                Article.project_id == current_user.current_project_id,
            )
        )
    else:
        stmt = (
            delete(Article)
            .where(
                Article.id.in_(body.ids),
                Article.user_id == current_user.id,
                Article.project_id.is_(None),
            )
        )

    result = await db.execute(stmt)
    await db.commit()

    return BulkDeleteResponse(deleted=result.rowcount)


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific article by ID.
    """
    if current_user.current_project_id:
        query = select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        query = select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
            Article.deleted_at.is_(None),
        )
    result = await db.execute(query)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    return article


@router.put("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: str,
    request: ArticleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an article.
    """
    if current_user.current_project_id:
        query = select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        query = select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
            Article.deleted_at.is_(None),
        )
    result = await db.execute(query)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    ALLOWED_UPDATE_FIELDS = {"title", "keyword", "meta_description", "content", "status"}
    update_data = request.model_dump(exclude_unset=True)

    # Save a revision before overwriting content (only when content actually changes)
    if "content" in update_data and update_data["content"] != article.content:
        await _save_revision(db, article, "manual_edit", current_user.id)

    for field, value in update_data.items():
        if field not in ALLOWED_UPDATE_FIELDS:
            continue
        # GEN-09: validate status transitions — users may only move between DRAFT and COMPLETED.
        # GENERATING, FAILED, and PUBLISHED are system-managed states.
        if field == "status" and value is not None:
            _user_settable = {ContentStatus.DRAFT.value, ContentStatus.COMPLETED.value}
            if value not in _user_settable:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid status '{value}'. Users may only set 'draft' or 'completed'.",
                )
        setattr(article, field, value)

    # Update derived fields
    if "content" in update_data and article.content:
        article.content_html = markdown.markdown(article.content)
        article.word_count = len(article.content.split())
        article.read_time = calculate_read_time(article.content)

        # Re-run SEO analysis
        seo_result = analyze_seo(
            article.content,
            article.keyword,
            article.title,
            article.meta_description or "",
        )
        article.seo_score = seo_result["score"]
        article.seo_analysis = seo_result

    if "title" in update_data:
        new_slug = slugify(article.title)
        existing = await db.execute(
            select(Article).where(
                Article.slug == new_slug,
                Article.id != article_id,
            )
        )
        if existing.scalar_one_or_none():
            new_slug = f"{new_slug}-{article_id[:8]}"
        article.slug = new_slug

    await db.commit()
    await db.refresh(article)

    return article


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")  # ART-03: rate-limit hard-delete to prevent mass deletion
async def delete_article(
    request: Request,
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an article.
    """
    if current_user.current_project_id:
        query = select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        query = select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
            Article.deleted_at.is_(None),
        )
    result = await db.execute(query)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    await db.delete(article)
    await db.commit()


@router.post("/{article_id}/improve", response_model=ArticleResponse)
@limiter.limit("10/minute")
async def improve_article(
    request: Request,
    article_id: str,
    body: ArticleImproveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Improve article content using AI.
    """
    if current_user.current_project_id:
        query = select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        query = select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
            Article.deleted_at.is_(None),
        )
    result = await db.execute(query)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    if not article.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Article has no content to improve",
        )

    # Each article may be improved at most ARTICLE_IMPROVE_LIMIT times (all tiers).
    # This is a per-article cap, not a monthly quota — it does not consume generation credits.
    if (article.improve_count or 0) >= ARTICLE_IMPROVE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"This article has already used all {ARTICLE_IMPROVE_LIMIT} AI improvement passes.",
        )

    # Save current content as a revision so the user can revert after AI changes it
    revision_type = f"before_ai_improve_{body.improvement_type}"
    await _save_revision(db, article, revision_type, current_user.id)

    try:
        # GEN-10: add timeout to prevent hanging on slow AI responses
        improved_content = await asyncio.wait_for(
            content_ai_service.improve_content(
                content=article.content,
                improvement_type=body.improvement_type,
                keyword=article.keyword,
            ),
            timeout=120.0,
        )

        article.content = improved_content
        article.content_html = markdown.markdown(improved_content)
        article.word_count = len(improved_content.split())
        article.read_time = calculate_read_time(improved_content)
        article.improve_count = (article.improve_count or 0) + 1

        # Re-run SEO analysis
        try:
            seo_result = analyze_seo(
                improved_content,
                article.keyword,
                article.title,
                article.meta_description or "",
            )
            article.seo_score = seo_result["score"]
            article.seo_analysis = seo_result
        except Exception as seo_err:
            logger.warning("SEO re-analysis failed for article %s: %s", article_id, seo_err)

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Article improvement timed out. Please try again.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to improve article: {str(e)}",
        )

    await db.commit()
    await db.refresh(article)

    return article


@router.post("/{article_id}/analyze-seo", response_model=ArticleResponse)
@limiter.limit("10/minute")
async def analyze_article_seo(
    request: Request,
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-run SEO analysis on an article.
    """
    if current_user.current_project_id:
        query = select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        query = select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
            Article.deleted_at.is_(None),
        )
    result = await db.execute(query)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    if not article.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Article has no content to analyze",
        )

    seo_result = analyze_seo(
        article.content,
        article.keyword,
        article.title,
        article.meta_description or "",
    )
    article.seo_score = seo_result["score"]
    article.seo_analysis = seo_result

    await db.commit()
    await db.refresh(article)

    return article


@router.post("/{article_id}/generate-image-prompt", response_model=ArticleResponse)
@limiter.limit("10/minute")
async def generate_article_image_prompt(
    request: Request,
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an image prompt for an existing article that doesn't have one yet.
    """
    if current_user.current_project_id:
        query = select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        query = select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
            Article.deleted_at.is_(None),
        )
    result = await db.execute(query)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    if not article.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Article has no content to generate an image prompt from",
        )

    try:
        image_prompt = await content_ai_service.generate_image_prompt(
            title=article.title,
            content=article.content,
            keyword=article.keyword,
        )
        article.image_prompt = image_prompt
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate image prompt: {str(e)}",
        )

    await db.commit()
    await db.refresh(article)

    return article


@router.get("/{article_id}/social-posts", response_model=SocialPostsResponse)
async def get_social_posts(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get social media posts for an article."""
    if current_user.current_project_id:
        query = select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        query = select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
            Article.deleted_at.is_(None),
        )
    result = await db.execute(query)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    social = article.social_posts or {}
    return SocialPostsResponse(
        twitter=social.get("twitter"),
        linkedin=social.get("linkedin"),
        facebook=social.get("facebook"),
        instagram=social.get("instagram"),
    )


@router.post("/{article_id}/generate-social-posts", response_model=SocialPostsResponse)
@limiter.limit("10/minute")
async def generate_social_posts(
    request: Request,
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI social media posts for an article."""
    if current_user.current_project_id:
        query = select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        query = select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
            Article.deleted_at.is_(None),
        )
    result = await db.execute(query)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    article_url = article.published_url or (
        f"https://wordpress.example.com/?p={article.wordpress_post_id}"
        if article.wordpress_post_id
        else None
    )

    if not article_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Article must be published to WordPress first to generate social posts",
        )

    # Check monthly social post quota
    tracker = GenerationTracker(db)
    if not await tracker.check_limit(
        project_id=current_user.current_project_id,
        resource_type="social_post",
        user_id=current_user.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly social post generation limit reached. Upgrade your plan to continue.",
        )

    log = await tracker.log_start(
        user_id=current_user.id,
        project_id=current_user.current_project_id,
        resource_type="social_post",
        resource_id=article_id,
    )

    summary = article.meta_description or (article.content[:300] if article.content else article.title)

    try:
        posts = await content_ai_service.generate_social_posts(
            article_title=article.title,
            article_summary=summary,
            article_url=article_url,
            keywords=[article.keyword],
        )
    except Exception as e:
        await tracker.log_failure(log_id=log.id, error_message=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate social posts: {str(e)}",
        )

    await tracker.log_success(log_id=log.id, ai_model=settings.anthropic_model)

    now = datetime.now(timezone.utc).isoformat()
    social_posts = {
        platform: {"text": text, "generated_at": now}
        for platform, text in posts.items()
    }

    article.social_posts = social_posts
    await db.commit()
    await db.refresh(article)

    return SocialPostsResponse(
        twitter=social_posts.get("twitter"),
        linkedin=social_posts.get("linkedin"),
        facebook=social_posts.get("facebook"),
        instagram=social_posts.get("instagram"),
    )


@router.put("/{article_id}/social-posts", response_model=SocialPostsResponse)
async def update_social_post(
    article_id: str,
    request: SocialPostUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a single platform's social post text."""
    if current_user.current_project_id:
        query = select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        query = select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
            Article.deleted_at.is_(None),
        )
    result = await db.execute(query)
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    social_posts = dict(article.social_posts or {})
    social_posts[request.platform] = {
        "text": request.text,
        "generated_at": (social_posts.get(request.platform, {}) or {}).get("generated_at"),
    }

    article.social_posts = social_posts
    await db.commit()
    await db.refresh(article)

    return SocialPostsResponse(
        twitter=social_posts.get("twitter"),
        linkedin=social_posts.get("linkedin"),
        facebook=social_posts.get("facebook"),
        instagram=social_posts.get("instagram"),
    )


# ============================================================================
# Revision endpoints
# ============================================================================


def _article_ownership_query(article_id: str, current_user: User):
    """Return a select() that fetches the article respecting project context."""
    if current_user.current_project_id:
        return select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    return select(Article).where(
        Article.id == article_id,
        Article.user_id == current_user.id,
        Article.deleted_at.is_(None),
    )


@router.get("/{article_id}/revisions", response_model=ArticleRevisionListResponse)
async def list_article_revisions(
    article_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List revision history for an article (newest first).
    Returns lightweight items — no full content — for fast list rendering.
    """
    # Verify the caller owns / has access to the article
    article_result = await db.execute(
        _article_ownership_query(article_id, current_user)
    )
    if not article_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    count_result = await db.execute(
        select(func.count()).where(ArticleRevision.article_id == article_id)
    )
    total = count_result.scalar() or 0

    revisions_result = await db.execute(
        select(ArticleRevision)
        .where(ArticleRevision.article_id == article_id)
        .order_by(ArticleRevision.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    revisions = revisions_result.scalars().all()

    return ArticleRevisionListResponse(items=list(revisions), total=total)


@router.get(
    "/{article_id}/revisions/{revision_id}",
    response_model=ArticleRevisionDetailResponse,
)
async def get_article_revision(
    article_id: str,
    revision_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific revision with full content for preview.
    """
    article_result = await db.execute(
        _article_ownership_query(article_id, current_user)
    )
    if not article_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    revision_result = await db.execute(
        select(ArticleRevision).where(
            ArticleRevision.id == revision_id,
            ArticleRevision.article_id == article_id,
        )
    )
    revision = revision_result.scalar_one_or_none()
    if not revision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")

    return revision


@router.post(
    "/{article_id}/revisions/{revision_id}/restore",
    response_model=ArticleResponse,
)
async def restore_article_revision(
    article_id: str,
    revision_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Restore an article to a previous revision.

    Before overwriting the article, a "restore" backup revision is saved
    with the article's current content so the user can undo the restore.
    """
    article_result = await db.execute(
        _article_ownership_query(article_id, current_user)
    )
    article = article_result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    revision_result = await db.execute(
        select(ArticleRevision).where(
            ArticleRevision.id == revision_id,
            ArticleRevision.article_id == article_id,
        )
    )
    revision = revision_result.scalar_one_or_none()
    if not revision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")
    if revision.article_id != article_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")

    # Backup the current state before overwriting
    await _save_revision(db, article, "restore", current_user.id)

    # Apply the revision content back to the article
    article.content = revision.content
    article.content_html = revision.content_html
    article.title = revision.title
    article.meta_description = revision.meta_description
    article.word_count = revision.word_count

    # Recompute read time and SEO if content is present
    if article.content:
        article.read_time = calculate_read_time(article.content)
        seo_result = analyze_seo(
            article.content,
            article.keyword,
            article.title,
            article.meta_description or "",
        )
        article.seo_score = seo_result["score"]
        article.seo_analysis = seo_result

    await db.commit()
    await db.refresh(article)

    return article


# ============================================================================
# Internal linking suggestions
# ============================================================================


@router.get("/{article_id}/link-suggestions")
async def get_link_suggestions(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get internal linking suggestions for an article.

    Returns other completed/published articles in the same project scope
    that share keywords or title words with the source article, scored by
    relevance.  No AI is required — this is a pure keyword-matching pass.
    """
    # Fetch the source article (project-scoped)
    result = await db.execute(
        _article_ownership_query(article_id, current_user)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    keyword = (article.keyword or "").lower().strip()
    title_words = [w.lower() for w in (article.title or "").split() if len(w) > 3]

    # Build candidate query — only completed/published articles, exclude self
    candidate_query = (
        select(Article)
        .options(defer(Article.content), defer(Article.content_html))
        .where(
            Article.id != article_id,
            Article.status.in_([ContentStatus.COMPLETED.value, ContentStatus.PUBLISHED.value]),
        )
    )

    # Project scoping: mirror the same logic used in list_articles / get_article
    if current_user.current_project_id:
        candidate_query = candidate_query.where(
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        candidate_query = candidate_query.where(
            Article.user_id == current_user.id,
            Article.project_id.is_(None),
            Article.deleted_at.is_(None),
        )

    candidate_result = await db.execute(candidate_query.limit(50))
    candidates = candidate_result.scalars().all()

    # Score each candidate by relevance
    suggestions = []
    for candidate in candidates:
        score = 0
        candidate_keyword = (candidate.keyword or "").lower().strip()
        candidate_title = (candidate.title or "").lower()

        if keyword:
            # Exact keyword match
            if candidate_keyword == keyword:
                score += 10
            # Source keyword appears in candidate title
            elif keyword in candidate_title:
                score += 5
            # Candidate keyword appears in source title
            elif candidate_keyword and candidate_keyword in (article.title or "").lower():
                score += 5

        # Shared significant title words
        for word in title_words:
            if word in candidate_title:
                score += 1

        if score > 0:
            suggestions.append(
                {
                    "id": candidate.id,
                    "title": candidate.title,
                    "keyword": candidate.keyword,
                    "slug": candidate.slug,
                    "relevance_score": score,
                }
            )

    # Tag A-Stats suggestions with source
    for s in suggestions:
        s["source"] = "platform"
        s["url"] = None

    # Fetch WordPress posts if project has WP connected (graceful degradation)
    if current_user.current_project_id:
        proj_result = await db.execute(
            select(Project).where(Project.id == current_user.current_project_id)
        )
        project = proj_result.scalar_one_or_none()
        if project and project.wordpress_credentials:
            try:
                from adapters.cms.wordpress_adapter import WordPressAdapter
                from core.security.encryption import decrypt_credential

                creds = project.wordpress_credentials
                site_url = creds.get("site_url", "")
                username = creds.get("username", "")
                app_password = decrypt_credential(
                    creds.get("app_password_encrypted", ""), settings.secret_key
                )

                if site_url and username and app_password:
                    async with WordPressAdapter(
                        site_url=site_url,
                        username=username,
                        app_password=app_password,
                        timeout=5,
                    ) as wp:
                        wp_posts = await wp.list_posts(per_page=50)

                    for post in wp_posts:
                        wp_title = (post.get("title") or {}).get("rendered") or ""
                        wp_link = post.get("link") or ""
                        wp_slug = post.get("slug") or ""
                        if not wp_title or not wp_link:
                            continue

                        score = 0
                        post_title_lower = wp_title.lower()
                        if keyword and keyword in post_title_lower:
                            score += 5
                        for word in title_words:
                            if word in post_title_lower:
                                score += 1

                        if score > 0:
                            suggestions.append(
                                {
                                    "id": f"wp-{post.get('id')}",
                                    "title": wp_title,
                                    "keyword": None,
                                    "slug": wp_slug,
                                    "url": wp_link,
                                    "source": "wordpress",
                                    "relevance_score": score,
                                }
                            )
            except Exception as e:
                logger.warning("Failed to fetch WordPress posts for link suggestions: %s", e)

    # Sort by relevance descending, return top 10
    suggestions.sort(key=lambda x: x["relevance_score"], reverse=True)
    return {"suggestions": suggestions[:10]}


# ============================================================================
# AEO (Answer Engine Optimization) Endpoints
# ============================================================================


@router.get("/{article_id}/aeo-score")
async def get_aeo_score(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get or calculate AEO score for an article."""
    from services.aeo_scoring import score_and_save
    from infrastructure.database.models.aeo import AEOScore as AEOScoreModel

    # Verify article belongs to current user
    if current_user.current_project_id:
        ownership_query = select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        ownership_query = select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
            Article.deleted_at.is_(None),
        )
    ownership_result = await db.execute(ownership_query)
    if not ownership_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    # Check for existing recent score
    existing_result = await db.execute(
        select(AEOScoreModel)
        .where(AEOScoreModel.article_id == article_id)
        .order_by(AEOScoreModel.scored_at.desc())
        .limit(1)
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        return {
            "id": existing.id,
            "article_id": existing.article_id,
            "aeo_score": existing.aeo_score,
            "score_breakdown": existing.score_breakdown,
            "suggestions": existing.suggestions,
            "previous_score": existing.previous_score,
            "scored_at": existing.scored_at.isoformat(),
        }

    # No existing score — calculate one
    score = await score_and_save(db, article_id, current_user.id)
    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    return {
        "id": score.id,
        "article_id": score.article_id,
        "aeo_score": score.aeo_score,
        "score_breakdown": score.score_breakdown,
        "suggestions": score.suggestions,
        "previous_score": score.previous_score,
        "scored_at": score.scored_at.isoformat(),
    }


@router.post("/{article_id}/aeo-score")
async def refresh_aeo_score(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recalculate AEO score for an article."""
    from services.aeo_scoring import score_and_save

    # ANA-02: Verify article ownership before allowing re-scoring
    if current_user.current_project_id:
        ownership_query = select(Article).where(
            Article.id == article_id,
            Article.project_id == current_user.current_project_id,
            Article.deleted_at.is_(None),
        )
    else:
        ownership_query = select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
            Article.deleted_at.is_(None),
        )
    if not (await db.execute(ownership_query)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    score = await score_and_save(db, article_id, current_user.id)
    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    return {
        "id": score.id,
        "article_id": score.article_id,
        "aeo_score": score.aeo_score,
        "score_breakdown": score.score_breakdown,
        "suggestions": score.suggestions,
        "previous_score": score.previous_score,
        "scored_at": score.scored_at.isoformat(),
    }


@router.post("/{article_id}/aeo-optimize")
@limiter.limit("10/minute")
async def aeo_optimize(
    request: Request,
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI-powered AEO improvement suggestions for an article."""
    from services.aeo_scoring import generate_aeo_suggestions

    result = await generate_aeo_suggestions(db, article_id, current_user.id)
    return result
