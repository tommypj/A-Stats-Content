"""
Email journey event database model.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class EmailJourneyEvent(Base):
    """Tracks scheduled and sent lifecycle emails per user."""

    __tablename__ = "user_email_journey_events"

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
    email_key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "uix_journey_user_email_key",
            "user_id",
            "email_key",
            unique=True,
            postgresql_where=text("status IN ('scheduled', 'sent')"),
        ),
        Index("ix_journey_status_scheduled", "status", "scheduled_for"),
    )

    def __repr__(self) -> str:
        return (
            f"<EmailJourneyEvent(id={self.id}, user_id={self.user_id}, "
            f"email_key={self.email_key}, status={self.status})>"
        )
