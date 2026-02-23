"""
Billing and subscription API routes.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import get_db
from infrastructure.database.models.user import User, SubscriptionTier
from infrastructure.config.settings import settings
from api.schemas.billing import (
    PlanInfo,
    PlanLimits,
    PricingResponse,
    SubscriptionStatus,
    CheckoutRequest,
    CheckoutResponse,
    CustomerPortalResponse,
    SubscriptionCancelResponse,
    WebhookEventType,
)
from api.routes.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# Plan configuration with features and limits
PLANS = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "features": [
            "5 articles per month",
            "10 outlines per month",
            "2 images per month",
            "Basic SEO analysis",
            "Community support",
        ],
        "limits": {
            "articles_per_month": 5,
            "outlines_per_month": 10,
            "images_per_month": 2,
        },
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 29,
        "price_yearly": 290,  # ~17% discount
        "features": [
            "25 articles per month",
            "50 outlines per month",
            "10 images per month",
            "Advanced SEO analysis",
            "WordPress integration",
            "Priority email support",
        ],
        "limits": {
            "articles_per_month": 25,
            "outlines_per_month": 50,
            "images_per_month": 10,
        },
    },
    "professional": {
        "name": "Professional",
        "price_monthly": 79,
        "price_yearly": 790,  # ~17% discount
        "features": [
            "100 articles per month",
            "200 outlines per month",
            "50 images per month",
            "Google Search Console integration",
            "Advanced analytics",
            "API access",
            "Priority support",
        ],
        "limits": {
            "articles_per_month": 100,
            "outlines_per_month": 200,
            "images_per_month": 50,
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 199,
        "price_yearly": 1990,  # ~17% discount
        "features": [
            "Unlimited articles",
            "Unlimited outlines",
            "Unlimited images",
            "All integrations",
            "Advanced analytics",
            "API access",
            "Dedicated support",
            "Custom integrations",
            "SLA guarantee",
        ],
        "limits": {
            "articles_per_month": -1,  # -1 = unlimited
            "outlines_per_month": -1,
            "images_per_month": -1,
        },
    },
}


def get_variant_id(plan: str, billing_cycle: str) -> str:
    """Get LemonSqueezy variant ID for a plan and billing cycle."""
    variant_key = f"lemonsqueezy_variant_{plan}_{billing_cycle}"
    variant_id = getattr(settings, variant_key, None)

    if not variant_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Variant not configured for {plan} {billing_cycle}",
        )

    return variant_id


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify LemonSqueezy webhook signature."""
    if not secret:
        logger.warning("LemonSqueezy webhook secret not configured")
        return False

    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


@router.get("/pricing", response_model=PricingResponse)
async def get_pricing():
    """
    Get available subscription plans and pricing.

    Public endpoint - no authentication required.
    """
    plans = []

    for plan_id, plan_data in PLANS.items():
        plans.append(
            PlanInfo(
                id=plan_id,
                name=plan_data["name"],
                price_monthly=plan_data["price_monthly"],
                price_yearly=plan_data["price_yearly"],
                features=plan_data["features"],
                limits=PlanLimits(**plan_data["limits"]),
            )
        )

    return PricingResponse(plans=plans)


