"""Article template model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class ArticleTemplate(Base, TimestampMixin):
    """Reusable article template with pre-configured settings."""

    __tablename__ = "article_templates"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Template metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Article defaults
    target_audience: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    word_count_target: Mapped[int] = mapped_column(Integer, default=1500, nullable=False)
    writing_style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    voice: Mapped[str | None] = mapped_column(String(100), nullable=True)
    custom_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Section structure (JSON array matching outline sections format)
    sections: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User", lazy="joined")
    project = relationship("Project", lazy="select")

    def __repr__(self) -> str:
        return f"<ArticleTemplate(id={self.id}, name={self.name[:30]})>"
