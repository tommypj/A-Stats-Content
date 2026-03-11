"""Notification preferences schemas."""

from pydantic import BaseModel


class NotificationPreferencesResponse(BaseModel):
    """Response schema for notification preferences."""

    email_generation_completed: bool
    email_generation_failed: bool
    email_usage_80_percent: bool
    email_usage_limit_reached: bool
    email_content_decay: bool
    email_weekly_digest: bool
    email_billing_alerts: bool
    email_product_updates: bool
    email_onboarding: bool
    email_conversion_tips: bool
    email_reengagement: bool

    model_config = {"from_attributes": True}


class NotificationPreferencesUpdate(BaseModel):
    """Update schema — all fields optional, only provided fields are updated."""

    email_generation_completed: bool | None = None
    email_generation_failed: bool | None = None
    email_usage_80_percent: bool | None = None
    email_usage_limit_reached: bool | None = None
    email_content_decay: bool | None = None
    email_weekly_digest: bool | None = None
    email_billing_alerts: bool | None = None
    email_product_updates: bool | None = None
    email_onboarding: bool | None = None
    email_conversion_tips: bool | None = None
    email_reengagement: bool | None = None
