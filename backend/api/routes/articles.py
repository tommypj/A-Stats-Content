"""
Article API routes.
"""

import math
import re
import markdown
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.content import (
    ArticleCreateRequest,
    ArticleGenerateRequest,
    ArticleUpdateRequest,
    ArticleResponse,
    ArticleListResponse,
    ArticleImproveRequest,
)
from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db
from infrastructure.database.models import Article, Outline, User, ContentStatus
from adapters.ai.anthropic_adapter import content_ai_service
from infrastructure.config.settings import settings

router = APIRouter(prefix="/articles", tags=["articles"])


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
    Analyze content for SEO metrics.
    """
    content_lower = content.lower()
    keyword_lower = keyword.lower()
    words = content.split()
    word_count = len(words)

    # Keyword density
    keyword_count = content_lower.count(keyword_lower)
    keyword_density = (keyword_count / word_count * 100) if word_count > 0 else 0

    # Check headings
    h2_count = len(re.findall(r"^##\s", content, re.MULTILINE))
    h3_count = len(re.findall(r"^###\s", content, re.MULTILINE))
    headings_structure = "good" if h2_count >= 3 and h3_count >= 2 else "needs_improvement"

    # Links
    internal_links = len(re.findall(r"\[.*?\]\(/", content))
    external_links = len(re.findall(r"\[.*?\]\(https?://", content))

    # Image alt texts
    images = re.findall(r"!\[(.*?)\]\(", content)
    image_alt_texts = all(alt.strip() for alt in images) if images else True

    # Basic readability (average sentence length)
    sentences = re.split(r"[.!?]+", content)
    avg_sentence_length = word_count / len(sentences) if sentences else 0
    readability_score = min(100, max(0, 100 - (avg_sentence_length - 15) * 2))

    # Generate suggestions
    suggestions = []
    if keyword_density < 1:
        suggestions.append(f"Increase keyword '{keyword}' usage (currently {keyword_density:.1f}%)")
    elif keyword_density > 3:
        suggestions.append(f"Reduce keyword stuffing (currently {keyword_density:.1f}%)")

    if keyword_lower not in title.lower():
        suggestions.append("Add target keyword to the title")

    if not meta_description:
        suggestions.append("Add a meta description")
    elif len(meta_description) < 120:
        suggestions.append("Make meta description longer (aim for 150-160 characters)")
    elif len(meta_description) > 160:
        suggestions.append("Shorten meta description to under 160 characters")

    if h2_count < 3:
        suggestions.append("Add more H2 headings for better structure")

    if internal_links < 2:
        suggestions.append("Add more internal links")

    if external_links < 1:
        suggestions.append("Consider adding external links to authoritative sources")

    # Calculate overall score
    score = 50
    score += 10 if 1 <= keyword_density <= 3 else 0
    score += 10 if keyword_lower in title.lower() else 0
    score += 10 if meta_description and 120 <= len(meta_description) <= 160 else 0
    score += 10 if headings_structure == "good" else 0
    score += 5 if internal_links >= 2 else 0
    score += 5 if external_links >= 1 else 0

    return {
        "score": min(100, score),
        "keyword_density": round(keyword_density, 2),
        "title_has_keyword": keyword_lower in title.lower(),
        "meta_description_length": len(meta_description) if meta_description else 0,
        "headings_structure": headings_structure,
        "h2_count": h2_count,
        "h3_count": h3_count,
        "internal_links": internal_links,
        "external_links": external_links,
        "image_alt_texts": image_alt_texts,
        "readability_score": round(readability_score, 1),
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

    article = Article(
        id=article_id,
        user_id=current_user.id,
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


@router.post("/generate", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def generate_article(
    request: ArticleGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an article from an outline using AI.
    """
    # Get the outline
    result = await db.execute(
        select(Outline).where(
            Outline.id == request.outline_id,
            Outline.user_id == current_user.id,
        )
    )
    outline = result.scalar_one_or_none()

    if not outline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outline not found",
        )

    if not outline.sections:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Outline has no sections. Generate outline first.",
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
        outline_id=outline.id,
        title=outline.title,
        slug=slug,
        keyword=outline.keyword,
        status=ContentStatus.GENERATING.value,
    )

    db.add(article)
    await db.commit()

    # Generate article content
    try:
        generated = await content_ai_service.generate_article(
            title=outline.title,
            keyword=outline.keyword,
            sections=outline.sections,
            tone=request.tone or outline.tone,
            target_audience=request.target_audience or outline.target_audience,
        )

        article.content = generated.content
        article.content_html = markdown.markdown(generated.content)
        article.meta_description = generated.meta_description
        article.word_count = generated.word_count
        article.read_time = calculate_read_time(generated.content)
        article.ai_model = settings.anthropic_model
        article.status = ContentStatus.COMPLETED.value

        # Run SEO analysis
        seo_result = analyze_seo(
            generated.content,
            outline.keyword,
            outline.title,
            generated.meta_description,
        )
        article.seo_score = seo_result["score"]
        article.seo_analysis = seo_result

    except Exception as e:
        article.status = ContentStatus.FAILED.value
        article.generation_error = str(e)

    await db.commit()
    await db.refresh(article)

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
    query = select(Article).where(Article.user_id == current_user.id)

    if status:
        query = query.where(Article.status == status)
    if keyword:
        query = query.where(Article.keyword.ilike(f"%{keyword}%"))

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


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific article by ID.
    """
    result = await db.execute(
        select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
        )
    )
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
    result = await db.execute(
        select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
        )
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    update_data = request.model_dump(exclude_unset=True)

    for field, value in update_data.items():
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
async def delete_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an article.
    """
    result = await db.execute(
        select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
        )
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    await db.delete(article)
    await db.commit()


@router.post("/{article_id}/improve", response_model=ArticleResponse)
async def improve_article(
    article_id: str,
    request: ArticleImproveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Improve article content using AI.
    """
    result = await db.execute(
        select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
        )
    )
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

    try:
        improved_content = await content_ai_service.improve_content(
            content=article.content,
            improvement_type=request.improvement_type,
            keyword=article.keyword,
        )

        article.content = improved_content
        article.content_html = markdown.markdown(improved_content)
        article.word_count = len(improved_content.split())
        article.read_time = calculate_read_time(improved_content)

        # Re-run SEO analysis
        seo_result = analyze_seo(
            improved_content,
            article.keyword,
            article.title,
            article.meta_description or "",
        )
        article.seo_score = seo_result["score"]
        article.seo_analysis = seo_result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to improve article: {str(e)}",
        )

    await db.commit()
    await db.refresh(article)

    return article


@router.post("/{article_id}/analyze-seo", response_model=ArticleResponse)
async def analyze_article_seo(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-run SEO analysis on an article.
    """
    result = await db.execute(
        select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
        )
    )
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
