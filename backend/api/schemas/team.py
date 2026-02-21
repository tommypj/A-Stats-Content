"""
Team and multi-tenancy API schemas.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import re


# Team Role Enum (matches database enum)
class TeamRole(str):
    """Team member role options."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# Invitation Status Enum
class InvitationStatus(str):
    """Team invitation status options."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVOKED = "revoked"


# =============================================================================
# Team Schemas
# =============================================================================


class TeamCreate(BaseModel):
    """Schema for creating a new team."""

    name: str = Field(..., min_length=1, max_length=100, description="Team name")
    slug: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        description="URL-friendly team identifier (auto-generated if not provided)",
    )
    description: Optional[str] = Field(None, max_length=500, description="Team description")
    logo_url: Optional[str] = Field(None, max_length=500, description="Team logo URL")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
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


class TeamUpdate(BaseModel):
    """Schema for updating a team."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    logo_url: Optional[str] = Field(None, max_length=500)
    settings: Optional[dict] = Field(None, description="Team settings JSON")


class TeamResponse(BaseModel):
    """Schema for team response."""

    id: str
    name: str
    slug: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None

    # Billing
    subscription_tier: str
    subscription_status: str
    lemonsqueezy_customer_id: Optional[str] = None
    lemonsqueezy_subscription_id: Optional[str] = None

    # Usage tracking
    articles_generated_this_month: int = 0
    outlines_generated_this_month: int = 0
    images_generated_this_month: int = 0
    usage_reset_date: Optional[datetime] = None
    max_members: int = 5

    # Metadata
    owner_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Member info (only when requested)
    member_count: Optional[int] = None
    current_user_role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TeamListResponse(BaseModel):
    """Paginated list of teams."""

    teams: List[TeamResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# =============================================================================
# Team Member Schemas
# =============================================================================


class TeamMemberAdd(BaseModel):
    """Schema for adding a member to a team (used internally after invitation accepted)."""

    user_id: str
    role: str = Field(default="member", description="Team role")


class TeamMemberUpdate(BaseModel):
    """Schema for updating a team member's role."""

    role: str = Field(..., description="New team role (owner, admin, member, viewer)")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is valid."""
        valid_roles = ["owner", "admin", "member", "viewer"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class TeamMemberResponse(BaseModel):
    """Schema for team member response."""

    id: str
    team_id: str
    user_id: str
    role: str
    joined_at: datetime
    invited_by_id: Optional[str] = None

    # User info (joined from users table)
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TeamMemberListResponse(BaseModel):
    """List of team members."""

    members: List[TeamMemberResponse]
    total: int


# =============================================================================
# Team Invitation Schemas
# =============================================================================


class TeamInvitationCreate(BaseModel):
    """Schema for creating a team invitation."""

    email: EmailStr = Field(..., description="Email address to invite")
    role: str = Field(default="member", description="Role to assign (owner, admin, member, viewer)")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is valid."""
        valid_roles = ["owner", "admin", "member", "viewer"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class TeamInvitationResponse(BaseModel):
    """Schema for team invitation response."""

    id: str
    team_id: str
    email: str
    role: str
    token: str
    status: str
    invited_by_id: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime

    # Team info (joined)
    team_name: Optional[str] = None
    team_slug: Optional[str] = None

    # Inviter info (joined)
    inviter_name: Optional[str] = None
    inviter_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TeamInvitationListResponse(BaseModel):
    """List of team invitations."""

    invitations: List[TeamInvitationResponse]
    total: int


class TeamInvitationAccept(BaseModel):
    """Schema for accepting a team invitation."""

    token: str = Field(..., description="Invitation token from email")


class TeamInvitationPublicResponse(BaseModel):
    """Public invitation details (no authentication required)."""

    team_name: str
    team_slug: str
    team_logo_url: Optional[str] = None
    inviter_name: str
    role: str
    expires_at: datetime
    is_expired: bool
    is_already_member: bool = False


class TeamInvitationAcceptResponse(BaseModel):
    """Response after accepting an invitation."""

    success: bool
    team_id: str
    team_name: str
    redirect_url: Optional[str] = None  # For unauthenticated users needing to register/login


# =============================================================================
# Team Statistics & Info
# =============================================================================


class TeamStats(BaseModel):
    """Team usage statistics."""

    articles_generated: int
    outlines_generated: int
    images_generated: int
    usage_reset_date: Optional[datetime] = None

    # Limits based on subscription tier
    articles_limit: int
    outlines_limit: int
    images_limit: int

    # Calculated percentages
    articles_used_percent: float
    outlines_used_percent: float
    images_used_percent: float


class TeamSettings(BaseModel):
    """Team settings schema."""

    branding: Optional[dict] = Field(
        None,
        description="Branding settings (primary_color, logo_url)",
    )
    content: Optional[dict] = Field(
        None,
        description="Content defaults (default_tone, default_language)",
    )
    integrations: Optional[dict] = Field(
        None,
        description="Integration settings (wordpress, gsc, etc)",
    )


# =============================================================================
# Team Switching
# =============================================================================


class TeamSwitchRequest(BaseModel):
    """Schema for switching current team."""

    team_id: str = Field(..., description="Team ID to switch to")


class TeamSwitchResponse(BaseModel):
    """Response after switching teams."""

    current_team_id: str
    message: Optional[str] = None
    team_name: Optional[str] = None
    team_slug: Optional[str] = None
    user_role: Optional[str] = None


# Aliases for route compatibility
SwitchTeamRequest = TeamSwitchRequest
SwitchTeamResponse = TeamSwitchResponse
TeamMembersListResponse = TeamMemberListResponse


class TeamWithMemberRoleResponse(BaseModel):
    """Team response including the current user's role."""

    id: str
    name: str
    slug: str
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    subscription_tier: str = "free"
    user_role: str  # Current user's role in this team


class TeamDetailResponse(BaseModel):
    """Detailed team response with stats and members."""

    id: str
    name: str
    slug: str
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    subscription_tier: str = "free"
    subscription_status: str = "active"
    subscription_expires: Optional[datetime] = None
    max_members: int = 5
    member_count: int = 0
    current_user_role: Optional[str] = None  # Current user's role
    members: Optional[list] = None


class TeamDeleteResponse(BaseModel):
    """Response after deleting a team."""

    success: bool = True
    message: str
    team_id: Optional[str] = None


class CurrentTeamResponse(BaseModel):
    """Response for current active team."""

    team: Optional["TeamResponse"] = None
    is_personal_workspace: bool = True
    # Legacy flat fields (kept for backward compatibility)
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    team_slug: Optional[str] = None
    user_role: Optional[str] = None


class AddMemberRequest(BaseModel):
    """Request to add a member to team (via invitation or direct)."""

    email: str = Field(..., description="Email of user to add")
    role: str = Field("editor", description="Role to assign")


class AddMemberResponse(BaseModel):
    """Response after adding a member."""

    success: bool
    message: str
    invitation_sent: bool = False
    member: Optional[TeamMemberResponse] = None


class UpdateMemberRoleRequest(BaseModel):
    """Request to update a team member's role."""

    role: str = Field(..., description="New role")


class UpdateMemberRoleResponse(BaseModel):
    """Response after updating member role."""

    success: bool
    message: str
    member: TeamMemberResponse


class RemoveMemberResponse(BaseModel):
    """Response after removing a member from team."""

    success: bool
    message: str


class LeaveTeamResponse(BaseModel):
    """Response after leaving a team."""

    success: bool
    message: str


class TransferOwnershipRequest(BaseModel):
    """Request to transfer team ownership."""

    new_owner_id: str = Field(..., description="User ID of new owner")


class TransferOwnershipResponse(BaseModel):
    """Response after transferring ownership."""

    success: bool
    message: str
    new_owner_id: str
    previous_owner_role: str = "admin"
