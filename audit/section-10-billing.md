# Audit Section 10 — Billing & Subscriptions
**Date**: 2026-02-27
**Status**: Complete

---

## Scope
- LemonSqueezy checkout and subscription management
- Webhook handling (subscription_created, updated, cancelled, payment events)
- Plan enforcement during content generation
- Project billing endpoints
- Frontend billing page (upgrade, cancel, portal link)

---

## Files Audited
- `backend/api/routes/billing.py`
- `backend/api/routes/project_billing.py`
- `backend/services/generation_tracker.py`
- `backend/core/plans.py`
- `backend/services/project_usage.py`
- `frontend/app/[locale]/(dashboard)/settings/billing/page.tsx`

---

## Findings

### CRITICAL

#### BILL-01 — Expired subscriptions not enforced during content generation
- **Severity**: CRITICAL
- **File**: `backend/services/generation_tracker.py:146-212`
- **Description**: `check_limit()` checks usage counters against plan limits but never validates `user.subscription_expires`. A user whose subscription has expired still generates content at their previous plan's limits indefinitely. The `subscription_expires` field exists in the User model and is set correctly by the webhook handler, but `check_limit()` never reads it. A cancelled user can use Professional-tier features until their counters fill up (which they never do if limits are high).
- **Attack scenario**: User cancels Professional subscription on Day 5. Webhook sets `subscription_expires = Day 30`. User continues generating 100 articles/month using Professional limits throughout Day 5-30 without paying for that period.
- **Fix**: In `check_limit()`, after loading the user, add: `if user.subscription_expires and user.subscription_expires < datetime.now(timezone.utc): return False`. Apply the same check in the project-level limit function.

#### BILL-02 — Checkout URL user_id not validated in webhook — subscription can be assigned to any user
- **Severity**: CRITICAL
- **File**: `backend/api/routes/billing.py:174-178, 494-503`
- **Description**: The checkout URL is constructed with `?checkout[custom][user_id]={current_user.id}`. The webhook handler extracts `user_id` from `custom_data` and activates the subscription for that user — without verifying the user_id matches the LemonSqueezy customer email or any authenticated session. An attacker who crafts a checkout URL with `user_id=VICTIM_ID` and completes payment (even with $0 test credentials, or by abandoning and reusing a callback) can trigger subscription activation for arbitrary users. While this requires completing checkout, it's a real business logic flaw.
- **Fix**: In the webhook handler, after loading the user by `user_id`, cross-validate against the email in the webhook payload: `if webhook_email and user.email != webhook_email: raise ValueError("User mismatch")`. Log and reject mismatches.

#### BILL-03 — No idempotency on webhook events — duplicate delivery causes double-processing
- **Severity**: CRITICAL
- **File**: `backend/api/routes/billing.py:406-626`
- **Description**: LemonSqueezy retries webhook delivery on network failures. The webhook handler has no idempotency key check — if the same `subscription_created` event is delivered twice, it processes both, potentially resetting usage counters twice, creating conflicting subscription states, or setting `subscription_expires` to two different values (whichever arrives second wins). There is no `WebhookEvent` deduplication table or `last_processed_event_id` field.
- **Fix**: Add a `WebhookEvent` table with `event_id` (unique) and `processed_at`. At the start of the handler, check if `event_id` already exists — if so, return 200 immediately. Only insert and process if new.

---

### HIGH

#### BILL-04 — Plan downgrade doesn't revoke features immediately
- **Severity**: HIGH
- **File**: `backend/api/routes/billing.py:538-550`
- **Description**: When a user downgrades (webhook `subscription_updated`), the handler sets `subscription_tier = "free"` but if `renews_at` (subscription end date) is in the future, `subscription_expires` is set to that future date. Combined with BILL-01 (expiry not checked in `check_limit()`), this means a downgraded user retains Professional-level features until `subscription_expires`. The downgrade takes effect in name only, not in capability.
- **Fix**: For downgrades (where new tier < old tier), set `subscription_expires = datetime.now(timezone.utc)` to immediately apply the new limits. Only set `subscription_expires` to `renews_at` for cancellations (where access should continue until period end).

