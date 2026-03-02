"""
Unit tests for social media adapters.

Tests the social media API integrations including:
- Twitter/X OAuth 2.0 with PKCE
- LinkedIn OAuth 2.0
- Facebook OAuth 2.0
- Post creation and scheduling
- Media upload
- Rate limit handling
- Token refresh
- Character limit validation
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# These imports will work once the adapters are created
# For now, we'll use pytest.importorskip to make tests conditional
try:
    from adapters.social.facebook_adapter import (
        FacebookAdapter,
        FacebookAuthError,
        FacebookError,
    )
    from adapters.social.linkedin_adapter import (
        LinkedInAdapter,
        LinkedInAuthError,
        LinkedInError,
    )
    from adapters.social.twitter_adapter import (
        TwitterAdapter,
        TwitterAuthError,
        TwitterError,
        TwitterRateLimitError,
    )

    ADAPTERS_AVAILABLE = True
except ImportError:
    ADAPTERS_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Social adapters not implemented yet")


# ============================================================================
# Twitter/X Adapter Tests
# ============================================================================


@pytest.fixture
def twitter_adapter():
    """Create TwitterAdapter instance with test credentials."""
    if not ADAPTERS_AVAILABLE:
        pytest.skip("Twitter adapter not available")
    return TwitterAdapter(
        client_id="test_twitter_client_id",
        client_secret="test_twitter_client_secret",
        redirect_uri="http://localhost:3000/callback",
    )


@pytest.fixture
def mock_twitter_auth_response() -> dict[str, Any]:
    """Mock successful Twitter OAuth token response."""
    return {
        "token_type": "bearer",
        "access_token": "test_twitter_access_token",
        "refresh_token": "test_twitter_refresh_token",
        "expires_in": 7200,
        "scope": "tweet.read tweet.write users.read offline.access",
    }


@pytest.fixture
def mock_twitter_post_response() -> dict[str, Any]:
    """Mock successful Twitter post creation response."""
    return {
        "data": {
            "id": "1234567890",
            "text": "Test tweet content",
            "edit_history_tweet_ids": ["1234567890"],
        }
    }


@pytest.fixture
def mock_twitter_media_response() -> dict[str, Any]:
    """Mock successful Twitter media upload response."""
    return {
        "media_id": 123456789,
        "media_id_string": "123456789",
        "size": 12345,
        "expires_after_secs": 86400,
        "image": {
            "image_type": "image/png",
            "w": 1200,
            "h": 675,
        },
    }


class TestTwitterAdapter:
    """Tests for Twitter/X API adapter."""

    def test_get_authorization_url(self, twitter_adapter):
        """Test Twitter OAuth authorization URL generation with PKCE."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        url, code_verifier = twitter_adapter.get_authorization_url()

        # Verify URL structure
        assert "https://twitter.com/i/oauth2/authorize" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "scope=" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert "state=" in url

        # Verify code_verifier for PKCE
        assert len(code_verifier) >= 43
        assert len(code_verifier) <= 128

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, twitter_adapter, mock_twitter_auth_response):
        """Test successful OAuth code exchange for access token."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_twitter_auth_response
            mock_post.return_value = mock_response

            code_verifier = "test_code_verifier_123456789"
            tokens = await twitter_adapter.exchange_code(
                code="test_auth_code",
                code_verifier=code_verifier,
            )

            assert tokens["access_token"] == "test_twitter_access_token"
            assert tokens["refresh_token"] == "test_twitter_refresh_token"
            assert tokens["expires_in"] == 7200
            assert "expires_at" in tokens

    @pytest.mark.asyncio
    async def test_exchange_code_invalid(self, twitter_adapter):
        """Test OAuth code exchange with invalid code."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "error": "invalid_grant",
                "error_description": "Invalid authorization code",
            }
            mock_post.return_value = mock_response

            with pytest.raises(TwitterAuthError) as exc_info:
                await twitter_adapter.exchange_code(
                    code="invalid_code",
                    code_verifier="test_verifier",
                )

            assert "invalid_grant" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_post_text_success(self, twitter_adapter, mock_twitter_post_response):
        """Test successful tweet posting."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 201
            mock_response.json.return_value = mock_twitter_post_response
            mock_post.return_value = mock_response

            result = await twitter_adapter.post_text(
                access_token="test_token",
                content="Test tweet content",
            )

            assert result["id"] == "1234567890"
            assert result["text"] == "Test tweet content"

    @pytest.mark.asyncio
    async def test_post_text_rate_limited(self, twitter_adapter):
        """Test handling of Twitter rate limit response."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 429
            mock_response.headers = {
                "x-rate-limit-reset": str(int(datetime.now(UTC).timestamp()) + 900)
            }
            mock_response.json.return_value = {
                "title": "Too Many Requests",
                "detail": "Too Many Requests",
                "type": "about:blank",
            }
            mock_post.return_value = mock_response

            with pytest.raises(TwitterRateLimitError) as exc_info:
                await twitter_adapter.post_text(
                    access_token="test_token",
                    content="Test tweet",
                )

            assert "rate limit" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_post_with_media(
        self, twitter_adapter, mock_twitter_media_response, mock_twitter_post_response
    ):
        """Test posting tweet with image attachments."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.post") as mock_post:
            # Mock media upload
            media_response = AsyncMock()
            media_response.status_code = 200
            media_response.json.return_value = mock_twitter_media_response

            # Mock tweet creation with media
            tweet_response = AsyncMock()
            tweet_response.status_code = 201
            mock_twitter_post_response["data"]["attachments"] = {"media_keys": ["123456789"]}
            tweet_response.json.return_value = mock_twitter_post_response

            mock_post.side_effect = [media_response, tweet_response]

            result = await twitter_adapter.post_with_media(
                access_token="test_token",
                content="Tweet with image",
                media_urls=["https://example.com/image.png"],
            )

            assert result["id"] == "1234567890"
            assert "attachments" in result

    @pytest.mark.asyncio
    async def test_character_limit_validation(self, twitter_adapter):
        """Test validation of Twitter's 280 character limit."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        # Content exactly at limit should work
        valid_content = "a" * 280
        assert twitter_adapter.validate_content(valid_content) is True

        # Content over limit should fail
        invalid_content = "a" * 281
        with pytest.raises(TwitterError) as exc_info:
            twitter_adapter.validate_content(invalid_content, raise_error=True)

        assert "280" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_token(self, twitter_adapter, mock_twitter_auth_response):
        """Test refreshing expired access token."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_twitter_auth_response["access_token"] = "new_access_token"
            mock_response.json.return_value = mock_twitter_auth_response
            mock_post.return_value = mock_response

            tokens = await twitter_adapter.refresh_access_token(
                refresh_token="test_refresh_token",
            )

            assert tokens["access_token"] == "new_access_token"
            assert tokens["refresh_token"] == "test_twitter_refresh_token"

    @pytest.mark.asyncio
    async def test_get_user_profile(self, twitter_adapter):
        """Test fetching authenticated user profile."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "id": "123456",
                    "name": "Test User",
                    "username": "testuser",
                    "profile_image_url": "https://example.com/avatar.jpg",
                }
            }
            mock_get.return_value = mock_response

            profile = await twitter_adapter.get_user_profile(
                access_token="test_token",
            )

            assert profile["id"] == "123456"
            assert profile["username"] == "testuser"


