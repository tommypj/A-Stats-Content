"""Tests for EmailJourneyWorker."""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

from services.email_journey import EMAIL_JOURNEY_MAP
from services.email_journey_worker import EmailJourneyWorker


def _make_event(
    *,
    email_key: str = "onboarding.welcome",
    user_id: str | None = None,
    status: str = "scheduled",
    scheduled_for: datetime | None = None,
    metadata_: dict | None = None,
    attempt_count: int = 0,
):
    """Create a mock EmailJourneyEvent."""
    event = MagicMock()
    event.id = str(uuid4())
    event.user_id = user_id or str(uuid4())
    event.email_key = email_key
    event.status = status
    event.scheduled_for = scheduled_for or (datetime.now(UTC) - timedelta(minutes=5))
    event.sent_at = None
    event.cancelled_at = None
    event.attempt_count = attempt_count
    event.metadata_ = metadata_ or {}
    return event


def _make_user(*, user_id: str | None = None, status: str = "active", name: str = "Test User", email: str = "test@example.com"):
    """Create a mock User."""
    user = MagicMock()
    user.id = user_id or str(uuid4())
    user.status = status
    user.name = name
    user.email = email
    return user


class TestProcessDueEmails:
    """Test the email processing pipeline."""

    @pytest.mark.asyncio
    async def test_sends_due_email_and_marks_sent(self):
        """Test that a due email is sent and marked as sent."""
        worker = EmailJourneyWorker.__new__(EmailJourneyWorker)
        worker._settings = MagicMock()
        worker._settings.resend_api_key = None  # Dev mode
        worker._settings.frontend_url = "https://example.com"
        worker._settings.secret_key = "test-secret"
        worker._templates = MagicMock()

        user = _make_user()
        event = _make_event(email_key="onboarding.welcome", user_id=user.id)

        # Template returns (html, subject)
        worker._templates.welcome = MagicMock(return_value=("<html>{unsubscribe_url}</html>", "Welcome"))

        db = AsyncMock()

        # Mock: query for due events
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [event]

        # Mock: query for user
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        # Mock: query for sent-today count
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        db.execute = AsyncMock(side_effect=[events_result, user_result, count_result])
        db.commit = AsyncMock()

        await worker.process_due_emails(db)

        assert event.status == "sent"
        assert event.sent_at is not None
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_marks_failed_on_send_error(self):
        """Test that an event is marked as failed after 3 failed attempts."""
        worker = EmailJourneyWorker.__new__(EmailJourneyWorker)
        worker._settings = MagicMock()
        worker._settings.resend_api_key = "re_test_key"
        worker._settings.resend_from_email = "noreply@example.com"
        worker._settings.frontend_url = "https://example.com"
        worker._settings.secret_key = "test-secret"
        worker._templates = MagicMock()

        user = _make_user()
        event = _make_event(
            email_key="onboarding.welcome",
            user_id=user.id,
            attempt_count=2,  # This will be the 3rd attempt
        )

        worker._templates.welcome = MagicMock(return_value=("<html>{unsubscribe_url}</html>", "Welcome"))

        db = AsyncMock()

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [event]

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        db.execute = AsyncMock(side_effect=[events_result, user_result, count_result])
        db.commit = AsyncMock()

        # Make resend.Emails.send raise an error
        with patch("services.email_journey_worker.resend") as mock_resend:
            mock_resend.Emails.send.side_effect = Exception("API error")
            with patch("services.email_journey_worker.asyncio.to_thread", side_effect=Exception("API error")):
                await worker.process_due_emails(db)

        assert event.status == "failed"
        assert event.attempt_count == 3
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_skips_deleted_users(self):
        """Test that events for deleted/inactive users are cancelled."""
        worker = EmailJourneyWorker.__new__(EmailJourneyWorker)
        worker._settings = MagicMock()
        worker._settings.frontend_url = "https://example.com"
        worker._settings.secret_key = "test-secret"
        worker._templates = MagicMock()

        user = _make_user(status="deleted")
        event = _make_event(email_key="onboarding.welcome", user_id=user.id)

        db = AsyncMock()

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [event]

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        db.execute = AsyncMock(side_effect=[events_result, user_result])
        db.commit = AsyncMock()

        await worker.process_due_emails(db)

        assert event.status == "cancelled"
        assert event.cancelled_at is not None
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_defers_lower_priority_email_same_day(self):
        """Test that only the highest priority email is sent; others deferred to tomorrow."""
        worker = EmailJourneyWorker.__new__(EmailJourneyWorker)
        worker._settings = MagicMock()
        worker._settings.resend_api_key = None  # Dev mode
        worker._settings.frontend_url = "https://example.com"
        worker._settings.secret_key = "test-secret"
        worker._templates = MagicMock()

        user = _make_user()

        # conversion.usage_80 has priority 10, onboarding.welcome has priority 20
        conversion_event = _make_event(
            email_key="conversion.usage_80",
            user_id=user.id,
            metadata_={"current_usage": 8, "limit": 10, "resource": "articles"},
        )
        onboarding_event = _make_event(
            email_key="onboarding.welcome",
            user_id=user.id,
        )

        worker._templates.usage_80_percent = MagicMock(
            return_value=("<html>{unsubscribe_url}</html>", "Usage 80%")
        )
        worker._templates.welcome = MagicMock(
            return_value=("<html>{unsubscribe_url}</html>", "Welcome")
        )

        db = AsyncMock()

        events_result = MagicMock()
        # Return both events for same user (order doesn't matter — worker sorts by priority)
        events_result.scalars.return_value.all.return_value = [
            onboarding_event,
            conversion_event,
        ]

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        db.execute = AsyncMock(side_effect=[events_result, user_result, count_result])
        db.commit = AsyncMock()

        await worker.process_due_emails(db)

        # Conversion email (priority 10) should be sent
        assert conversion_event.status == "sent"
        assert conversion_event.sent_at is not None

        # Onboarding email (priority 20) should be deferred to tomorrow
        assert onboarding_event.status == "scheduled"
        assert onboarding_event.scheduled_for > datetime.now(UTC)
        # Should be deferred to tomorrow 9am UTC
        assert onboarding_event.scheduled_for.hour == 9
        assert onboarding_event.scheduled_for.minute == 0
