"""Tag model and association tables."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Tag(Base, TimestampMixin):
    """User-created tag for organizing articles and outlines."""

    __tablename__ = "tags"

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

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
    )

    user = relationship("User", lazy="select")

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name={self.name})>"


class ArticleTag(Base):
    """Association between articles and tags."""

    __tablename__ = "article_tags"

    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )


class OutlineTag(Base):
    """Association between outlines and tags."""

    __tablename__ = "outline_tags"

    outline_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("outlines.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
