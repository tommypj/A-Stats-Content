"""
Blog database models: BlogCategory, BlogTag, BlogPost, BlogPostTag.

Platform-level models — not scoped to user projects.
Admins own and manage all blog content.
"""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class BlogPostStatus(StrEnum):
    """Blog post status enumeration."""

    DRAFT = "draft"
    PUBLISHED = "published"


class BlogCategory(Base, TimestampMixin):
    """Blog category model."""

    __tablename__ = "blog_categories"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    posts: Mapped[list["BlogPost"]] = relationship(
        "BlogPost",
        back_populates="category",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<BlogCategory(id={self.id}, slug={self.slug})>"


class BlogTag(Base, TimestampMixin):
    """Blog tag model."""

    __tablename__ = "blog_tags"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    # Relationships
    post_tags: Mapped[list["BlogPostTag"]] = relationship(
        "BlogPostTag",
        back_populates="tag",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BlogTag(id={self.id}, slug={self.slug})>"


class BlogPostTag(Base):
    """Association table linking blog posts to tags."""

    __tablename__ = "blog_post_tags"

    post_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("blog_tags.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    post: Mapped["BlogPost"] = relationship("BlogPost", back_populates="post_tags")
    tag: Mapped[BlogTag] = relationship("BlogTag", back_populates="post_tags")

    __table_args__ = (
        PrimaryKeyConstraint("post_id", "tag_id"),
    )


class BlogPost(Base, TimestampMixin):
    """Blog post model."""

    __tablename__ = "blog_posts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # URL
    slug: Mapped[str] = mapped_column(String(300), nullable=False, unique=True, index=True)

    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    meta_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=BlogPostStatus.DRAFT,
        index=True,
    )

    # Images
    featured_image_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    featured_image_alt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    og_image_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Author (platform-level, cached name for display)
    author_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    author_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Category
    category_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("blog_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Publishing
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Structured data
    schema_faq: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    author: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[author_id],
        lazy="joined",
    )
    category: Mapped[BlogCategory | None] = relationship(
        "BlogCategory",
        back_populates="posts",
        lazy="joined",
    )
    post_tags: Mapped[list[BlogPostTag]] = relationship(
        "BlogPostTag",
        back_populates="post",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index("ix_blog_posts_status_published_at", "status", "published_at"),
        Index("ix_blog_posts_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<BlogPost(id={self.id}, slug={self.slug}, status={self.status})>"
