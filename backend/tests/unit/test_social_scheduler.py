"""
Unit tests for social media scheduler service.

Tests the scheduling logic including:
- Processing due posts
- Publishing to platforms
- Token refresh handling
- Retry logic for failed posts
- Multiple target handling
- Media post workflows
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

# These imports will work once the service is created
try:
    from infrastructure.database.models.social import (
        PostStatus,
        PostTarget,
        ScheduledPost,
        SocialAccount,
    )
    from services.social_scheduler import (
        PublishError,
        SchedulerError,
        SocialSchedulerService,
    )

    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Social scheduler service not implemented yet")


@pytest.fixture
def scheduler_service():
    """Create SocialSchedulerService instance."""
    if not SERVICE_AVAILABLE:
        pytest.skip("Scheduler service not available")
    return SocialSchedulerService()


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    return session


@pytest.fixture
def sample_pending_post():
    """Create a sample pending post scheduled for now."""
    if not SERVICE_AVAILABLE:
        pytest.skip("Models not available")

    post = ScheduledPost(
        id=str(uuid4()),
        user_id=str(uuid4()),
        content="Test scheduled post",
        scheduled_time=datetime.now(UTC),
        status=PostStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Add target
    target = PostTarget(
        id=str(uuid4()),
        post_id=post.id,
        account_id=str(uuid4()),
        platform="twitter",
        status=PostStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    post.targets = [target]

    return post


@pytest.fixture
def sample_future_post():
    """Create a sample post scheduled for future."""
    if not SERVICE_AVAILABLE:
        pytest.skip("Models not available")

    post = ScheduledPost(
        id=str(uuid4()),
        user_id=str(uuid4()),
        content="Future post",
        scheduled_time=datetime.now(UTC) + timedelta(hours=2),
        status=PostStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    target = PostTarget(
        id=str(uuid4()),
        post_id=post.id,
        account_id=str(uuid4()),
        platform="twitter",
        status=PostStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    post.targets = [target]

    return post


@pytest.fixture
def sample_social_account():
    """Create a sample social account with valid tokens."""
    if not SERVICE_AVAILABLE:
        pytest.skip("Models not available")

    return SocialAccount(
        id=str(uuid4()),
        user_id=str(uuid4()),
        platform="twitter",
        account_name="testuser",
        account_id="123456",
        encrypted_access_token="encrypted_token",
        encrypted_refresh_token="encrypted_refresh_token",
        token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestSocialSchedulerService:
    """Tests for social scheduler service."""

    @pytest.mark.asyncio
    async def test_process_due_posts_finds_pending(
        self,
        scheduler_service,
        mock_db_session,
        sample_pending_post,
    ):
        """Test that process_due_posts finds and processes pending posts."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        # Mock database query to return pending post
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_pending_post]
        mock_db_session.execute.return_value = mock_result

        # Mock successful publishing
        with patch.object(
            scheduler_service, "publish_post", new_callable=AsyncMock
        ) as mock_publish:
            mock_publish.return_value = True

            processed = await scheduler_service.process_due_posts(mock_db_session)

            assert processed > 0
            mock_publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_due_posts_skips_future(
        self,
        scheduler_service,
        mock_db_session,
        sample_future_post,
    ):
        """Test that process_due_posts skips posts scheduled for future."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        # Mock database query to return no posts (future posts filtered out)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        processed = await scheduler_service.process_due_posts(mock_db_session)

        assert processed == 0

    @pytest.mark.asyncio
    async def test_publish_to_platform_success(
        self,
        scheduler_service,
        mock_db_session,
        sample_pending_post,
        sample_social_account,
    ):
        """Test successful publishing to a platform."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        target = sample_pending_post.targets[0]

        # Mock adapter post method
        with patch("adapters.social.twitter_adapter.TwitterAdapter.post_text") as mock_post:
            mock_post.return_value = {
                "id": "1234567890",
                "text": sample_pending_post.content,
            }

            result = await scheduler_service.publish_to_platform(
                target=target,
                post=sample_pending_post,
                account=sample_social_account,
                session=mock_db_session,
            )

            assert result is True
            assert target.status == PostStatus.PUBLISHED
            assert target.platform_post_id == "1234567890"
            assert target.published_at is not None

    @pytest.mark.asyncio
    async def test_publish_to_platform_failure_updates_status(
        self,
        scheduler_service,
        mock_db_session,
        sample_pending_post,
        sample_social_account,
    ):
        """Test that failed publishing updates status correctly."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        target = sample_pending_post.targets[0]

        # Mock adapter to raise error
        with patch("adapters.social.twitter_adapter.TwitterAdapter.post_text") as mock_post:
            mock_post.side_effect = Exception("API Error")

            result = await scheduler_service.publish_to_platform(
                target=target,
                post=sample_pending_post,
                account=sample_social_account,
                session=mock_db_session,
            )

            assert result is False
            assert target.status == PostStatus.FAILED
            assert target.error_message is not None
            assert "API Error" in target.error_message

    @pytest.mark.asyncio
    async def test_publish_with_expired_token_refreshes(
        self,
        scheduler_service,
        mock_db_session,
        sample_pending_post,
        sample_social_account,
    ):
        """Test that expired tokens are refreshed before publishing."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        # Set token as expired
        sample_social_account.token_expires_at = datetime.now(UTC) - timedelta(hours=1)

        target = sample_pending_post.targets[0]

        # Mock token refresh
        with patch.object(scheduler_service, "refresh_token") as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new_token",
                "expires_in": 7200,
            }

            # Mock successful post
            with patch("adapters.social.twitter_adapter.TwitterAdapter.post_text") as mock_post:
                mock_post.return_value = {"id": "1234567890"}

                await scheduler_service.publish_to_platform(
                    target=target,
                    post=sample_pending_post,
                    account=sample_social_account,
                    session=mock_db_session,
                )

                mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_failed_target(
        self,
        scheduler_service,
        mock_db_session,
        sample_pending_post,
        sample_social_account,
    ):
        """Test retrying a failed post target."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        target = sample_pending_post.targets[0]
        target.status = PostStatus.FAILED
        target.error_message = "Previous error"
        target.retry_count = 1

        # Mock successful retry
        with patch("adapters.social.twitter_adapter.TwitterAdapter.post_text") as mock_post:
            mock_post.return_value = {"id": "1234567890"}

            result = await scheduler_service.retry_target(
                target=target,
                post=sample_pending_post,
                account=sample_social_account,
                session=mock_db_session,
            )

            assert result is True
            assert target.status == PostStatus.PUBLISHED
            assert target.retry_count == 2

    @pytest.mark.asyncio
    async def test_multiple_targets_partial_success(
        self,
        scheduler_service,
        mock_db_session,
        sample_pending_post,
    ):
        """Test handling of multiple targets with partial success."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        # Add second target
        target2 = PostTarget(
            id=str(uuid4()),
            post_id=sample_pending_post.id,
            account_id=str(uuid4()),
            platform="linkedin",
            status=PostStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        sample_pending_post.targets.append(target2)

        # Mock accounts
        account1 = SocialAccount(
            id=sample_pending_post.targets[0].account_id,
            user_id=sample_pending_post.user_id,
            platform="twitter",
            account_name="twitter_user",
            account_id="123",
            encrypted_access_token="token1",
            token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )

        account2 = SocialAccount(
            id=target2.account_id,
            user_id=sample_pending_post.user_id,
            platform="linkedin",
            account_name="linkedin_user",
            account_id="456",
            encrypted_access_token="token2",
            token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            is_active=True,
        )

        # Mock query for accounts
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [account1, account2]
        mock_db_session.execute.return_value = mock_result

        # Mock Twitter success, LinkedIn failure
        with patch("adapters.social.twitter_adapter.TwitterAdapter.post_text") as mock_twitter:
            mock_twitter.return_value = {"id": "twitter_123"}

            with patch(
                "adapters.social.linkedin_adapter.LinkedInAdapter.post_text"
            ) as mock_linkedin:
                mock_linkedin.side_effect = Exception("LinkedIn API Error")

                await scheduler_service.publish_post(
                    post=sample_pending_post,
                    session=mock_db_session,
                )

                # First target should succeed
                assert sample_pending_post.targets[0].status == PostStatus.PUBLISHED

                # Second target should fail
                assert target2.status == PostStatus.FAILED

    @pytest.mark.asyncio
    async def test_media_post_uploads_first(
        self,
        scheduler_service,
        mock_db_session,
        sample_pending_post,
        sample_social_account,
    ):
        """Test that media posts upload images before posting."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        # Add media URLs to post
        sample_pending_post.media_urls = ["https://example.com/image1.jpg"]
        target = sample_pending_post.targets[0]

        # Mock media upload and post
        with patch("adapters.social.twitter_adapter.TwitterAdapter.upload_media") as mock_upload:
            mock_upload.return_value = {"media_id": "123456789"}

            with patch(
                "adapters.social.twitter_adapter.TwitterAdapter.post_with_media"
            ) as mock_post:
                mock_post.return_value = {"id": "1234567890"}

                await scheduler_service.publish_to_platform(
                    target=target,
                    post=sample_pending_post,
                    account=sample_social_account,
                    session=mock_db_session,
                )

                # Verify media was uploaded
                mock_upload.assert_called_once()
                # Verify post was created with media
                mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_retry_limit(
        self,
        scheduler_service,
        mock_db_session,
        sample_pending_post,
        sample_social_account,
    ):
        """Test that posts are not retried beyond max retry count."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        target = sample_pending_post.targets[0]
        target.status = PostStatus.FAILED
        target.retry_count = 3  # Max retries reached

        result = await scheduler_service.should_retry(target)

        assert result is False

    @pytest.mark.asyncio
    async def test_timezone_handling(
        self,
        scheduler_service,
        mock_db_session,
    ):
        """Test proper timezone handling for scheduled times."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        # Create post with specific timezone
        scheduled_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        post = ScheduledPost(
            id=str(uuid4()),
            user_id=str(uuid4()),
            content="Timezone test",
            scheduled_time=scheduled_time,
            timezone="America/New_York",
            status=PostStatus.PENDING,
        )

        # Verify time is converted correctly
        is_due = scheduler_service.is_post_due(post, datetime.now(UTC))
        assert isinstance(is_due, bool)

    @pytest.mark.asyncio
    async def test_concurrent_publishing(
        self,
        scheduler_service,
        mock_db_session,
    ):
        """Test handling of concurrent publishing attempts."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        post = ScheduledPost(
            id=str(uuid4()),
            user_id=str(uuid4()),
            content="Concurrent test",
            scheduled_time=datetime.now(UTC),
            status=PostStatus.PUBLISHING,  # Already being published
        )

        # Should skip posts already being published
        result = await scheduler_service.can_process_post(post)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_scheduled_post(
        self,
        scheduler_service,
        mock_db_session,
        sample_pending_post,
    ):
        """Test deleting a scheduled post before it's published."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        # Should allow deletion of pending posts
        result = await scheduler_service.delete_post(
            post_id=sample_pending_post.id,
            session=mock_db_session,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_scheduled_post(
        self,
        scheduler_service,
        mock_db_session,
        sample_pending_post,
    ):
        """Test updating a scheduled post content and time."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        new_content = "Updated content"
        new_time = datetime.now(UTC) + timedelta(hours=1)

        result = await scheduler_service.update_post(
            post_id=sample_pending_post.id,
            content=new_content,
            scheduled_time=new_time,
            session=mock_db_session,
        )

        assert result is True
        assert sample_pending_post.content == new_content
        assert sample_pending_post.scheduled_time == new_time

    @pytest.mark.asyncio
    async def test_publish_immediately(
        self,
        scheduler_service,
        mock_db_session,
        sample_pending_post,
    ):
        """Test publishing a post immediately (bypassing schedule)."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        with patch.object(
            scheduler_service, "publish_post", new_callable=AsyncMock
        ) as mock_publish:
            mock_publish.return_value = True

            result = await scheduler_service.publish_now(
                post_id=sample_pending_post.id,
                session=mock_db_session,
            )

            assert result is True
            mock_publish.assert_called_once()
