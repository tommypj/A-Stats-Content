"""
Unit tests for GenerationTracker service.

All database and Redis interactions are mocked so the tests run without any
real infrastructure.  Each test is fully independent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

from services.generation_tracker import GenerationTracker

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_session() -> AsyncMock:
    """Return a minimal mock that satisfies AsyncSession usage."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_project(
    project_id: str,
    tier: str = "free",
    articles_used: int = 0,
    outlines_used: int = 0,
    images_used: int = 0,
) -> MagicMock:
    """Build a mock Project with the usage fields needed by GenerationTracker."""
    project = MagicMock()
    project.id = project_id
    project.subscription_tier = tier
    project.articles_generated_this_month = articles_used
    project.outlines_generated_this_month = outlines_used
    project.images_generated_this_month = images_used
    project.usage_reset_date = None
    project.members = []
    return project


def _make_user(
    user_id: str,
    tier: str = "free",
    articles_used: int = 0,
) -> MagicMock:
    """Build a mock User with the usage fields needed by GenerationTracker."""
    user = MagicMock()
    user.id = user_id
    user.subscription_tier = tier
    user.articles_generated_this_month = articles_used
    user.outlines_generated_this_month = 0
    user.images_generated_this_month = 0
    return user


# ---------------------------------------------------------------------------
# Tests: log_start / log_success / log_failure lifecycle
# ---------------------------------------------------------------------------

class TestGenerationLog:
    """Tests for the generation logging lifecycle methods."""

    async def test_log_start_creates_record(self):
        """log_start should add a GenerationLog with status 'started'."""
        db = _make_db_session()
        tracker = GenerationTracker(db)

        user_id = str(uuid4())
        project_id = str(uuid4())
        resource_id = str(uuid4())

        log = await tracker.log_start(
            user_id=user_id,
            project_id=project_id,
            resource_type="article",
            resource_id=resource_id,
            input_metadata={"keyword": "seo"},
        )

        # The log entry was added to the session
        db.add.assert_called_once()
        db.flush.assert_called_once()

        assert log.status == "started"
        assert log.user_id == user_id
        assert log.project_id == project_id
        assert log.resource_type == "article"
        assert log.cost_credits == 0  # not charged yet

    async def test_log_success_marks_log_and_increments_usage(self):
        """log_success sets status to 'success' and triggers usage increment."""
        db = _make_db_session()
        tracker = GenerationTracker(db)

        log_id = str(uuid4())
        project_id = str(uuid4())

        # Build a fake log record
        fake_log = MagicMock()
        fake_log.id = log_id
        fake_log.project_id = project_id
        fake_log.resource_type = "article"

        # Patch DB execute to return the fake log
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = fake_log
        db.execute = AsyncMock(return_value=execute_result)

        with patch(
            "services.generation_tracker.ProjectUsageService"
        ) as MockUsageService:
            mock_usage = AsyncMock()
            MockUsageService.return_value = mock_usage

            await tracker.log_success(
                log_id=log_id,
                ai_model="claude-3-5-sonnet",
                duration_ms=1500,
            )

        assert fake_log.status == "success"
        assert fake_log.ai_model == "claude-3-5-sonnet"
        assert fake_log.duration_ms == 1500
        assert fake_log.cost_credits == 1

        # Usage should be incremented for the project
        mock_usage.increment_usage.assert_called_once_with(project_id, "articles")

    async def test_log_success_no_project_skips_usage_increment(self):
        """When project_id is None, log_success should NOT call usage service."""
        db = _make_db_session()
        tracker = GenerationTracker(db)

        log_id = str(uuid4())
        fake_log = MagicMock()
        fake_log.id = log_id
        fake_log.project_id = None  # personal workspace
        fake_log.resource_type = "article"

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = fake_log
        db.execute = AsyncMock(return_value=execute_result)

        with patch("services.generation_tracker.ProjectUsageService") as MockUsage:
            await tracker.log_success(log_id=log_id)

        MockUsage.assert_not_called()
        assert fake_log.status == "success"

    async def test_log_failure_sets_status_and_creates_alert(self):
        """log_failure marks status 'failed', cost=0, and creates an AdminAlert."""
        db = _make_db_session()
        tracker = GenerationTracker(db)

        log_id = str(uuid4())
        fake_log = MagicMock()
        fake_log.id = log_id
        fake_log.project_id = str(uuid4())
        fake_log.resource_type = "article"
        fake_log.resource_id = str(uuid4())
        fake_log.user_id = str(uuid4())

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = fake_log
        db.execute = AsyncMock(return_value=execute_result)

        await tracker.log_failure(
            log_id=log_id,
            error_message="AI service timed out",
        )

        assert fake_log.status == "failed"
        assert fake_log.cost_credits == 0
        assert fake_log.error_message == "AI service timed out"

        # An AdminAlert record was added to the session
        # db.add is called: once for the alert
        db.add.assert_called_once()
        alert_added = db.add.call_args[0][0]
        assert alert_added.alert_type == "generation_failed"
        assert "article" in alert_added.title.lower()

    async def test_log_failure_truncates_long_error_messages(self):
        """Error messages longer than 2000 chars should be truncated."""
        db = _make_db_session()
        tracker = GenerationTracker(db)

        log_id = str(uuid4())
        fake_log = MagicMock()
        fake_log.id = log_id
        fake_log.project_id = None
        fake_log.resource_type = "image"
        fake_log.resource_id = str(uuid4())
        fake_log.user_id = str(uuid4())

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = fake_log
        db.execute = AsyncMock(return_value=execute_result)

        long_error = "x" * 5000

        await tracker.log_failure(log_id=log_id, error_message=long_error)

        # error_message stored on the log must be truncated at 2000
        assert len(fake_log.error_message) == 2000


