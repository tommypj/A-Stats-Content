"""Keyword research cache model."""
from __future__ import annotations
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Text, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class KeywordResearchCache(Base, TimestampMixin):
    """Stores keyword research results for deduplication and history."""

    __tablename__ = "keyword_research_cache"

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
    # Normalized (lowercase, stripped) version of the seed keyword for cache key
    seed_keyword_normalized: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    # Original casing as entered by the user
    seed_keyword_original: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    # Full JSON result stored as text (the entire response dict)
    result_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    # When this cache entry expires (30 days from creation)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        # Fast lookup by user + normalized keyword
        Index(
            "ix_kw_cache_user_keyword",
            "user_id",
            "seed_keyword_normalized",
        ),
    )
