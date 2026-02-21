"""
Team and multi-tenancy database models.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import uuid4
import secrets

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class TeamMemberRole(str, Enum):
    """Team member role enumeration."""

    OWNER = "owner"  # Full control, can delete team
    ADMIN = "admin"  # Manage members, settings, billing
    EDITOR = "editor"  # Create/edit content
    VIEWER = "viewer"  # Read-only access


class InvitationStatus(str, Enum):
    """Team invitation status enumeration."""

    PENDING = "pending"  # Waiting for user to accept
    ACCEPTED = "accepted"  # User accepted and joined team
    REVOKED = "revoked"  # Invitation was cancelled
    EXPIRED = "expired"  # Invitation expired (auto-marked by background job)


class Team(Base, TimestampMixin):
    """Team/organization model for multi-tenancy."""

    __tablename__ = "teams"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Owner (creator of the team)
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Billing
    subscription_tier: Mapped[str] = mapped_column(
        String(50), default="free", nullable=False
    )
    subscription_status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False
    )
    subscription_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lemonsqueezy_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True
    )
    lemonsqueezy_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Team limits (shared across all members)
    max_members: Mapped[int] = mapped_column(default=5, nullable=False)
    articles_generated_this_month: Mapped[int] = mapped_column(
        default=0, nullable=False
    )
    outlines_generated_this_month: Mapped[int] = mapped_column(
        default=0, nullable=False
    )
    images_generated_this_month: Mapped[int] = mapped_column(default=0, nullable=False)
    usage_reset_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], lazy="joined")
    members = relationship(
        "TeamMember",
        back_populates="team",
        cascade="all, delete-orphan",
        lazy="selectinload",
    )
    invitations = relationship(
        "TeamInvitation",
        back_populates="team",
        cascade="all, delete-orphan",
        lazy="selectinload",
    )

    # Indexes
    # Note: slug and owner_id already have index=True on their column definitions
    __table_args__ = (
        Index("ix_teams_subscription", "subscription_tier", "subscription_expires"),
    )

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name={self.name}, slug={self.slug})>"

    @property
    def is_active(self) -> bool:
        """Check if team is active (not deleted)."""
        return self.deleted_at is None

    def can_add_member(self) -> bool:
        """Check if team can add more members."""
        current_count = len([m for m in self.members if m.deleted_at is None])
        return current_count < self.max_members


class TeamMember(Base, TimestampMixin):
    """Team member model (junction table between users and teams)."""

    __tablename__ = "team_members"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Foreign keys
    team_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role in team
    role: Mapped[str] = mapped_column(
        String(50), default=TeamMemberRole.EDITOR.value, nullable=False
    )

    # Invitation tracking
    invited_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    inviter = relationship("User", foreign_keys=[invited_by], lazy="joined")

    # Indexes and constraints
    # Note: team_id and user_id already have index=True on the column definition
    # Only keep the composite unique index here
    __table_args__ = (
        Index("ix_team_members_team_user", "team_id", "user_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<TeamMember(id={self.id}, team_id={self.team_id}, user_id={self.user_id}, role={self.role})>"

    @property
    def is_active(self) -> bool:
        """Check if team member is active (not deleted)."""
        return self.deleted_at is None

    @property
    def is_admin(self) -> bool:
        """Check if member has admin privileges."""
        return self.role in (TeamMemberRole.OWNER.value, TeamMemberRole.ADMIN.value)


class TeamInvitation(Base, TimestampMixin):
    """Team invitation model for inviting users to teams."""

    __tablename__ = "team_invitations"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Foreign keys
    team_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_by: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Invitee info
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(
        String(50), default=TeamMemberRole.EDITOR.value, nullable=False
    )

    # Invitation token (secure URL-safe token)
    token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: secrets.token_urlsafe(32),
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50), default=InvitationStatus.PENDING.value, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow() + timedelta(days=7),
        nullable=False,
    )

    # Acceptance tracking
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_by_user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Revocation tracking
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    team = relationship("Team", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[invited_by], lazy="joined")
    accepted_by = relationship(
        "User", foreign_keys=[accepted_by_user_id], lazy="joined"
    )
    revoker = relationship("User", foreign_keys=[revoked_by], lazy="joined")

    # Indexes
    # Note: team_id, invited_by, email, and token already have index=True on their column definitions
    # Only keep indexes for columns that don't have column-level index=True
    __table_args__ = (
        Index("ix_team_invitations_status", "status"),
        Index("ix_team_invitations_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<TeamInvitation(id={self.id}, email={self.email}, team_id={self.team_id}, status={self.status})>"

    @property
    def is_pending(self) -> bool:
        """Check if invitation is pending."""
        return self.status == InvitationStatus.PENDING.value

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        if self.status == InvitationStatus.EXPIRED.value:
            return True
        return datetime.utcnow() > self.expires_at

    def can_accept(self) -> bool:
        """Check if invitation can be accepted."""
        return (
            self.status == InvitationStatus.PENDING.value
            and not self.is_expired
        )

    def can_resend(self) -> bool:
        """Check if invitation can be resent."""
        return self.status == InvitationStatus.PENDING.value
