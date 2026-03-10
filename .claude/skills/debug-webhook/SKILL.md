---
name: debug-webhook
description: Trace and debug LemonSqueezy webhook processing issues. Use when user reports billing bugs, tier mismatches, subscription state problems, webhook failures, or says "debug webhook", "tier is wrong", "billing bug", or "subscription issue".
disable-model-invocation: true
---

# Debug LemonSqueezy Webhook

Systematic investigation of billing/subscription issues caused by webhook processing.

## Architecture Overview

```
LemonSqueezy → POST /api/v1/billing/webhook
  → Signature verification (X-Signature header + HMAC-SHA256)
  → Parse event_name + payload
  → Guard: skip if user.subscription_status == "refunded"
  → Map variant_id → tier name
  → Handle event (created/updated/cancelled/expired/payment_success/payment_failed)
  → Update user model (tier, status, dates, LS IDs)
  → Commit to DB
```

**Key files:**
- Webhook handler: `backend/api/routes/billing.py` (the `/webhook` POST endpoint)
- Payment adapter: `backend/adapters/payments/lemonsqueezy_adapter.py`
- User model: `backend/infrastructure/database/models/user.py`
- Billing schemas: `backend/schemas/billing.py`

## Step 1: Identify the Problem

Ask the user:
1. What is the **user's email**?
2. What **tier** do they see vs what they **expect**?
3. Did they recently **refund**, **cancel**, **upgrade**, or **downgrade**?
4. Any **error messages** on the billing page?

## Step 2: Check User State in DB

Look at the user model fields that billing touches:
- `subscription_tier` — current tier (free/starter/professional/agency)
- `subscription_status` — (active/cancelled/expired/refunded/past_due)
- `subscription_expires` — when access ends (especially for cancelled users in grace period)
- `lemonsqueezy_subscription_id` — LS subscription reference
- `lemonsqueezy_customer_id` — LS customer reference
- `lemonsqueezy_variant_id` — which plan variant they're on
- `refund_count` — number of refunds (abuse tracking)

## Step 3: Trace the Webhook Flow

Read the webhook handler in `backend/api/routes/billing.py` and trace these paths:

### Known Race Conditions

**1. Refund → Webhook Overwrite (FIXED)**
- Refund endpoint downgrades user to `free` + sets status to `refunded`
- Webhook guard at top of handler: `if user.subscription_status == "refunded"` → skip
- **If this guard is missing or broken:** webhook can overwrite the refund

**2. Cancellation Grace Period**
- Cancel sets status to `cancelled` but user keeps access until `subscription_expires` (= `ends_at`)
- `subscription_expired` webhook fires at period end → downgrades to `free`
- **Bug pattern:** If `subscription_updated` webhook fires AFTER cancel, it might reset status

**3. Variant ID → Tier Mapping**
- Variant IDs are numeric (NOT UUIDs): 1353425, 1353417, 1353437, 1353434, 1353446, 1353443
- If a variant ID doesn't map to a known tier, the handler may set tier to `None` or `free`
- **Check:** Verify the variant mapping dict in the webhook handler

### Event Types to Trace

| Event | Expected Behavior |
|-------|-------------------|
| `subscription_created` | Set tier, status=active, store LS IDs |
| `subscription_updated` | Update tier, status, variant, expiry |
| `subscription_cancelled` | Keep tier, set status=cancelled, set expires=ends_at |
| `subscription_expired` | Downgrade to free, clear LS fields |
| `subscription_payment_success` | Update status=active, update expiry |
| `subscription_payment_failed` | Set status=past_due |

## Step 4: Check the Billing Page Data Flow

The frontend billing page (`frontend/app/(dashboard)/billing/`) has its own data flow:
- Prefers `subscription_tier` from `/billing/subscription` over `/auth/me`
- After refund: does a full page reload (`window.location.reload()`) to clear stale state
- **Bug pattern:** If the billing endpoint and auth endpoint return different tiers, the UI shows inconsistent data

## Step 5: Verify the Fix

After identifying the issue:

1. **If DB state is wrong:** Fix via admin panel or direct DB update
2. **If webhook handler has a bug:** Fix the code, trace ALL event paths for similar issues
3. **If race condition:** Ensure proper guards exist (check `subscription_status` before overwriting)
4. **If variant mapping is wrong:** Verify all 6 variant IDs map correctly

### Known Past Fixes
- `pronetworksolutions@gmail.com` — tier stuck on `starter` after webhook race overwrote refund downgrade. Required manual admin panel fix to set to `free`.
- Webhook guard added: skip ALL webhook processing if `subscription_status == "refunded"`
- Billing page: prefers `/billing/subscription` tier over `/auth/me` to avoid stale cache

## Step 6: Regression Check

After fixing, verify:
```bash
cd D:/A-Stats-Online/backend && grep -n "subscription_status.*refunded\|refunded.*skip\|refund.*guard" api/routes/billing.py
```

Confirm the refund guard is intact and covers all webhook event paths.
