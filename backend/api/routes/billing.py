"""
Billing and subscription API routes.
"""

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps_admin import get_current_admin_user
from api.middleware.rate_limit import limiter
from api.routes.auth import get_current_user
from adapters.payments.lemonsqueezy_adapter import LemonSqueezyAdapter, LemonSqueezyAPIError
from api.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    CustomerPortalResponse,
    PlanInfo,
    PlanLimits,
    PricingResponse,
    RefundResponse,
    SubscriptionCancelResponse,
    SubscriptionStatus,
    WebhookEventType,
)
from core.plans import PLANS
from infrastructure.config.settings import settings
from infrastructure.database.connection import get_db
from infrastructure.database.models.refund_blocked_email import RefundBlockedEmail
from infrastructure.database.models.user import SubscriptionTier, User

# Configure logging
logger = logging.getLogger(__name__)

VALID_SUBSCRIPTION_STATUSES = {
    "active",
    "cancelled",
    "paused",
    "expired",
    "past_due",
    "unpaid",
    "on_trial",
}

router = APIRouter(prefix="/billing", tags=["billing"])


# BILL-34: single canonical variant_id → tier mapping used by both user and project webhook handlers
# Built lazily at call time so settings values are resolved after app startup.
def _build_variant_to_tier() -> dict:
    return {
        str(v): tier
        for tier, keys in [
            (
                SubscriptionTier.STARTER.value,
                [
                    settings.lemonsqueezy_variant_starter_monthly,
                    settings.lemonsqueezy_variant_starter_yearly,
                ],
            ),
            (
                SubscriptionTier.PROFESSIONAL.value,
                [
                    settings.lemonsqueezy_variant_professional_monthly,
                    settings.lemonsqueezy_variant_professional_yearly,
                ],
            ),
            (
                SubscriptionTier.ENTERPRISE.value,
                [
                    settings.lemonsqueezy_variant_enterprise_monthly,
                    settings.lemonsqueezy_variant_enterprise_yearly,
                ],
            ),
        ]
        for v in keys
        if v is not None
    }


