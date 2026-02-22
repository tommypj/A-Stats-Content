"""
Content database models: Outline and Article.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class ContentStatus(str, Enum):
    """Content status enumeration."""

    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    PUBLISHED = "published"
    FAILED = "failed"


class ContentTone(str, Enum):
    """Content tone enumeration."""

    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    EMPATHETIC = "empathetic"
    INFORMATIVE = "informative"
    CONVERSATIONAL = "conversational"


class Outline(Base, TimestampMixin):
    """Article outline model."""

    __tablename__ = "outlines"

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

    # Team ownership (optional - for multi-tenancy)
    team_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_audience: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tone: Mapped[str] = mapped_column(
        String(50),
        default=ContentTone.PROFESSIONAL.value,
        nullable=False,
    )

    # Structure (JSON array of sections)
    sections: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """
    Structure:
    [
        {
            "heading": "Introduction",
            "subheadings": ["What is...", "Why it matters"],
            "notes": "Brief overview",
            "word_count_target": 200
        },
        ...
    ]
    """

    # Metadata
    status: Mapped[str] = mapped_column(
        String(50),
        default=ContentStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    word_count_target: Mapped[int] = mapped_column(default=1500, nullable=False)
    estimated_read_time: Mapped[Optional[int]] = mapped_column(nullable=True)  # minutes

    # AI Generation
    ai_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    generation_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    articles: Mapped[List["Article"]] = relationship(
        "Article",
        back_populates="outline",
        cascade="all, delete-orphan",
    )
    # team: Mapped[Optional["Team"]] = relationship(back_populates="outlines")  # Uncomment when Team model exists

    def __repr__(self) -> str:
        return f"<Outline(id={self.id}, title={self.title[:30]}, status={self.status})>"

    @property
    def section_count(self) -> int:
        """Get number of sections."""
        if self.sections:
            return len(self.sections)
        return 0


class Article(Base, TimestampMixin):
    """Article content model."""

    __tablename__ = "articles"

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

    # Team ownership (optional - for multi-tenancy)
    team_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Optional outline reference
    outline_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("outlines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, unique=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    meta_description: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    status: Mapped[str] = mapped_column(
        String(50),
        default=ContentStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    word_count: Mapped[int] = mapped_column(default=0, nullable=False)
    read_time: Mapped[Optional[int]] = mapped_column(nullable=True)  # minutes

    # SEO
    seo_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    seo_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """
    Structure:
    {
        "keyword_density": 2.5,
        "title_has_keyword": true,
        "meta_description_length": 155,
        "headings_structure": "good",
        "internal_links": 3,
        "external_links": 2,
        "image_alt_texts": true,
        "readability_score": 65,
        "suggestions": ["Add more internal links", "..."]
    }
    """

    # AI Generation
    ai_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    generation_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Publishing
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    wordpress_post_id: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Social media posts (AI-generated content for sharing)
    social_posts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Featured image
    featured_image_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("generated_images.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    outline: Mapped[Optional["Outline"]] = relationship(
        "Outline",
        back_populates="articles",
    )
    images: Mapped[List["GeneratedImage"]] = relationship(
        "GeneratedImage",
        back_populates="article",
        foreign_keys="GeneratedImage.article_id",
    )
    # team: Mapped[Optional["Team"]] = relationship(back_populates="articles")  # Uncomment when Team model exists

    def __repr__(self) -> str:
        return f"<Article(id={self.id}, title={self.title[:30]}, status={self.status})>"

    @property
    def is_published(self) -> bool:
        """Check if article is published."""
        return self.status == ContentStatus.PUBLISHED.value and self.published_at is not None


class GeneratedImage(Base, TimestampMixin):
    """AI-generated image model."""

    __tablename__ = "generated_images"

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

    # Team ownership (optional - for multi-tenancy)
    team_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Optional article reference
    article_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Image data
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    local_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    alt_text: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Generation metadata
    style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(nullable=True)
    height: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="completed",
        nullable=False,
    )

    # Relationships
    article: Mapped[Optional["Article"]] = relationship(
        "Article",
        back_populates="images",
        foreign_keys=[article_id],
    )
    # team: Mapped[Optional["Team"]] = relationship(back_populates="images")  # Uncomment when Team model exists

    def __repr__(self) -> str:
        return f"<GeneratedImage(id={self.id}, prompt={self.prompt[:30]})>"
