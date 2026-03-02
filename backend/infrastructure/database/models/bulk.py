"""
Bulk content generation database models.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class ContentTemplate(Base, TimestampMixin):
    """Reusable content generation template."""

    __tablename__ = "content_templates"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    # template_config schema:
    # {
    #   "tone": "professional",
    #   "writing_style": "editorial",
    #   "word_count_target": 1500,
    #   "target_audience": "...",
    #   "custom_instructions": "...",
    #   "include_faq": true,
    #   "include_conclusion": true,
    #   "language": "en"
    # }

    def __repr__(self) -> str:
        return f"<ContentTemplate(name={self.name})>"


class BulkJob(Base, TimestampMixin):
    """A bulk content generation job."""

    __tablename__ = "bulk_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    template_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("content_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_bulk_jobs_user_status", "user_id", "status"),)

    def __repr__(self) -> str:
        return f"<BulkJob(type={self.job_type}, status={self.status}, items={self.total_items})>"


class BulkJobItem(Base, TimestampMixin):
    """Individual item within a bulk job."""

    __tablename__ = "bulk_job_items"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    bulk_job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("bulk_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    keyword: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_bulk_job_items_job_status", "bulk_job_id", "status"),)

    def __repr__(self) -> str:
        return f"<BulkJobItem(keyword={self.keyword}, status={self.status})>"
