"""
AEO (Answer Engine Optimization) Scoring Service.

Analyzes article content for AI-readability — how likely it is to be cited
by AI answer engines like ChatGPT, Perplexity, and Gemini.

Scoring dimensions:
- Structure: heading hierarchy, list/table usage, logical flow
- FAQ: question-answer patterns, direct answer paragraphs
- Entity: topic coverage, named entities, factual density
- Conciseness: answer-first paragraphs, scannable format
- Schema: structured data indicators, semantic markup potential
- Citation Readiness: quotable snippets, definitive statements
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.aeo import AEOScore
from infrastructure.database.models.content import Article

logger = logging.getLogger(__name__)


def _count_headings(content: str) -> dict:
    """Count heading levels in markdown content."""
    h2_count = len(re.findall(r'^##\s', content, re.MULTILINE))
    h3_count = len(re.findall(r'^###\s', content, re.MULTILINE))
    h4_count = len(re.findall(r'^####\s', content, re.MULTILINE))
    return {"h2": h2_count, "h3": h3_count, "h4": h4_count, "total": h2_count + h3_count + h4_count}


def _count_lists(content: str) -> int:
    """Count list items in markdown."""
    bullets = len(re.findall(r'^[\s]*[-*+]\s', content, re.MULTILINE))
    numbered = len(re.findall(r'^[\s]*\d+\.\s', content, re.MULTILINE))
    return bullets + numbered


def _count_tables(content: str) -> int:
    """Count markdown tables."""
    return len(re.findall(r'^\|.*\|.*\|', content, re.MULTILINE))


def _count_faq_patterns(content: str) -> int:
    """Count question-answer patterns."""
    questions = len(re.findall(r'^#+\s.*\?', content, re.MULTILINE))
    questions += len(re.findall(r'\*\*.*\?\*\*', content))
    return questions


def _has_direct_answers(content: str) -> int:
    """Count paragraphs that start with definitive statements."""
    # Patterns like "X is...", "The answer is...", "In short,..."
    patterns = [
        r'(?:^|\n\n)(?:The |A |An |In short|To summarize|Simply put|Essentially)[A-Z]',
        r'(?:^|\n\n)\w+ (?:is|are|was|were|refers to|means|describes) ',
    ]
    count = 0
    for p in patterns:
        count += len(re.findall(p, content))
    return count


def _calculate_avg_paragraph_length(content: str) -> float:
    """Calculate average paragraph length in words."""
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip() and not p.strip().startswith('#')]
    if not paragraphs:
        return 0
    lengths = [len(p.split()) for p in paragraphs]
    return sum(lengths) / len(lengths)


def score_article_content(content: str, title: str, keyword: str, meta_description: str = "") -> dict:
    """
    Score article content for AEO readiness.
    Returns dict with aeo_score (0-100), score_breakdown, and basic suggestions.
    """
    if not content:
        return {
            "aeo_score": 0,
            "score_breakdown": {
                "structure_score": 0,
                "faq_score": 0,
                "entity_score": 0,
                "conciseness_score": 0,
                "schema_score": 0,
                "citation_readiness": 0,
            },
            "suggestions": ["Article has no content to analyze."],
        }

    word_count = len(content.split())
    headings = _count_headings(content)
    list_count = _count_lists(content)
    table_count = _count_tables(content)
    faq_count = _count_faq_patterns(content)
    direct_answers = _has_direct_answers(content)
    avg_para_len = _calculate_avg_paragraph_length(content)

    suggestions = []

    # 1. Structure Score (0-20)
    structure_score = 0
    if headings["h2"] >= 3:
        structure_score += 6
    elif headings["h2"] >= 1:
        structure_score += 3
    else:
        suggestions.append("Add H2 headings to create clear content sections")

    if headings["h3"] >= 2:
        structure_score += 4
    elif headings["h3"] >= 1:
        structure_score += 2

    if list_count >= 3:
        structure_score += 5
    elif list_count >= 1:
        structure_score += 3
    else:
        suggestions.append("Add bullet or numbered lists for scannable, AI-friendly content")

    if table_count >= 1:
        structure_score += 5
    else:
        if word_count > 500:
            suggestions.append("Add a comparison table or data table to improve structured data extraction")

    structure_score = min(20, structure_score)

    # 2. FAQ Score (0-20)
    faq_score = 0
    if faq_count >= 5:
        faq_score = 20
    elif faq_count >= 3:
        faq_score = 15
    elif faq_count >= 1:
        faq_score = 10
    else:
        faq_score = 0
        suggestions.append("Add FAQ-style headings (questions as H2/H3) to match how AI engines search for answers")

    # 3. Entity Score (0-15) - topic coverage and keyword presence
    entity_score = 0
    kw_lower = keyword.lower() if keyword else ""

    if kw_lower and kw_lower in content.lower():
        kw_occurrences = content.lower().count(kw_lower)
        if kw_occurrences >= 5:
            entity_score += 8
        elif kw_occurrences >= 3:
            entity_score += 5
        else:
            entity_score += 3

    if kw_lower and kw_lower in title.lower():
        entity_score += 4
    else:
        suggestions.append("Include your target keyword in the article title for better AI recognition")

    if meta_description and kw_lower and kw_lower in meta_description.lower():
        entity_score += 3

    entity_score = min(15, entity_score)

    # 4. Conciseness Score (0-20) - answer-first, scannable format
    conciseness_score = 0
    if direct_answers >= 3:
        conciseness_score += 10
    elif direct_answers >= 1:
        conciseness_score += 5
    else:
        suggestions.append("Start key paragraphs with direct, definitive statements (e.g., 'X is...')")

    if 40 <= avg_para_len <= 80:
        conciseness_score += 5
    elif avg_para_len < 40:
        conciseness_score += 3
    elif avg_para_len > 120:
        suggestions.append("Break long paragraphs into shorter ones (50-80 words) for AI extraction")

    # Short summary/TL;DR at top
    first_500 = content[:500].lower()
    if any(marker in first_500 for marker in ["tldr", "tl;dr", "in short", "key takeaway", "summary"]):
        conciseness_score += 5
    else:
        suggestions.append("Add a TL;DR or key takeaway near the top of the article")

    conciseness_score = min(20, conciseness_score)

    # 5. Schema Score (0-10) - structured data potential
    schema_score = 0
    if "**" in content:  # Bold text
        schema_score += 2
    if re.search(r'\[.*\]\(.*\)', content):  # Links
        schema_score += 2
    if table_count >= 1:
        schema_score += 3
    if list_count >= 2:
        schema_score += 3
    schema_score = min(10, schema_score)

    # 6. Citation Readiness (0-15) - quotable, definitive content
    citation_readiness = 0

    # Has stats/numbers
    number_count = len(re.findall(r'\b\d+(?:\.\d+)?%?\b', content))
    if number_count >= 10:
        citation_readiness += 5
    elif number_count >= 5:
        citation_readiness += 3

    # Has quotable statements (bold phrases, definitions)
    bold_phrases = len(re.findall(r'\*\*[^*]+\*\*', content))
    if bold_phrases >= 5:
        citation_readiness += 5
    elif bold_phrases >= 2:
        citation_readiness += 3

    if direct_answers >= 2:
        citation_readiness += 5

    citation_readiness = min(15, citation_readiness)

    # Total
    aeo_score = structure_score + faq_score + entity_score + conciseness_score + schema_score + citation_readiness
    aeo_score = min(100, max(0, aeo_score))

    return {
        "aeo_score": aeo_score,
        "score_breakdown": {
            "structure_score": structure_score,
            "faq_score": faq_score,
            "entity_score": entity_score,
            "conciseness_score": conciseness_score,
            "schema_score": schema_score,
            "citation_readiness": citation_readiness,
        },
        "suggestions": suggestions,
    }


async def score_and_save(
    db: AsyncSession,
    article_id: str,
    user_id: str,
) -> Optional[AEOScore]:
    """Score an article and save/update the AEO score record."""
    article_result = await db.execute(
        select(Article).where(
            and_(Article.id == article_id, Article.user_id == user_id)
        )
    )
    article = article_result.scalar_one_or_none()
    if not article:
        return None

    # Calculate score
    result = score_article_content(
        content=article.content or "",
        title=article.title or "",
        keyword=article.keyword or "",
        meta_description=article.meta_description or "",
    )

    # Check for existing score
    existing_result = await db.execute(
        select(AEOScore)
        .where(AEOScore.article_id == article_id)
        .order_by(AEOScore.scored_at.desc())
        .limit(1)
    )
    existing = existing_result.scalar_one_or_none()
    previous_score = existing.aeo_score if existing else None

    # Create new score record
    aeo = AEOScore(
        id=str(uuid4()),
        article_id=article_id,
        user_id=user_id,
        project_id=article.project_id,
        aeo_score=result["aeo_score"],
        score_breakdown=result["score_breakdown"],
        suggestions=result["suggestions"],
        previous_score=previous_score,
        scored_at=datetime.now(timezone.utc),
    )
    db.add(aeo)
    await db.commit()
    await db.refresh(aeo)
    return aeo


async def generate_aeo_suggestions(
    db: AsyncSession,
    article_id: str,
    user_id: str,
) -> dict:
    """Generate AI-powered AEO improvement suggestions."""
    article_result = await db.execute(
        select(Article).where(
            and_(Article.id == article_id, Article.user_id == user_id)
        )
    )
    article = article_result.scalar_one_or_none()
    if not article:
        return {"suggestions": []}

    # Get current score
    score_result = await db.execute(
        select(AEOScore)
        .where(AEOScore.article_id == article_id)
        .order_by(AEOScore.scored_at.desc())
        .limit(1)
    )
    current_score = score_result.scalar_one_or_none()

    # Truncate content to avoid token overflow
    content_preview = (article.content or "")[:3000]

    from adapters.ai.anthropic_adapter import content_ai_service

    prompt = f"""Analyze this article for Answer Engine Optimization (AEO) — how well it can be cited by AI engines like ChatGPT, Perplexity, and Gemini.

