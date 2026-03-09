"""
Model for tracking emails blocked from self-service refunds.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RefundBlockedEmail(Base):
    """Email addresses blocked from requesting self-service refunds."""

    __tablename__ = "refund_blocked_emails"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    blocked_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
