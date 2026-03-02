"""
Tests for WordPress REST API adapter.
"""

import base64
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from adapters.cms.wordpress_adapter import (
    WordPressAdapter,
    WordPressAPIError,
    WordPressAuthError,
    WordPressConnection,
    WordPressConnectionError,
)


class TestWordPressConnection:
    """Tests for WordPressConnection dataclass."""

    def test_connection_initialization(self):
        """Test WordPressConnection initialization."""
        conn = WordPressConnection(
            site_url="https://example.com",
            username="testuser",
            app_password="test1234",
        )

        assert conn.site_url == "https://example.com"
        assert conn.username == "testuser"
        assert conn.app_password == "test1234"
        assert conn.is_valid is False

    def test_get_api_base_url(self):
        """Test API base URL generation."""
        conn = WordPressConnection(
            site_url="https://example.com",
            username="testuser",
            app_password="test1234",
        )

        base_url = conn.get_api_base_url()
        assert base_url == "https://example.com/wp-json/wp/v2"

    def test_get_api_base_url_with_trailing_slash(self):
        """Test API base URL generation with trailing slash."""
        conn = WordPressConnection(
            site_url="https://example.com/",
            username="testuser",
            app_password="test1234",
        )

        base_url = conn.get_api_base_url()
        assert base_url == "https://example.com/wp-json/wp/v2"


