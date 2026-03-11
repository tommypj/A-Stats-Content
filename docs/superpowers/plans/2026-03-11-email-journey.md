# Email Journey Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an event-driven email journey engine that sends lifecycle emails (onboarding, conversion, retention, ongoing) through the existing Resend adapter.

**Architecture:** EmailJourneyService receives fire-and-forget events from existing routes, schedules emails in a DB table with optional JSON metadata, and a background worker polls for due emails and sends them via ResendEmailService. User activity is tracked via `last_active_at` updates inside the `get_current_user` dependency (throttled by Redis).

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Resend, Redis (throttling), JWT (unsubscribe tokens)

**Spec:** `docs/superpowers/specs/2026-03-11-email-journey-design.md`

**Important codebase conventions:**
- All imports use **relative paths** (no `backend.` prefix) — e.g., `from infrastructure.database.models.user import User`
- DB sessions use `async_session_maker` from `infrastructure.database.connection`
- Background context manager: `get_db_context()` from `infrastructure.database`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `backend/infrastructure/database/migrations/versions/060_email_journey.py` | Migration: new table + column additions |
| `backend/infrastructure/database/models/email_journey_event.py` | SQLAlchemy model for `user_email_journey_events` |
| `backend/adapters/email/journey_templates.py` | HTML email templates (17 total: 15 journey + 2 system) |
| `backend/services/email_journey.py` | Journey orchestrator: event handling, scheduling, cancellation |
| `backend/services/email_journey_worker.py` | Background worker: polls DB, sends due emails, inactivity checks |
| `backend/services/email_journey_unsubscribe.py` | JWT token generation/verification for unsubscribe |
| `tests/services/test_email_journey.py` | Tests for journey service |
| `tests/services/test_email_journey_worker.py` | Tests for background worker |
| `tests/adapters/test_journey_templates.py` | Tests for template rendering |

### Modified Files
| File | Change |
|------|--------|
| `backend/infrastructure/database/models/user.py` | Add `last_active_at` column |
| `backend/infrastructure/database/models/notification_preferences.py` | Add 3 new preference columns |
| `backend/infrastructure/database/models/__init__.py` | Register `EmailJourneyEvent` model |
| `backend/api/schemas/notification_preferences.py` | Add 3 new fields to response/update schemas |
| `backend/api/routes/auth.py` | Replace direct `send_welcome_email` with journey event + add `last_active_at` tracking to `get_current_user` |
| `backend/api/routes/outlines.py` | Emit `outline.created` event |
| `backend/api/routes/articles.py` | Emit `article.generated` event |
| `backend/api/routes/notifications.py` | Add unsubscribe endpoints |
| `backend/api/routes/wordpress.py` | Emit `integration.connected` event |
| `backend/api/routes/analytics.py` | Emit `integration.connected` event |
| `backend/api/routes/site_audit.py` | Emit `audit.completed` event |
| `backend/api/routes/billing.py` | Emit `user.tier_changed` event |
| `backend/services/generation_tracker.py` | Add `get_usage_percentage()` method |
| `backend/main.py` | Add journey worker to lifespan |
| `frontend/app/[locale]/(dashboard)/settings/page.tsx` | Add 3 new notification preference toggles |
| `frontend/lib/api.ts` | Add new preference fields to types |

---

## Chunk 1: Database Foundation

### Task 1: Alembic Migration

**Files:**
- Create: `backend/infrastructure/database/migrations/versions/060_email_journey.py`

- [ ] **Step 1: Create migration file**

```python
"""Email journey infrastructure.

Revision ID: 060
Revises: 059
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New table: user_email_journey_events
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'user_email_journey_events'
            ) THEN
                CREATE TABLE user_email_journey_events (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    email_key VARCHAR(100) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
                    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
                    sent_at TIMESTAMP WITH TIME ZONE,
                    cancelled_at TIMESTAMP WITH TIME ZONE,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
                CREATE UNIQUE INDEX uix_journey_user_email_key
                    ON user_email_journey_events(user_id, email_key)
                    WHERE status IN ('scheduled', 'sent');
                CREATE INDEX ix_journey_status_scheduled
                    ON user_email_journey_events(status, scheduled_for);
            END IF;
        END $$;
    """)

    -- Add last_active_at to users
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'last_active_at'
            ) THEN
                ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP WITH TIME ZONE;
            END IF;
        END $$;
    """)

    -- Add new notification preference columns
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'notification_preferences'
                AND column_name = 'email_onboarding'
            ) THEN
                ALTER TABLE notification_preferences
                    ADD COLUMN email_onboarding BOOLEAN NOT NULL DEFAULT TRUE;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'notification_preferences'
                AND column_name = 'email_conversion_tips'
            ) THEN
                ALTER TABLE notification_preferences
                    ADD COLUMN email_conversion_tips BOOLEAN NOT NULL DEFAULT TRUE;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'notification_preferences'
                AND column_name = 'email_reengagement'
            ) THEN
                ALTER TABLE notification_preferences
                    ADD COLUMN email_reengagement BOOLEAN NOT NULL DEFAULT TRUE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("user_email_journey_events")
    op.drop_column("users", "last_active_at")
    op.drop_column("notification_preferences", "email_onboarding")
    op.drop_column("notification_preferences", "email_conversion_tips")
    op.drop_column("notification_preferences", "email_reengagement")
```

Key changes from v1:
- Added `metadata JSONB` column for template-specific kwargs (usage counts, article titles, etc.)
- Unique index is now **partial**: `WHERE status IN ('scheduled', 'sent')` — allows repeatable emails (content decay, weekly digest) by inserting new rows after previous ones are cancelled/failed

- [ ] **Step 2: Commit**

```bash
git add backend/infrastructure/database/migrations/versions/060_email_journey.py
git commit -m "feat(migration-060): add email journey table and preference columns"
```

### Task 2: SQLAlchemy Model + Schema Updates

**Files:**
- Create: `backend/infrastructure/database/models/email_journey_event.py`
- Modify: `backend/infrastructure/database/models/__init__.py`
- Modify: `backend/infrastructure/database/models/user.py`
- Modify: `backend/infrastructure/database/models/notification_preferences.py`
- Modify: `backend/api/schemas/notification_preferences.py`

- [ ] **Step 1: Create EmailJourneyEvent model**

```python
"""Email journey event tracking model."""

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base


class EmailJourneyEvent(Base):
    __tablename__ = "user_email_journey_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    email_key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    scheduled_for = Column(sa.DateTime(timezone=True), nullable=False)
    sent_at = Column(sa.DateTime(timezone=True), nullable=True)
    cancelled_at = Column(sa.DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        Index(
            "uix_journey_user_email_key",
            "user_id", "email_key",
            unique=True,
            postgresql_where=sa.text("status IN ('scheduled', 'sent')"),
        ),
        Index("ix_journey_status_scheduled", "status", "scheduled_for"),
    )
```

Note: Python attribute is `metadata_` (trailing underscore) to avoid conflict with SQLAlchemy's `metadata`. The DB column name is `metadata`.

Check the import path for `Base` by looking at existing models (e.g., `from infrastructure.database.models.base import Base`). Match exactly.

- [ ] **Step 2: Add `last_active_at` to User model**

In `backend/infrastructure/database/models/user.py`, after the `last_login` column, add:

```python
last_active_at = Column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 3: Add preference columns to NotificationPreferences model**

In `backend/infrastructure/database/models/notification_preferences.py`, after `email_product_updates`, add:

```python
email_onboarding: Mapped[bool] = mapped_column(default=True, nullable=False)
email_conversion_tips: Mapped[bool] = mapped_column(default=True, nullable=False)
email_reengagement: Mapped[bool] = mapped_column(default=True, nullable=False)
```

- [ ] **Step 4: Register model in `__init__.py`**

In `backend/infrastructure/database/models/__init__.py`, add:

```python
from infrastructure.database.models.email_journey_event import EmailJourneyEvent
```

And add `EmailJourneyEvent` to the `__all__` list if one exists.

- [ ] **Step 5: Update notification preferences schemas**

In `backend/api/schemas/notification_preferences.py`:

Add to `NotificationPreferencesResponse`:
```python
email_onboarding: bool
email_conversion_tips: bool
email_reengagement: bool
```

Add to `NotificationPreferencesUpdate`:
```python
email_onboarding: bool | None = None
email_conversion_tips: bool | None = None
email_reengagement: bool | None = None
```

- [ ] **Step 6: Commit**

```bash
git add backend/infrastructure/database/models/email_journey_event.py \
      backend/infrastructure/database/models/__init__.py \
      backend/infrastructure/database/models/user.py \
      backend/infrastructure/database/models/notification_preferences.py \
      backend/api/schemas/notification_preferences.py
