"""
Project and multi-tenancy API schemas.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# Project Role Enum (matches database enum)
class ProjectRole(str):
    """Project member role options."""

    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


# Invitation Status Enum
class InvitationStatus(str):
    """Project invitation status options."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVOKED = "revoked"


# =============================================================================
# Project Schemas
# =============================================================================


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    slug: str | None = Field(
        None,
        min_length=3,
        max_length=100,
        description="URL-friendly project identifier (auto-generated if not provided)",
    )
    description: str | None = Field(None, max_length=500, description="Project description")
    logo_url: str | None = Field(None, max_length=500, description="Project logo URL")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        """Validate slug format (lowercase alphanumeric with hyphens)."""
        if v is None:
            return v
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Slug cannot start or end with a hyphen")
        if "--" in v:
            raise ValueError("Slug cannot contain consecutive hyphens")
        return v


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    logo_url: str | None = Field(None, max_length=500)
    settings: dict | None = Field(None, description="Project settings JSON")


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: str
    name: str
    slug: str
    description: str | None = None
    avatar_url: str | None = None
    logo_url: str | None = None  # Alias for avatar_url (frontend compatibility)

    is_personal: bool = False

    # Billing
    subscription_tier: str
    subscription_status: str
    lemonsqueezy_customer_id: str | None = None
    lemonsqueezy_subscription_id: str | None = None

    # Usage tracking
    articles_generated_this_month: int = 0
    outlines_generated_this_month: int = 0
    images_generated_this_month: int = 0
    usage_reset_date: datetime | None = None
    max_members: int = 5

    # Metadata
    owner_id: str
    created_at: datetime
    updated_at: datetime | None = None

    # Member info (only when requested)
    member_count: int | None = None
    current_user_role: str | None = None
    my_role: str | None = None  # Alias for current_user_role (frontend compatibility)

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    """Paginated list of projects."""

    projects: list[ProjectResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# =============================================================================
# Project Member Schemas
# =============================================================================


class ProjectMemberAdd(BaseModel):
    """Schema for adding a member to a project (used internally after invitation accepted)."""

    user_id: str
    role: str = Field(default="editor", description="Project role")


class ProjectMemberUpdate(BaseModel):
    """Schema for updating a project member's role."""

    role: str = Field(..., description="New project role (owner, admin, editor, viewer)")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is valid."""
        valid_roles = ["owner", "admin", "editor", "viewer"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class ProjectMemberResponse(BaseModel):
    """Schema for project member response."""

    id: str
    project_id: str
    user_id: str
    role: str
    joined_at: datetime
    invited_by_id: str | None = None

    # User info (joined from users table)
    user_email: str | None = None
    user_name: str | None = None
    user_avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectMemberListResponse(BaseModel):
    """List of project members."""

    members: list[ProjectMemberResponse]
    total: int


# =============================================================================
# Project Invitation Schemas
# =============================================================================


class ProjectInvitationCreate(BaseModel):
    """Schema for creating a project invitation."""

    email: EmailStr = Field(..., description="Email address to invite")
    role: str = Field(default="editor", description="Role to assign (owner, admin, editor, viewer)")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is valid."""
        valid_roles = ["owner", "admin", "editor", "viewer"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class ProjectInvitationResponse(BaseModel):
    """Schema for project invitation response."""

    id: str
    project_id: str
    email: str
    role: str
    token: str
    status: str
    invited_by_id: str
    expires_at: datetime
    accepted_at: datetime | None = None
    created_at: datetime

    # Project info (joined)
    project_name: str | None = None
    project_slug: str | None = None

    # Inviter info (joined)
    inviter_name: str | None = None
    inviter_email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectInvitationListResponse(BaseModel):
    """List of project invitations."""

    invitations: list[ProjectInvitationResponse]
    total: int


class ProjectInvitationAccept(BaseModel):
    """Schema for accepting a project invitation."""

    token: str = Field(..., description="Invitation token from email")


class ProjectInvitationPublicResponse(BaseModel):
    """Public invitation details (no authentication required)."""

    project_name: str
    project_slug: str
    project_logo_url: str | None = None
    inviter_name: str
    role: str
    expires_at: datetime
    is_expired: bool
    is_already_member: bool = False


class ProjectInvitationAcceptResponse(BaseModel):
    """Response after accepting an invitation."""

    success: bool
    project_id: str
    project_name: str
    redirect_url: str | None = None  # For unauthenticated users needing to register/login


# =============================================================================
# Project Statistics & Info
# =============================================================================


class ProjectStats(BaseModel):
    """Project usage statistics."""

    articles_generated: int
    outlines_generated: int
    images_generated: int
    usage_reset_date: datetime | None = None

    # Limits based on subscription tier
    articles_limit: int
    outlines_limit: int
    images_limit: int

    # Calculated percentages
    articles_used_percent: float
    outlines_used_percent: float
    images_used_percent: float


class ProjectSettings(BaseModel):
    """Project settings schema."""

    branding: dict | None = Field(
        None,
        description="Branding settings (primary_color, logo_url)",
    )
    content: dict | None = Field(
        None,
        description="Content defaults (default_tone, default_language)",
    )
    integrations: dict | None = Field(
        None,
        description="Integration settings (wordpress, gsc, etc)",
    )


# =============================================================================
# Project Switching
# =============================================================================


class ProjectSwitchRequest(BaseModel):
    """Schema for switching current project."""

    project_id: str | None = Field(
        None, description="Project ID to switch to, or null for personal workspace"
    )


class ProjectSwitchResponse(BaseModel):
    """Response after switching projects."""

    current_project_id: str | None = None
    message: str | None = None
    project_name: str | None = None
    project_slug: str | None = None
    user_role: str | None = None


# Aliases for route compatibility
SwitchProjectRequest = ProjectSwitchRequest
SwitchProjectResponse = ProjectSwitchResponse
ProjectMembersListResponse = ProjectMemberListResponse


class ProjectWithMemberRoleResponse(BaseModel):
    """Project response including the current user's role."""

    id: str
    name: str
    slug: str
    avatar_url: str | None = None
    description: str | None = None
    created_at: datetime
    subscription_tier: str = "free"
    user_role: str  # Current user's role in this project


class ProjectDetailResponse(BaseModel):
    """Detailed project response with stats and members."""

    id: str
    name: str
    slug: str
    avatar_url: str | None = None
    description: str | None = None
    owner_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    is_personal: bool = False
    subscription_tier: str = "free"
    subscription_status: str = "active"
    subscription_expires: datetime | None = None
    max_members: int = 5
    member_count: int = 0
    current_user_role: str | None = None  # Current user's role
    members: list | None = None


class ProjectDeleteResponse(BaseModel):
    """Response after deleting a project."""

    success: bool = True
    message: str
    project_id: str | None = None


class CurrentProjectResponse(BaseModel):
    """Response for current active project."""

    project: Optional["ProjectResponse"] = None
    is_personal_workspace: bool = True
    # Legacy flat fields (kept for backward compatibility)
    project_id: str | None = None
    project_name: str | None = None
    project_slug: str | None = None
    user_role: str | None = None


class AddMemberRequest(BaseModel):
    """Request to add a member to project (via invitation or direct)."""

    email: str = Field(..., description="Email of user to add")
    role: str = Field("editor", description="Role to assign")


class AddMemberResponse(BaseModel):
    """Response after adding a member."""

    success: bool
    message: str
    invitation_sent: bool = False
    member: ProjectMemberResponse | None = None


class UpdateMemberRoleRequest(BaseModel):
    """Request to update a project member's role."""

    role: str = Field(..., description="New role")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = ["owner", "admin", "editor", "viewer"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class UpdateMemberRoleResponse(BaseModel):
    """Response after updating member role."""

    success: bool
    message: str
    member: ProjectMemberResponse


class RemoveMemberResponse(BaseModel):
    """Response after removing a member from project."""

    success: bool
    message: str


class LeaveProjectResponse(BaseModel):
    """Response after leaving a project."""

    success: bool
    message: str


class TransferOwnershipRequest(BaseModel):
    """Request to transfer project ownership."""

    new_owner_id: str = Field(..., description="User ID of new owner")


class TransferOwnershipResponse(BaseModel):
    """Response after transferring ownership."""

    success: bool
    message: str
    new_owner_id: str
    previous_owner_role: str = "admin"


# =============================================================================
# Brand Voice Schemas
# =============================================================================


class BrandVoiceSettings(BaseModel):
    """Brand voice settings for a project."""

    tone: str | None = Field(
        None, description="Tone of voice (e.g., professional, casual, authoritative)"
    )
    writing_style: str | None = Field(
        None, description="Writing style (e.g., informative, conversational, persuasive)"
    )
    target_audience: str | None = Field(None, description="Target audience description")
    custom_instructions: str | None = Field(
        None, max_length=500, description="Free-text custom instructions for AI generation"
    )
    language: str | None = Field(None, description="Default language code (e.g., en, es, de)")