#### BILL-05 — Invalid JSON in webhook returns HTTP 200 — LemonSqueezy stops retrying
- **Severity**: HIGH
- **File**: `backend/api/routes/billing.py:445-451`
- **Description**: When JSON parsing fails, the handler returns `{"status": "error"}` with HTTP 200. LemonSqueezy (and most webhook systems) considers a 2xx response as "delivered successfully" and stops retrying. A malformed or truncated webhook payload is silently dropped, potentially leaving subscription state permanently out of sync.
- **Fix**: Return HTTP 400 Bad Request on JSON parse failure: `raise HTTPException(status_code=400, detail="Invalid webhook payload")`. LemonSqueezy will retry 400 responses.

#### BILL-06 — Webhook rejected with 503 when secret not configured — non-fail-open but disruptive
- **Severity**: HIGH
- **File**: `backend/api/routes/billing.py:426-443`
- **Description**: If `settings.lemonsqueezy_webhook_secret` is not set (empty or missing in env), the webhook handler returns 503 Service Unavailable. LemonSqueezy interprets 5xx as "server error" and retries aggressively. If the secret is accidentally cleared in production, the webhook endpoint becomes a retry storm sink. Additionally, 503 suggests "try again later" which is misleading — the real issue is misconfiguration.
- **Fix**: Return 403 Forbidden when the secret is not configured: "Webhook secret not configured." This correctly signals that the endpoint exists but is not accepting requests, without triggering aggressive retries.

#### BILL-07 — Variant ID stored incorrectly in project billing response
- **Severity**: HIGH
- **File**: `backend/api/routes/project_billing.py:162`
- **Description**: `ProjectSubscriptionResponse.variant_id` is populated with `project.lemonsqueezy_subscription_id` (the subscription ID) instead of the variant ID (which identifies the plan tier). The `Project` model has no `lemonsqueezy_variant_id` field. The frontend uses `variant_id` to determine which plan is active and to generate upgrade checkout URLs — sending the wrong value causes incorrect plan UI display and broken upgrade flows.
- **Fix**: Add `lemonsqueezy_variant_id: Optional[str]` to the `Project` model. Populate it in the webhook handler alongside `subscription_id`. Use this field in `ProjectSubscriptionResponse`.

---

### MEDIUM

#### BILL-08 — Subscription status field never persisted from webhook
- **Severity**: MEDIUM
- **File**: `backend/api/routes/billing.py:527-598`
- **Description**: The `User` model has a `subscription_status` field. The webhook handler reads `subscription_status` from the payload and logs it, but never writes it to the database: `user.subscription_status = subscription_status` is absent. The field is always stale (likely `"active"` from initial creation). The frontend billing page reads this field to show "Active", "Cancelled", "Paused" etc. — it always shows "active" regardless of actual state.
- **Fix**: Add `user.subscription_status = subscription_status or "active"` in the `subscription_updated` webhook handler path. Do the same for project subscriptions.

#### BILL-09 — No row-level lock on concurrent webhook updates — race condition on subscription state
- **Severity**: MEDIUM
- **File**: `backend/api/routes/billing.py:604-618`
- **Description**: Two simultaneous webhook deliveries (e.g., `subscription_updated` + `payment_success`) both load the User record, apply their changes, and commit. Without `SELECT ... FOR UPDATE`, the second commit can silently overwrite fields set by the first. The subscription tier, status, and expiry can end up in an inconsistent mixed state.
- **Fix**: Add `.with_for_update()` to the User query in the webhook handler: `select(User).where(...).with_for_update()`.

#### BILL-10 — No rate limiting on billing endpoints
- **Severity**: MEDIUM
- **File**: `backend/api/routes/billing.py:79-259`, `backend/api/routes/project_billing.py`
- **Description**: `GET /billing/subscription`, `POST /billing/checkout`, `GET /billing/portal`, `POST /billing/cancel` have no rate limiting. An attacker can spam checkout creation (generating hundreds of LemonSqueezy sessions) or cancel requests. Also, checkout URL generation is idempotent so repeated calls don't cause billing harm, but they waste external API calls and could expose LemonSqueezy credentials in response payloads.
- **Fix**: Add `@limiter.limit("5/minute")` to checkout and cancel endpoints. `@limiter.limit("30/minute")` on read endpoints.

