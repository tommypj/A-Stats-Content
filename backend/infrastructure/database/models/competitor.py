"""
Competitor analyzer database models.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class CompetitorAnalysis(Base, TimestampMixin):
    """Competitor analysis job model."""

    __tablename__ = "competitor_analyses"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Owner
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Project ownership (optional)
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Target domain
    domain: Mapped[str] = mapped_column(String(255), nullable=False)

    # Job status
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )

    # Progress counters
    total_urls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scraped_urls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_keywords: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Error reporting
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lifecycle timestamps
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    articles: Mapped[list["CompetitorArticle"]] = relationship(
        "CompetitorArticle",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_comp_analysis_user_domain", "user_id", "domain"),
        Index("ix_comp_analysis_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<CompetitorAnalysis(id={self.id}, domain={self.domain}, status={self.status})>"


class CompetitorArticle(Base, TimestampMixin):
    """A single scraped URL belonging to a competitor analysis."""

    __tablename__ = "competitor_articles"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Parent analysis
    analysis_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("competitor_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scraped content
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    headings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    url_slug: Mapped[str | None] = mapped_column(String(500), nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Keyword extraction
    extracted_keyword: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    keyword_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Scrape timestamp
    scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    analysis: Mapped[Optional["CompetitorAnalysis"]] = relationship(
        "CompetitorAnalysis",
        back_populates="articles",
    )

    def __repr__(self) -> str:
        return f"<CompetitorArticle(id={self.id}, url={self.url[:60]}, keyword={self.extracted_keyword})>"
