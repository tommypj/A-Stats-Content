# Email Journey for New Customers — Design Spec

**Date:** 2026-03-11
**Status:** Approved (revised after review)

## Goal

Build a full lifecycle email journey covering activation, education, conversion, retention, and ongoing engagement for A-Stats-Online users.

## Architecture

Event-driven email engine built in-house using the existing Resend adapter for delivery.

### Core Components

1. **`EmailJourneyService`** (`backend/services/email_journey.py`) — orchestrator that decides which emails to send based on events and schedules
2. **`user_email_journey_events`** table — tracks which emails each user has received and which are scheduled
3. **`EmailJourneyTemplates`** (`backend/adapters/email/journey_templates.py`) — dedicated template module (keeps `resend_adapter.py` from bloating)
4. **Event hooks** — lightweight calls from existing services that notify the journey service of user actions

### Flow

```
User Action (signup, generate outline, etc.)
  -> Event emitted to EmailJourneyService
    -> Service checks: what journey stage is this user in?
    -> Cancels any now-irrelevant scheduled emails
    -> Schedules next appropriate email(s) via Redis
    -> Background worker picks up scheduled emails at send time
    -> Sends via existing ResendEmailService
    -> Logs delivery in user_email_journey_events
```

### Design Decisions

- Events are fire-and-forget — if the journey service is down, the main action still succeeds
- Scheduled emails stored in DB; Redis used only as a lightweight "next check" sorted set
- Users can unsubscribe per-category using existing notification preferences
- No email sends if user has already completed the action the email encourages
- Max 1 email per day (queue and delay if multiple would fire)

## Email Journey Map

### Phase 1 — Onboarding (Days 0-7)

| Trigger | Timing | Email | Skipped if... |
|---------|--------|-------|---------------|
| Email verified OR first Google OAuth login | Immediate | **Welcome** (enhance existing) | — |
| No outline created | Day 1 (+24h) | **"Create your first outline"** | User already created an outline |
| First outline created | Immediate | **"Nice! Now generate your article"** | — |
| No article by Day 3 | Day 3 | **"Your outline is waiting"** | User already generated an article |
| Day 5 | Scheduled | **"Connect your tools"** (WordPress, GA4, site audit) | User already connected an integration |
| Day 7 | Scheduled | **"Your first week recap"** | — |

**Google OAuth handling:** The `user.verified` event fires for both email verification AND first Google OAuth login. The existing direct `send_welcome_email()` calls in `auth.py` (email verify endpoint + Google OAuth endpoint) are removed and replaced by the journey event emission.

### Phase 2 — Conversion (Triggered)

| Trigger | Email |
|---------|-------|
| Usage hits 80% of free tier | **"You're almost at your limit"** |
| Usage hits 100% | **"You've hit your limit"** |
| 5+ articles generated | **"Power users love these features"** |
| Site audit completed + issues found | **"Fix these issues faster"** |

### Phase 3 — Retention (Graduated)

| Trigger | Email |
|---------|-------|
| 7 days inactive | **"Your content might need attention"** |
| 21 days inactive | **"Here's what's new"** |
| 45 days inactive | **"We miss you"** |

### Phase 4 — Ongoing

| Trigger | Email |
|---------|-------|
| Weekly (if opted in) | **Weekly digest** |
| Content decay detected | **"Article X is losing rankings"** |

### Email Priority (same-day conflicts)

When multiple emails would fire on the same day, send the highest priority one and defer the rest:

1. **Conversion** (most time-sensitive — usage limits)
2. **Onboarding** (time-boxed to 7 days)
3. **Retention** (can wait another day)
4. **Ongoing** (least urgent)

### Tier Change Handling

When a user upgrades or downgrades tier, cancel any pending conversion emails (usage 80%/100%) as they are no longer relevant. Emit `user.tier_changed` event.

## Database Schema

### Migration 060: Email journey infrastructure

### New table: `user_email_journey_events`

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID, PK | — |
| `user_id` | UUID, FK -> users | — |
| `email_key` | VARCHAR(100) | Identifier, e.g. `onboarding.first_outline_nudge` |
| `status` | VARCHAR(20) | `scheduled`, `sent`, `cancelled`, `failed` |
| `scheduled_for` | TIMESTAMP | When to send |
| `sent_at` | TIMESTAMP, nullable | When actually sent |
| `cancelled_at` | TIMESTAMP, nullable | When cancelled |
| `created_at` | TIMESTAMP | — |

**Indexes:**
- `(user_id, email_key)` UNIQUE — no duplicate emails per user
- `(status, scheduled_for)` — worker query index

**Retry strategy:** On failure, the existing row's status is updated back to `scheduled` with a new `scheduled_for` (retry after 1 hour). Max 3 retries tracked via an `attempt_count` INTEGER column (default 0). After 3 failures, status stays `failed`.

### Schema changes (same migration 060)