class TestWordPressAdapter:
    """Tests for WordPressAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create WordPressAdapter instance."""
        return WordPressAdapter(
            site_url="https://example.com",
            username="testuser",
            app_password="abcd efgh ijkl mnop",  # Test with spaces
        )

    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""

        def _create_response(status_code=200, json_data=None):
            response = Mock(spec=httpx.Response)
            response.status_code = status_code
            response.json.return_value = json_data or {}
            response.text = ""
            return response

        return _create_response

    def test_adapter_initialization(self, adapter):
        """Test adapter initialization."""
        assert adapter.connection.site_url == "https://example.com"
        assert adapter.connection.username == "testuser"
        # Spaces should be removed from app password
        assert adapter.connection.app_password == "abcdefghijklmnop"
        assert adapter.timeout == 30

    def test_build_url(self, adapter):
        """Test URL building."""
        url = adapter._build_url("posts")
        assert url == "https://example.com/wp-json/wp/v2/posts"

        url = adapter._build_url("media")
        assert url == "https://example.com/wp-json/wp/v2/media"

    def test_get_client_creates_auth_headers(self, adapter):
        """Test that client is created with correct auth headers."""
        client = adapter._get_client()

        # Verify Authorization header
        credentials = "testuser:abcdefghijklmnop"
        expected_auth = f"Basic {base64.b64encode(credentials.encode()).decode()}"

        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == expected_auth
        assert client.headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_close_client(self, adapter):
        """Test closing the HTTP client."""
        # Create client
        adapter._get_client()
        assert adapter._client is not None

        # Close it
        await adapter.close()
        assert adapter._client is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager usage."""
        async with WordPressAdapter(
            site_url="https://example.com",
            username="testuser",
            app_password="test1234",
        ) as adapter:
            assert adapter is not None

        # Client should be closed after exiting context
        assert adapter._client is None

    @pytest.mark.asyncio
    async def test_handle_response_success(self, adapter, mock_response):
        """Test successful response handling."""
        response = mock_response(200, {"id": 1, "title": "Test"})
        result = await adapter._handle_response(response)

        assert result == {"id": 1, "title": "Test"}

    @pytest.mark.asyncio
    async def test_handle_response_auth_error_401(self, adapter, mock_response):
        """Test 401 authentication error."""
        response = mock_response(401, {"code": "invalid_credentials"})

        with pytest.raises(WordPressAuthError) as exc_info:
            await adapter._handle_response(response)

        assert "Authentication failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_response_auth_error_403(self, adapter, mock_response):
        """Test 403 authorization error."""
        response = mock_response(403, {"code": "forbidden"})

        with pytest.raises(WordPressAuthError) as exc_info:
            await adapter._handle_response(response)

        assert "Authorization failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_response_api_error(self, adapter, mock_response):
        """Test API error handling."""
        response = mock_response(400, {"code": "invalid_post", "message": "Invalid post data"})

        with pytest.raises(WordPressAPIError) as exc_info:
            await adapter._handle_response(response)

        assert "Invalid post data" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_test_connection_success(self, adapter, mock_response):
        """Test successful connection test."""
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response(200, {"id": 1, "name": "Test User"})

        with patch.object(adapter, "_get_client", return_value=mock_client):
            result = await adapter.test_connection()

        assert result is True
        assert adapter.connection.is_valid is True

    @pytest.mark.asyncio
    async def test_test_connection_auth_failure(self, adapter, mock_response):
        """Test connection test with auth failure."""
        mock_client = AsyncMock()
        # Status code 401 will trigger _handle_response which raises WordPressAuthError
        mock_response_obj = mock_response(401, {"code": "invalid_auth"})
        mock_client.get.return_value = mock_response_obj

        with patch.object(adapter, "_get_client", return_value=mock_client):
            # Since status is not 200, test_connection won't return False
            # Instead, _handle_response is called which raises WordPressAuthError
            with pytest.raises(WordPressAuthError):
                await adapter.test_connection()

        assert adapter.connection.is_valid is False

    @pytest.mark.asyncio
    async def test_test_connection_network_error(self, adapter):
        """Test connection test with network error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with pytest.raises(WordPressConnectionError) as exc_info:
                await adapter.test_connection()

        assert "Cannot connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_test_connection_timeout(self, adapter):
        """Test connection test with timeout."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with pytest.raises(WordPressConnectionError) as exc_info:
                await adapter.test_connection()

        assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_categories(self, adapter, mock_response):
        """Test fetching categories."""
        mock_categories = [
            {"id": 1, "name": "Category 1", "slug": "category-1"},
            {"id": 2, "name": "Category 2", "slug": "category-2"},
        ]

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response(200, mock_categories)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            categories = await adapter.get_categories()

        assert len(categories) == 2
        assert categories[0]["name"] == "Category 1"

    @pytest.mark.asyncio
    async def test_get_tags(self, adapter, mock_response):
        """Test fetching tags."""
        mock_tags = [
            {"id": 1, "name": "Tag 1", "slug": "tag-1"},
            {"id": 2, "name": "Tag 2", "slug": "tag-2"},
        ]

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response(200, mock_tags)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            tags = await adapter.get_tags()

        assert len(tags) == 2
        assert tags[0]["name"] == "Tag 1"

    @pytest.mark.asyncio
    async def test_upload_media(self, adapter, mock_response):
        """Test media upload."""
        # Mock image download
        image_data = b"fake image data"
        mock_download_response = Mock()
        mock_download_response.status = 200
        mock_download_response.content = image_data
        mock_download_response.raise_for_status = Mock()

        # Mock WordPress media upload response
        mock_media_response = {
            "id": 123,
            "source_url": "https://example.com/wp-content/uploads/test.jpg",
            "alt_text": "Test image",
        }

        with patch("httpx.AsyncClient") as mock_async_client:
            # Mock download client
            mock_download_ctx = AsyncMock()
            mock_download_ctx.__aenter__.return_value.get.return_value = mock_download_response

            # Mock upload client
            mock_upload_ctx = AsyncMock()
            mock_upload_ctx.__aenter__.return_value.post.return_value = mock_response(
                201, mock_media_response
            )

            # Configure the mock to return different contexts
            mock_async_client.return_value.__aenter__.side_effect = [
                mock_download_ctx.__aenter__.return_value,
                mock_upload_ctx.__aenter__.return_value,
            ]

            media = await adapter.upload_media(
                image_url="https://example.com/image.jpg",
                filename="test.jpg",
                alt_text="Test image",
            )

        assert media["id"] == 123
        assert "source_url" in media

    @pytest.mark.asyncio
    async def test_create_post_minimal(self, adapter, mock_response):
        """Test creating a post with minimal data."""
        mock_post = {
            "id": 456,
            "title": {"rendered": "Test Post"},
            "link": "https://example.com/test-post",
            "status": "draft",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response(201, mock_post)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            post = await adapter.create_post(
                title="Test Post",
                content="<p>Test content</p>",
            )

        assert post["id"] == 456
        assert post["status"] == "draft"

    @pytest.mark.asyncio
    async def test_create_post_full_options(self, adapter, mock_response):
        """Test creating a post with all options."""
        mock_post = {
            "id": 789,
            "title": {"rendered": "Full Post"},
            "link": "https://example.com/full-post",
            "status": "publish",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response(201, mock_post)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            post = await adapter.create_post(
                title="Full Post",
                content="<p>Full content</p>",
                status="publish",
                categories=[1, 2],
                tags=[3, 4],
                featured_media_id=123,
                meta_description="Test meta description",
                excerpt="Test excerpt",
            )

        assert post["id"] == 789
        assert post["status"] == "publish"

        # Verify the post data sent to WordPress
        call_args = mock_client.post.call_args
        post_data = call_args.kwargs["json"]

        assert post_data["categories"] == [1, 2]
        assert post_data["tags"] == [3, 4]
        assert post_data["featured_media"] == 123
        assert post_data["excerpt"] == "Test excerpt"
        assert "_yoast_wpseo_metadesc" in post_data["meta"]

    @pytest.mark.asyncio
    async def test_update_post(self, adapter, mock_response):
        """Test updating a post."""
        mock_updated_post = {
            "id": 456,
            "title": {"rendered": "Updated Title"},
            "status": "publish",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response(200, mock_updated_post)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            post = await adapter.update_post(
                post_id=456,
                title="Updated Title",
                status="publish",
            )

        assert post["id"] == 456
        assert post["title"]["rendered"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_post_filters_none_values(self, adapter, mock_response):
        """Test that update_post filters out None values."""
        mock_updated_post = {"id": 456}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response(200, mock_updated_post)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            await adapter.update_post(
                post_id=456,
                title="Updated Title",
                status=None,  # Should be filtered out
                categories=None,  # Should be filtered out
            )

        # Verify only non-None values were sent
        call_args = mock_client.post.call_args
        post_data = call_args.kwargs["json"]

        assert "title" in post_data
        assert "status" not in post_data
        assert "categories" not in post_data

    @pytest.mark.asyncio
    async def test_get_post(self, adapter, mock_response):
        """Test retrieving a post."""
        mock_post = {
            "id": 456,
            "title": {"rendered": "Test Post"},
            "content": {"rendered": "<p>Content</p>"},
            "status": "publish",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response(200, mock_post)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            post = await adapter.get_post(post_id=456)

        assert post["id"] == 456
        assert post["title"]["rendered"] == "Test Post"

    @pytest.mark.asyncio
    async def test_get_post_not_found(self, adapter, mock_response):
        """Test retrieving a non-existent post."""
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response(
            404, {"code": "not_found", "message": "Post not found"}
        )

        with patch.object(adapter, "_get_client", return_value=mock_client):
            with pytest.raises(WordPressAPIError) as exc_info:
                await adapter.get_post(post_id=999)

        assert "Post not found" in str(exc_info.value)


class TestWordPressAdapterIntegration:
    """Integration-style tests for WordPress adapter."""

    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""

        def _create_response(status_code=200, json_data=None):
            response = Mock(spec=httpx.Response)
            response.status_code = status_code
            response.json.return_value = json_data or {}
            response.text = ""
            return response

        return _create_response

    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_response):
        """Test a complete workflow: test connection, upload media, create post."""
        adapter = WordPressAdapter(
            site_url="https://example.com",
            username="testuser",
            app_password="test1234",
        )

        # Mock all HTTP interactions
        mock_client = AsyncMock()

        # Step 1: Test connection
        mock_client.get.return_value = mock_response(200, {"id": 1, "name": "Test User"})

        with patch.object(adapter, "_get_client", return_value=mock_client):
            connection_ok = await adapter.test_connection()
            assert connection_ok is True

        # Step 2: Upload media
        image_data = b"fake image data"
        mock_download_response = Mock()
        mock_download_response.status = 200
        mock_download_response.content = image_data
        mock_download_response.raise_for_status = Mock()

        mock_media = {"id": 123, "source_url": "https://example.com/image.jpg"}

        with patch("httpx.AsyncClient") as mock_async_client:
            mock_download_ctx = AsyncMock()
            mock_download_ctx.__aenter__.return_value.get.return_value = mock_download_response

            mock_upload_ctx = AsyncMock()
            mock_upload_ctx.__aenter__.return_value.post.return_value = mock_response(
                201, mock_media
            )

            mock_async_client.return_value.__aenter__.side_effect = [
                mock_download_ctx.__aenter__.return_value,
                mock_upload_ctx.__aenter__.return_value,
            ]

            media = await adapter.upload_media(
                image_url="https://example.com/test.jpg",
                filename="test.jpg",
                alt_text="Test",
            )

        # Step 3: Create post with uploaded media
        mock_post = {"id": 456, "link": "https://example.com/test-post"}
        mock_client.post.return_value = mock_response(201, mock_post)

        with patch.object(adapter, "_get_client", return_value=mock_client):
            post = await adapter.create_post(
                title="Test Post",
                content="<p>Content</p>",
                featured_media_id=media["id"],
            )

        assert post["id"] == 456

        # Clean up (mock client doesn't need closing in this test)
        adapter._client = None