Title: {article.title}
Keyword: {article.keyword}
Current AEO Score: {current_score.aeo_score if current_score else 'Not scored'}
Score Breakdown: {json.dumps(current_score.score_breakdown) if current_score and current_score.score_breakdown else 'N/A'}

Content preview (first 3000 chars):
{content_preview}

Provide 4-6 specific, actionable suggestions to improve this article's AEO score. For each:
- action: A concise title
- description: What to do and why it helps AI citation
- category: One of: structure, faq, entity, conciseness, schema, citation_readiness
- estimated_impact: "high", "medium", or "low"

Return as JSON array of objects with keys: action, description, category, estimated_impact"""

    try:
        response = await content_ai_service.generate_text(prompt, max_tokens=1500)
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

        # Save to score record
        if current_score:
            current_score.suggestions = suggestions
            await db.commit()

        return {"suggestions": suggestions}
    except Exception as e:
        logger.error("Failed to generate AEO suggestions: %s", str(e))
        return {"suggestions": [
            {"action": "Add FAQ section", "description": "Add question-answer headings matching common user queries.", "category": "faq", "estimated_impact": "high"},
            {"action": "Improve structure", "description": "Use clear H2/H3 hierarchy with descriptive headings.", "category": "structure", "estimated_impact": "high"},
            {"action": "Add TL;DR", "description": "Add a summary paragraph near the top of the article.", "category": "conciseness", "estimated_impact": "medium"},
            {"action": "Include data points", "description": "Add statistics, percentages, and factual data for citation.", "category": "citation_readiness", "estimated_impact": "medium"},
        ]}


async def get_aeo_overview(
    db: AsyncSession,
    user_id: str,
) -> dict:
    """Get AEO overview stats for all user articles."""
    # Get latest score per article using a subquery
    latest_scores_sq = (
        select(
            AEOScore.article_id,
            func.max(AEOScore.scored_at).label("max_scored_at"),
        )
        .where(AEOScore.user_id == user_id)
        .group_by(AEOScore.article_id)
        .subquery()
    )

    scores_q = (
        select(AEOScore)
        .join(
            latest_scores_sq,
            and_(
                AEOScore.article_id == latest_scores_sq.c.article_id,
                AEOScore.scored_at == latest_scores_sq.c.max_scored_at,
            ),
        )
        .where(AEOScore.user_id == user_id)
        .limit(10000)  # ANA-33: Cap result set to prevent unbounded memory use
    )
    scores_result = await db.execute(scores_q)
    scores = scores_result.scalars().all()

    if not scores:
        return {
            "total_scored": 0,
            "average_score": 0,
            "excellent_count": 0,
            "good_count": 0,
            "needs_work_count": 0,
            "score_distribution": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
            "top_articles": [],
            "bottom_articles": [],
        }

    total = len(scores)
    avg = sum(s.aeo_score for s in scores) / total
    excellent = sum(1 for s in scores if s.aeo_score >= 80)
    good = sum(1 for s in scores if 50 <= s.aeo_score < 80)
    needs_work = sum(1 for s in scores if s.aeo_score < 50)

    dist = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for s in scores:
        if s.aeo_score <= 20:
            dist["0-20"] += 1
        elif s.aeo_score <= 40:
            dist["21-40"] += 1
        elif s.aeo_score <= 60:
            dist["41-60"] += 1
        elif s.aeo_score <= 80:
            dist["61-80"] += 1
        else:
            dist["81-100"] += 1

    # Get article titles for top/bottom
    sorted_scores = sorted(scores, key=lambda s: s.aeo_score, reverse=True)
    article_ids = [s.article_id for s in sorted_scores[:5]] + [s.article_id for s in sorted_scores[-5:]]
    articles_q = select(Article.id, Article.title, Article.keyword).where(Article.id.in_(article_ids))
    articles_result = await db.execute(articles_q)
    title_map = {row.id: {"title": row.title, "keyword": row.keyword} for row in articles_result.all()}

    top = [
        {
            "article_id": s.article_id,
            "title": title_map.get(s.article_id, {}).get("title", ""),
            "keyword": title_map.get(s.article_id, {}).get("keyword", ""),
            "aeo_score": s.aeo_score,
            "score_breakdown": s.score_breakdown,
        }
        for s in sorted_scores[:5]
    ]
    bottom = [
        {
            "article_id": s.article_id,
            "title": title_map.get(s.article_id, {}).get("title", ""),
            "keyword": title_map.get(s.article_id, {}).get("keyword", ""),
            "aeo_score": s.aeo_score,
            "score_breakdown": s.score_breakdown,
        }
        for s in sorted_scores[-5:]
        if s.aeo_score < 80  # only show bottom if they actually need work
    ]

    return {
        "total_scored": total,
        "average_score": round(avg),
        "excellent_count": excellent,
        "good_count": good,
        "needs_work_count": needs_work,
        "score_distribution": dist,
        "top_articles": top,
        "bottom_articles": bottom,
    }
