"""
Billing and subscription API routes.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from urllib.parse import urlencode

VALID_SUBSCRIPTION_STATUSES = {"active", "cancelled", "paused", "expired", "past_due", "unpaid", "on_trial"}

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import get_db
from infrastructure.database.models.user import User, SubscriptionTier
from infrastructure.database.models.project import Project
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
from api.middleware.rate_limit import limiter
from core.plans import PLANS

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

# BILL-34: single canonical variant_id → tier mapping used by both user and project webhook handlers
# Built lazily at call time so settings values are resolved after app startup.
def _build_variant_to_tier() -> dict:
    return {
        str(v): tier
        for tier, keys in [
            (SubscriptionTier.STARTER.value, [
                settings.lemonsqueezy_variant_starter_monthly,
                settings.lemonsqueezy_variant_starter_yearly,
            ]),
            (SubscriptionTier.PROFESSIONAL.value, [
                settings.lemonsqueezy_variant_professional_monthly,
                settings.lemonsqueezy_variant_professional_yearly,
            ]),
            (SubscriptionTier.ENTERPRISE.value, [
                settings.lemonsqueezy_variant_enterprise_monthly,
                settings.lemonsqueezy_variant_enterprise_yearly,
            ]),
        ]
        for v in keys
        if v is not None
    }


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    """Parse ISO 8601 datetime string, handling Z suffix and invalid formats.

    Returns None on failure so callers don't accidentally set an immediate
    expiry date when the webhook payload contains a malformed timestamp.
    """
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # BILL-29: Reject past timestamps — setting subscription_expires to a past date
        # would immediately revoke access. A 5-minute grace window absorbs clock skew.
        if parsed < datetime.now(timezone.utc) - timedelta(minutes=5):
            logger.warning(
                "Webhook datetime %s is in the past — skipping to avoid immediate revocation", parsed
            )
            return None
        return parsed
    except (ValueError, AttributeError) as e:
        logger.warning("Failed to parse datetime '%s': %s — skipping expiry update", value, e)
        return None


def get_variant_id(plan: str, billing_cycle: str) -> str:
    """Get LemonSqueezy variant ID for a plan and billing cycle."""
    variant_key = f"lemonsqueezy_variant_{plan}_{billing_cycle}"
    variant_id = getattr(settings, variant_key, None)

    if not variant_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
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
        social_posts_generated_this_month=current_user.social_posts_generated_this_month,
        usage_reset_date=current_user.usage_reset_date,
    )


@router.post("/checkout", response_model=CheckoutResponse)
@limiter.limit("5/minute")
async def create_checkout(
    request: Request,
    body: CheckoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Create a LemonSqueezy checkout session for plan upgrade.

    Returns a checkout URL where the user can complete payment.
    """
    # Validate plan
    if body.plan not in ["starter", "professional", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan. Must be one of: starter, professional, enterprise",
        )

    # Validate billing cycle
    if body.billing_cycle not in ["monthly", "yearly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid billing cycle. Must be 'monthly' or 'yearly'",
        )

    # Check LemonSqueezy configuration
    if not settings.lemonsqueezy_api_key or not settings.lemonsqueezy_store_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system not configured",
        )

    # Get variant ID for the plan and billing cycle
    variant_id = get_variant_id(body.plan, body.billing_cycle)

    # Build checkout URL using the store slug
    store_slug = settings.lemonsqueezy_store_slug or settings.lemonsqueezy_store_id
    if not store_slug:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system not configured",
        )
    frontend_url = settings.frontend_url.rstrip("/")
    params = urlencode({
        "checkout[email]": current_user.email,
        "checkout[custom][user_id]": str(current_user.id),
        "checkout[redirect_url]": f"{frontend_url}/billing/success",
    })
    checkout_url = f"https://{store_slug}.lemonsqueezy.com/checkout/buy/{variant_id}?{params}"

    logger.info(
        f"Created checkout session for user {current_user.id}, "
        f"plan={body.plan}, billing_cycle={body.billing_cycle}"
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
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system not configured",
        )

    # Build customer portal URL
    # Format: https://YOUR_STORE.lemonsqueezy.com/billing
    portal_url = f"https://{settings.lemonsqueezy_store_id}.lemonsqueezy.com/billing"

    logger.info(f"Generated customer portal URL for user {current_user.id}")

    return CustomerPortalResponse(portal_url=portal_url)