#### BILL-11 — Checkout URL lacks CSRF protection
- **Severity**: MEDIUM
- **File**: `backend/api/routes/billing.py:136-185`
- **Description**: The checkout URL is constructed server-side and returned to the frontend, which opens it in a new window. An attacker who can lure an authenticated user to a malicious page could trigger a `POST /billing/checkout` request (via CSRF) and redirect the user to a checkout for an attacker-chosen plan. The user would see a legitimate LemonSqueezy checkout page with their account details pre-filled.
- **Fix**: Add a short-lived checkout session token (UUID, stored in Redis with 10-minute TTL). Return it alongside the checkout URL. The webhook handler should validate the token matches the initiating user.

---

### LOW

#### BILL-12 — `_parse_iso_datetime()` returns `datetime.now()` on parse failure — wrong expiry dates
- **Severity**: LOW
- **File**: `backend/api/routes/billing.py:41-47`
- **Description**: If LemonSqueezy sends a malformed date string, `_parse_iso_datetime()` catches the exception and returns `datetime.now(timezone.utc)`. This sets `subscription_expires` to "right now" — immediately expiring the subscription. The error is logged as a warning, not an error. The user's subscription is incorrectly terminated.
- **Fix**: Return `None` on parse failure and propagate the error upstream. Treat missing/unparseable dates as an indication to not update the expiry field.

#### BILL-13 — Personal project subscription sync silently skips if no personal project exists
- **Severity**: LOW
- **File**: `backend/api/routes/billing.py:603-615`
- **Description**: The webhook handler tries to sync subscription tier to the user's personal project but silently skips if `personal_project` is not found (`if personal_project: ...`). No log warning is emitted. If a user somehow lacks a personal project (edge case from registration failure or DB cleanup), their project-level limits are never updated.
- **Fix**: Add `else: logger.warning("Personal project not found for user %s during subscription sync", user.id)` to detect and investigate these cases.

#### BILL-14 — Variant ID → tier mapping duplicated in billing.py and project_billing.py
- **Severity**: LOW
- **File**: `backend/api/routes/billing.py:302-316, 509-523`
- **Description**: The logic mapping LemonSqueezy variant IDs to subscription tier strings is copy-pasted in both `billing.py` (for users) and `project_billing.py` (for projects). Any update to pricing requires changes in two places.
- **Fix**: Extract to a shared function in `backend/core/plans.py`: `def get_tier_from_variant_id(variant_id: str) -> str`.

#### BILL-15 — Subscription cancel doesn't validate LemonSqueezy API success before updating DB
- **Severity**: LOW
- **File**: `backend/api/routes/billing.py:237-254`
- **Description**: The cancel endpoint makes an API call to LemonSqueezy and logs errors if it fails, but then proceeds to mark the subscription as cancelled in the DB regardless. If the external API call fails (LemonSqueezy outage), the user's local subscription shows as cancelled but LemonSqueezy continues billing — subscription state desync.
- **Fix**: Only update DB state after confirmed successful API response. If the API call fails, return 500 to the frontend with "Cancellation failed, please try again."

---

## What's Working Well
- HMAC-SHA256 webhook signature validation — correctly rejects tampered webhooks
- Webhook event type parsing is robust — unknown events handled gracefully
- `get_current_user` dependency correctly enforces authentication on all billing endpoints
- LemonSqueezy customer portal link generation is correct (read-only management portal)
- Frontend polls for subscription update after checkout (with 5-minute timeout)
- Project billing correctly scoped to current user's projects
- Plan limits defined in `core/plans.py` used consistently in generation checks
- Audit logging implemented for most billing operations

---

## Fix Priority Order
1. BILL-01 — Expired subscriptions not enforced (CRITICAL)
2. BILL-02 — user_id in checkout not validated in webhook (CRITICAL)
3. BILL-03 — No webhook idempotency (CRITICAL)
4. BILL-04 — Downgrade doesn't revoke features immediately (HIGH)
5. BILL-05 — Invalid JSON webhook returns 200 OK (HIGH)
6. BILL-06 — Missing secret returns 503 instead of 403 (HIGH)
7. BILL-07 — Wrong variant_id in project billing response (HIGH)
8. BILL-08 — Subscription status not persisted from webhook (MEDIUM)
9. BILL-09 — No row lock on concurrent webhook updates (MEDIUM)
10. BILL-10 — No rate limiting on billing endpoints (MEDIUM)
11. BILL-11 — Checkout lacks CSRF protection (MEDIUM)
12. BILL-12 through BILL-15 — Low severity (LOW)