def _parse_iso_datetime(value: str) -> datetime | None:
    """Parse ISO 8601 datetime string, handling Z suffix and invalid formats.

    Returns None on failure so callers don't accidentally set an immediate
    expiry date when the webhook payload contains a malformed timestamp.
    """
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # BILL-29: Reject past timestamps — setting subscription_expires to a past date
        # would immediately revoke access. A 5-minute grace window absorbs clock skew.
        if parsed < datetime.now(UTC) - timedelta(minutes=5):
            logger.warning(
                "Webhook datetime %s is in the past — skipping to avoid immediate revocation",
                parsed,
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

    expected_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

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


REFUND_WINDOW_DAYS = 14  # EU right of withdrawal


@router.get("/subscription", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get current user's subscription status and usage."""
    subscription_status = "none"
    refund_eligible = False
    refund_deadline = None

    if current_user.subscription_tier != SubscriptionTier.FREE.value:
        if current_user.lemonsqueezy_subscription_id:
            if current_user.subscription_expires:
                if current_user.subscription_expires > datetime.now(UTC):
                    if current_user.subscription_status == "cancelled":
                        subscription_status = "cancelled"
                    else:
                        subscription_status = "active"
                else:
                    subscription_status = "expired"
            else:
                subscription_status = "active"

            # Check refund eligibility: active, first refund, not blocked, within 14 days
            if subscription_status == "active" and (current_user.refund_count or 0) == 0:
                # Check blocked email list
                blocked = await db.scalar(
                    select(RefundBlockedEmail.id).where(
                        func.lower(RefundBlockedEmail.email) == func.lower(current_user.email)
                    )
                )
                if not blocked:
                    try:
                        adapter = LemonSqueezyAdapter()
                        sub_data = await adapter._make_request(
                            "GET",
                            f"subscriptions/{current_user.lemonsqueezy_subscription_id}",
                        )
                        created_at_str = sub_data.get("data", {}).get("attributes", {}).get("created_at")
                        if created_at_str:
                            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                            deadline = created_at + timedelta(days=REFUND_WINDOW_DAYS)
                            if datetime.now(UTC) < deadline:
                                refund_eligible = True
                                refund_deadline = deadline
                    except Exception:
                        logger.debug("Could not check refund eligibility", exc_info=True)

    return SubscriptionStatus(
        subscription_tier=current_user.subscription_tier,
        subscription_status=subscription_status,
        subscription_expires=current_user.subscription_expires,
        customer_id=current_user.lemonsqueezy_customer_id,
        subscription_id=current_user.lemonsqueezy_subscription_id,
        can_manage=current_user.lemonsqueezy_customer_id is not None,
        refund_eligible=refund_eligible,
        refund_deadline=refund_deadline,
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

    frontend_url = settings.frontend_url.rstrip("/")

    # Use the Checkouts API to get an overlay-compatible URL
    from adapters.payments.lemonsqueezy_adapter import LemonSqueezyAdapter, LemonSqueezyError

    adapter = LemonSqueezyAdapter()
    try:
        checkout_url = await adapter.create_checkout(
            variant_id=variant_id,
            email=current_user.email,
            user_id=str(current_user.id),
            plan=body.plan,
            redirect_url=f"{frontend_url}/billing/success",
        )
    except LemonSqueezyError as e:
        logger.error(
            "Failed to create checkout session: %s "
            "(store_id=%s, variant_id=%s, plan=%s, cycle=%s)",
            e, settings.lemonsqueezy_store_id, variant_id, body.plan, body.billing_cycle,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create checkout session. Please try again.",
        )

    logger.info(
        f"Created checkout session for user {current_user.id}, "
        f"plan={body.plan}, billing_cycle={body.billing_cycle}"
    )

    return CheckoutResponse(checkout_url=checkout_url)


@router.get("/portal", response_model=CustomerPortalResponse)
async def get_customer_portal(current_user: Annotated[User, Depends(get_current_user)]):
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

    if not settings.lemonsqueezy_store_slug:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing portal not configured.",
        )

    # Build customer portal URL
    # Format: https://YOUR_STORE.lemonsqueezy.com/billing
    portal_url = f"https://{settings.lemonsqueezy_store_slug}.lemonsqueezy.com/billing"

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

    adapter = LemonSqueezyAdapter()
    try:
        await adapter.cancel_subscription(current_user.lemonsqueezy_subscription_id)
    except Exception as e:
        logger.error("Failed to cancel subscription for user %s: %s", current_user.id, str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to cancel subscription. Please try again or contact support.",
        )

    return SubscriptionCancelResponse(
        success=True,
        message="Subscription will be cancelled at the end of the billing period.",
    )


@router.post("/refund", response_model=RefundResponse)
@limiter.limit("3/minute")
async def refund_subscription(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Request a full refund within the 14-day EU right of withdrawal period.

    - First refund: processed automatically
    - Subsequent refunds: rejected (must contact support)
    - Blocked emails: rejected outright
    """
    if not current_user.lemonsqueezy_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription to refund",
        )

    if current_user.subscription_tier == SubscriptionTier.FREE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Free tier subscriptions cannot be refunded",
        )

    # Check if email is blocked from refunds
    blocked = await db.scalar(
        select(RefundBlockedEmail.id).where(
            func.lower(RefundBlockedEmail.email) == func.lower(current_user.email)
        )
    )
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not eligible for self-service refunds. "
            "Please contact billing@astats.app for assistance.",
        )

    # Only first refund is automatic; subsequent ones require manual approval
    if current_user.refund_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already used your automatic refund. "
            "For additional refund requests, please contact billing@astats.app.",
        )

    adapter = LemonSqueezyAdapter()

    # Verify the subscription is within the 14-day refund window
    try:
        sub_data = await adapter._make_request(
            "GET",
            f"subscriptions/{current_user.lemonsqueezy_subscription_id}",
        )
        created_at_str = sub_data.get("data", {}).get("attributes", {}).get("created_at")
        if not created_at_str:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not verify subscription creation date",
            )

        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        deadline = created_at + timedelta(days=REFUND_WINDOW_DAYS)

        if datetime.now(UTC) >= deadline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The {REFUND_WINDOW_DAYS}-day refund window has expired. "
                "You can still cancel your subscription to stop future charges.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to verify refund eligibility: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not verify refund eligibility. Please contact support.",
        )

    # Find the most recent invoice and refund it
    try:
        invoices = await adapter.get_subscription_invoices(
            current_user.lemonsqueezy_subscription_id
        )
        if not invoices:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No invoice found to refund. Please contact support.",
            )

        invoice_id = invoices[0]["id"]
        await adapter.refund_invoice(invoice_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to issue refund: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process refund. Please contact billing@astats.app.",
        )

    # Cancel the subscription
    try:
        await adapter.cancel_subscription(current_user.lemonsqueezy_subscription_id)
    except Exception as e:
        logger.error("Refund succeeded but cancellation failed: %s", e)

    # Immediately downgrade to free and increment refund count
    current_user.subscription_tier = SubscriptionTier.FREE.value
    current_user.subscription_status = "refunded"
    current_user.subscription_expires = None
    current_user.lemonsqueezy_subscription_id = None
    current_user.refund_count = (current_user.refund_count or 0) + 1
    await db.commit()

    logger.info(
        "Refund processed for user %s (refund_count=%d)",
        current_user.id,
        current_user.refund_count,
    )

    return RefundResponse(
        success=True,
        message="Your subscription has been refunded. You have been downgraded to the free plan.",
    )


# --- Admin: Refund Blocked Emails ---


@router.get("/admin/refund-blocked-emails")
async def list_blocked_emails(
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
):
    """List all emails blocked from self-service refunds (admin only)."""
    result = await db.execute(
        select(RefundBlockedEmail).order_by(RefundBlockedEmail.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "email": r.email,
            "reason": r.reason,
            "blocked_by": r.blocked_by,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/admin/refund-blocked-emails")
async def block_email_from_refunds(
    request: Request,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
):
    """Block an email from requesting self-service refunds (admin only)."""
    body = await request.json()
    email = body.get("email", "").strip().lower()
    reason = body.get("reason", "").strip() or None

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required",
        )

    # Check if already blocked
    existing = await db.scalar(
        select(RefundBlockedEmail.id).where(
            func.lower(RefundBlockedEmail.email) == email
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already blocked",
        )

    blocked = RefundBlockedEmail(
        email=email,
        reason=reason,
        blocked_by=current_user.id,
    )
    db.add(blocked)
    await db.commit()

    logger.info("Admin %s blocked email %s from refunds", current_user.id, email)
    return {"success": True, "message": f"Email {email} blocked from self-service refunds"}


@router.delete("/admin/refund-blocked-emails/{blocked_id}")
async def unblock_email_from_refunds(
    blocked_id: str,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: AsyncSession = Depends(get_db),
):
    """Remove an email from the refund block list (admin only)."""
    result = await db.execute(
        select(RefundBlockedEmail).where(RefundBlockedEmail.id == blocked_id)
    )
    blocked = result.scalar_one_or_none()
    if not blocked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blocked email entry not found",
        )

    email = blocked.email
    await db.delete(blocked)
    await db.commit()

    logger.info("Admin %s unblocked email %s from refunds", current_user.id, email)
    return {"success": True, "message": f"Email {email} unblocked"}


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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Webhook verification not configured"
        )

    # Parse webhook payload
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Invalid JSON in webhook payload: %s", e)
        # BILL-05: Return 400 so LemonSqueezy stops retrying a malformed payload.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook payload: {e}"
        )

    # Idempotency: deduplicate webhook events using Redis (24h TTL covers LemonSqueezy retry window)
    meta = payload.get("meta", {})
    event_id = meta.get("event_id") or payload.get("id")
    if event_id:
        try:
            from infrastructure.redis import get_redis

            r = await get_redis()
            if r is not None:
                redis_key = f"webhook:processed:{event_id}"
                is_new = await r.set(redis_key, "1", nx=True, ex=86400)
            else:
                is_new = True  # No Redis — proceed without idempotency check
            if not is_new:
                logger.info("Duplicate webhook event %s — skipping", event_id)
                return {"status": "ok", "message": "already processed"}
        except Exception as redis_err:
            logger.warning("Webhook idempotency check unavailable (Redis error): %s", redis_err)
            # BILL-19: Proceed without idempotency check — acceptable degradation

    # Extract event info
    event_name = meta.get("event_name")
    custom_data = meta.get("custom_data", {}) or {}
    user_id = custom_data.get("user_id")

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
    ends_at = attributes.get("ends_at")

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
        f"subscription_id={subscription_id}, status={subscription_status}"
    )

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

    # Skip webhook processing for refunded users — refund handler already downgraded them.
    # Without this, the subscription_updated webhook (fired by cancel) would re-set the tier.
    if user.subscription_status == "refunded":
        logger.info(
            "Skipping webhook %s for refunded user %s", event_name, user_id
        )
        return {"status": "ok", "message": "Skipped — user was refunded"}

    # BILL-02: Validate customer_id in webhook matches the one stored on the user.
    # Prevents an attacker who knows another user's user_id from spoofing events
    # by crafting a webhook with their customer_id but a victim's user_id.
    if customer_id and user.lemonsqueezy_customer_id:
        if str(user.lemonsqueezy_customer_id) != str(customer_id):
            logger.error(
                "BILL-02: Webhook customer_id %s does not match stored customer_id %s for user %s — rejecting",
                customer_id,
                user.lemonsqueezy_customer_id,
                user_id,
            )
            return {"status": "error", "message": "Customer ID mismatch"}

    # Determine tier: prefer custom_data.plan (set at checkout), fall back to variant_id mapping.
    plan_from_custom = (custom_data.get("plan") or "").lower()
    valid_paid_tiers = {t.value for t in SubscriptionTier} - {SubscriptionTier.FREE.value}
    if plan_from_custom in valid_paid_tiers:
        tier = plan_from_custom
    elif variant_id:
        variant_to_tier = _build_variant_to_tier()
        tier = variant_to_tier.get(str(variant_id), SubscriptionTier.FREE.value)
        if tier == SubscriptionTier.FREE.value and str(variant_id) not in variant_to_tier:
            logger.warning(
                "BILL-22: variant_id %s did not match any known tier — defaulting to free",
                variant_id,
            )
    else:
        tier = SubscriptionTier.FREE.value

    # Handle different event types
    try:
        if event_name == WebhookEventType.SUBSCRIPTION_CREATED.value:
            # New subscription
            user.subscription_tier = tier
            user.subscription_status = subscription_status or "active"  # BILL-08
            # Only set customer_id if not already stored to avoid unique constraint violation
            if customer_id and not user.lemonsqueezy_customer_id:
                user.lemonsqueezy_customer_id = str(customer_id)
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
            user.lemonsqueezy_variant_id = (
                str(variant_id) if variant_id else None
            )  # BILL-36: keep variant_id in sync on plan changes

            if renews_at:
                user.subscription_expires = _parse_iso_datetime(renews_at)

            # If subscription is cancelled or paused, don't downgrade immediately
            # Let it expire naturally
            if subscription_status in ["cancelled", "paused", "expired"]:
                logger.info(
                    f"Subscription {subscription_status} for user {user_id}, will expire at {renews_at}"
                )
            else:
                logger.info(
                    f"Subscription updated for user {user_id}: tier={tier}, status={subscription_status}"
                )

        elif event_name == WebhookEventType.SUBSCRIPTION_CANCELLED.value:
            # Grace period: keep tier access until billing period ends.
            # LemonSqueezy sets ends_at to the next renewal date.
            # The subscription_expired webhook will downgrade to free.
            user.subscription_status = "cancelled"
            if ends_at:
                user.subscription_expires = _parse_iso_datetime(ends_at)
            elif renews_at:
                user.subscription_expires = _parse_iso_datetime(renews_at)
            logger.info(
                "Subscription cancelled for user %s, access until %s",
                user_id,
                user.subscription_expires,
            )

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
                user_id,
                subscription_id,
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
                user_id,
                subscription_id,
            )

        elif event_name == WebhookEventType.SUBSCRIPTION_UNPAUSED.value:
            # Subscription unpaused
            user.subscription_tier = tier

            if renews_at:
                user.subscription_expires = _parse_iso_datetime(renews_at)

            logger.info(f"Subscription unpaused for user {user_id}")

        else:
            logger.warning(f"Unknown webhook event type: {event_name}")

        # Commit changes
        await db.commit()
        await db.refresh(user)

        logger.info(f"Webhook processed successfully for user {user_id}")

    except Exception as e:
        logger.error("Webhook processing failed: %s", str(e), exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Webhook processing failed"
        )