@router.post("/cancel", response_model=SubscriptionCancelResponse)
@limiter.limit("5/minute")
async def cancel_subscription(
    request: Request,
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

    # BILL-25: Prevent redundant cancellation API calls for already-terminated subscriptions
    if current_user.subscription_status in ("cancelled", "expired"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is already cancelled or expired",
        )

    logger.info(f"Subscription cancellation requested for user {current_user.id}")

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"https://api.lemonsqueezy.com/v1/subscriptions/{current_user.lemonsqueezy_subscription_id}",
            headers={
                "Authorization": f"Bearer {settings.lemonsqueezy_api_key}",
                "Accept": "application/vnd.api+json",
            },
        )
        if response.status_code not in (200, 204):
            logger.error(
                "LemonSqueezy cancel failed: %s %s",
                response.status_code,
                response.text,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel subscription. Please try again or contact support.",
            )

    return SubscriptionCancelResponse(
        success=True,
        message="Subscription will be cancelled at the end of the billing period.",
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

    # Find project — BILL-18: row-level lock prevents concurrent webhook updates from racing
    result = await db.execute(select(Project).where(Project.id == project_id).with_for_update())
    project = result.scalar_one_or_none()

    if not project:
        logger.error(f"Project {project_id} not found for webhook")
        return {"status": "error", "message": "Project not found"}

    # BILL-34: Determine subscription tier from variant_id using shared mapping
    tier = SubscriptionTier.FREE.value
    if variant_id:
        variant_to_tier = _build_variant_to_tier()
        tier = variant_to_tier.get(str(variant_id), SubscriptionTier.FREE.value)
        if tier == SubscriptionTier.FREE.value and str(variant_id) not in variant_to_tier:
            # BILL-22: variant_id didn't match any known tier — defaulting to free
            logger.warning(
                "BILL-22: variant_id %s did not match any known tier — defaulting to free",
                variant_id,
            )

    # Handle different event types
    try:
        if event_name == WebhookEventType.SUBSCRIPTION_CREATED.value:
            # New project subscription
            project.subscription_tier = tier
            project.subscription_status = subscription_status or "active"  # BILL-08
            project.lemonsqueezy_customer_id = str(customer_id) if customer_id else None
            # BILL-28: only overwrite subscription_id when webhook provides one
            if subscription_id is not None:
                project.lemonsqueezy_subscription_id = str(subscription_id)
            project.lemonsqueezy_variant_id = str(variant_id) if variant_id else None  # BILL-07

            if renews_at:
                project.subscription_expires = _parse_iso_datetime(renews_at)

            logger.info(f"Project subscription created: project_id={project_id}, tier={tier}")

        elif event_name == WebhookEventType.SUBSCRIPTION_UPDATED.value:
            # Project subscription updated
            project.subscription_tier = tier
            project.subscription_status = subscription_status or "active"  # BILL-08
            project.lemonsqueezy_variant_id = str(variant_id) if variant_id else None  # BILL-07

            if renews_at:
                project.subscription_expires = _parse_iso_datetime(renews_at)

            if subscription_status in ["cancelled", "paused", "expired"]:
                logger.info(f"Project subscription {subscription_status}: project_id={project_id}, expires={renews_at}")
            else:
                logger.info(f"Project subscription updated: project_id={project_id}, tier={tier}, status={subscription_status}")

        elif event_name == WebhookEventType.SUBSCRIPTION_CANCELLED.value:
            # BILL-04: Revoke features immediately on cancellation rather than waiting
            # for the billing period to end. subscription_expires = now() means
            # BILL-01's expiry check in check_limit() will immediately treat them as free.
            project.subscription_expires = datetime.now(timezone.utc)
            project.subscription_status = "cancelled"  # BILL-27
            logger.info(f"Project subscription cancelled: project_id={project_id}, access revoked immediately")

        elif event_name == WebhookEventType.SUBSCRIPTION_EXPIRED.value:
            # Project subscription expired - downgrade to free
            project.subscription_tier = SubscriptionTier.FREE.value
            project.subscription_status = "expired"  # BILL-08
            project.subscription_expires = None
            project.lemonsqueezy_subscription_id = None
            project.lemonsqueezy_variant_id = None  # BILL-07

            logger.info(f"Project subscription expired: project_id={project_id}, downgraded to free")

        elif event_name == WebhookEventType.SUBSCRIPTION_PAYMENT_SUCCESS.value:
            # Payment successful - update renewal date
            if renews_at:
                project.subscription_expires = _parse_iso_datetime(renews_at)

            logger.info(f"Project payment successful: project_id={project_id}, renews={renews_at}")

        elif event_name == WebhookEventType.SUBSCRIPTION_PAYMENT_FAILED.value:
            # Payment failed
            logger.warning(f"Project payment failed: project_id={project_id}")

        elif event_name == WebhookEventType.SUBSCRIPTION_RESUMED.value:
            # Project subscription resumed
            project.subscription_tier = tier

            if renews_at:
                project.subscription_expires = _parse_iso_datetime(renews_at)

            logger.info(f"Project subscription resumed: project_id={project_id}")

        elif event_name == WebhookEventType.SUBSCRIPTION_PAUSED.value:
            # Project subscription paused
            logger.info(f"Project subscription paused: project_id={project_id}")

        elif event_name == WebhookEventType.SUBSCRIPTION_UNPAUSED.value:
            # Project subscription unpaused
            project.subscription_tier = tier

            if renews_at:
                project.subscription_expires = _parse_iso_datetime(renews_at)

            logger.info(f"Project subscription unpaused: project_id={project_id}")

        else:
            logger.warning(f"Unknown webhook event type: {event_name}")

        # Commit changes
        await db.commit()
        await db.refresh(project)

        logger.info(f"Project webhook processed successfully: project_id={project_id}")

    except Exception as e:
        logger.error("Webhook processing failed for project %s: %s", project_id, str(e), exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Webhook processing failed")


@router.post("/webhook")
@limiter.limit("100/minute")  # BILL-26: webhooks can fire fast from LemonSqueezy
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
        # BILL-06: Return 403 (not 503) when secret is unconfigured — prevents aggressive LS retries.
        logger.error("Webhook rejected: LEMONSQUEEZY_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Webhook verification not configured")

    # Parse webhook payload
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Invalid JSON in webhook payload: %s", e)
        # BILL-05: Return 400 so LemonSqueezy stops retrying a malformed payload.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook payload: {e}")

    # Idempotency: deduplicate webhook events using Redis (24h TTL covers LemonSqueezy retry window)
    meta = payload.get("meta", {})
    event_id = meta.get("event_id") or payload.get("id")
    if event_id:
        try:
            import redis.asyncio as aioredis
            from infrastructure.config.settings import settings as _settings
            r = aioredis.from_url(_settings.redis_url)
            redis_key = f"webhook:processed:{event_id}"
            already_processed = await r.exists(redis_key)
            if not already_processed:
                await r.setex(redis_key, 86400, "1")  # 24h TTL
            await r.aclose()
            if already_processed:
                logger.info("Duplicate webhook event %s — skipping", event_id)
                return {"status": "ok", "message": "already processed"}
        except Exception as redis_err:
            logger.warning("Webhook idempotency check unavailable (Redis error): %s", redis_err)
            # BILL-19: Proceed without idempotency check — acceptable degradation

    # Extract event info
    event_name = meta.get("event_name")
    custom_data = meta.get("custom_data", {}) or {}
    user_id = custom_data.get("user_id")
    project_id = custom_data.get("project_id")  # Project subscription support

    if not event_name:
        logger.error("Webhook payload missing event_name in meta")
        return {"status": "error", "message": "Missing event_name"}

    data = payload.get("data", {})
    attributes = data.get("attributes", {})

    subscription_id = data.get("id")
    customer_id = attributes.get("customer_id")
    variant_id = attributes.get("variant_id")
    subscription_status = attributes.get("status")
    renews_at = attributes.get("renews_at")

    # BILL-21: Validate subscription_status from webhook payload
    if subscription_status and subscription_status not in VALID_SUBSCRIPTION_STATUSES:
        logger.warning("Unknown subscription_status from webhook: %s", subscription_status)
        subscription_status = "active"  # safe default, webhook event type drives logic

    # BILL-24: Reject paid events that are missing subscription_id to avoid corrupting records
    if event_name in ("subscription_created", "order_created") and not subscription_id:
        logger.warning("Webhook %s missing subscription_id, ignoring", event_name)
        return {"status": "ok"}

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

    # BILL-11: Reject malformed user_id before hitting the DB
    import uuid as _uuid
    try:
        _uuid.UUID(str(user_id))
    except (ValueError, AttributeError):
        logger.error("BILL-11: Invalid user_id format in webhook payload: %r", user_id)
        return {"status": "error", "message": "Invalid user_id"}

    # BILL-09: row-level lock prevents concurrent webhook updates from racing
    result = await db.execute(select(User).where(User.id == user_id).with_for_update())
    user = result.scalar_one_or_none()

    if not user:
        logger.error(f"User {user_id} not found for webhook")
        return {"status": "error", "message": "User not found"}

    # BILL-02: Validate customer_id in webhook matches the one stored on the user.
    # Prevents an attacker who knows another user's user_id from spoofing events
    # by crafting a webhook with their customer_id but a victim's user_id.
    if customer_id and user.lemonsqueezy_customer_id:
        if str(user.lemonsqueezy_customer_id) != str(customer_id):
            logger.error(
                "BILL-02: Webhook customer_id %s does not match stored customer_id %s for user %s — rejecting",
                customer_id, user.lemonsqueezy_customer_id, user_id,
            )
            return {"status": "error", "message": "Customer ID mismatch"}

    # BILL-34: Determine subscription tier from variant_id using shared mapping
    tier = SubscriptionTier.FREE.value
    if variant_id:
        variant_to_tier = _build_variant_to_tier()
        tier = variant_to_tier.get(str(variant_id), SubscriptionTier.FREE.value)
        if tier == SubscriptionTier.FREE.value and str(variant_id) not in variant_to_tier:
            # BILL-22: variant_id didn't match any known tier — defaulting to free
            logger.warning(
                "BILL-22: variant_id %s did not match any known tier — defaulting to free",
                variant_id,
            )

    # Handle different event types
    try:
        if event_name == WebhookEventType.SUBSCRIPTION_CREATED.value:
            # New subscription
            user.subscription_tier = tier
            user.subscription_status = subscription_status or "active"  # BILL-08
            user.lemonsqueezy_customer_id = str(customer_id) if customer_id else None
            # BILL-28: only overwrite subscription_id when webhook provides one
            if subscription_id is not None:
                user.lemonsqueezy_subscription_id = str(subscription_id)
            user.lemonsqueezy_variant_id = str(variant_id) if variant_id else None  # BILL-36

            if renews_at:
                user.subscription_expires = _parse_iso_datetime(renews_at)

            logger.info(f"Subscription created for user {user_id}: tier={tier}")

        elif event_name == WebhookEventType.SUBSCRIPTION_UPDATED.value:
            # Subscription updated (plan change, status change, etc.)
            user.subscription_tier = tier
            user.subscription_status = subscription_status or "active"  # BILL-08
            user.lemonsqueezy_variant_id = str(variant_id) if variant_id else None  # BILL-36: keep variant_id in sync on plan changes

            if renews_at:
                user.subscription_expires = _parse_iso_datetime(renews_at)

            # If subscription is cancelled or paused, don't downgrade immediately
            # Let it expire naturally
            if subscription_status in ["cancelled", "paused", "expired"]:
                logger.info(f"Subscription {subscription_status} for user {user_id}, will expire at {renews_at}")
            else:
                logger.info(f"Subscription updated for user {user_id}: tier={tier}, status={subscription_status}")

        elif event_name == WebhookEventType.SUBSCRIPTION_CANCELLED.value:
            # BILL-04: Revoke features immediately on cancellation
            user.subscription_status = "cancelled"  # BILL-08
            user.subscription_expires = datetime.now(timezone.utc)
            logger.info(f"Subscription cancelled for user {user_id}, access revoked immediately")

        elif event_name == WebhookEventType.SUBSCRIPTION_EXPIRED.value:
            # Subscription expired - downgrade to free
            user.subscription_tier = SubscriptionTier.FREE.value
            user.subscription_status = "expired"  # BILL-08
            user.subscription_expires = None
            user.lemonsqueezy_subscription_id = None

            logger.info(f"Subscription expired for user {user_id}, downgraded to free")

        elif event_name == WebhookEventType.SUBSCRIPTION_PAYMENT_SUCCESS.value:
            # Payment successful - update renewal date
            if renews_at:
                user.subscription_expires = _parse_iso_datetime(renews_at)

            logger.info(f"Payment successful for user {user_id}, renews at {renews_at}")

        elif event_name == WebhookEventType.SUBSCRIPTION_PAYMENT_FAILED.value:
            # Payment failed - don't downgrade yet, let LemonSqueezy retry
            # BILL-33: structured log includes subscription_id for easier ops investigation
            logger.warning(
                "Payment failed for user %s (subscription %s)",
                user_id, subscription_id,
            )

        elif event_name == WebhookEventType.SUBSCRIPTION_RESUMED.value:
            # Subscription resumed
            user.subscription_tier = tier
            user.subscription_status = "active"  # BILL-08

            if renews_at:
                user.subscription_expires = _parse_iso_datetime(renews_at)

            logger.info(f"Subscription resumed for user {user_id}")

        elif event_name == WebhookEventType.SUBSCRIPTION_PAUSED.value:
            # Subscription paused - keep tier until expiration
            # BILL-33: structured log includes subscription_id for easier ops investigation
            logger.info(
                "Subscription paused for user %s (subscription %s)",
                user_id, subscription_id,
            )

        elif event_name == WebhookEventType.SUBSCRIPTION_UNPAUSED.value:
            # Subscription unpaused
            user.subscription_tier = tier

            if renews_at:
                user.subscription_expires = _parse_iso_datetime(renews_at)

            logger.info(f"Subscription unpaused for user {user_id}")

        else:
            logger.warning(f"Unknown webhook event type: {event_name}")

        # Sync subscription tier to user's personal project
        personal_project_result = await db.execute(
            select(Project).where(
                Project.owner_id == user.id,
                Project.is_personal == True,
            )
        )
        personal_project = personal_project_result.scalar_one_or_none()
        if personal_project:
            personal_project.subscription_tier = user.subscription_tier
            # BILL-27: propagate subscription_status so personal project stays in sync
            if hasattr(personal_project, "subscription_status"):
                personal_project.subscription_status = user.subscription_status
            # BILL-37: always mirror subscription_expires (including None) to avoid stale values
            personal_project.subscription_expires = user.subscription_expires
        else:
            # BILL-13/BILL-23: warn if personal project is missing so ops can investigate
            logger.warning(
                "BILL-23: Personal project not found for user %s (tier=%s) — subscription sync skipped. "
                "User and project tiers may diverge.",
                user_id, tier,
            )

        # Commit changes
        await db.commit()
        await db.refresh(user)

        logger.info(f"Webhook processed successfully for user {user_id}")

    except Exception as e:
        logger.error("Webhook processing failed: %s", str(e), exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Webhook processing failed")
