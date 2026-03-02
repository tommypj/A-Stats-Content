"""
Billing and subscription request/response schemas.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PlanLimits(BaseModel):
    """Usage limits for a subscription plan."""

    articles_per_month: int = Field(
        ..., description="Number of articles allowed per month (-1 for unlimited)"
    )
    outlines_per_month: int = Field(
        ..., description="Number of outlines allowed per month (-1 for unlimited)"
    )
    images_per_month: int = Field(
        ..., description="Number of images allowed per month (-1 for unlimited)"
    )
    social_posts_per_month: int = Field(
        ..., description="Number of social post sets allowed per month (-1 for unlimited)"
    )


class PlanInfo(BaseModel):
    """Information about a subscription plan."""

    id: str = Field(..., description="Plan ID (free, starter, professional, enterprise)")
    name: str = Field(..., description="Display name of the plan")
    price_monthly: float = Field(..., description="Monthly price in USD")
    price_yearly: float = Field(..., description="Yearly price in USD")
    features: list[str] = Field(..., description="List of features included in the plan")
    limits: PlanLimits = Field(..., description="Usage limits for the plan")


class PricingResponse(BaseModel):
    """Response containing all available pricing plans."""

    plans: list[PlanInfo] = Field(..., description="List of all available plans")


class SubscriptionStatus(BaseModel):
    """Current subscription status for a user."""

    subscription_tier: str = Field(..., description="Current subscription tier")
    subscription_status: str = Field(
        ..., description="Subscription status (active, cancelled, paused, past_due, expired, none)"
    )
    subscription_expires: datetime | None = Field(None, description="When the subscription expires")
    customer_id: str | None = Field(None, description="LemonSqueezy customer ID")
    subscription_id: str | None = Field(None, description="LemonSqueezy subscription ID")
    can_manage: bool = Field(..., description="Whether user can access customer portal")

    # Usage tracking
    articles_generated_this_month: int = Field(0, description="Articles generated this month")
    outlines_generated_this_month: int = Field(0, description="Outlines generated this month")
    images_generated_this_month: int = Field(0, description="Images generated this month")
    social_posts_generated_this_month: int = Field(
        0, description="Social post sets generated this month"
    )
    usage_reset_date: datetime | None = Field(None, description="When usage counters reset")


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""

    plan: str = Field(..., description="Plan ID (starter, professional, enterprise)")
    billing_cycle: str = Field(..., description="Billing cycle (monthly, yearly)")

    model_config = {
        "json_schema_extra": {"example": {"plan": "starter", "billing_cycle": "monthly"}}
    }


class CheckoutResponse(BaseModel):
    """Response containing checkout URL."""

    checkout_url: str = Field(..., description="URL to LemonSqueezy checkout page")


class CustomerPortalResponse(BaseModel):
    """Response containing customer portal URL."""

    portal_url: str = Field(..., description="URL to LemonSqueezy customer portal")


class WebhookEventType(StrEnum):
    """LemonSqueezy webhook event types."""

    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    SUBSCRIPTION_RESUMED = "subscription_resumed"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    SUBSCRIPTION_PAUSED = "subscription_paused"
    SUBSCRIPTION_UNPAUSED = "subscription_unpaused"
    SUBSCRIPTION_PAYMENT_SUCCESS = "subscription_payment_success"
    SUBSCRIPTION_PAYMENT_FAILED = "subscription_payment_failed"


class SubscriptionCancelResponse(BaseModel):
    """Response after cancelling subscription."""

    success: bool = Field(..., description="Whether cancellation was successful")
    message: str = Field(..., description="Status message")