git commit -m "feat: add EmailJourneyEvent model and preference columns"
```

---

## Chunk 2: Journey Templates

### Task 3: Email HTML Templates

**Files:**
- Create: `backend/adapters/email/journey_templates.py`
- Create: `tests/adapters/test_journey_templates.py`

- [ ] **Step 1: Write template tests**

Create `tests/adapters/test_journey_templates.py`:

```python
"""Tests for email journey HTML templates."""

import pytest
from adapters.email.journey_templates import JourneyTemplates


class TestJourneyTemplates:
    """Test that all templates render valid HTML with expected content."""

    def setup_method(self):
        self.templates = JourneyTemplates(frontend_url="https://app.astats.app")

    def test_welcome_contains_user_name(self):
        html, subject = self.templates.welcome(user_name="Alice")
        assert "Alice" in html
        assert subject != ""
        assert "<!DOCTYPE html>" in html

    def test_welcome_escapes_html_in_name(self):
        html, _ = self.templates.welcome(user_name="<script>alert('xss')</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_first_outline_nudge(self):
        html, subject = self.templates.first_outline_nudge(user_name="Bob")
        assert "outline" in html.lower()
        assert "Bob" in html

    def test_outline_to_article_nudge(self):
        html, subject = self.templates.outline_to_article_nudge(user_name="Carol")
        assert "article" in html.lower()

    def test_outline_reminder(self):
        html, subject = self.templates.outline_reminder(user_name="Dave")
        assert "Dave" in html

    def test_connect_tools(self):
        html, subject = self.templates.connect_tools(user_name="Eve")
        assert "WordPress" in html or "connect" in html.lower()

    def test_week_one_recap(self):
        html, subject = self.templates.week_one_recap(
            user_name="Frank", outlines_count=3, articles_count=1,
        )
        assert "Frank" in html

    def test_usage_80_percent(self):
        html, subject = self.templates.usage_80_percent(
            user_name="Grace", current_usage=8, limit=10, resource="articles",
        )
        assert "8" in html
        assert "10" in html

    def test_usage_100_percent(self):
        html, subject = self.templates.usage_100_percent(
            user_name="Heidi", resource="articles",
        )
        assert "limit" in html.lower() or "upgrade" in html.lower()

    def test_power_user_features(self):
        html, subject = self.templates.power_user_features(user_name="Ivan")
        assert "Ivan" in html

    def test_audit_upsell(self):
        html, subject = self.templates.audit_upsell(user_name="Judy", issues_count=12)
        assert "12" in html

    def test_inactive_7_days(self):
        html, subject = self.templates.inactive_7_days(user_name="Karl")
        assert "Karl" in html

    def test_inactive_21_days(self):
        html, subject = self.templates.inactive_21_days(user_name="Lara")
        assert "Lara" in html

    def test_inactive_45_days(self):
        html, subject = self.templates.inactive_45_days(user_name="Mike")
        assert "Mike" in html

    def test_weekly_digest(self):
        html, subject = self.templates.weekly_digest(
            user_name="Nina", articles_generated=5, decay_alerts=2,
        )
        assert "Nina" in html
        assert "5" in html

    def test_content_decay_alert(self):
        html, subject = self.templates.content_decay_alert(
            user_name="Oscar",
            article_title="Best SEO Tips 2026",
            decay_type="position_drop",
        )
        assert "Best SEO Tips 2026" in html

    def test_unsubscribe_confirmation(self):
        html, subject = self.templates.unsubscribe_confirmation(user_name="Pat")
        assert "Pat" in html
        assert "unsubscribe" in html.lower() or "preference" in html.lower()

    def test_resubscribe_confirmation(self):
        html, subject = self.templates.resubscribe_confirmation(user_name="Quinn")
        assert "Quinn" in html

    def test_all_templates_have_unsubscribe_link(self):
        """Every journey template (not system templates) must include an unsubscribe link."""
        methods = [
            ("welcome", {"user_name": "Test"}),
            ("first_outline_nudge", {"user_name": "Test"}),
            ("outline_to_article_nudge", {"user_name": "Test"}),
            ("outline_reminder", {"user_name": "Test"}),
            ("connect_tools", {"user_name": "Test"}),
            ("week_one_recap", {"user_name": "Test", "outlines_count": 0, "articles_count": 0}),
            ("usage_80_percent", {"user_name": "Test", "current_usage": 8, "limit": 10, "resource": "articles"}),
            ("usage_100_percent", {"user_name": "Test", "resource": "articles"}),
            ("power_user_features", {"user_name": "Test"}),
            ("audit_upsell", {"user_name": "Test", "issues_count": 5}),
            ("inactive_7_days", {"user_name": "Test"}),
            ("inactive_21_days", {"user_name": "Test"}),
            ("inactive_45_days", {"user_name": "Test"}),
            ("weekly_digest", {"user_name": "Test", "articles_generated": 0, "decay_alerts": 0}),
            ("content_decay_alert", {"user_name": "Test", "article_title": "Test", "decay_type": "position_drop"}),
        ]
        for method_name, kwargs in methods:
            html, _ = getattr(self.templates, method_name)(**kwargs)
            assert "unsubscribe" in html.lower(), f"{method_name} missing unsubscribe link"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/adapters/test_journey_templates.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement JourneyTemplates class**

Create `backend/adapters/email/journey_templates.py`. The class should:

- Follow the exact HTML structure from `resend_adapter.py` (warm cream #FFF8F0, gradient CTA #da7756, dark text #1A1A2E, 560px container)
- Each method returns `tuple[str, str]` — `(html_body, subject_line)`
- Use `html.escape()` on all user-provided strings
- Every journey template includes an unsubscribe placeholder `{unsubscribe_url}` in the footer
- CTA buttons link to relevant dashboard pages via `self.frontend_url`
- 17 template methods total (15 journey + 2 system)

```python
from html import escape as html_escape


class JourneyTemplates:
    def __init__(self, frontend_url: str):
        self.frontend_url = frontend_url

    def _base_layout(self, content: str, unsubscribe_url: str = "#") -> str:
        """Wrap content in the branded email layout with unsubscribe footer."""
        # Copy HTML structure from resend_adapter.py _get_welcome_email_html:
        # - Background: #FFF8F0, container: white 560px, border-radius 16px
        # - Logo: 48px gradient div (#ed8f73 -> #da7756)
        # - Font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto
        # - CTA button: #da7756 background, white text, border-radius 12px
        # Add unsubscribe footer after main content:
        # <div style="text-align:center;padding-top:24px;border-top:1px solid #F1F3F5;margin-top:32px;">
        #   <a href="{unsubscribe_url}" style="color:#8B8BA7;font-size:12px;text-decoration:underline;">
        #     Unsubscribe from these emails
        #   </a>
        # </div>
        ...

    # Phase 1: Onboarding
    def welcome(self, user_name: str) -> tuple[str, str]: ...
    def first_outline_nudge(self, user_name: str) -> tuple[str, str]: ...
    def outline_to_article_nudge(self, user_name: str) -> tuple[str, str]: ...
    def outline_reminder(self, user_name: str) -> tuple[str, str]: ...
    def connect_tools(self, user_name: str) -> tuple[str, str]: ...
    def week_one_recap(self, user_name: str, outlines_count: int, articles_count: int) -> tuple[str, str]: ...

    # Phase 2: Conversion
    def usage_80_percent(self, user_name: str, current_usage: int, limit: int, resource: str) -> tuple[str, str]: ...
    def usage_100_percent(self, user_name: str, resource: str) -> tuple[str, str]: ...
    def power_user_features(self, user_name: str) -> tuple[str, str]: ...
    def audit_upsell(self, user_name: str, issues_count: int) -> tuple[str, str]: ...

    # Phase 3: Retention
    def inactive_7_days(self, user_name: str) -> tuple[str, str]: ...
    def inactive_21_days(self, user_name: str) -> tuple[str, str]: ...
    def inactive_45_days(self, user_name: str) -> tuple[str, str]: ...

    # Phase 4: Ongoing
    def weekly_digest(self, user_name: str, articles_generated: int, decay_alerts: int) -> tuple[str, str]: ...
    def content_decay_alert(self, user_name: str, article_title: str, decay_type: str) -> tuple[str, str]: ...

    # System
    def unsubscribe_confirmation(self, user_name: str) -> tuple[str, str]: ...
    def resubscribe_confirmation(self, user_name: str) -> tuple[str, str]: ...
```

Template content guidance:
- **Welcome**: Enhanced version — "Your account is ready" + 4 getting-started steps + CTA to dashboard
- **First outline nudge**: "Create your first outline in 30 seconds" + CTA to `/outlines/new`
- **Outline→article**: "Your outline is ready — generate an article" + CTA to `/articles`
- **Outline reminder**: "Your outline is still waiting" + softer nudge
- **Connect tools**: Highlight WordPress + GA4 + Site Audit + CTA to `/settings`
- **Week 1 recap**: Stats summary (outlines, articles) + what to explore next
- **Usage 80%**: "{current_usage} of {limit} {resource} used" + upgrade CTA
- **Usage 100%**: "You've reached your limit" + tier comparison + upgrade CTA
- **Power user**: "You've generated 5+ articles — unlock bulk workflows, templates"
- **Audit upsell**: "{issues_count} issues found — fix them faster"
- **Inactive 7d**: "Your content might need attention — check for decay"
- **Inactive 21d**: "Here's what's new in A-Stats" + feature highlights
- **Inactive 45d**: "We miss you — need help getting started?" + support link
- **Weekly digest**: Articles generated, decay alerts count, CTA to dashboard
- **Content decay**: "{article_title} is losing rankings — take action"
- **Unsubscribe confirmation**: "You've been unsubscribed" + link to re-enable
- **Resubscribe confirmation**: "Welcome back! You'll receive emails again"

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/adapters/test_journey_templates.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/adapters/email/journey_templates.py tests/adapters/test_journey_templates.py
git commit -m "feat: add email journey HTML templates (15 journey + 2 system)"
```

---

## Chunk 3: Journey Service Core

### Task 4: EmailJourneyService

**Files:**
- Create: `backend/services/email_journey.py`
- Create: `tests/services/test_email_journey.py`

- [ ] **Step 1: Write journey service tests**

Create `tests/services/test_email_journey.py`:

```python
"""Tests for EmailJourneyService."""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.email_journey import EmailJourneyService, EMAIL_JOURNEY_MAP


class TestEmailJourneyMap:
    """Test that the journey map is correctly defined."""

    def test_all_email_keys_are_unique(self):
        keys = list(EMAIL_JOURNEY_MAP.keys())
        assert len(keys) == len(set(keys))

    def test_onboarding_emails_exist(self):
        assert "onboarding.welcome" in EMAIL_JOURNEY_MAP
        assert "onboarding.first_outline_nudge" in EMAIL_JOURNEY_MAP
        assert "onboarding.outline_to_article" in EMAIL_JOURNEY_MAP

    def test_conversion_emails_exist(self):
        assert "conversion.usage_80" in EMAIL_JOURNEY_MAP
        assert "conversion.usage_100" in EMAIL_JOURNEY_MAP

    def test_retention_emails_exist(self):
        assert "retention.inactive_7d" in EMAIL_JOURNEY_MAP
        assert "retention.inactive_21d" in EMAIL_JOURNEY_MAP
        assert "retention.inactive_45d" in EMAIL_JOURNEY_MAP

    def test_all_entries_have_priority(self):
        for key, entry in EMAIL_JOURNEY_MAP.items():
            assert "priority" in entry, f"{key} missing priority"


class TestEventHandling:
    """Test event-to-email mapping logic."""

    @pytest.fixture
    def service(self):
        db = AsyncMock()
        return EmailJourneyService(db)

    @pytest.mark.asyncio
    async def test_user_verified_schedules_welcome_and_nudge(self, service):
        user_id = str(uuid4())
        with patch.object(service, "_schedule_email", new_callable=AsyncMock) as mock_schedule, \
             patch.object(service, "_cancel_email", new_callable=AsyncMock), \
             patch.object(service, "_check_preference", new_callable=AsyncMock, return_value=True):
            await service.emit("user.verified", user_id=user_id)
            email_keys = [call.args[1] for call in mock_schedule.call_args_list]
            assert "onboarding.welcome" in email_keys
            assert "onboarding.first_outline_nudge" in email_keys

    @pytest.mark.asyncio
    async def test_outline_created_cancels_nudge_and_schedules_next(self, service):
        user_id = str(uuid4())
        with patch.object(service, "_schedule_email", new_callable=AsyncMock) as mock_schedule, \
             patch.object(service, "_cancel_email", new_callable=AsyncMock) as mock_cancel, \
             patch.object(service, "_check_preference", new_callable=AsyncMock, return_value=True):
            await service.emit("outline.created", user_id=user_id)
            cancel_keys = [call.args[1] for call in mock_cancel.call_args_list]
            assert "onboarding.first_outline_nudge" in cancel_keys
            schedule_keys = [call.args[1] for call in mock_schedule.call_args_list]
            assert "onboarding.outline_to_article" in schedule_keys

    @pytest.mark.asyncio
    async def test_preference_disabled_skips_scheduling(self, service):
        user_id = str(uuid4())
        with patch.object(service, "_schedule_email", new_callable=AsyncMock) as mock_schedule, \
             patch.object(service, "_cancel_email", new_callable=AsyncMock), \
             patch.object(service, "_check_preference", new_callable=AsyncMock, return_value=False):
            await service.emit("user.verified", user_id=user_id)
            mock_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_tier_changed_cancels_conversion_emails(self, service):
        user_id = str(uuid4())
        with patch.object(service, "_cancel_email", new_callable=AsyncMock) as mock_cancel, \
             patch.object(service, "_schedule_email", new_callable=AsyncMock), \
             patch.object(service, "_check_preference", new_callable=AsyncMock, return_value=True):
            await service.emit("user.tier_changed", user_id=user_id)
            cancel_keys = [call.args[1] for call in mock_cancel.call_args_list]
            assert "conversion.usage_80" in cancel_keys
            assert "conversion.usage_100" in cancel_keys

    @pytest.mark.asyncio
    async def test_article_generated_with_milestone(self, service):
        user_id = str(uuid4())
        with patch.object(service, "_schedule_email", new_callable=AsyncMock) as mock_schedule, \
             patch.object(service, "_cancel_email", new_callable=AsyncMock), \
             patch.object(service, "_check_preference", new_callable=AsyncMock, return_value=True):
            await service.emit("article.generated", user_id=user_id, metadata={"article_count": 5})
            schedule_keys = [call.args[1] for call in mock_schedule.call_args_list]
            assert "conversion.power_user" in schedule_keys

    @pytest.mark.asyncio
    async def test_unknown_event_does_not_crash(self, service):
        """Fire-and-forget: unknown events are silently ignored."""
        await service.emit("unknown.event", user_id=str(uuid4()))


class TestScheduleEmail:
    """Test the _schedule_email internal method."""

    @pytest.fixture
    def service(self):
        db = AsyncMock()
        return EmailJourneyService(db)

    @pytest.mark.asyncio
    async def test_schedule_creates_db_record(self, service):
        user_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(return_value=mock_result)
        service.db.add = MagicMock()
        service.db.commit = AsyncMock()

        await service._schedule_email(user_id, "onboarding.welcome", timedelta(0))
        service.db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_skips_if_already_sent(self, service):
        user_id = str(uuid4())
        existing = MagicMock()
        existing.status = "sent"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        service.db.execute = AsyncMock(return_value=mock_result)
        service.db.add = MagicMock()

        await service._schedule_email(user_id, "onboarding.welcome", timedelta(0))
        service.db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_schedule_retries_failed_under_max(self, service):
        user_id = str(uuid4())
        existing = MagicMock()
        existing.status = "failed"
        existing.attempt_count = 1
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        service.db.execute = AsyncMock(return_value=mock_result)
        service.db.commit = AsyncMock()

        await service._schedule_email(user_id, "onboarding.welcome", timedelta(0))
        assert existing.status == "scheduled"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/services/test_email_journey.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement EmailJourneyService**

Create `backend/services/email_journey.py`:

```python
"""Email journey orchestrator.

Receives events from application code, decides which emails to schedule
or cancel, and persists scheduling decisions to the database. The actual
sending is handled by the background worker (email_journey_worker.py).
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.email_journey_event import EmailJourneyEvent
from infrastructure.database.models.notification_preferences import NotificationPreferences

logger = logging.getLogger(__name__)

# Map of email_key -> metadata
# phase: which notification preference column gates this email
# priority: for same-day conflict resolution (lower number = higher priority)
EMAIL_JOURNEY_MAP = {
    # Phase 1: Onboarding
    "onboarding.welcome": {"phase": "onboarding", "priority": 20},
    "onboarding.first_outline_nudge": {"phase": "onboarding", "priority": 21},
    "onboarding.outline_to_article": {"phase": "onboarding", "priority": 22},
    "onboarding.outline_reminder": {"phase": "onboarding", "priority": 23},
    "onboarding.connect_tools": {"phase": "onboarding", "priority": 24},
    "onboarding.week_one_recap": {"phase": "onboarding", "priority": 25},
    # Phase 2: Conversion
    "conversion.usage_80": {"phase": "usage", "priority": 10},
    "conversion.usage_100": {"phase": "usage", "priority": 11},
    "conversion.power_user": {"phase": "conversion_tips", "priority": 12},
    "conversion.audit_upsell": {"phase": "conversion_tips", "priority": 13},
    # Phase 3: Retention
    "retention.inactive_7d": {"phase": "reengagement", "priority": 30},
    "retention.inactive_21d": {"phase": "reengagement", "priority": 31},
    "retention.inactive_45d": {"phase": "reengagement", "priority": 32},
    # Phase 4: Ongoing
    "ongoing.weekly_digest": {"phase": "weekly_digest", "priority": 40},
    "ongoing.content_decay": {"phase": "content_decay", "priority": 41},
}

# Map phase -> notification_preferences column name
PHASE_TO_PREF_COLUMN = {
    "onboarding": "email_onboarding",
    "usage": None,  # Uses existing email_usage_80_percent / email_usage_limit_reached
    "conversion_tips": "email_conversion_tips",
    "reengagement": "email_reengagement",
    "weekly_digest": "email_weekly_digest",
    "content_decay": "email_content_decay",
}


class EmailJourneyService:
    """Orchestrates email journey scheduling based on user events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def emit(self, event: str, *, user_id: str, metadata: dict | None = None) -> None:
        """Handle an event and schedule/cancel appropriate emails.

        This is fire-and-forget — exceptions are caught and logged.
        """
        try:
            await self._handle_event(event, user_id, metadata or {})
        except Exception:
            logger.exception("Email journey error handling event=%s user=%s", event, user_id)

    async def _handle_event(self, event: str, user_id: str, metadata: dict) -> None:
        handlers = {
            "user.verified": self._on_user_verified,
            "outline.created": self._on_outline_created,
            "article.generated": self._on_article_generated,
            "integration.connected": self._on_integration_connected,
            "audit.completed": self._on_audit_completed,
            "usage.threshold_reached": self._on_usage_threshold,
            "content.decay_detected": self._on_content_decay,
            "user.tier_changed": self._on_tier_changed,
        }
        handler = handlers.get(event)
        if handler:
            await handler(user_id, metadata)

    async def _on_user_verified(self, user_id: str, metadata: dict) -> None:
        if not await self._check_preference(user_id, "onboarding"):
            return
        await self._schedule_email(user_id, "onboarding.welcome", timedelta(0))
        await self._schedule_email(user_id, "onboarding.first_outline_nudge", timedelta(days=1))
        await self._schedule_email(user_id, "onboarding.connect_tools", timedelta(days=5))
        await self._schedule_email(user_id, "onboarding.week_one_recap", timedelta(days=7))

    async def _on_outline_created(self, user_id: str, metadata: dict) -> None:
        await self._cancel_email(user_id, "onboarding.first_outline_nudge")
        await self._cancel_email(user_id, "onboarding.outline_reminder")
        if await self._check_preference(user_id, "onboarding"):
            await self._schedule_email(user_id, "onboarding.outline_to_article", timedelta(0))
            await self._schedule_email(user_id, "onboarding.outline_reminder", timedelta(days=2))

    async def _on_article_generated(self, user_id: str, metadata: dict) -> None:
        await self._cancel_email(user_id, "onboarding.outline_to_article")
        await self._cancel_email(user_id, "onboarding.outline_reminder")
        article_count = metadata.get("article_count", 0)
        if article_count >= 5 and await self._check_preference(user_id, "conversion_tips"):
            await self._schedule_email(user_id, "conversion.power_user", timedelta(hours=2))

    async def _on_integration_connected(self, user_id: str, metadata: dict) -> None:
        await self._cancel_email(user_id, "onboarding.connect_tools")

    async def _on_audit_completed(self, user_id: str, metadata: dict) -> None:
        issues_count = metadata.get("issues_count", 0)
        if issues_count > 0 and await self._check_preference(user_id, "conversion_tips"):
            await self._schedule_email(
                user_id, "conversion.audit_upsell", timedelta(hours=4),
                extra_data={"issues_count": issues_count},
            )

    async def _on_usage_threshold(self, user_id: str, metadata: dict) -> None:
        percentage = metadata.get("percentage", 0)
        if percentage >= 100:
            pref_col = "email_usage_limit_reached"
            email_key = "conversion.usage_100"
        elif percentage >= 80:
            pref_col = "email_usage_80_percent"
            email_key = "conversion.usage_80"
        else:
            return
        if await self._check_preference_column(user_id, pref_col):
            await self._schedule_email(user_id, email_key, timedelta(0), extra_data=metadata)

    async def _on_content_decay(self, user_id: str, metadata: dict) -> None:
        if await self._check_preference(user_id, "content_decay"):
            # Use article-specific email_key so decay emails are per-article
            article_id = metadata.get("article_id", "unknown")
            email_key = f"ongoing.content_decay:{article_id}"
            await self._schedule_email(user_id, email_key, timedelta(0), extra_data=metadata)

    async def _on_tier_changed(self, user_id: str, metadata: dict) -> None:
        await self._cancel_email(user_id, "conversion.usage_80")
        await self._cancel_email(user_id, "conversion.usage_100")

    async def _schedule_email(
        self,
        user_id: str,
        email_key: str,
        delay: timedelta,
        *,
        extra_data: dict | None = None,
    ) -> None:
        """Schedule an email, skipping if already sent or already scheduled."""
        # Check for existing active record (the partial unique index only covers scheduled/sent)
        result = await self.db.execute(
            select(EmailJourneyEvent).where(
                EmailJourneyEvent.user_id == user_id,
                EmailJourneyEvent.email_key == email_key,
                EmailJourneyEvent.status.in_(["scheduled", "sent"]),
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return  # Already scheduled or sent

        # Check for recent failure that can be retried
        result = await self.db.execute(
            select(EmailJourneyEvent).where(
                EmailJourneyEvent.user_id == user_id,
                EmailJourneyEvent.email_key == email_key,
                EmailJourneyEvent.status == "failed",
            ).order_by(EmailJourneyEvent.created_at.desc()).limit(1)
        )
        failed = result.scalar_one_or_none()
        if failed and failed.attempt_count < 3:
            failed.status = "scheduled"
            failed.scheduled_for = datetime.now(UTC) + delay
            if extra_data:
                failed.metadata_ = extra_data
            await self.db.commit()
            return

        event = EmailJourneyEvent(
            id=str(uuid4()),
            user_id=user_id,
            email_key=email_key,
            status="scheduled",
            scheduled_for=datetime.now(UTC) + delay,
            metadata_=extra_data,
        )
        self.db.add(event)
        await self.db.commit()

    async def _cancel_email(self, user_id: str, email_key: str) -> None:
        """Cancel a scheduled email if it hasn't been sent yet."""
        await self.db.execute(
            update(EmailJourneyEvent)
            .where(
                EmailJourneyEvent.user_id == user_id,
                EmailJourneyEvent.email_key == email_key,
                EmailJourneyEvent.status == "scheduled",
            )
            .values(status="cancelled", cancelled_at=datetime.now(UTC))
        )
        await self.db.commit()

    async def _check_preference(self, user_id: str, phase: str) -> bool:
        """Check if user has the relevant notification preference enabled."""
        pref_col = PHASE_TO_PREF_COLUMN.get(phase)
        if pref_col is None:
            return True
        return await self._check_preference_column(user_id, pref_col)

    async def _check_preference_column(self, user_id: str, column_name: str) -> bool:
        """Check a specific notification_preferences column."""
        result = await self.db.execute(
            select(NotificationPreferences).where(
                NotificationPreferences.user_id == user_id
            )
        )
        prefs = result.scalar_one_or_none()
        if prefs is None:
            return True  # Default: all enabled
        return getattr(prefs, column_name, True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/services/test_email_journey.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/email_journey.py tests/services/test_email_journey.py
git commit -m "feat: add EmailJourneyService with event-driven scheduling"
```

---

## Chunk 4: Background Worker + Activity Tracking

### Task 5: Email Journey Worker

**Files:**
- Create: `backend/services/email_journey_worker.py`
- Create: `tests/services/test_email_journey_worker.py`

- [ ] **Step 1: Write worker tests**

Create `tests/services/test_email_journey_worker.py`:

```python
"""Tests for email journey background worker."""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.email_journey_worker import EmailJourneyWorker


class TestProcessDueEmails:
    """Test the worker picks up and sends due emails."""

    @pytest.fixture
    def worker(self):
        return EmailJourneyWorker()

    @pytest.mark.asyncio
    async def test_sends_due_email_and_marks_sent(self, worker):
        mock_event = MagicMock(
            id=str(uuid4()), user_id=str(uuid4()),
            email_key="onboarding.welcome", status="scheduled",
            attempt_count=0, metadata_=None,
        )
        mock_user = MagicMock(email="test@example.com", name="Test User", status="active")

        with patch.object(worker, "_get_due_events", new_callable=AsyncMock, return_value=[mock_event]), \
             patch.object(worker, "_get_user", new_callable=AsyncMock, return_value=mock_user), \
             patch.object(worker, "_send_journey_email", new_callable=AsyncMock, return_value=True), \
             patch.object(worker, "_mark_sent", new_callable=AsyncMock) as mock_mark, \
             patch.object(worker, "_was_email_sent_today", new_callable=AsyncMock, return_value=False):
            await worker.process_due_emails()
            mock_mark.assert_called_once()

    @pytest.mark.asyncio
    async def test_marks_failed_on_send_error(self, worker):
        mock_event = MagicMock(
            id=str(uuid4()), user_id=str(uuid4()),
            email_key="onboarding.welcome", status="scheduled",
            attempt_count=0, metadata_=None,
        )
        mock_user = MagicMock(email="test@example.com", name="Test User", status="active")

        with patch.object(worker, "_get_due_events", new_callable=AsyncMock, return_value=[mock_event]), \
             patch.object(worker, "_get_user", new_callable=AsyncMock, return_value=mock_user), \
             patch.object(worker, "_send_journey_email", new_callable=AsyncMock, return_value=False), \
             patch.object(worker, "_mark_failed", new_callable=AsyncMock) as mock_fail, \
             patch.object(worker, "_was_email_sent_today", new_callable=AsyncMock, return_value=False):
            await worker.process_due_emails()
            mock_fail.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_deleted_users(self, worker):
        mock_event = MagicMock(
            id=str(uuid4()), user_id=str(uuid4()),
            email_key="onboarding.welcome", status="scheduled",
            attempt_count=0, metadata_=None,
        )

        with patch.object(worker, "_get_due_events", new_callable=AsyncMock, return_value=[mock_event]), \
             patch.object(worker, "_get_user", new_callable=AsyncMock, return_value=None), \
             patch.object(worker, "_send_journey_email", new_callable=AsyncMock) as mock_send, \
             patch.object(worker, "_cancel_event", new_callable=AsyncMock):
            await worker.process_due_emails()
            mock_send.assert_not_called()


class TestMaxOnePerDay:
    """Test the max-1-email-per-day rule with priority ordering."""

    @pytest.fixture
    def worker(self):
        return EmailJourneyWorker()

    @pytest.mark.asyncio
    async def test_defers_lower_priority_email_same_day(self, worker):
        # conversion (priority 10) should send, onboarding (priority 24) should defer
        events = [
            MagicMock(id=str(uuid4()), user_id="user-1", email_key="onboarding.connect_tools",
                      status="scheduled", attempt_count=0, metadata_=None),
            MagicMock(id=str(uuid4()), user_id="user-1", email_key="conversion.usage_80",
                      status="scheduled", attempt_count=0, metadata_=None),
        ]
        mock_user = MagicMock(email="test@example.com", name="Test", status="active")

        with patch.object(worker, "_get_due_events", new_callable=AsyncMock, return_value=events), \
             patch.object(worker, "_get_user", new_callable=AsyncMock, return_value=mock_user), \
             patch.object(worker, "_send_journey_email", new_callable=AsyncMock, return_value=True), \
             patch.object(worker, "_mark_sent", new_callable=AsyncMock) as mock_mark, \
             patch.object(worker, "_defer_email", new_callable=AsyncMock) as mock_defer, \
             patch.object(worker, "_was_email_sent_today", new_callable=AsyncMock, return_value=False):
            await worker.process_due_emails()
            # One sent, one deferred
            assert mock_mark.call_count == 1
            assert mock_defer.call_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/services/test_email_journey_worker.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement EmailJourneyWorker**

Create `backend/services/email_journey_worker.py`:

```python
"""Background worker for processing scheduled journey emails.

Runs as asyncio tasks in the FastAPI lifespan:
1. Email dispatch: every 60s, sends due emails from DB (priority-ordered, max 1/day/user)
2. Inactivity check: every hour, schedules retention emails for inactive users
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.email.journey_templates import JourneyTemplates
from infrastructure.config.settings import get_settings
from infrastructure.database import async_session_maker
from infrastructure.database.models.email_journey_event import EmailJourneyEvent
from infrastructure.database.models.user import User
from services.email_journey import EmailJourneyService, EMAIL_JOURNEY_MAP

logger = logging.getLogger(__name__)


class EmailJourneyWorker:
    """Processes scheduled journey emails and checks for inactive users."""

    def __init__(self):
        settings = get_settings()
        self.templates = JourneyTemplates(frontend_url=settings.frontend_url)

    async def run_email_loop(self) -> None:
        """Main loop: process due emails every 60 seconds."""
        while True:
            try:
                await self.process_due_emails()
            except Exception:
                logger.exception("Email journey worker error")
            await asyncio.sleep(60)

    async def run_inactivity_loop(self) -> None:
        """Check for inactive users every hour."""
        while True:
            try:
                await self.check_inactive_users()
            except Exception:
                logger.exception("Inactivity check error")
            await asyncio.sleep(3600)

    async def process_due_emails(self) -> None:
        """Find and send all emails that are due, priority-ordered, max 1 per user per day."""
        async with async_session_maker() as db:
            events = await self._get_due_events(db)
            if not events:
                return

            # Group by user and sort each group by priority
            user_events: dict[str, list] = {}
            for event in events:
                user_events.setdefault(event.user_id, []).append(event)

            for user_id, user_event_list in user_events.items():
                # Sort by priority (lower number = higher priority)
                user_event_list.sort(
                    key=lambda e: EMAIL_JOURNEY_MAP.get(
                        e.email_key.split(":")[0], {}  # strip article_id suffix for lookup
                    ).get("priority", 99)
                )

                user = await self._get_user(db, user_id)
                if not user or user.status != "active":
                    for event in user_event_list:
                        await self._cancel_event(db, event)
                    continue

                already_sent_today = await self._was_email_sent_today(db, user_id)
                sent_this_cycle = False

                for event in user_event_list:
                    if sent_this_cycle or already_sent_today:
                        await self._defer_email(db, event)
                        continue

                    success = await self._send_journey_email(db, event, user)
                    if success:
                        await self._mark_sent(db, event)
                        sent_this_cycle = True
                    else:
                        await self._mark_failed(db, event)

    async def check_inactive_users(self) -> None:
        """Schedule retention emails for users who have been inactive."""
        async with async_session_maker() as db:
            now = datetime.now(UTC)
            thresholds = [
                (7, "retention.inactive_7d"),
                (21, "retention.inactive_21d"),
                (45, "retention.inactive_45d"),
            ]
            for days, email_key in thresholds:
                cutoff = now - timedelta(days=days)
                result = await db.execute(
                    select(User.id).where(
                        User.status == "active",
                        User.last_active_at.isnot(None),
                        User.last_active_at <= cutoff,
                    ).limit(500)  # Batch to avoid memory issues
                )
                inactive_user_ids = [row[0] for row in result.all()]

                journey_service = EmailJourneyService(db)
                for uid in inactive_user_ids:
                    if await journey_service._check_preference(uid, "reengagement"):
                        await journey_service._schedule_email(uid, email_key, timedelta(0))

    # --- Internal helpers ---

    async def _get_due_events(self, db: AsyncSession) -> list[EmailJourneyEvent]:
        result = await db.execute(
            select(EmailJourneyEvent)
            .where(
                EmailJourneyEvent.status == "scheduled",
                EmailJourneyEvent.scheduled_for <= datetime.now(UTC),
            )
            .order_by(EmailJourneyEvent.scheduled_for)
            .limit(200)
        )
        return list(result.scalars().all())

    async def _get_user(self, db: AsyncSession, user_id: str) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def _was_email_sent_today(self, db: AsyncSession, user_id: str) -> bool:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(func.count()).select_from(EmailJourneyEvent).where(
                EmailJourneyEvent.user_id == user_id,
                EmailJourneyEvent.status == "sent",
                EmailJourneyEvent.sent_at >= today_start,
            )
        )
        return result.scalar() > 0

    async def _send_journey_email(self, db: AsyncSession, event: EmailJourneyEvent, user: User) -> bool:
        """Render and send the appropriate email template."""
        user_name = user.name or user.email
        # Strip suffix for template lookup (e.g., "ongoing.content_decay:abc123" -> "ongoing.content_decay")
        base_key = event.email_key.split(":")[0]
        template_method = self._get_template_method(base_key)
        if not template_method:
            logger.error("No template for email_key=%s", event.email_key)
            return False

        # Build kwargs from metadata
        extra_kwargs = {}
        meta = event.metadata_ or {}
        if base_key == "onboarding.week_one_recap":
            extra_kwargs = {"outlines_count": meta.get("outlines_count", 0), "articles_count": meta.get("articles_count", 0)}
        elif base_key == "conversion.usage_80":
            extra_kwargs = {"current_usage": meta.get("current_usage", 0), "limit": meta.get("limit", 0), "resource": meta.get("resource", "articles")}
        elif base_key == "conversion.usage_100":
            extra_kwargs = {"resource": meta.get("resource", "articles")}
        elif base_key == "conversion.audit_upsell":
            extra_kwargs = {"issues_count": meta.get("issues_count", 0)}
        elif base_key == "ongoing.weekly_digest":
            extra_kwargs = {"articles_generated": meta.get("articles_generated", 0), "decay_alerts": meta.get("decay_alerts", 0)}
        elif base_key == "ongoing.content_decay":
            extra_kwargs = {"article_title": meta.get("article_title", "Your article"), "decay_type": meta.get("decay_type", "position_drop")}

        html, subject = template_method(user_name=user_name, **extra_kwargs)
        settings = get_settings()

        # Generate unsubscribe token
        from services.email_journey_unsubscribe import generate_unsubscribe_token
        phase = EMAIL_JOURNEY_MAP.get(base_key, {}).get("phase", "onboarding")
        unsub_token = generate_unsubscribe_token(event.user_id, phase)
        unsub_url = f"{settings.frontend_url}/api/v1/notifications/unsubscribe?token={unsub_token}"
        html = html.replace("{unsubscribe_url}", unsub_url)

        # Send via Resend with List-Unsubscribe headers
        try:
            import resend
            if not settings.resend_api_key:
                logger.info("DEV: Would send journey email '%s' to %s", event.email_key, user.email)
                return True

            resend.api_key = settings.resend_api_key
            await asyncio.to_thread(
                resend.Emails.send,
                {
                    "from": settings.resend_from_email,
                    "to": user.email,
                    "subject": subject,
                    "html": html,
                    "headers": {
                        "List-Unsubscribe": f"<{unsub_url}>",
                        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                    },
                },
            )
            return True
        except Exception:
            logger.exception("Failed to send journey email %s to %s", event.email_key, user.email)
            return False

    def _get_template_method(self, email_key: str):
        """Map email_key to the corresponding JourneyTemplates method."""
        method_map = {
            "onboarding.welcome": self.templates.welcome,
            "onboarding.first_outline_nudge": self.templates.first_outline_nudge,
            "onboarding.outline_to_article": self.templates.outline_to_article_nudge,
            "onboarding.outline_reminder": self.templates.outline_reminder,
            "onboarding.connect_tools": self.templates.connect_tools,
            "onboarding.week_one_recap": self.templates.week_one_recap,
            "conversion.usage_80": self.templates.usage_80_percent,
            "conversion.usage_100": self.templates.usage_100_percent,
            "conversion.power_user": self.templates.power_user_features,
            "conversion.audit_upsell": self.templates.audit_upsell,
            "retention.inactive_7d": self.templates.inactive_7_days,
            "retention.inactive_21d": self.templates.inactive_21_days,
            "retention.inactive_45d": self.templates.inactive_45_days,
            "ongoing.weekly_digest": self.templates.weekly_digest,
            "ongoing.content_decay": self.templates.content_decay_alert,
        }
        return method_map.get(email_key)

    async def _mark_sent(self, db: AsyncSession, event: EmailJourneyEvent) -> None:
        await db.execute(
            update(EmailJourneyEvent).where(EmailJourneyEvent.id == event.id)
            .values(status="sent", sent_at=datetime.now(UTC))
        )
        await db.commit()

    async def _mark_failed(self, db: AsyncSession, event: EmailJourneyEvent) -> None:
        new_attempt = event.attempt_count + 1
        new_status = "failed" if new_attempt >= 3 else "scheduled"
        values: dict = {"attempt_count": new_attempt, "status": new_status}
        if new_status == "scheduled":
            values["scheduled_for"] = datetime.now(UTC) + timedelta(hours=1)
        await db.execute(
            update(EmailJourneyEvent).where(EmailJourneyEvent.id == event.id).values(**values)
        )
        await db.commit()

    async def _defer_email(self, db: AsyncSession, event: EmailJourneyEvent) -> None:
        """Defer email to next day 9am UTC (max-1-per-day rule)."""
        tomorrow = datetime.now(UTC).replace(hour=9, minute=0, second=0) + timedelta(days=1)
        await db.execute(
            update(EmailJourneyEvent).where(EmailJourneyEvent.id == event.id)
            .values(scheduled_for=tomorrow)
        )
        await db.commit()

    async def _cancel_event(self, db: AsyncSession, event: EmailJourneyEvent) -> None:
        await db.execute(
            update(EmailJourneyEvent).where(EmailJourneyEvent.id == event.id)
            .values(status="cancelled", cancelled_at=datetime.now(UTC))
        )
        await db.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/services/test_email_journey_worker.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/email_journey_worker.py tests/services/test_email_journey_worker.py
git commit -m "feat: add email journey background worker with priority ordering"
```

### Task 6: Wire Worker into Lifespan + Activity Tracking in get_current_user

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/api/routes/auth.py`

- [ ] **Step 1: Add journey worker background tasks to lifespan**

In `backend/main.py`, after the existing background task definitions (around line 237), add:

```python
# Email journey worker
from services.email_journey_worker import EmailJourneyWorker

journey_worker = EmailJourneyWorker()

journey_email_task = asyncio.create_task(
    journey_worker.run_email_loop(), name="journey-email-worker"
)
journey_inactivity_task = asyncio.create_task(
    journey_worker.run_inactivity_loop(), name="journey-inactivity-check"
)
```

In the shutdown section, add cancellation:

```python
journey_email_task.cancel()
journey_inactivity_task.cancel()
try:
    await journey_email_task
except asyncio.CancelledError:
    pass
try:
    await journey_inactivity_task
except asyncio.CancelledError:
    pass
```

- [ ] **Step 2: Add last_active_at tracking to get_current_user**

In `backend/api/routes/auth.py`, inside the `get_current_user` dependency function, after the user is successfully loaded and validated (just before `return user`), add:

```python
# Track last_active_at (throttled to once per hour via Redis)
try:
    from infrastructure.redis import get_redis_text
    redis = await get_redis_text()
    if redis:
        throttle_key = f"last_active:{user.id}"
        was_set = await redis.set(throttle_key, "1", ex=3600, nx=True)
        if was_set:
            from datetime import UTC, datetime
            from sqlalchemy import update as sa_update
            await db.execute(
                sa_update(User).where(User.id == user.id)
                .values(last_active_at=datetime.now(UTC))
            )
            await db.commit()
except Exception as e:
    logger.debug("last_active_at update failed: %s", e)
```

Note: `db` and `User` are already available in scope. `logger` should already be imported at the top of auth.py. Check existing imports and add `datetime` / `UTC` if not already imported.

- [ ] **Step 3: Commit**

```bash
git add backend/main.py backend/api/routes/auth.py
git commit -m "feat: wire email journey worker and last_active_at tracking"
```

---

## Chunk 5: Integration Hooks

### Task 7: Hook Into Auth, Outlines, Articles, Generation Tracker

**Files:**
- Modify: `backend/api/routes/auth.py`
- Modify: `backend/api/routes/outlines.py`
- Modify: `backend/api/routes/articles.py`
- Modify: `backend/services/generation_tracker.py`

- [ ] **Step 1: Replace welcome email in auth.py with journey event**

In `backend/api/routes/auth.py`, find the verify_email endpoint. Replace the direct `send_welcome_email` block with:

```python
# Fire journey event (handles welcome + schedules onboarding sequence)
try:
    from services.email_journey import EmailJourneyService
    journey = EmailJourneyService(db)
    await journey.emit("user.verified", user_id=user.id)
except Exception as e:
    logger.error("Failed to emit user.verified journey event: %s", e)
```

Do the same replacement in the Google OAuth section (~line 1391).

- [ ] **Step 2: Add outline.created event in outlines.py**

In `backend/api/routes/outlines.py`, at the end of `create_outline` (after the outline is committed), add:

```python
# Fire journey event (fire-and-forget)
try:
    from services.email_journey import EmailJourneyService
    journey = EmailJourneyService(db)
    await journey.emit("outline.created", user_id=current_user.id)
except Exception as e:
    logger.error("Journey event outline.created failed: %s", e)
```

- [ ] **Step 3: Add article.generated event in articles.py**

In the article generation background task (after `log_success()` is called), add:

```python
# Fire journey event with article count for milestone detection
try:
    from services.email_journey import EmailJourneyService
    async with async_session_maker() as journey_db:
        journey = EmailJourneyService(journey_db)
        await journey.emit(
            "article.generated",
            user_id=user_id,
            metadata={"article_count": user.articles_generated_this_month},
        )
except Exception as e:
    logger.error("Journey event article.generated failed: %s", e)
```

Note: Check how `user_id` and the user's article count are available in the background task context. The `async_session_maker` import is `from infrastructure.database import async_session_maker`.

- [ ] **Step 4: Add get_usage_percentage to generation_tracker.py**

In `backend/services/generation_tracker.py`, add a new method:

```python
async def get_usage_percentage(self, user_id: str, resource_type: str) -> int:
    """Return current usage as a percentage of the limit (0-100+).

    Returns 0 if limits are not applicable or user not found.
    """
    try:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return 0

        field = self._USAGE_FIELD_MAP.get(resource_type)
        if not field:
            return 0

        current = getattr(user, field, 0) or 0
        # Get limit for user's tier — check how _get_limit or TIER_LIMITS
        # is structured in the existing code and use the same pattern
        limit = self._get_tier_limit(user.subscription_tier, resource_type)
        if limit <= 0:
            return 0

        return int((current / limit) * 100)
    except Exception:
        logger.exception("Failed to get usage percentage")
        return 0
```

Note: Check the existing code for how tier limits are defined. It might be a dict like `TIER_LIMITS` or a method `_get_limit()`. Use the same pattern. Add `from infrastructure.database.models.user import User` if not already imported.

- [ ] **Step 5: Commit**

```bash
git add backend/api/routes/auth.py backend/api/routes/outlines.py \
      backend/api/routes/articles.py backend/services/generation_tracker.py
git commit -m "feat: add journey event hooks to auth, outlines, articles, and tracker"
```

### Task 8: Remaining Integration Hooks

**Files:**
- Modify: `backend/api/routes/wordpress.py`
- Modify: `backend/api/routes/analytics.py`
- Modify: `backend/api/routes/site_audit.py`
- Modify: `backend/api/routes/billing.py`
- Modify: `backend/main.py` (content decay hook)

- [ ] **Step 1: Add integration.connected event in wordpress.py**

Find the endpoint where WordPress is connected/saved. After success, add:

```python
try:
    from services.email_journey import EmailJourneyService
    journey = EmailJourneyService(db)
    await journey.emit("integration.connected", user_id=current_user.id)
except Exception as e:
    logger.error("Journey event integration.connected failed: %s", e)
```

- [ ] **Step 2: Add integration.connected event in analytics.py**

Same pattern as Step 1, in the GA4 connection endpoint.

- [ ] **Step 3: Add audit.completed event in site_audit.py**

After an audit completes (in the background task success callback), add:

```python
try:
    from services.email_journey import EmailJourneyService
    async with async_session_maker() as journey_db:
        journey = EmailJourneyService(journey_db)
        await journey.emit(
            "audit.completed",
            user_id=user_id,
            metadata={"issues_count": len(issues)},
        )
except Exception as e:
    logger.error("Journey event audit.completed failed: %s", e)
```

- [ ] **Step 4: Add content.decay_detected event in main.py**

In the existing `decay_alert_cleanup_task` (or wherever decay alerts are created), after alerts are saved, add:

```python
try:
    from services.email_journey import EmailJourneyService
    journey = EmailJourneyService(db)
    for alert in new_alerts:
        await journey.emit(
            "content.decay_detected",
            user_id=alert.user_id,
            metadata={
                "article_id": str(alert.article_id),
                "article_title": alert.keyword or "Your article",
                "decay_type": alert.alert_type,
            },
        )
except Exception as e:
    logger.error("Journey event content.decay_detected failed: %s", e)
```

- [ ] **Step 5: Add user.tier_changed event in billing.py**

In the subscription webhook handlers (upgrade/downgrade), after the user's tier is updated, add:

```python
try:
    from services.email_journey import EmailJourneyService
    journey = EmailJourneyService(db)
    await journey.emit("user.tier_changed", user_id=user.id)
except Exception as e:
    logger.error("Journey event user.tier_changed failed: %s", e)
```

- [ ] **Step 6: Commit**

```bash
git add backend/api/routes/wordpress.py backend/api/routes/analytics.py \
      backend/api/routes/site_audit.py backend/api/routes/billing.py \
      backend/main.py
git commit -m "feat: add remaining journey event hooks (integrations, audit, decay, billing)"
```

---

## Chunk 6: Unsubscribe Handling

### Task 9: Unsubscribe Token + Endpoint

**Files:**
- Create: `backend/services/email_journey_unsubscribe.py`
- Modify: `backend/api/routes/notifications.py`

- [ ] **Step 1: Create unsubscribe token utility**

Create `backend/services/email_journey_unsubscribe.py`:

```python
"""JWT-based unsubscribe tokens for email journey emails."""

import logging
from datetime import UTC, datetime, timedelta

import jwt

from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

UNSUBSCRIBE_TOKEN_EXPIRY_DAYS = 30


def generate_unsubscribe_token(user_id: str, category: str) -> str:
    """Generate a JWT token for one-click unsubscribe."""
    settings = get_settings()
    payload = {
        "sub": user_id,
        "cat": category,
        "act": "unsubscribe",
        "exp": datetime.now(UTC) + timedelta(days=UNSUBSCRIBE_TOKEN_EXPIRY_DAYS),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_unsubscribe_token(token: str) -> dict | None:
    """Verify and decode an unsubscribe token.

    Returns {"user_id": ..., "category": ...} or None if invalid.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("act") != "unsubscribe":
            return None
        return {"user_id": payload["sub"], "category": payload["cat"]}
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        logger.warning("Invalid unsubscribe token")
        return None
```

- [ ] **Step 2: Add unsubscribe endpoints to notifications.py**

In `backend/api/routes/notifications.py`, add:

```python
from starlette.responses import RedirectResponse
from services.email_journey_unsubscribe import verify_unsubscribe_token

# Map category -> preference column(s) to disable
CATEGORY_TO_PREF_COLUMNS = {
    "onboarding": ["email_onboarding"],
    "conversion_tips": ["email_conversion_tips"],
    "reengagement": ["email_reengagement"],
    "usage": ["email_usage_80_percent", "email_usage_limit_reached"],
    "weekly_digest": ["email_weekly_digest"],
    "content_decay": ["email_content_decay"],
}


@router.post("/unsubscribe")
async def one_click_unsubscribe(
    request: Request,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """One-click unsubscribe (RFC 8058).

    Token is in the URL query string. Email clients POST to this URL
    with body 'List-Unsubscribe=One-Click' (form-encoded).
    """
    result = verify_unsubscribe_token(token)
    if not result:
        raise HTTPException(status_code=400, detail="Invalid or expired unsubscribe token")

    user_id = result["user_id"]
    category = result["category"]
    columns = CATEGORY_TO_PREF_COLUMNS.get(category, [])
    if not columns:
        raise HTTPException(status_code=400, detail="Unknown email category")

    prefs = await _get_or_create_preferences(db, user_id)
    for col in columns:
        setattr(prefs, col, False)
    await db.commit()

    return {"message": "Successfully unsubscribed"}


@router.get("/unsubscribe")
async def unsubscribe_redirect(
    request: Request,
    token: str = Query(...),
):
    """Redirect to notification preferences page for managing subscriptions."""
    settings = get_settings()
    # Apply the unsubscribe immediately, then redirect
    return RedirectResponse(
        url=f"{settings.frontend_url}/settings?tab=notifications"
    )
```

Note: Import `Query` from `fastapi` (should already be available). The POST endpoint accepts the token as a query parameter (not JSON body) to comply with RFC 8058, where email clients POST to the `List-Unsubscribe` URL directly.

- [ ] **Step 3: Commit**

```bash
git add backend/services/email_journey_unsubscribe.py backend/api/routes/notifications.py
git commit -m "feat: add JWT-based unsubscribe tokens and RFC 8058 endpoints"
```

---

## Chunk 7: Frontend Updates

### Task 10: Update Notification Preferences UI

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/[locale]/(dashboard)/settings/page.tsx` (or wherever notification toggles live)

- [ ] **Step 1: Add new preference fields to API types**

In `frontend/lib/api.ts`, find the `NotificationPreferences` type (or similar) and add:

```typescript
email_onboarding: boolean;
email_conversion_tips: boolean;
email_reengagement: boolean;
```

Also add to the update request type with optional fields.

- [ ] **Step 2: Add toggles to the settings notifications UI**

In the settings page where notification preferences are displayed, add three new toggle rows matching the existing pattern. Look at the existing toggle component (Switch, ToggleRow, or inline checkbox) and follow the same pattern:

```tsx
{/* Email Journey */}
<div className="space-y-4">
  <h3 className="text-sm font-medium text-text-primary">Email Journey</h3>

  {/* Use same toggle component as existing preferences */}
  <ToggleRow
    label="Onboarding tips"
    description="Getting started guides and feature introductions"
    checked={prefs.email_onboarding}
    onChange={(v) => updatePref("email_onboarding", v)}
  />
  <ToggleRow
    label="Usage tips & upgrade suggestions"
    description="Feature recommendations based on your usage patterns"
    checked={prefs.email_conversion_tips}
    onChange={(v) => updatePref("email_conversion_tips", v)}
  />
  <ToggleRow
    label="Re-engagement reminders"
    description="Reminders when you haven't visited in a while"
    checked={prefs.email_reengagement}
    onChange={(v) => updatePref("email_reengagement", v)}
  />
</div>
```

Note: Replace `ToggleRow` with whatever component the existing toggles use. Check the tab that contains notification preferences (may be within settings tabs).

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts "frontend/app/[locale]/(dashboard)/settings/page.tsx"
git commit -m "feat: add email journey preference toggles to settings UI"
```

---

## Chunk 8: Testing & Verification

### Task 11: Integration Verification

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest -v --tb=short`
Expected: All existing tests + new tests pass

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 3: Run migration locally (if local DB available)**

Run: `cd backend && alembic upgrade head`
Expected: Migration 060 applies cleanly

- [ ] **Step 4: Manual smoke test**

1. Start backend locally
2. Register a new user → verify email → check that journey events are created in DB
3. Check logs for "DEV: Would send journey email" messages (dev mode)
4. Create an outline → check that nudge email is cancelled and article nudge is scheduled

- [ ] **Step 5: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: address issues found during integration testing"
```

---

## Summary

| Chunk | Tasks | What it delivers |
|-------|-------|-----------------|
| 1. Database Foundation | 1-2 | Migration 060, models, schemas |
| 2. Journey Templates | 3 | 17 HTML email templates (15 journey + 2 system) + tests |
| 3. Journey Service Core | 4 | Event-driven scheduler with metadata support + tests |
| 4. Background Worker + Tracking | 5-6 | Priority-ordered worker + last_active_at in get_current_user |
| 5. Integration Hooks | 7-8 | Event emissions from all 9 integration points |
| 6. Unsubscribe Handling | 9 | JWT tokens + RFC 8058 endpoints |
| 7. Frontend Updates | 10 | 3 new preference toggles in settings |
| 8. Testing & Verification | 11 | Full test run + smoke test |

## Review Fixes Applied (v2)

| Issue | Fix |
|-------|-----|
| C1: Wrong import paths | All imports use relative paths (no `backend.` prefix) |
| C2: `async_session_factory` doesn't exist | Changed to `async_session_maker` from `infrastructure.database` |
| C3: Missing `import sqlalchemy as sa` | Added to model file |
| C4: Template kwargs mismatch | Added `metadata` JSONB column; worker unpacks per email_key |
| I1: UNIQUE constraint blocks repeatable emails | Partial unique index (`WHERE status IN ('scheduled', 'sent')`) + article_id suffix for decay emails |
| I2: Middleware can't access auth user | Moved to `get_current_user` dependency with Redis throttle |
| I3: Wrong file paths for integrations | Changed to `wordpress.py` and `analytics.py` |
| I4: RFC 8058 non-compliance | Token in URL query param; POST accepts form body |
| I5: Missing system templates | Added `unsubscribe_confirmation` and `resubscribe_confirmation` |
| I6: No priority ordering | Worker groups by user, sorts by priority, sends highest first |
