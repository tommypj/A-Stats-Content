"""
Social media scheduling database models.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Platform(str, Enum):
    """Supported social media platforms."""

    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class PostStatus(str, Enum):
    """Status of a scheduled post."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PostTargetStatus(str, Enum):
    """Status of an individual post target (platform-specific)."""

    PENDING = "pending"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    SKIPPED = "skipped"


class SocialAccount(Base, TimestampMixin):
    """
    Connected social media accounts.

    Stores OAuth tokens and account metadata for connected platforms.
    """

    __tablename__ = "social_accounts"

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

    # Project ownership (optional - for multi-tenancy)
    project_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Platform info
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    platform_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    platform_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    platform_display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # OAuth tokens (encrypted)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Account metadata
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    account_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Connection status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Indexes
    __table_args__ = (
        Index("ix_social_accounts_user_platform", "user_id", "platform"),
        Index(
            "ix_social_accounts_platform_user",
            "platform",
            "platform_user_id",
            unique=True,
        ),
        Index("ix_social_accounts_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<SocialAccount(platform={self.platform}, username={self.platform_username})>"


class ScheduledPost(Base, TimestampMixin):
    """
    Scheduled social media posts.

    Represents a post that can be published to one or more platforms.
    """

    __tablename__ = "scheduled_posts"

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

    # Project ownership (optional - for multi-tenancy)
    project_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Post content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    media_urls: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    link_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=PostStatus.DRAFT.value
    )

    # Publishing metadata
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    publish_attempted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    publish_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Optional article linkage
    article_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    targets: Mapped[list["PostTarget"]] = relationship(
        "PostTarget",
        foreign_keys="PostTarget.scheduled_post_id",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_scheduled_posts_user_status", "user_id", "status"),
        Index("ix_scheduled_posts_scheduled_at", "scheduled_at"),
        Index("ix_scheduled_posts_user_scheduled", "user_id", "scheduled_at"),
        Index("ix_scheduled_posts_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ScheduledPost(id={self.id}, status={self.status})>"


class PostTarget(Base, TimestampMixin):
    """
    Target platform for a scheduled post.

    Links a ScheduledPost to a SocialAccount with platform-specific settings.
    """

    __tablename__ = "post_targets"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # References
    scheduled_post_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("scheduled_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    social_account_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("social_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Platform-specific content overrides
    platform_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Publishing status for this target
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    platform_post_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    platform_post_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    publish_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Analytics snapshot
    analytics_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_analytics_fetch: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    social_account: Mapped["SocialAccount"] = relationship(
        "SocialAccount",
        lazy="noload",
    )

    # Indexes
    __table_args__ = (
        Index("ix_post_targets_post", "scheduled_post_id", "social_account_id"),
    )

    def __repr__(self) -> str:
        return f"<PostTarget(id={self.id}, account={self.social_account_id})>"