@router.get("/subscription", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Get current user's subscription status and usage."""
    # Determine subscription status
    subscription_status = "none"

    if current_user.subscription_tier != SubscriptionTier.FREE.value:
        if current_user.lemonsqueezy_subscription_id:
            # Check if subscription has expired
            if current_user.subscription_expires:
                if current_user.subscription_expires > datetime.now(timezone.utc):
                    subscription_status = "active"
                else:
                    subscription_status = "expired"
            else:
                subscription_status = "active"

    return SubscriptionStatus(
        subscription_tier=current_user.subscription_tier,
        subscription_status=subscription_status,
        subscription_expires=current_user.subscription_expires,
        customer_id=current_user.lemonsqueezy_customer_id,
        subscription_id=current_user.lemonsqueezy_subscription_id,
        can_manage=current_user.lemonsqueezy_customer_id is not None,
        articles_generated_this_month=current_user.articles_generated_this_month,
        outlines_generated_this_month=current_user.outlines_generated_this_month,
        images_generated_this_month=current_user.images_generated_this_month,
        usage_reset_date=current_user.usage_reset_date,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Create a LemonSqueezy checkout session for plan upgrade.

    Returns a checkout URL where the user can complete payment.
    """
    # Validate plan
    if request.plan not in ["starter", "professional", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan. Must be one of: starter, professional, enterprise",
        )

    # Validate billing cycle
    if request.billing_cycle not in ["monthly", "yearly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid billing cycle. Must be 'monthly' or 'yearly'",
        )

    # Check LemonSqueezy configuration
    if not settings.lemonsqueezy_api_key or not settings.lemonsqueezy_store_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment system not configured",
        )

    # Get variant ID for the plan and billing cycle
    variant_id = get_variant_id(request.plan, request.billing_cycle)

    # Build checkout URL with query parameters
    # LemonSqueezy checkout format:
    # https://YOUR_STORE.lemonsqueezy.com/checkout/buy/{variant_id}?checkout[email]=...&checkout[custom][user_id]=...
    store_url = f"https://{settings.lemonsqueezy_store_id}.lemonsqueezy.com"
    checkout_url = (
        f"{store_url}/checkout/buy/{variant_id}"
        f"?checkout[email]={current_user.email}"
        f"&checkout[custom][user_id]={current_user.id}"
    )

    logger.info(
        f"Created checkout session for user {current_user.id}, "
        f"plan={request.plan}, billing_cycle={request.billing_cycle}"
    )

    return CheckoutResponse(checkout_url=checkout_url)


@router.get("/portal", response_model=CustomerPortalResponse)
async def get_customer_portal(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get LemonSqueezy customer portal URL for managing subscription.

    Only available if user has an active LemonSqueezy subscription.
    """
    if not current_user.lemonsqueezy_customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found",
        )

    if not settings.lemonsqueezy_store_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment system not configured",
        )

    # Build customer portal URL
    # Format: https://YOUR_STORE.lemonsqueezy.com/billing
    portal_url = f"https://{settings.lemonsqueezy_store_id}.lemonsqueezy.com/billing"

    logger.info(f"Generated customer portal URL for user {current_user.id}")

    return CustomerPortalResponse(portal_url=portal_url)


