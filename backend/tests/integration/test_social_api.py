"""
Integration tests for social media API routes.

Tests all social media endpoints including:
- Account connection and management
- Post scheduling and management
- Calendar view
- Publishing workflow
"""

import pytest
from datetime import datetime, date, timedelta, timezone
from unittest.mock import AsyncMock, patch, Mock
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import User

# Skip all tests if social routes are not available
try:
    from api.routes import social
    from infrastructure.database.models.social import (
        SocialAccount,
        ScheduledPost,
        PostStatus,
        PostTarget,
    )
    SOCIAL_AVAILABLE = True
except (ImportError, AttributeError):
    SOCIAL_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Social media routes not implemented yet")


# ============================================================================
# Account Management Tests
# ============================================================================

class TestAccountsEndpoint:
    """Tests for /social/accounts endpoints."""

    @pytest.mark.asyncio
    async def test_list_accounts_empty(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test listing accounts when user has no connected accounts."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.get(
            "/api/v1/social/accounts",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "accounts" in data
        assert len(data["accounts"]) == 0

    @pytest.mark.asyncio
    async def test_list_accounts_with_connected(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        connected_twitter_account,
    ):
        """Test listing accounts returns connected accounts."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.get(
            "/api/v1/social/accounts",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["accounts"]) >= 1

        account = data["accounts"][0]
        assert "id" in account
        assert "platform" in account
        assert "platform_username" in account
        assert "is_active" in account
        # Tokens should not be exposed
        assert "access_token" not in account
        assert "refresh_token" not in account

    @pytest.mark.asyncio
    async def test_list_accounts_unauthorized(
        self,
        async_client: AsyncClient,
    ):
        """Test listing accounts without authentication returns 401."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.get("/api/v1/social/accounts")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_initiate_connection_returns_auth_url(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test initiating OAuth connection returns authorization URL."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.get(
            "/api/v1/social/twitter/connect",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "authorization_url" in data
        assert "twitter" in data["authorization_url"]
        assert "state" in data

    @pytest.mark.asyncio
    async def test_initiate_connection_invalid_platform(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test initiating connection with invalid platform returns 400."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.get(
            "/api/v1/social/invalid_platform/connect",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_oauth_callback_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test successful OAuth callback saves account."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.get(
            "/api/v1/social/twitter/callback",
            headers=auth_headers,
            params={
                "code": "test_auth_code",
                "state": "test_state",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["platform"] == "twitter"
        assert "message" in data

    @pytest.mark.asyncio
    async def test_disconnect_account(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        connected_twitter_account,
    ):
        """Test disconnecting a social account."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.delete(
            f"/api/v1/social/accounts/{connected_twitter_account.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "disconnected successfully" in data["message"]

    @pytest.mark.asyncio
    async def test_disconnect_wrong_account_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test disconnecting account that doesn't belong to user fails."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        fake_account_id = str(uuid4())

        response = await async_client.delete(
            f"/api/v1/social/accounts/{fake_account_id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Post Management Tests
# ============================================================================

class TestPostsEndpoint:
    """Tests for /social/posts endpoints."""

    @pytest.mark.asyncio
    async def test_create_post_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        connected_twitter_account,
    ):
        """Test creating a scheduled post."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        scheduled_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        response = await async_client.post(
            "/api/v1/social/posts",
            headers=auth_headers,
            json={
                "content": "Test scheduled post",
                "scheduled_at": scheduled_time,
                "account_ids": [connected_twitter_account.id],
                "media_urls": [],
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["content"] == "Test scheduled post"
        assert data["status"] in ("scheduled", "pending", "draft")
        assert len(data["targets"]) == 1

    @pytest.mark.asyncio
    async def test_create_post_invalid_account(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test creating post with invalid account_id returns 400."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        scheduled_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        response = await async_client.post(
            "/api/v1/social/posts",
            headers=auth_headers,
            json={
                "content": "Test post",
                "scheduled_at": scheduled_time,
                "account_ids": [str(uuid4())],  # Non-existent account
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_post_content_too_long(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        connected_twitter_account,
    ):
        """Test creating post with content exceeding Twitter's limit."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        scheduled_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        # Twitter has 280 character limit
        long_content = "a" * 281

        response = await async_client.post(
            "/api/v1/social/posts",
            headers=auth_headers,
            json={
                "content": long_content,
                "scheduled_at": scheduled_time,
                "account_ids": [connected_twitter_account.id],
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "280" in data["detail"].lower() or "character" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_post_past_time_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        connected_twitter_account,
    ):
        """Test creating post with past scheduled time returns 400."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        response = await async_client.post(
            "/api/v1/social/posts",
            headers=auth_headers,
            json={
                "content": "Test post",
                "scheduled_at": past_time,
                "account_ids": [connected_twitter_account.id],
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_list_posts_paginated(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        multiple_scheduled_posts,
    ):
        """Test listing posts with pagination."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.get(
            "/api/v1/social/posts",
            headers=auth_headers,
            params={"skip": 0, "limit": 5},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "posts" in data
        assert "total" in data
        assert len(data["posts"]) <= 5

    @pytest.mark.asyncio
    async def test_list_posts_filter_by_status(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        multiple_scheduled_posts,
    ):
        """Test filtering posts by status."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.get(
            "/api/v1/social/posts",
            headers=auth_headers,
            params={"status": "scheduled"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All returned posts should be scheduled
        for post in data["posts"]:
            assert post["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_get_post_by_id(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        pending_post,
    ):
        """Test getting a specific post by ID."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.get(
            f"/api/v1/social/posts/{pending_post.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == pending_post.id
        assert data["content"] == pending_post.content

    @pytest.mark.asyncio
    async def test_update_pending_post(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        pending_post,
    ):
        """Test updating a pending post."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        new_content = "Updated post content"
        new_time = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()

        response = await async_client.put(
            f"/api/v1/social/posts/{pending_post.id}",
            headers=auth_headers,
            json={
                "content": new_content,
                "scheduled_time": new_time,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content"] == new_content

    @pytest.mark.asyncio
    async def test_update_posted_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        posted_post,
    ):
        """Test that published posts cannot be edited."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.put(
            f"/api/v1/social/posts/{posted_post.id}",
            headers=auth_headers,
            json={
                "content": "New content",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_delete_post(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        pending_post,
    ):
        """Test deleting a pending post."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.delete(
            f"/api/v1/social/posts/{pending_post.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify post is deleted
        get_response = await async_client.get(
            f"/api/v1/social/posts/{pending_post.id}",
            headers=auth_headers,
        )

        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_publish_now(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        pending_post,
        connected_twitter_account,
    ):
        """Test publishing a post immediately."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.post(
            f"/api/v1/social/posts/{pending_post.id}/publish-now",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] in ["published", "publishing", "scheduled", "draft"]

    @pytest.mark.asyncio
    async def test_retry_failed_post(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        failed_post,
        connected_twitter_account,
    ):
        """Test retrying a failed post."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.post(
            f"/api/v1/social/posts/{failed_post.id}/publish-now",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Calendar View Tests
# ============================================================================

class TestCalendarEndpoint:
    """Tests for /social/calendar endpoint."""

    @pytest.mark.asyncio
    async def test_get_calendar_range(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        multiple_scheduled_posts,
    ):
        """Test getting calendar view for date range."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        start_date = date.today().isoformat()
        end_date = (date.today() + timedelta(days=7)).isoformat()

        response = await async_client.get(
            "/api/v1/social/calendar",
            headers=auth_headers,
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "days" in data
        assert "start_date" in data
        assert "end_date" in data

        # All posts within each day should be within date range
        for day in data["days"]:
            day_date = date.fromisoformat(day["date"])
            assert date.fromisoformat(start_date) <= day_date <= date.fromisoformat(end_date)

    @pytest.mark.asyncio
    async def test_get_calendar_empty_range(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting calendar view with no posts in range."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        # Far future date range with no posts
        start_date = (date.today() + timedelta(days=365)).isoformat()
        end_date = (date.today() + timedelta(days=372)).isoformat()

        response = await async_client.get(
            "/api/v1/social/calendar",
            headers=auth_headers,
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "days" in data
        # Days with no posts should be empty or absent
        total_posts = sum(day["post_count"] for day in data["days"])
        assert total_posts == 0

    @pytest.mark.asyncio
    async def test_calendar_grouped_by_day(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        multiple_scheduled_posts,
    ):
        """Test calendar groups posts by day."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        start_date = date.today().isoformat()
        end_date = (date.today() + timedelta(days=7)).isoformat()

        response = await async_client.get(
            "/api/v1/social/calendar",
            headers=auth_headers,
            params={
                "start_date": start_date,
                "end_date": end_date,
                "group_by": "day",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should return CalendarResponse with days list
        assert "days" in data
        assert isinstance(data["days"], list)


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatsEndpoint:
    """Tests for /social/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_statistics(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        multiple_scheduled_posts,
    ):
        """Test getting post statistics."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.get(
            "/api/v1/social/stats",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "pending" in data
        assert "published" in data
        assert "failed" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_stats_by_platform(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        multiple_scheduled_posts,
        connected_accounts,
    ):
        """Test getting statistics broken down by platform."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        response = await async_client.get(
            "/api/v1/social/stats",
            headers=auth_headers,
            params={"breakdown": "platform"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "by_platform" in data


# ============================================================================
# Media Upload Tests
# ============================================================================

class TestMediaUpload:
    """Tests for media upload functionality."""

    @pytest.mark.asyncio
    async def test_create_post_with_media(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        connected_twitter_account,
    ):
        """Test creating post with media URLs."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        scheduled_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        response = await async_client.post(
            "/api/v1/social/posts",
            headers=auth_headers,
            json={
                "content": "Post with image",
                "scheduled_at": scheduled_time,
                "account_ids": [connected_twitter_account.id],
                "media_urls": ["https://example.com/image.jpg"],
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["media_urls"]) == 1

    @pytest.mark.asyncio
    async def test_upload_media_file(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test uploading media file for use in posts."""
        if not SOCIAL_AVAILABLE:
            pytest.skip("Social routes not available")

        pytest.skip("Media upload endpoint not yet implemented")

        # Create fake image file
        files = {
            "file": ("test.jpg", b"fake image content", "image/jpeg")
        }

        response = await async_client.post(
            "/api/v1/social/media/upload",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "url" in data
        assert "media_id" in data