- `users` table: add `last_active_at` TIMESTAMP column
- `notification_preferences` table: add new columns:
  - `email_onboarding` BOOLEAN (default: true) — gates Phase 1 emails
  - `email_conversion_tips` BOOLEAN (default: true) — gates Phase 2 emails (power user, audit upsell)
  - `email_reengagement` BOOLEAN (default: true) — gates Phase 3 emails

Note: Phase 2 usage threshold emails are already covered by existing `email_usage_80_percent` and `email_usage_limit_reached` toggles. Phase 4 emails are covered by existing `email_weekly_digest` and `email_content_decay` toggles.

Migration must be idempotent (`DO $$ BEGIN IF NOT EXISTS ... END $$`) per Railway deploy conventions.

## Service Integration Points

| Existing Service | Event | File |
|---|---|---|
| Auth verify | `user.verified` | `backend/api/routes/auth.py` |
| Auth Google OAuth | `user.verified` | `backend/api/routes/auth.py` |
| Outline creation | `outline.created` | `backend/api/routes/outlines.py` |
| Article generation | `article.generated` | `backend/api/routes/articles.py` |
| Integration connected | `integration.connected` | `backend/api/routes/integrations.py` |
| Site audit completed | `audit.completed` | `backend/api/routes/site_audit.py` |
| Generation tracker thresholds | `usage.threshold_reached` | `backend/services/generation_tracker.py` |
| Content decay detected | `content.decay_detected` | `backend/services/content_decay.py` |
| Tier change (upgrade/downgrade) | `user.tier_changed` | `backend/api/routes/billing.py` |

Each hook is a single line: `await email_journey_service.emit("event.name", user_id=user.id)`

### Welcome email migration

The existing direct calls to `send_welcome_email()` in `auth.py` (email verification endpoint ~line 798 and Google OAuth endpoint ~line 1391) are **removed** and replaced by `email_journey_service.emit("user.verified", user_id=user.id)`. The journey service now owns the Welcome email.

### Generation tracker changes

Add a new method `get_usage_percentage(user_id, generation_type)` to `generation_tracker.py` that returns current usage as a percentage. The existing binary check remains unchanged. The calling code (article/outline generation endpoints) checks the percentage after a successful generation and emits `usage.threshold_reached` with metadata `{"percentage": 80}` or `{"percentage": 100}` when thresholds are crossed.

### Content decay integration

The `content.decay_detected` event is emitted from the existing `decay_alert_cleanup_task` in `main.py` lifespan, which already runs periodic decay checks. No new scheduled job needed.

## Background Worker

- Async task running in FastAPI lifespan (asyncio)
- **Email dispatch loop**: polls every 60 seconds for scheduled emails due now
- **Inactivity check loop**: runs once per hour (not every 60s) — queries `users.last_active_at` for 7/21/45 day thresholds
- No new infrastructure — runs alongside existing app

## `last_active_at` Tracking

- Middleware on authenticated routes
- Throttled: updates at most once per hour per user (Redis key with 1h TTL)
- Avoids DB write on every request

## Email Templates

16 new templates + 1 enhanced existing, in dedicated module `backend/adapters/email/journey_templates.py`:
- Warm cream background (#FFF8F0), gradient CTA buttons (#ed8f73 -> #da7756), dark text (#1A1A2E)
- Each email has ONE primary CTA
- Subject lines are benefit-driven
- All emails include `List-Unsubscribe` and `List-Unsubscribe-Post` headers (RFC 8058)

| Phase | Count | Templates |
|---|---|---|
| Onboarding | 6 | Welcome (enhanced), First outline nudge, Outline->article nudge, Outline reminder, Connect tools, Week 1 recap |
| Conversion | 4 | Usage 80%, Usage 100%, Power user features, Audit upsell |
| Retention | 3 | 7-day soft nudge, 21-day what's new, 45-day win-back |
| Ongoing | 2 | Weekly digest, Content decay alert |
| System | 2 | Unsubscribe confirmation, Re-subscribe confirmation |

## Unsubscribe Handling

### Token mechanism
- JWT-signed tokens encoding `{user_id, category, action}` with 30-day expiry
- Signed with the app's existing `SECRET_KEY`

### Endpoints
- `POST /api/v1/notifications/unsubscribe` — one-click unsubscribe (accepts JWT token in body)
- `GET /api/v1/notifications/unsubscribe?token=...` — redirects to notification preferences page with category pre-toggled

### Email headers
Every journey email includes:
- `List-Unsubscribe: <https://app.astats.app/api/v1/notifications/unsubscribe?token=...>`
- `List-Unsubscribe-Post: List-Unsubscribe=One-Click`

This satisfies RFC 8058 and improves deliverability with Gmail/Yahoo.

### Frontend
The existing notification preferences page (`/settings` Integrations tab) is extended with the new toggles (`email_onboarding`, `email_conversion_tips`, `email_reengagement`).

## Rules

- Max 1 email per day per user
- Priority: conversion > onboarding > retention > ongoing
- Never send onboarding emails after day 7
- Cancel pending conversion emails on tier change
- Respect all `notification_preferences` toggles
- Fire-and-forget event emission — never block main actions
- Max 3 retry attempts on failure, then mark as permanently failed
