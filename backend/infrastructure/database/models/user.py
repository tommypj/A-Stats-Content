"""
User database model.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class UserRole(str, Enum):
    """User roles enumeration."""

    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    """User account status enumeration."""

    PENDING = "pending"  # Email not verified
    ACTIVE = "active"  # Account active
    SUSPENDED = "suspended"  # Account suspended
    DELETED = "deleted"  # Soft deleted


class SubscriptionTier(str, Enum):
    """Subscription tier enumeration."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class User(Base, TimestampMixin):
    """User account model."""

    __tablename__ = "users"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Basic info
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Authentication
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50),
        default=UserRole.USER.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=UserStatus.PENDING.value,
        nullable=False,
    )

    # Email verification
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    email_verification_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Password reset
    password_reset_token: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Subscription
    subscription_tier: Mapped[str] = mapped_column(
        String(50),
        default=SubscriptionTier.FREE.value,
        nullable=False,
    )
    subscription_status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
    )  # active, cancelled, paused, past_due, expired
    subscription_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lemonsqueezy_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True
    )
    lemonsqueezy_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    lemonsqueezy_variant_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Preferences
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(50), default="UTC", nullable=False
    )

    # Usage tracking
    articles_generated_this_month: Mapped[int] = mapped_column(
        default=0, nullable=False
    )
    outlines_generated_this_month: Mapped[int] = mapped_column(
        default=0, nullable=False
    )
    images_generated_this_month: Mapped[int] = mapped_column(
        default=0, nullable=False
    )
    usage_reset_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Login tracking
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    login_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # WordPress integration
    wordpress_credentials: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """
    Structure:
    {
        "site_url": "https://mysite.com",
        "username": "admin",
        "app_password_encrypted": "encrypted_password_here",
        "connected_at": "2025-01-15T12:00:00Z",
        "last_tested_at": "2025-01-15T12:00:00Z"
    }
    """

    # Suspension fields
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    suspended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    suspended_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Multi-tenancy - currently selected team
    current_team_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Indexes
    __table_args__ = (
        Index("ix_users_email_status", "email", "status"),
        Index("ix_users_subscription", "subscription_tier", "subscription_expires"),
        Index("ix_users_lemonsqueezy", "lemonsqueezy_customer_id"),
        Index("ix_users_role", "role"),
        Index("ix_users_current_team", "current_team_id"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE.value and self.deleted_at is None

    @property
    def is_verified(self) -> bool:
        """Check if user email is verified."""
        return self.email_verified

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role in (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value)

    @property
    def subscription_tier_enum(self) -> SubscriptionTier:
        """Get subscription tier as enum."""
        return SubscriptionTier(self.subscription_tier)

    def can_generate_article(self, limit: int) -> bool:
        """Check if user can generate more articles this month."""
        return self.articles_generated_this_month < limit

    def can_generate_outline(self, limit: int) -> bool:
        """Check if user can generate more outlines this month."""
        return self.outlines_generated_this_month < limit

    def can_generate_image(self, limit: int) -> bool:
        """Check if user can generate more images this month."""
        return self.images_generated_this_month < limit
