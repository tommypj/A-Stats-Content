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

        # First call returns None (no active), second call returns the failed record
        no_result = MagicMock()
        no_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(side_effect=[no_result, mock_result])
        service.db.commit = AsyncMock()

        await service._schedule_email(user_id, "onboarding.welcome", timedelta(0))
        assert existing.status == "scheduled"
