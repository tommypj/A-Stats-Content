"""
Notification preferences database model.
"""

from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class NotificationPreferences(Base, TimestampMixin):
    """Per-user notification preferences."""

    __tablename__ = "notification_preferences"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Generation alerts — when articles/outlines/images finish or fail
    email_generation_completed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_generation_failed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Usage alerts — approaching or hitting monthly limits
    email_usage_80_percent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_usage_limit_reached: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Content performance
    email_content_decay: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Weekly digest summary
    email_weekly_digest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Billing — payment issues, renewal reminders
    email_billing_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Product updates and announcements
    email_product_updates: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<NotificationPreferences(user_id={self.user_id})>"
