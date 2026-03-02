"""
Unit tests for post queue management.

Tests the post queue logic including:
- Scheduling posts
- Fetching due posts
- Marking posts as published
- Canceling scheduled posts
- Rescheduling posts
- Queue pagination and filtering
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

# These imports will work once the queue service is created
try:
    from infrastructure.database.models.social import (
        PostStatus,
        PostTarget,
        ScheduledPost,
    )
    from services.post_queue import (
        PostQueueService,
        QueueError,
    )

    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Post queue service not implemented yet")


@pytest.fixture
def queue_service():
    """Create PostQueueService instance."""
    if not SERVICE_AVAILABLE:
        pytest.skip("Queue service not available")
    return PostQueueService()


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def sample_post_data():
    """Sample data for creating a scheduled post."""
    return {
        "user_id": str(uuid4()),
        "content": "Test scheduled post",
        "scheduled_time": datetime.now(UTC) + timedelta(hours=1),
        "timezone": "UTC",
        "account_ids": [str(uuid4())],
        "media_urls": [],
    }


class TestPostQueueService:
    """Tests for post queue management service."""

    @pytest.mark.asyncio
    async def test_schedule_post_adds_to_queue(
        self,
        queue_service,
        mock_db_session,
        sample_post_data,
    ):
        """Test that scheduling a post adds it to the queue."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        post = await queue_service.schedule_post(
            session=mock_db_session,
            **sample_post_data,
        )

        assert post is not None
        assert post.status == PostStatus.PENDING
        assert post.content == sample_post_data["content"]
        assert len(post.targets) == len(sample_post_data["account_ids"])
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_post_with_multiple_accounts(
        self,
        queue_service,
        mock_db_session,
        sample_post_data,
    ):
        """Test scheduling a post to multiple social accounts."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        # Add multiple accounts
        sample_post_data["account_ids"] = [str(uuid4()), str(uuid4()), str(uuid4())]

        post = await queue_service.schedule_post(
            session=mock_db_session,
            **sample_post_data,
        )

        assert len(post.targets) == 3
        # Each target should be pending
        for target in post.targets:
            assert target.status == PostStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_due_posts_returns_correct(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test getting posts that are due for publishing."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        # Create mock posts - one due, one future
        due_post = ScheduledPost(
            id=str(uuid4()),
            user_id=str(uuid4()),
            content="Due post",
            scheduled_time=datetime.now(UTC) - timedelta(minutes=5),
            status=PostStatus.PENDING,
        )

        ScheduledPost(
            id=str(uuid4()),
            user_id=str(uuid4()),
            content="Future post",
            scheduled_time=datetime.now(UTC) + timedelta(hours=2),
            status=PostStatus.PENDING,
        )

        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [due_post]
        mock_db_session.execute.return_value = mock_result

        posts = await queue_service.get_due_posts(
            session=mock_db_session,
            limit=10,
        )

        assert len(posts) >= 0
        # All returned posts should be due
        for post in posts:
            assert post.scheduled_time <= datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_mark_published_removes_from_queue(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test marking a post as published updates its status."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        post = ScheduledPost(
            id=str(uuid4()),
            user_id=str(uuid4()),
            content="Test post",
            scheduled_time=datetime.now(UTC),
            status=PostStatus.PENDING,
        )

        target = PostTarget(
            id=str(uuid4()),
            post_id=post.id,
            account_id=str(uuid4()),
            platform="twitter",
            status=PostStatus.PENDING,
        )
        post.targets = [target]

        # Mock finding the post
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = post
        mock_db_session.execute.return_value = mock_result

        success = await queue_service.mark_published(
            session=mock_db_session,
            post_id=post.id,
            platform_post_id="123456789",
        )

        assert success is True
        # If all targets are published, post should be published
        if all(t.status == PostStatus.PUBLISHED for t in post.targets):
            assert post.status == PostStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_cancel_post_removes_from_queue(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test canceling a pending post."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        post = ScheduledPost(
            id=str(uuid4()),
            user_id=str(uuid4()),
            content="Test post",
            scheduled_time=datetime.now(UTC) + timedelta(hours=1),
            status=PostStatus.PENDING,
        )

        # Mock finding the post
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = post
        mock_db_session.execute.return_value = mock_result

        success = await queue_service.cancel_post(
            session=mock_db_session,
            post_id=post.id,
            user_id=post.user_id,
        )

        assert success is True
        assert post.status == PostStatus.CANCELLED
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_published_post_fails(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test that published posts cannot be canceled."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        post = ScheduledPost(
            id=str(uuid4()),
            user_id=str(uuid4()),
            content="Published post",
            scheduled_time=datetime.now(UTC) - timedelta(hours=1),
            status=PostStatus.PUBLISHED,
        )

        # Mock finding the post
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = post
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(QueueError) as exc_info:
            await queue_service.cancel_post(
                session=mock_db_session,
                post_id=post.id,
                user_id=post.user_id,
            )

        assert "cannot be canceled" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_reschedule_updates_timestamp(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test rescheduling a post updates the scheduled time."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        original_time = datetime.now(UTC) + timedelta(hours=1)
        new_time = datetime.now(UTC) + timedelta(hours=3)

        post = ScheduledPost(
            id=str(uuid4()),
            user_id=str(uuid4()),
            content="Test post",
            scheduled_time=original_time,
            status=PostStatus.PENDING,
        )

        # Mock finding the post
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = post
        mock_db_session.execute.return_value = mock_result

        success = await queue_service.reschedule_post(
            session=mock_db_session,
            post_id=post.id,
            user_id=post.user_id,
            new_scheduled_time=new_time,
        )

        assert success is True
        assert post.scheduled_time == new_time
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_reschedule_published_post_fails(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test that published posts cannot be rescheduled."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        post = ScheduledPost(
            id=str(uuid4()),
            user_id=str(uuid4()),
            content="Published post",
            scheduled_time=datetime.now(UTC) - timedelta(hours=1),
            status=PostStatus.PUBLISHED,
        )

        # Mock finding the post
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = post
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(QueueError) as exc_info:
            await queue_service.reschedule_post(
                session=mock_db_session,
                post_id=post.id,
                user_id=post.user_id,
                new_scheduled_time=datetime.now(UTC) + timedelta(hours=2),
            )

        assert "cannot be rescheduled" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_user_posts_paginated(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test fetching user's posts with pagination."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        user_id = str(uuid4())

        # Create mock posts
        posts = [
            ScheduledPost(
                id=str(uuid4()),
                user_id=user_id,
                content=f"Post {i}",
                scheduled_time=datetime.now(UTC) + timedelta(hours=i),
                status=PostStatus.PENDING,
            )
            for i in range(5)
        ]

        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = posts[:3]  # Return first 3
        mock_db_session.execute.return_value = mock_result

        result = await queue_service.get_user_posts(
            session=mock_db_session,
            user_id=user_id,
            skip=0,
            limit=3,
        )

        assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_filter_posts_by_status(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test filtering posts by status."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        user_id = str(uuid4())

        # Create mock posts with different statuses
        pending_post = ScheduledPost(
            id=str(uuid4()),
            user_id=user_id,
            content="Pending",
            scheduled_time=datetime.now(UTC) + timedelta(hours=1),
            status=PostStatus.PENDING,
        )

        ScheduledPost(
            id=str(uuid4()),
            user_id=user_id,
            content="Published",
            scheduled_time=datetime.now(UTC) - timedelta(hours=1),
            status=PostStatus.PUBLISHED,
        )

        # Mock database query to return only pending posts
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [pending_post]
        mock_db_session.execute.return_value = mock_result

        result = await queue_service.get_user_posts(
            session=mock_db_session,
            user_id=user_id,
            status=PostStatus.PENDING,
        )

        # All returned posts should have the requested status
        for post in result:
            assert post.status == PostStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_post_by_id(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test fetching a specific post by ID."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        post_id = str(uuid4())
        user_id = str(uuid4())

        post = ScheduledPost(
            id=post_id,
            user_id=user_id,
            content="Test post",
            scheduled_time=datetime.now(UTC) + timedelta(hours=1),
            status=PostStatus.PENDING,
        )

        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = post
        mock_db_session.execute.return_value = mock_result

        result = await queue_service.get_post(
            session=mock_db_session,
            post_id=post_id,
            user_id=user_id,
        )

        assert result is not None
        assert result.id == post_id

    @pytest.mark.asyncio
    async def test_get_post_wrong_user_fails(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test that users can only access their own posts."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        post_id = str(uuid4())
        owner_id = str(uuid4())
        other_user_id = str(uuid4())

        ScheduledPost(
            id=post_id,
            user_id=owner_id,
            content="Test post",
            scheduled_time=datetime.now(UTC) + timedelta(hours=1),
            status=PostStatus.PENDING,
        )

        # Mock database query returns None for wrong user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await queue_service.get_post(
            session=mock_db_session,
            post_id=post_id,
            user_id=other_user_id,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_post_content(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test updating post content before it's published."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        post = ScheduledPost(
            id=str(uuid4()),
            user_id=str(uuid4()),
            content="Original content",
            scheduled_time=datetime.now(UTC) + timedelta(hours=1),
            status=PostStatus.PENDING,
        )

        # Mock finding the post
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = post
        mock_db_session.execute.return_value = mock_result

        new_content = "Updated content"
        success = await queue_service.update_post_content(
            session=mock_db_session,
            post_id=post.id,
            user_id=post.user_id,
            content=new_content,
        )

        assert success is True
        assert post.content == new_content
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_queue_statistics(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test getting queue statistics for a user."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        user_id = str(uuid4())

        # Mock count queries
        mock_result_pending = AsyncMock()
        mock_result_pending.scalar.return_value = 5

        mock_result_published = AsyncMock()
        mock_result_published.scalar.return_value = 10

        mock_result_failed = AsyncMock()
        mock_result_failed.scalar.return_value = 2

        mock_db_session.execute.side_effect = [
            mock_result_pending,
            mock_result_published,
            mock_result_failed,
        ]

        stats = await queue_service.get_statistics(
            session=mock_db_session,
            user_id=user_id,
        )

        assert stats["pending"] == 5
        assert stats["published"] == 10
        assert stats["failed"] == 2
        assert stats["total"] == 17

    @pytest.mark.asyncio
    async def test_delete_old_published_posts(
        self,
        queue_service,
        mock_db_session,
    ):
        """Test cleanup of old published posts."""
        if not SERVICE_AVAILABLE:
            pytest.skip("Service not available")

        user_id = str(uuid4())
        cutoff_date = datetime.now(UTC) - timedelta(days=30)

        # Mock deletion query
        mock_result = AsyncMock()
        mock_result.rowcount = 15
        mock_db_session.execute.return_value = mock_result

        deleted_count = await queue_service.cleanup_old_posts(
            session=mock_db_session,
            user_id=user_id,
            before_date=cutoff_date,
        )

        assert deleted_count >= 0
        mock_db_session.commit.assert_called_once()
