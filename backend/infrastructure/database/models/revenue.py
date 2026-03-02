"""
Revenue attribution database models for Phase 4: Content-to-Revenue Attribution.
"""

from datetime import UTC, datetime
from datetime import date as date_type
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class ConversionGoal(Base, TimestampMixin):
    """A named conversion goal (e.g. form submission, purchase) tracked against organic traffic."""

    __tablename__ = "conversion_goals"

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

    # Optional project scope
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Goal definition
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    goal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    goal_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("ix_conversion_goals_user_active", "user_id", "is_active"),)

    def __repr__(self) -> str:
        return f"<ConversionGoal(name={self.name!r}, goal_type={self.goal_type!r}, is_active={self.is_active})>"


class ContentConversion(Base, TimestampMixin):
    """Daily conversion event attributed to a specific article, keyword, and conversion goal."""

    __tablename__ = "content_conversions"

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

    # Optional project scope
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Content reference (nullable: row survives article deletion)
    article_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Goal reference
    goal_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversion_goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Traffic source detail
    page_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    keyword: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Aggregation period
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)

    # Metrics
    visits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversion_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Attribution model used to assign credit
    attribution_model: Mapped[str] = mapped_column(String(50), default="last_touch", nullable=False)

    __table_args__ = (
        Index("ix_content_conversions_user_date", "user_id", "date"),
        Index("ix_content_conversions_article_date", "article_id", "date"),
        Index("ix_content_conversions_goal_date", "goal_id", "date"),
    )

    def __repr__(self) -> str:
        return (
            f"<ContentConversion("
            f"article_id={self.article_id!r}, "
            f"date={self.date}, "
            f"conversions={self.conversions}, "
            f"revenue={self.revenue}"
            f")>"
        )


class RevenueReport(Base, TimestampMixin):
    """Pre-computed revenue attribution report covering a specified date range."""

    __tablename__ = "revenue_reports"

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

    # Optional project scope
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Report classification and period
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    period_start: Mapped[date_type] = mapped_column(Date, nullable=False)
    period_end: Mapped[date_type] = mapped_column(Date, nullable=False)

    # Aggregate metrics
    total_organic_visits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Ranked breakdowns (stored as ordered JSON arrays)
    top_articles: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    top_keywords: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Generation timestamp
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_revenue_reports_user_type", "user_id", "report_type"),
        Index("ix_revenue_reports_period", "period_start", "period_end"),
    )

    def __repr__(self) -> str:
        return (
            f"<RevenueReport("
            f"report_type={self.report_type!r}, "
            f"period_start={self.period_start}, "
            f"period_end={self.period_end}, "
            f"total_revenue={self.total_revenue}"
            f")>"
        )
