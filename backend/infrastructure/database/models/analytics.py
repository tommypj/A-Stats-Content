"""
Analytics database models for Google Search Console integration.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Float,
    Date,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class GSCConnection(Base, TimestampMixin):
    """Google Search Console OAuth connection model."""

    __tablename__ = "gsc_connections"

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
        unique=True,  # One GSC connection per user
        index=True,
    )

    # Team ownership (optional - for multi-tenancy)
    team_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Site being tracked
    site_url: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # OAuth tokens (encrypted in production)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expiry: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Connection metadata
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    last_sync: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<GSCConnection(user_id={self.user_id}, site={self.site_url})>"

    @property
    def is_token_expired(self) -> bool:
        """Check if access token is expired."""
        return datetime.utcnow() >= self.token_expiry


class KeywordRanking(Base, TimestampMixin):
    """Historical keyword ranking data from Google Search Console."""

    __tablename__ = "keyword_rankings"

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

    # Site and keyword
    site_url: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # Date of the data
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)

    # GSC metrics
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ctr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    position: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_keyword_rankings_user_date", "user_id", "date"),
        Index("ix_keyword_rankings_site_date", "site_url", "date"),
        Index("ix_keyword_rankings_keyword_date", "keyword", "date"),
        # Unique constraint to prevent duplicates
        UniqueConstraint(
            "user_id",
            "site_url",
            "keyword",
            "date",
            name="uq_keyword_ranking_user_site_keyword_date",
        ),
    )

    def __repr__(self) -> str:
        return f"<KeywordRanking(keyword={self.keyword[:30]}, date={self.date}, position={self.position})>"


class PagePerformance(Base, TimestampMixin):
    """Historical page performance data from Google Search Console."""

    __tablename__ = "page_performances"

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

    # Site and page
    site_url: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    page_url: Mapped[str] = mapped_column(String(1000), nullable=False, index=True)

    # Date of the data
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)

    # GSC metrics
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ctr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    position: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_page_performances_user_date", "user_id", "date"),
        Index("ix_page_performances_site_date", "site_url", "date"),
        Index("ix_page_performances_page_date", "page_url", "date"),
        # Unique constraint to prevent duplicates
        UniqueConstraint(
            "user_id",
            "site_url",
            "page_url",
            "date",
            name="uq_page_performance_user_site_page_date",
        ),
    )

    def __repr__(self) -> str:
        return f"<PagePerformance(page={self.page_url[:50]}, date={self.date}, clicks={self.clicks})>"


class DailyAnalytics(Base, TimestampMixin):
    """Daily aggregated analytics data from Google Search Console."""

    __tablename__ = "daily_analytics"

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

    # Site
    site_url: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # Date of the data
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)

    # Aggregated GSC metrics
    total_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_ctr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_position: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_daily_analytics_user_date", "user_id", "date"),
        Index("ix_daily_analytics_site_date", "site_url", "date"),
        # Unique constraint to prevent duplicates
        UniqueConstraint(
            "user_id",
            "site_url",
            "date",
            name="uq_daily_analytics_user_site_date",
        ),
    )

    def __repr__(self) -> str:
        return f"<DailyAnalytics(date={self.date}, clicks={self.total_clicks}, impressions={self.total_impressions})>"
