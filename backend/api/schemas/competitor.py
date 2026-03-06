"""
Competitor Analysis API schemas.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Request schemas

class AnalyzeCompetitorRequest(BaseModel):
    """Request to start a competitor analysis."""
    domain: str = Field(..., min_length=3, max_length=255, description="Competitor domain (e.g., example-blog.com)")
    project_id: str | None = Field(None, description="Project ID for scoping")

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        """Strip protocol, www prefix, trailing slashes, and paths."""
        d = v.strip().lower()
        for prefix in ("https://", "http://", "//"):
            if d.startswith(prefix):
                d = d[len(prefix):]
        d = d.split("/")[0]  # remove any path
        d = d.split("?")[0]  # remove query string
        if d.startswith("www."):
            d = d[4:]
        return d.rstrip(".")


# Response schemas

class CompetitorArticleResponse(BaseModel):
    """Single competitor article."""
    id: str
    url: str
    title: str | None
    meta_description: str | None
    url_slug: str | None
    word_count: int | None
    extracted_keyword: str | None
    keyword_confidence: float | None

    model_config = ConfigDict(from_attributes=True)


class CompetitorAnalysisResponse(BaseModel):
    """Competitor analysis summary."""
    id: str
    user_id: str
    project_id: str | None
    domain: str
    status: str
    total_urls: int
    scraped_urls: int
    total_keywords: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompetitorAnalysisDetailResponse(CompetitorAnalysisResponse):
    """Analysis with full article list."""
    articles: list[CompetitorArticleResponse]


class CompetitorAnalysisListResponse(BaseModel):
    """Paginated list of analyses."""
    items: list[CompetitorAnalysisResponse]
    total: int
    page: int
    page_size: int
    pages: int


class KeywordArticle(BaseModel):
    """Lightweight article reference within a keyword aggregation."""
    url: str
    title: str | None


class KeywordAggregation(BaseModel):
    """Keyword with its article count and references."""
    keyword: str
    article_count: int
    articles: list[KeywordArticle]


class KeywordAggregationListResponse(BaseModel):
    """Aggregated keywords response."""
    keywords: list[KeywordAggregation]
    total: int


class KeywordGapItem(BaseModel):
    """A keyword the competitor covers but the user does not."""
    keyword: str
    competitor_articles: int
    competitor_urls: list[str]


class KeywordGapResponse(BaseModel):
    """Keyword gap analysis response."""
    gaps: list[KeywordGapItem]
    total_competitor_keywords: int
    total_your_keywords: int
    total_gaps: int
