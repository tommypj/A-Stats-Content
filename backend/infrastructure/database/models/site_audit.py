"""
Site audit database models.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class SiteAudit(Base, TimestampMixin):
    """Site audit job model."""

    __tablename__ = "site_audits"

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
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Issue counters
    total_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    info_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Overall health score (0-100)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Error reporting
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lifecycle timestamps
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    pages: Mapped[list["AuditPage"]] = relationship(
        "AuditPage",
        back_populates="audit",
        cascade="all, delete-orphan",
    )
    issues: Mapped[list["AuditIssue"]] = relationship(
        "AuditIssue",
        back_populates="audit",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SiteAudit(id={self.id}, domain={self.domain}, status={self.status})>"


class AuditPage(Base):
    """A single crawled page belonging to a site audit."""

    __tablename__ = "audit_pages"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Parent audit
    audit_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("site_audits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Page data
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # SEO signals
    h1_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_canonical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_og_tags: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_structured_data: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    has_robots_meta: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Size and redirect info
    page_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    redirect_chain: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Per-page issues snapshot
    issues_json: Mapped[dict | None] = mapped_column(
        "issues", JSONB, nullable=True
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )

    # Relationships
    audit: Mapped[Optional["SiteAudit"]] = relationship(
        "SiteAudit",
        back_populates="pages",
    )
    issues: Mapped[list["AuditIssue"]] = relationship(
        "AuditIssue",
        back_populates="page",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AuditPage(id={self.id}, url={self.url[:60]}, status_code={self.status_code})>"


class AuditIssue(Base):
    """An individual issue found during a site audit."""

    __tablename__ = "audit_issues"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Parent audit
    audit_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("site_audits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional parent page
    page_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("audit_pages.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Issue details
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )

    # Relationships
    audit: Mapped[Optional["SiteAudit"]] = relationship(
        "SiteAudit",
        back_populates="issues",
    )
    page: Mapped[Optional["AuditPage"]] = relationship(
        "AuditPage",
        back_populates="issues",
    )

    def __repr__(self) -> str:
        return f"<AuditIssue(id={self.id}, type={self.issue_type}, severity={self.severity})>"