# ============================================================================
# LinkedIn Adapter Tests
# ============================================================================


@pytest.fixture
def linkedin_adapter():
    """Create LinkedInAdapter instance with test credentials."""
    if not ADAPTERS_AVAILABLE:
        pytest.skip("LinkedIn adapter not available")
    return LinkedInAdapter(
        client_id="test_linkedin_client_id",
        client_secret="test_linkedin_client_secret",
        redirect_uri="http://localhost:3000/callback",
    )


@pytest.fixture
def mock_linkedin_auth_response() -> dict[str, Any]:
    """Mock successful LinkedIn OAuth token response."""
    return {
        "access_token": "test_linkedin_access_token",
        "expires_in": 5184000,  # 60 days
        "scope": "r_liteprofile w_member_social",
    }


@pytest.fixture
def mock_linkedin_post_response() -> dict[str, Any]:
    """Mock successful LinkedIn post creation response."""
    return {
        "id": "urn:li:share:1234567890",
        "activity": "urn:li:activity:9876543210",
    }


class TestLinkedInAdapter:
    """Tests for LinkedIn API adapter."""

    def test_get_authorization_url(self, linkedin_adapter):
        """Test LinkedIn OAuth authorization URL generation."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        url = linkedin_adapter.get_authorization_url()

        assert "https://www.linkedin.com/oauth/v2/authorization" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "scope=" in url
        assert "state=" in url

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, linkedin_adapter, mock_linkedin_auth_response):
        """Test successful OAuth code exchange for access token."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_linkedin_auth_response
            mock_post.return_value = mock_response

            tokens = await linkedin_adapter.exchange_code(code="test_auth_code")

            assert tokens["access_token"] == "test_linkedin_access_token"
            assert tokens["expires_in"] == 5184000

    @pytest.mark.asyncio
    async def test_post_text_success(self, linkedin_adapter, mock_linkedin_post_response):
        """Test successful LinkedIn post creation."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 201
            mock_response.json.return_value = mock_linkedin_post_response
            mock_post.return_value = mock_response

            result = await linkedin_adapter.post_text(
                access_token="test_token",
                author_id="urn:li:person:123456",
                content="Test LinkedIn post",
            )

            assert "urn:li:share:" in result["id"]

    @pytest.mark.asyncio
    async def test_character_limit_validation(self, linkedin_adapter):
        """Test validation of LinkedIn's 3000 character limit."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        # Content at limit should work
        valid_content = "a" * 3000
        assert linkedin_adapter.validate_content(valid_content) is True

        # Content over limit should fail
        invalid_content = "a" * 3001
        with pytest.raises(LinkedInError) as exc_info:
            linkedin_adapter.validate_content(invalid_content, raise_error=True)

        assert "3000" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_profile(self, linkedin_adapter):
        """Test fetching authenticated user profile."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "urn:li:person:123456",
                "firstName": {
                    "localized": {"en_US": "Test"},
                },
                "lastName": {
                    "localized": {"en_US": "User"},
                },
                "profilePicture": {
                    "displayImage": "urn:li:digitalmediaAsset:12345",
                },
            }
            mock_get.return_value = mock_response

            profile = await linkedin_adapter.get_user_profile(
                access_token="test_token",
            )

            assert "urn:li:person:" in profile["id"]


# ============================================================================
# Facebook Adapter Tests
# ============================================================================


@pytest.fixture
def facebook_adapter():
    """Create FacebookAdapter instance with test credentials."""
    if not ADAPTERS_AVAILABLE:
        pytest.skip("Facebook adapter not available")
    return FacebookAdapter(
        app_id="test_facebook_app_id",
        app_secret="test_facebook_app_secret",
        redirect_uri="http://localhost:3000/callback",
    )


@pytest.fixture
def mock_facebook_auth_response() -> dict[str, Any]:
    """Mock successful Facebook OAuth token response."""
    return {
        "access_token": "test_facebook_access_token",
        "token_type": "bearer",
        "expires_in": 5184000,  # 60 days
    }


@pytest.fixture
def mock_facebook_post_response() -> dict[str, Any]:
    """Mock successful Facebook post creation response."""
    return {
        "id": "123456789_987654321",
    }


class TestFacebookAdapter:
    """Tests for Facebook API adapter."""

    def test_get_authorization_url(self, facebook_adapter):
        """Test Facebook OAuth authorization URL generation."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        url = facebook_adapter.get_authorization_url()

        assert "https://www.facebook.com/v18.0/dialog/oauth" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "scope=" in url
        assert "state=" in url

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, facebook_adapter, mock_facebook_auth_response):
        """Test successful OAuth code exchange for access token."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_facebook_auth_response
            mock_get.return_value = mock_response

            tokens = await facebook_adapter.exchange_code(code="test_auth_code")

            assert tokens["access_token"] == "test_facebook_access_token"
            assert tokens["expires_in"] == 5184000

    @pytest.mark.asyncio
    async def test_post_text_success(self, facebook_adapter, mock_facebook_post_response):
        """Test successful Facebook post creation."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_facebook_post_response
            mock_post.return_value = mock_response

            result = await facebook_adapter.post_text(
                access_token="test_token",
                page_id="123456789",
                content="Test Facebook post",
            )

            assert result["id"] == "123456789_987654321"

    @pytest.mark.asyncio
    async def test_character_limit_validation(self, facebook_adapter):
        """Test validation of Facebook's 63206 character limit."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        # Content at limit should work
        valid_content = "a" * 63206
        assert facebook_adapter.validate_content(valid_content) is True

        # Content over limit should fail
        invalid_content = "a" * 63207
        with pytest.raises(FacebookError) as exc_info:
            facebook_adapter.validate_content(invalid_content, raise_error=True)

        assert "63206" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_pages(self, facebook_adapter):
        """Test fetching user's Facebook pages."""
        if not ADAPTERS_AVAILABLE:
            pytest.skip("Adapters not available")

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {
                        "id": "123456789",
                        "name": "Test Page",
                        "access_token": "page_access_token",
                    },
                ],
            }
            mock_get.return_value = mock_response

            pages = await facebook_adapter.get_pages(
                access_token="test_token",
            )

            assert len(pages) == 1
            assert pages[0]["id"] == "123456789"
            assert pages[0]["name"] == "Test Page"
