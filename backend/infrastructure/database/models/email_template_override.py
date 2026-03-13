"""
Email template override database model.
"""

from uuid import uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class EmailTemplateOverride(Base, TimestampMixin):
    """Stores admin-edited overrides for journey email templates."""

    __tablename__ = "email_template_overrides"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    email_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    html: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_admin_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<EmailTemplateOverride(id={self.id}, email_key={self.email_key})>"
        )
