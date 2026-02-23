"""
Generation tracking and admin alert database models.
"""

from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Index, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class GenerationLog(Base, TimestampMixin):
    """Tracks each AI generation attempt (article, outline, image)."""

    __tablename__ = "generation_logs"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # User who triggered the generation
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Project context (optional)
    project_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # What was generated
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    """Values: 'article', 'outline', 'image'"""

    resource_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
    )
    """ID of the article, outline, or image that was generated."""

    # Generation outcome
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    """Values: 'started', 'success', 'failed'"""

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Performance & cost tracking
    ai_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    """Duration of the generation in milliseconds."""

    input_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """
    Structure:
    {
        "keyword": "...",
        "prompt": "...",
        "settings": {...}
    }
    """

    cost_credits: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    """Credits consumed by this generation. 0 if failed."""

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="joined",
    )
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        foreign_keys=[project_id],
        lazy="joined",
    )

    # Indexes
    __table_args__ = (
        Index("ix_generation_logs_user_resource", "user_id", "resource_type"),
        Index("ix_generation_logs_created", "created_at"),
        Index("ix_generation_logs_status_type", "status", "resource_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<GenerationLog(id={self.id}, resource_type={self.resource_type}, "
            f"status={self.status}, user_id={self.user_id})>"
        )


class AdminAlert(Base, TimestampMixin):
    """Admin-facing alerts for notable system events."""

    __tablename__ = "admin_alerts"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Alert classification
    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    """E.g. 'generation_failed', 'rate_limit_hit'"""

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="warning",
    )
    """Values: 'info', 'warning', 'critical'"""

    # Alert content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Related resource
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    """Values: 'article', 'outline', 'image'"""

    resource_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )

    # User who triggered the alert
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Project context
    project_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Alert state
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="joined",
    )
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        foreign_keys=[project_id],
        lazy="joined",
    )

    # Indexes
    __table_args__ = (
        Index("ix_admin_alerts_unread", "is_read", "created_at"),
        Index("ix_admin_alerts_type_severity", "alert_type", "severity"),
    )

    def __repr__(self) -> str:
        return (
            f"<AdminAlert(id={self.id}, alert_type={self.alert_type}, "
            f"severity={self.severity}, is_resolved={self.is_resolved})>"
        )