@router.post("/cancel", response_model=SubscriptionCancelResponse)
async def cancel_subscription(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel current subscription.

    The subscription will remain active until the end of the billing period,
    then revert to the free plan.
    """
    if not current_user.lemonsqueezy_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription to cancel",
        )

    # Note: Actual cancellation should be done via LemonSqueezy API
    # For now, we'll just mark it in our database
    # TODO: Implement LemonSqueezy API call to cancel subscription

    logger.info(f"Subscription cancellation requested for user {current_user.id}")

    return SubscriptionCancelResponse(
        success=True,
        message="Subscription will be cancelled at the end of the billing period. "
                "Please visit the customer portal to complete cancellation.",
    )


async def handle_project_subscription_webhook(
    db: AsyncSession,
    project_id: str,
    event_name: str,
    subscription_id: str,
    customer_id: str,
    variant_id: str,
    subscription_status: str,
    renews_at: str,
):
    """
    Handle LemonSqueezy webhook events for project subscriptions.

    Args:
        db: Database session
        project_id: Project ID from custom_data
        event_name: Webhook event type
        subscription_id: LemonSqueezy subscription ID
        customer_id: LemonSqueezy customer ID
        variant_id: LemonSqueezy variant ID
        subscription_status: Subscription status
        renews_at: Renewal date

    Returns:
        Response dictionary
    """
    from infrastructure.database.models.project import Project

    # Find project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        logger.error(f"Project {project_id} not found for webhook")
        return {"status": "error", "message": "Project not found"}

    # Determine subscription tier from variant_id
    tier = SubscriptionTier.FREE.value
    if variant_id:
        variant_str = str(variant_id)
        if variant_str in [
            settings.lemonsqueezy_variant_starter_monthly,
            settings.lemonsqueezy_variant_starter_yearly,
        ]:
            tier = SubscriptionTier.STARTER.value
        elif variant_str in [
            settings.lemonsqueezy_variant_professional_monthly,
            settings.lemonsqueezy_variant_professional_yearly,
        ]:
            tier = SubscriptionTier.PROFESSIONAL.value
        elif variant_str in [
            settings.lemonsqueezy_variant_enterprise_monthly,
            settings.lemonsqueezy_variant_enterprise_yearly,
        ]:
            tier = SubscriptionTier.ENTERPRISE.value

    # Handle different event types
    try:
        if event_name == WebhookEventType.SUBSCRIPTION_CREATED.value:
            # New project subscription
            project.subscription_tier = tier
            project.lemonsqueezy_customer_id = str(customer_id) if customer_id else None
            project.lemonsqueezy_subscription_id = str(subscription_id) if subscription_id else None

            if renews_at:
                project.subscription_expires = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))

            logger.info(f"Project subscription created: project_id={project_id}, tier={tier}")

        elif event_name == WebhookEventType.SUBSCRIPTION_UPDATED.value:
            # Project subscription updated
            project.subscription_tier = tier

            if renews_at:
                project.subscription_expires = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))

            if subscription_status in ["cancelled", "paused", "expired"]:
                logger.info(f"Project subscription {subscription_status}: project_id={project_id}, expires={renews_at}")
            else:
                logger.info(f"Project subscription updated: project_id={project_id}, tier={tier}, status={subscription_status}")

        elif event_name == WebhookEventType.SUBSCRIPTION_CANCELLED.value:
            # Project subscription cancelled - keep tier until expiration
            if renews_at:
                project.subscription_expires = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))

            logger.info(f"Project subscription cancelled: project_id={project_id}, expires={renews_at}")

        elif event_name == WebhookEventType.SUBSCRIPTION_EXPIRED.value:
            # Project subscription expired - downgrade to free
            project.subscription_tier = SubscriptionTier.FREE.value
            project.subscription_expires = None
            project.lemonsqueezy_subscription_id = None

            logger.info(f"Project subscription expired: project_id={project_id}, downgraded to free")

        elif event_name == WebhookEventType.SUBSCRIPTION_PAYMENT_SUCCESS.value:
            # Payment successful - update renewal date
            if renews_at:
                project.subscription_expires = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))

            logger.info(f"Project payment successful: project_id={project_id}, renews={renews_at}")

        elif event_name == WebhookEventType.SUBSCRIPTION_PAYMENT_FAILED.value:
            # Payment failed
            logger.warning(f"Project payment failed: project_id={project_id}")

        elif event_name == WebhookEventType.SUBSCRIPTION_RESUMED.value:
            # Project subscription resumed
            project.subscription_tier = tier

            if renews_at:
                project.subscription_expires = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))

            logger.info(f"Project subscription resumed: project_id={project_id}")

        elif event_name == WebhookEventType.SUBSCRIPTION_PAUSED.value:
            # Project subscription paused
            logger.info(f"Project subscription paused: project_id={project_id}")

        elif event_name == WebhookEventType.SUBSCRIPTION_UNPAUSED.value:
            # Project subscription unpaused
            project.subscription_tier = tier

            if renews_at:
                project.subscription_expires = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))

            logger.info(f"Project subscription unpaused: project_id={project_id}")

        else:
            logger.warning(f"Unknown webhook event type: {event_name}")

        # Commit changes
        await db.commit()
        await db.refresh(project)

        logger.info(f"Project webhook processed successfully: project_id={project_id}")

    except Exception as e:
        logger.error(f"Error processing project webhook: {str(e)}", exc_info=True)
        await db.rollback()

    # Always return 200 OK
    return {"status": "success"}


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    x_signature: Annotated[str | None, Header(alias="X-Signature")] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle LemonSqueezy webhook events.

    This endpoint receives notifications about subscription changes:
    - subscription_created: New subscription started
    - subscription_updated: Subscription plan or status changed
    - subscription_cancelled: Subscription cancelled
    - subscription_expired: Subscription ended
    - subscription_payment_success: Payment processed successfully
    - subscription_payment_failed: Payment failed
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify webhook signature
    if settings.lemonsqueezy_webhook_secret:
        if not x_signature:
            logger.warning("Webhook received without signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature",
            )

        if not verify_webhook_signature(body, x_signature, settings.lemonsqueezy_webhook_secret):
            logger.error("Invalid webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )
    else:
        logger.warning("Webhook signature verification skipped (secret not configured)")

    # Parse webhook payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        # Always return 200 to acknowledge receipt, even on errors
        return {"status": "error", "message": "Invalid JSON"}

    # Extract event info
    meta = payload.get("meta", {})
    event_name = meta.get("event_name")
    custom_data = meta.get("custom_data", {})
    user_id = custom_data.get("user_id")
    project_id = custom_data.get("project_id")  # Project subscription support

    data = payload.get("data", {})
    attributes = data.get("attributes", {})

    subscription_id = data.get("id")
    customer_id = attributes.get("customer_id")
    variant_id = attributes.get("variant_id")
    subscription_status = attributes.get("status")
    renews_at = attributes.get("renews_at")

    logger.info(
        f"Webhook received: event={event_name}, user_id={user_id}, "
        f"project_id={project_id}, subscription_id={subscription_id}, status={subscription_status}"
    )

    # Handle project subscription vs user subscription
    if project_id:
        # Project subscription - delegate to project webhook handler
        return await handle_project_subscription_webhook(
            db=db,
            project_id=project_id,
            event_name=event_name,
            subscription_id=subscription_id,
            customer_id=customer_id,
            variant_id=variant_id,
            subscription_status=subscription_status,
            renews_at=renews_at,
        )

    # User subscription (original behavior)
    # Find user
    if not user_id:
        logger.error("No user_id in webhook custom_data")
        return {"status": "error", "message": "Missing user_id"}

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.error(f"User {user_id} not found for webhook")
        return {"status": "error", "message": "User not found"}

    # Determine subscription tier from variant_id
    tier = SubscriptionTier.FREE.value
    if variant_id:
        variant_str = str(variant_id)
        if variant_str in [
            settings.lemonsqueezy_variant_starter_monthly,
            settings.lemonsqueezy_variant_starter_yearly,
        ]:
            tier = SubscriptionTier.STARTER.value
        elif variant_str in [
            settings.lemonsqueezy_variant_professional_monthly,
            settings.lemonsqueezy_variant_professional_yearly,
        ]:
            tier = SubscriptionTier.PROFESSIONAL.value
        elif variant_str in [
            settings.lemonsqueezy_variant_enterprise_monthly,
            settings.lemonsqueezy_variant_enterprise_yearly,
        ]:
            tier = SubscriptionTier.ENTERPRISE.value

    # Handle different event types
    try:
        if event_name == WebhookEventType.SUBSCRIPTION_CREATED.value:
            # New subscription
            user.subscription_tier = tier
            user.lemonsqueezy_customer_id = str(customer_id) if customer_id else None
            user.lemonsqueezy_subscription_id = str(subscription_id) if subscription_id else None

            if renews_at:
                user.subscription_expires = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))

            logger.info(f"Subscription created for user {user_id}: tier={tier}")

        elif event_name == WebhookEventType.SUBSCRIPTION_UPDATED.value:
            # Subscription updated (plan change, status change, etc.)
            user.subscription_tier = tier

            if renews_at:
                user.subscription_expires = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))

            # If subscription is cancelled or paused, don't downgrade immediately
            # Let it expire naturally
            if subscription_status in ["cancelled", "paused", "expired"]:
                logger.info(f"Subscription {subscription_status} for user {user_id}, will expire at {renews_at}")
            else:
                logger.info(f"Subscription updated for user {user_id}: tier={tier}, status={subscription_status}")

        elif event_name == WebhookEventType.SUBSCRIPTION_CANCELLED.value:
            # Subscription cancelled - keep tier until expiration
            if renews_at:
                user.subscription_expires = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))

            logger.info(f"Subscription cancelled for user {user_id}, will expire at {renews_at}")

        elif event_name == WebhookEventType.SUBSCRIPTION_EXPIRED.value:
            # Subscription expired - downgrade to free
            user.subscription_tier = SubscriptionTier.FREE.value
            user.subscription_expires = None
            user.lemonsqueezy_subscription_id = None

            logger.info(f"Subscription expired for user {user_id}, downgraded to free")

        elif event_name == WebhookEventType.SUBSCRIPTION_PAYMENT_SUCCESS.value:
            # Payment successful - update renewal date
            if renews_at:
                user.subscription_expires = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))

            logger.info(f"Payment successful for user {user_id}, renews at {renews_at}")

        elif event_name == WebhookEventType.SUBSCRIPTION_PAYMENT_FAILED.value:
            # Payment failed - don't downgrade yet, let LemonSqueezy retry
            logger.warning(f"Payment failed for user {user_id}")

        elif event_name == WebhookEventType.SUBSCRIPTION_RESUMED.value:
            # Subscription resumed
            user.subscription_tier = tier

            if renews_at:
                user.subscription_expires = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))

            logger.info(f"Subscription resumed for user {user_id}")

        elif event_name == WebhookEventType.SUBSCRIPTION_PAUSED.value:
            # Subscription paused - keep tier until expiration
            logger.info(f"Subscription paused for user {user_id}")

        elif event_name == WebhookEventType.SUBSCRIPTION_UNPAUSED.value:
            # Subscription unpaused
            user.subscription_tier = tier

            if renews_at:
                user.subscription_expires = datetime.fromisoformat(renews_at.replace("Z", "+00:00"))

            logger.info(f"Subscription unpaused for user {user_id}")

        else:
            logger.warning(f"Unknown webhook event type: {event_name}")

        # Commit changes
        await db.commit()
        await db.refresh(user)

        logger.info(f"Webhook processed successfully for user {user_id}")

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        await db.rollback()
        # Still return 200 to prevent retries

    # Always return 200 OK to acknowledge receipt
    return {"status": "success"}
