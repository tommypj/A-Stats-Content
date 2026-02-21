# Social Media Test Fixtures - To be merged into conftest.py
# This file contains all fixtures needed for Phase 8 Social Media Scheduling tests

from datetime import datetime, timedelta
from uuid import uuid4
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.models import User

# ============================================================================
# Social Media Test Fixtures
# ============================================================================

@pytest.fixture
async def connected_twitter_account(db_session: AsyncSession, test_user: User):
    """
    Create a connected Twitter account for testing.

    Used for testing post creation and publishing to Twitter.
    """
    from infrastructure.database.models.social import SocialAccount
    from core.security.encryption import encrypt_token

    account = SocialAccount(
        id=str(uuid4()),
        user_id=test_user.id,
        platform="twitter",
        account_name="testuser",
        account_id="123456",
        encrypted_access_token=encrypt_token("test_twitter_token"),
        encrypted_refresh_token=encrypt_token("test_twitter_refresh"),
        token_expires_at=datetime.utcnow() + timedelta(hours=2),
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.fixture
async def connected_linkedin_account(db_session: AsyncSession, test_user: User):
    """
    Create a connected LinkedIn account for testing.

    Used for testing post creation and publishing to LinkedIn.
    """
    from infrastructure.database.models.social import SocialAccount
    from core.security.encryption import encrypt_token

    account = SocialAccount(
        id=str(uuid4()),
        user_id=test_user.id,
        platform="linkedin",
        account_name="Test User",
        account_id="urn:li:person:123456",
        encrypted_access_token=encrypt_token("test_linkedin_token"),
        token_expires_at=datetime.utcnow() + timedelta(days=60),
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.fixture
async def connected_facebook_account(db_session: AsyncSession, test_user: User):
    """
    Create a connected Facebook account for testing.

    Used for testing post creation and publishing to Facebook.
    """
    from infrastructure.database.models.social import SocialAccount
    from core.security.encryption import encrypt_token

    account = SocialAccount(
        id=str(uuid4()),
        user_id=test_user.id,
        platform="facebook",
        account_name="Test Page",
        account_id="123456789",
        encrypted_access_token=encrypt_token("test_facebook_token"),
        token_expires_at=datetime.utcnow() + timedelta(days=60),
        is_active=True,
        metadata={"page_id": "123456789"},
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.fixture
async def connected_accounts(
    db_session: AsyncSession,
    test_user: User,
    connected_twitter_account,
    connected_linkedin_account,
):
    """
    Create multiple connected accounts for testing.

    Used for testing multi-platform posting and account management.
    """
    return [connected_twitter_account, connected_linkedin_account]


@pytest.fixture
async def pending_post(
    db_session: AsyncSession,
    test_user: User,
    connected_twitter_account,
):
    """
    Create a pending scheduled post for testing.

    Used for testing post retrieval, updates, and publishing.
    """
    from infrastructure.database.models.social import ScheduledPost, PostTarget, PostStatus

    post = ScheduledPost(
        id=str(uuid4()),
        user_id=test_user.id,
        content="Test pending post",
        scheduled_time=datetime.utcnow() + timedelta(hours=2),
        timezone="UTC",
        status=PostStatus.PENDING,
    )
    db_session.add(post)
    await db_session.flush()

    # Add target
    target = PostTarget(
        id=str(uuid4()),
        post_id=post.id,
        account_id=connected_twitter_account.id,
        platform="twitter",
        status=PostStatus.PENDING,
    )
    db_session.add(target)

    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.fixture
async def posted_post(
    db_session: AsyncSession,
    test_user: User,
    connected_twitter_account,
):
    """
    Create a post that has already been published.

    Used for testing operations that should fail on published posts.
    """
    from infrastructure.database.models.social import ScheduledPost, PostTarget, PostStatus

    post = ScheduledPost(
        id=str(uuid4()),
        user_id=test_user.id,
        content="Test published post",
        scheduled_time=datetime.utcnow() - timedelta(hours=1),
        timezone="UTC",
        status=PostStatus.PUBLISHED,
    )
    db_session.add(post)
    await db_session.flush()

    # Add published target
    target = PostTarget(
        id=str(uuid4()),
        post_id=post.id,
        account_id=connected_twitter_account.id,
        platform="twitter",
        status=PostStatus.PUBLISHED,
        platform_post_id="1234567890",
        published_at=datetime.utcnow() - timedelta(hours=1),
    )
    db_session.add(target)

    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.fixture
async def failed_post(
    db_session: AsyncSession,
    test_user: User,
    connected_twitter_account,
):
    """
    Create a post that failed to publish.

    Used for testing retry operations and error handling.
    """
    from infrastructure.database.models.social import ScheduledPost, PostTarget, PostStatus

    post = ScheduledPost(
        id=str(uuid4()),
        user_id=test_user.id,
        content="Test failed post",
        scheduled_time=datetime.utcnow() - timedelta(minutes=30),
        timezone="UTC",
        status=PostStatus.FAILED,
    )
    db_session.add(post)
    await db_session.flush()

    # Add failed target
    target = PostTarget(
        id=str(uuid4()),
        post_id=post.id,
        account_id=connected_twitter_account.id,
        platform="twitter",
        status=PostStatus.FAILED,
        error_message="API Error: Rate limit exceeded",
        retry_count=1,
    )
    db_session.add(target)

    await db_session.commit()
    await db_session.refresh(post)
    return post


@pytest.fixture
async def multiple_scheduled_posts(
    db_session: AsyncSession,
    test_user: User,
    connected_accounts,
):
    """
    Create multiple scheduled posts with various statuses.

    Used for testing pagination, filtering, and calendar views.
    """
    from infrastructure.database.models.social import ScheduledPost, PostTarget, PostStatus

    posts = []

    statuses = [
        PostStatus.PENDING,
        PostStatus.PENDING,
        PostStatus.PUBLISHED,
        PostStatus.FAILED,
        PostStatus.PENDING,
    ]

    for i, status in enumerate(statuses):
        scheduled_time = datetime.utcnow() + timedelta(hours=(i + 1))
        if status == PostStatus.PUBLISHED:
            scheduled_time = datetime.utcnow() - timedelta(hours=1)

        post = ScheduledPost(
            id=str(uuid4()),
            user_id=test_user.id,
            content=f"Test post {i + 1}",
            scheduled_time=scheduled_time,
            timezone="UTC",
            status=status,
        )
        db_session.add(post)
        await db_session.flush()

        # Add target for each account
        for account in connected_accounts:
            target = PostTarget(
                id=str(uuid4()),
                post_id=post.id,
                account_id=account.id,
                platform=account.platform,
                status=status,
                platform_post_id=f"post_{i}_{account.platform}" if status == PostStatus.PUBLISHED else None,
                published_at=datetime.utcnow() - timedelta(hours=1) if status == PostStatus.PUBLISHED else None,
            )
            db_session.add(target)

        posts.append(post)

    await db_session.commit()

    for post in posts:
        await db_session.refresh(post)

    return posts


@pytest.fixture
def mock_twitter_api():
    """
    Mock Twitter API responses for testing.

    Usage:
        def test_example(mock_twitter_api):
            # Mock responses are pre-configured
            # Test code here
    """
    from unittest.mock import patch, AsyncMock

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()

        # Mock tweet creation
        async def mock_post(*args, **kwargs):
            mock_response = AsyncMock()
            if "tweets" in str(kwargs.get("url", "")):
                mock_response.status_code = 201
                mock_response.json.return_value = {
                    "data": {
                        "id": "1234567890",
                        "text": kwargs.get("json", {}).get("text", "Test tweet"),
                    }
                }
            # Mock token endpoints
            elif "oauth2/token" in str(kwargs.get("url", "")):
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "access_token": "new_access_token",
                    "refresh_token": "new_refresh_token",
                    "expires_in": 7200,
                }
            return mock_response

        mock_instance.post = mock_post
        mock_client.return_value.__aenter__.return_value = mock_instance

        yield mock_instance


@pytest.fixture
def mock_linkedin_api():
    """
    Mock LinkedIn API responses for testing.

    Usage:
        def test_example(mock_linkedin_api):
            # Mock responses are pre-configured
            # Test code here
    """
    from unittest.mock import patch, AsyncMock

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()

        # Mock post creation
        async def mock_post(*args, **kwargs):
            mock_response = AsyncMock()
            if "ugcPosts" in str(kwargs.get("url", "")):
                mock_response.status_code = 201
                mock_response.json.return_value = {
                    "id": "urn:li:share:1234567890",
                }
            # Mock token endpoints
            elif "oauth/v2/accessToken" in str(kwargs.get("url", "")):
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "access_token": "new_access_token",
                    "expires_in": 5184000,
                }
            return mock_response

        mock_instance.post = mock_post
        mock_client.return_value.__aenter__.return_value = mock_instance

        yield mock_instance


@pytest.fixture
def mock_facebook_api():
    """
    Mock Facebook API responses for testing.

    Usage:
        def test_example(mock_facebook_api):
            # Mock responses are pre-configured
            # Test code here
    """
    from unittest.mock import patch, AsyncMock

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()

        # Mock post creation
        async def mock_post(*args, **kwargs):
            mock_response = AsyncMock()
            if "/feed" in str(kwargs.get("url", "")):
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "id": "123456789_987654321",
                }
            return mock_response

        mock_instance.post = mock_post
        mock_client.return_value.__aenter__.return_value = mock_instance

        yield mock_instance
