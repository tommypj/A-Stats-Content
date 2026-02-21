"""
Team billing schemas for multi-tenancy subscription management.

These schemas handle team-level subscriptions, usage tracking,
and billing operations.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class TeamLimits(BaseModel):
    """Team usage limits based on subscription tier."""

    articles_per_month: int = Field(..., description="Articles limit per month (-1 = unlimited)")
    outlines_per_month: int = Field(..., description="Outlines limit per month (-1 = unlimited)")
    images_per_month: int = Field(..., description="Images limit per month (-1 = unlimited)")
    max_members: int = Field(..., description="Maximum team members allowed")

    model_config = ConfigDict(from_attributes=True)


class TeamUsageStats(BaseModel):
    """Current team usage statistics."""

    articles_used: int = Field(..., description="Articles generated this month")
    articles_limit: int = Field(..., description="Articles limit per month")
    outlines_used: int = Field(..., description="Outlines generated this month")
    outlines_limit: int = Field(..., description="Outlines limit per month")
    images_used: int = Field(..., description="Images generated this month")
    images_limit: int = Field(..., description="Images limit per month")
    members_count: int = Field(..., description="Current number of team members")
    members_limit: int = Field(..., description="Maximum members allowed")
    usage_reset_date: Optional[datetime] = Field(None, description="Date when usage resets")

    model_config = ConfigDict(from_attributes=True)


class TeamSubscriptionResponse(BaseModel):
    """Team subscription status response."""

    team_id: UUID = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    subscription_tier: str = Field(..., description="Subscription tier (free, starter, professional, enterprise)")
    subscription_status: str = Field(..., description="Subscription status (active, cancelled, expired, past_due)")
    subscription_expires: Optional[datetime] = Field(None, description="Subscription expiration date")
    customer_id: Optional[str] = Field(None, description="LemonSqueezy customer ID")
    subscription_id: Optional[str] = Field(None, description="LemonSqueezy subscription ID")
    variant_id: Optional[str] = Field(None, description="LemonSqueezy variant ID")
    usage: TeamUsageStats = Field(..., description="Current usage statistics")
    limits: TeamLimits = Field(..., description="Usage limits for current tier")
    can_manage: bool = Field(..., description="Whether user can manage billing (OWNER role)")

    model_config = ConfigDict(from_attributes=True)


class TeamCheckoutRequest(BaseModel):
    """Request to create team checkout session."""

    variant_id: str = Field(..., description="LemonSqueezy variant ID for the plan")

    model_config = ConfigDict(from_attributes=True)


class TeamCheckoutResponse(BaseModel):
    """Response with team checkout URL."""

    checkout_url: str = Field(..., description="LemonSqueezy checkout URL")

    model_config = ConfigDict(from_attributes=True)


class TeamPortalResponse(BaseModel):
    """Response with team billing portal URL."""

    portal_url: str = Field(..., description="LemonSqueezy customer portal URL")

    model_config = ConfigDict(from_attributes=True)


class TeamCancelResponse(BaseModel):
    """Response for team subscription cancellation."""

    success: bool = Field(..., description="Whether cancellation was successful")
    message: str = Field(..., description="Status message")

    model_config = ConfigDict(from_attributes=True)


class TeamUsageResponse(BaseModel):
    """Detailed team usage response."""

    team_id: UUID = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    subscription_tier: str = Field(..., description="Current subscription tier")
    usage: TeamUsageStats = Field(..., description="Current usage statistics")
    limits: TeamLimits = Field(..., description="Usage limits for current tier")

    # Usage percentages for UI
    articles_usage_percent: float = Field(..., description="Percentage of articles used (0-100)")
    outlines_usage_percent: float = Field(..., description="Percentage of outlines used (0-100)")
    images_usage_percent: float = Field(..., description="Percentage of images used (0-100)")
    members_usage_percent: float = Field(..., description="Percentage of member slots used (0-100)")

    model_config = ConfigDict(from_attributes=True)
