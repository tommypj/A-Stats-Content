"""
Project billing schemas for multi-tenancy subscription management.

These schemas handle project-level subscriptions, usage tracking,
and billing operations.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ProjectLimits(BaseModel):
    """Project usage limits based on subscription tier."""

    articles_per_month: int = Field(..., description="Articles limit per month (-1 = unlimited)")
    outlines_per_month: int = Field(..., description="Outlines limit per month (-1 = unlimited)")
    images_per_month: int = Field(..., description="Images limit per month (-1 = unlimited)")
    social_posts_per_month: int = Field(..., description="Social post sets limit per month (-1 = unlimited)")
    max_members: int = Field(..., description="Maximum project members allowed")

    model_config = ConfigDict(from_attributes=True)


class ProjectUsageStats(BaseModel):
    """Current project usage statistics."""

    articles_used: int = Field(..., description="Articles generated this month")
    articles_limit: int = Field(..., description="Articles limit per month")
    outlines_used: int = Field(..., description="Outlines generated this month")
    outlines_limit: int = Field(..., description="Outlines limit per month")
    images_used: int = Field(..., description="Images generated this month")
    images_limit: int = Field(..., description="Images limit per month")
    social_posts_used: int = Field(..., description="Social post sets generated this month")
    social_posts_limit: int = Field(..., description="Social post sets limit per month")
    members_count: int = Field(..., description="Current number of project members")
    members_limit: int = Field(..., description="Maximum members allowed")
    usage_reset_date: Optional[datetime] = Field(None, description="Date when usage resets")

    model_config = ConfigDict(from_attributes=True)


class ProjectSubscriptionResponse(BaseModel):
    """Project subscription status response."""

    project_id: UUID = Field(..., description="Project ID")
    project_name: str = Field(..., description="Project name")
    subscription_tier: str = Field(..., description="Subscription tier (free, starter, professional, enterprise)")
    subscription_status: str = Field(..., description="Subscription status (active, cancelled, expired, past_due)")
    subscription_expires: Optional[datetime] = Field(None, description="Subscription expiration date")
    customer_id: Optional[str] = Field(None, description="LemonSqueezy customer ID")
    subscription_id: Optional[str] = Field(None, description="LemonSqueezy subscription ID")
    variant_id: Optional[str] = Field(None, description="LemonSqueezy variant ID")
    usage: ProjectUsageStats = Field(..., description="Current usage statistics")
    limits: ProjectLimits = Field(..., description="Usage limits for current tier")
    can_manage: bool = Field(..., description="Whether user can manage billing (OWNER role)")

    model_config = ConfigDict(from_attributes=True)


class ProjectCheckoutRequest(BaseModel):
    """Request to create project checkout session."""

    variant_id: str = Field(..., description="LemonSqueezy variant ID for the plan")

    model_config = ConfigDict(from_attributes=True)


class ProjectCheckoutResponse(BaseModel):
    """Response with project checkout URL."""

    checkout_url: str = Field(..., description="LemonSqueezy checkout URL")

    model_config = ConfigDict(from_attributes=True)


class ProjectPortalResponse(BaseModel):
    """Response with project billing portal URL."""

    portal_url: str = Field(..., description="LemonSqueezy customer portal URL")

    model_config = ConfigDict(from_attributes=True)


class ProjectCancelResponse(BaseModel):
    """Response for project subscription cancellation."""

    success: bool = Field(..., description="Whether cancellation was successful")
    message: str = Field(..., description="Status message")

    model_config = ConfigDict(from_attributes=True)


class ProjectUsageResponse(BaseModel):
    """Detailed project usage response."""

    project_id: UUID = Field(..., description="Project ID")
    project_name: str = Field(..., description="Project name")
    subscription_tier: str = Field(..., description="Current subscription tier")
    usage: ProjectUsageStats = Field(..., description="Current usage statistics")
    limits: ProjectLimits = Field(..., description="Usage limits for current tier")

    # Usage percentages for UI
    articles_usage_percent: float = Field(..., description="Percentage of articles used (0-100)")
    outlines_usage_percent: float = Field(..., description="Percentage of outlines used (0-100)")
    images_usage_percent: float = Field(..., description="Percentage of images used (0-100)")
    members_usage_percent: float = Field(..., description="Percentage of member slots used (0-100)")

    model_config = ConfigDict(from_attributes=True)