# ---------------------------------------------------------------------------
# Tests: check_limit — project-level (fail-closed)
# ---------------------------------------------------------------------------

class TestCheckLimitProjectLevel:
    """Tests for check_limit when a project_id is supplied."""

    async def test_check_limit_within_limit_returns_true(self):
        """Project has used fewer articles than its monthly cap."""
        project_id = str(uuid4())
        # free tier: 10 articles/month; 5 used -> should be allowed
        mock_project = _make_project(project_id, tier="free", articles_used=5)

        db = _make_db_session()

        with patch(
            "services.generation_tracker.ProjectUsageService"
        ) as MockUsage:
            mock_usage_instance = AsyncMock()
            mock_usage_instance.reset_project_usage_if_needed = AsyncMock(return_value=False)
            mock_usage_instance.check_project_limit = AsyncMock(return_value=True)
            MockUsage.return_value = mock_usage_instance

            tracker = GenerationTracker(db)
            result = await tracker.check_limit(
                project_id=project_id,
                resource_type="article",
            )

        assert result is True
        mock_usage_instance.check_project_limit.assert_called_once_with(
            project_id, "articles"
        )

    async def test_check_limit_exceeded_returns_false(self):
        """Project has reached its monthly article limit."""
        project_id = str(uuid4())

        db = _make_db_session()

        with patch(
            "services.generation_tracker.ProjectUsageService"
        ) as MockUsage:
            mock_usage_instance = AsyncMock()
            mock_usage_instance.reset_project_usage_if_needed = AsyncMock(return_value=False)
            mock_usage_instance.check_project_limit = AsyncMock(return_value=False)
            MockUsage.return_value = mock_usage_instance

            tracker = GenerationTracker(db)
            result = await tracker.check_limit(
                project_id=project_id,
                resource_type="article",
            )

        assert result is False

    async def test_check_limit_project_error_fails_closed(self):
        """
        If ProjectUsageService raises an exception the method must return False
        (fail-closed behavior — deny generation when limits can't be verified).
        """
        project_id = str(uuid4())
        db = _make_db_session()

        with patch(
            "services.generation_tracker.ProjectUsageService"
        ) as MockUsage:
            mock_usage_instance = AsyncMock()
            mock_usage_instance.reset_project_usage_if_needed = AsyncMock(
                side_effect=Exception("DB is down")
            )
            MockUsage.return_value = mock_usage_instance

            tracker = GenerationTracker(db)
            result = await tracker.check_limit(
                project_id=project_id,
                resource_type="article",
            )

        assert result is False

    async def test_check_limit_resets_usage_before_checking(self):
        """check_limit calls reset_project_usage_if_needed before checking."""
        project_id = str(uuid4())
        db = _make_db_session()

        reset_called = []

        with patch(
            "services.generation_tracker.ProjectUsageService"
        ) as MockUsage:
            mock_usage_instance = AsyncMock()

            async def _fake_reset(pid):
                reset_called.append(pid)
                return False

            mock_usage_instance.reset_project_usage_if_needed = _fake_reset
            mock_usage_instance.check_project_limit = AsyncMock(return_value=True)
            MockUsage.return_value = mock_usage_instance

            tracker = GenerationTracker(db)
            await tracker.check_limit(project_id=project_id, resource_type="article")

        assert project_id in reset_called


