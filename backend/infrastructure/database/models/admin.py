"""
Admin database models.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Index, String, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class AuditAction(str, Enum):
    """Admin audit log action types."""

    # User management
    USER_UPDATED = "user_updated"
    USER_SUSPENDED = "user_suspended"
    USER_UNSUSPENDED = "user_unsuspended"
    USER_DELETED = "user_deleted"
    USER_PASSWORD_RESET = "user_password_reset"

    # Role changes
    ROLE_CHANGED = "role_changed"

    # Subscription management
    SUBSCRIPTION_UPDATED = "subscription_updated"

    # Content moderation
    ARTICLE_DELETED = "article_deleted"
    OUTLINE_DELETED = "outline_deleted"
    IMAGE_DELETED = "image_deleted"
    SOCIAL_POST_DELETED = "social_post_deleted"
    BULK_DELETE_CONTENT = "bulk_delete_content"

    # Alert management
    ALERTS_MARK_ALL_READ = "alerts_mark_all_read"

    # System actions
    SETTINGS_UPDATED = "settings_updated"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"


class AuditTargetType(str, Enum):
    """Admin audit log target types."""

    USER = "user"
    SUBSCRIPTION = "subscription"
    ARTICLE = "article"
    OUTLINE = "outline"
    IMAGE = "image"
    SOCIAL_POST = "social_post"
    SETTINGS = "settings"
    SYSTEM = "system"


class AdminAuditLog(Base, TimestampMixin):
    """Admin audit log model for tracking administrative actions."""

    __tablename__ = "admin_audit_logs"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Admin who performed the action
    admin_user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Action details
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # Target user (if action is on a user)
    target_user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Target resource
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    target_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )

    # Additional context
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """
    Structure:
    {
        "old_value": {...},
        "new_value": {...},
        "reason": "Policy violation",
        "notes": "Additional context"
    }
    """

    # Request tracking
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max length

    # Relationships
    admin_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[admin_user_id],
        lazy="joined",
    )
    target_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[target_user_id],
        lazy="joined",
    )

    # Indexes
    __table_args__ = (
        Index("ix_admin_audit_admin_action", "admin_user_id", "action"),
        Index("ix_admin_audit_target", "target_type", "target_id"),
        Index("ix_admin_audit_target_user", "target_user_id"),
        Index("ix_admin_audit_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AdminAuditLog(id={self.id}, action={self.action}, admin_id={self.admin_user_id})>"
