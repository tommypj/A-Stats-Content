"""
AEO (Answer Engine Optimization) database models.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class AEOScore(Base, TimestampMixin):
    """AEO score for an article - measures AI-readability and citation potential."""

    __tablename__ = "aeo_scores"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Overall score (0-100)
    aeo_score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Score breakdown (JSON: structure_score, faq_score, entity_score, conciseness_score, schema_score, citation_readiness)
    score_breakdown: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # AI suggestions for improvement
    suggestions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Previous score for trend tracking
    previous_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # When this score was computed
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_aeo_scores_article_scored", "article_id", "scored_at"),
        Index("ix_aeo_scores_user_project", "user_id", "project_id"),
    )

    def __repr__(self) -> str:
        return f"<AEOScore(article_id={self.article_id}, score={self.aeo_score})>"


class AEOCitation(Base, TimestampMixin):
    """Tracks when content appears in AI-generated answers."""

    __tablename__ = "aeo_citations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # chatgpt, perplexity, gemini, bing_copilot
    query: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    citation_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    citation_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_aeo_citations_article_source", "article_id", "source"),
    )

    def __repr__(self) -> str:
        return f"<AEOCitation(article_id={self.article_id}, source={self.source})>"