# ---------------------------------------------------------------------------
# Tests: check_limit — user-level (fail-open)
# ---------------------------------------------------------------------------

class TestCheckLimitUserLevel:
    """Tests for check_limit when project_id is None (personal workspace)."""

    async def test_check_limit_user_within_limit_returns_true(self):
        """User on free plan with 0 articles used this month — allowed."""
        user_id = str(uuid4())
        mock_user = _make_user(user_id, tier="free", articles_used=0)

        db = _make_db_session()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = mock_user
        db.execute = AsyncMock(return_value=execute_result)

        tracker = GenerationTracker(db)

        # Disable Redis to exercise the DB-level branch
        with patch("services.generation_tracker.settings") as mock_settings:
            mock_settings.redis_url = None
            result = await tracker.check_limit(
                project_id=None,
                resource_type="article",
                user_id=user_id,
            )

        assert result is True

    async def test_check_limit_user_exceeded_returns_false(self):
        """User on free plan that has already used all 5 articles."""
        user_id = str(uuid4())
        # free tier limit = 5; user used 5 -> exceeded
        mock_user = _make_user(user_id, tier="free", articles_used=5)

        db = _make_db_session()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = mock_user
        db.execute = AsyncMock(return_value=execute_result)

        tracker = GenerationTracker(db)

        with patch("services.generation_tracker.settings") as mock_settings:
            mock_settings.redis_url = None
            result = await tracker.check_limit(
                project_id=None,
                resource_type="article",
                user_id=user_id,
            )

        assert result is False

    async def test_check_limit_user_unlimited_plan_returns_true(self):
        """Enterprise user has no article cap (-1 = unlimited)."""
        user_id = str(uuid4())
        mock_user = _make_user(user_id, tier="enterprise", articles_used=9999)

        db = _make_db_session()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = mock_user
        db.execute = AsyncMock(return_value=execute_result)

        tracker = GenerationTracker(db)

        with patch("services.generation_tracker.settings") as mock_settings:
            mock_settings.redis_url = None
            result = await tracker.check_limit(
                project_id=None,
                resource_type="article",
                user_id=user_id,
            )

        assert result is True

    async def test_check_limit_user_not_found_returns_false(self):
        """If the user record doesn't exist, deny generation."""
        user_id = str(uuid4())

        db = _make_db_session()
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None  # user missing
        db.execute = AsyncMock(return_value=execute_result)

        tracker = GenerationTracker(db)

        with patch("services.generation_tracker.settings") as mock_settings:
            mock_settings.redis_url = None
            result = await tracker.check_limit(
                project_id=None,
                resource_type="article",
                user_id=user_id,
            )

        assert result is False

    async def test_check_limit_no_context_fails_open(self):
        """No project_id and no user_id — fail open (return True)."""
        db = _make_db_session()
        tracker = GenerationTracker(db)

        with patch("services.generation_tracker.settings") as mock_settings:
            mock_settings.redis_url = None
            result = await tracker.check_limit(
                project_id=None,
                resource_type="article",
                user_id=None,
            )

        assert result is True

    async def test_check_limit_user_db_exception_fails_open(self):
        """
        If user-level limit check raises an unexpected exception,
        the method should fail open (return True).
        """
        user_id = str(uuid4())
        db = _make_db_session()
        db.execute = AsyncMock(side_effect=Exception("Connection refused"))

        tracker = GenerationTracker(db)

        with patch("services.generation_tracker.settings") as mock_settings:
            mock_settings.redis_url = None
            result = await tracker.check_limit(
                project_id=None,
                resource_type="article",
                user_id=user_id,
            )

        assert result is True


# ---------------------------------------------------------------------------
# Tests: check_limit — Redis atomic counter
# ---------------------------------------------------------------------------

