"""
System error log database model for centralized error tracking.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class SystemErrorLog(Base, TimestampMixin):
    """Centralized system error log for tracking all backend errors."""

    __tablename__ = "system_error_logs"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Error classification
    error_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    """E.g. 'ReplicateError', 'OpenAIError', 'ValidationError', 'DatabaseError'"""

    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    """HTTP status code or provider error code, e.g. '422', 'rate_limit_exceeded'"""

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="error",
    )
    """Values: 'warning', 'error', 'critical'"""

    # Error content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Request context
    service: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    """E.g. 'content_pipeline', 'image_generation', 'site_audit', 'wordpress'"""

    endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    http_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Related entities
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    # Extra context (provider response, input params, etc.)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Client info
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Deduplication & frequency
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Resolution tracking
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Fingerprint for grouping duplicate errors
    error_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="select",
    )
    resolver: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[resolved_by],
        lazy="select",
    )

    # Indexes
    __table_args__ = (
        Index("ix_system_error_logs_type_severity", "error_type", "severity"),
        Index("ix_system_error_logs_resolved_created", "is_resolved", "created_at"),
        Index("ix_system_error_logs_fingerprint", "error_fingerprint"),
    )

    def __repr__(self) -> str:
        return (
            f"<SystemErrorLog(id={self.id}, error_type={self.error_type}, "
            f"severity={self.severity}, is_resolved={self.is_resolved})>"
        )