class TestCheckLimitRedisAtomicCounter:
    """Tests for the Redis-based atomic counter in check_limit."""

    async def test_redis_counter_within_limit_returns_true(self):
        """
        When Redis is configured and the counter is below the plan cap,
        check_limit returns True without hitting the DB for the limit check.
        """
        project_id = str(uuid4())
        db = _make_db_session()
        tracker = GenerationTracker(db)

        # Simulate Redis incrementing to 3 (below free-tier cap of 10)
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=3)
        mock_redis.expire = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with patch("services.generation_tracker.settings") as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379/0"

            with patch(
                "services.generation_tracker.GenerationTracker._get_limit",
                new_callable=AsyncMock,
                return_value=10,  # free-tier articles cap
            ):
                with patch("redis.asyncio.from_url", return_value=mock_redis):
                    result = await tracker.check_limit(
                        project_id=project_id,
                        resource_type="article",
                    )

        assert result is True
        mock_redis.incr.assert_called_once()
        mock_redis.aclose.assert_called_once()

    async def test_redis_counter_exceeded_returns_false(self):
        """Redis counter exceeds the cap — should deny generation."""
        project_id = str(uuid4())
        db = _make_db_session()
        tracker = GenerationTracker(db)

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=11)  # over cap=10
        mock_redis.expire = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with patch("services.generation_tracker.settings") as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379/0"

            with patch(
                "services.generation_tracker.GenerationTracker._get_limit",
                new_callable=AsyncMock,
                return_value=10,
            ):
                with patch("redis.asyncio.from_url", return_value=mock_redis):
                    result = await tracker.check_limit(
                        project_id=project_id,
                        resource_type="article",
                    )

        assert result is False

    async def test_redis_unlimited_plan_returns_true(self):
        """When limit is -1 (unlimited), Redis counter is irrelevant."""
        project_id = str(uuid4())
        db = _make_db_session()
        tracker = GenerationTracker(db)

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=99999)
        mock_redis.expire = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with patch("services.generation_tracker.settings") as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379/0"

            with patch(
                "services.generation_tracker.GenerationTracker._get_limit",
                new_callable=AsyncMock,
                return_value=-1,  # unlimited
            ):
                with patch("redis.asyncio.from_url", return_value=mock_redis):
                    result = await tracker.check_limit(
                        project_id=project_id,
                        resource_type="article",
                    )

        assert result is True

    async def test_redis_unavailable_falls_back_to_db(self):
        """
        If Redis raises an exception, check_limit falls back to the DB-based
        check rather than raising or returning an incorrect result.
        """
        project_id = str(uuid4())
        db = _make_db_session()
        tracker = GenerationTracker(db)

        # Redis throws ConnectionError
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=ConnectionError("Redis down"))

        with patch("services.generation_tracker.settings") as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379/0"

            with patch("redis.asyncio.from_url", return_value=mock_redis):
                with patch(
                    "services.generation_tracker.ProjectUsageService"
                ) as MockUsage:
                    mock_usage_instance = AsyncMock()
                    mock_usage_instance.reset_project_usage_if_needed = AsyncMock(
                        return_value=False
                    )
                    mock_usage_instance.check_project_limit = AsyncMock(return_value=True)
                    MockUsage.return_value = mock_usage_instance

                    result = await tracker.check_limit(
                        project_id=project_id,
                        resource_type="article",
                    )

        # Should have fallen back to DB check and returned True
        assert result is True
        mock_usage_instance.check_project_limit.assert_called_once()

    async def test_redis_sets_ttl_on_first_use(self):
        """When Redis counter is first created (value == 1), a TTL is set."""
        project_id = str(uuid4())
        db = _make_db_session()
        tracker = GenerationTracker(db)

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)  # first use
        mock_redis.expire = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with patch("services.generation_tracker.settings") as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379/0"

            with patch(
                "services.generation_tracker.GenerationTracker._get_limit",
                new_callable=AsyncMock,
                return_value=10,
            ):
                with patch("redis.asyncio.from_url", return_value=mock_redis):
                    await tracker.check_limit(
                        project_id=project_id,
                        resource_type="article",
                    )

        # expire must have been called with 86400 * 35 seconds TTL
        mock_redis.expire.assert_called_once()
        ttl_arg = mock_redis.expire.call_args[0][1]
        assert ttl_arg == 86400 * 35

    async def test_redis_no_ttl_on_subsequent_increments(self):
        """When Redis counter > 1, no TTL call is made (key already exists)."""
        project_id = str(uuid4())
        db = _make_db_session()
        tracker = GenerationTracker(db)

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=5)  # not first use
        mock_redis.expire = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with patch("services.generation_tracker.settings") as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379/0"

            with patch(
                "services.generation_tracker.GenerationTracker._get_limit",
                new_callable=AsyncMock,
                return_value=10,
            ):
                with patch("redis.asyncio.from_url", return_value=mock_redis):
                    await tracker.check_limit(
                        project_id=project_id,
                        resource_type="article",
                    )

        mock_redis.expire.assert_not_called()
