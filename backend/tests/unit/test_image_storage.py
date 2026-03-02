"""
Tests for image storage adapters.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from adapters.storage.image_storage import (
    LocalStorageAdapter,
    S3StorageAdapter,
    download_image,
    get_storage_adapter,
)


class TestLocalStorageAdapter:
    """Tests for LocalStorageAdapter."""

    @pytest.fixture
    def temp_storage_path(self, tmp_path):
        """Create temporary storage path for testing."""
        storage_path = tmp_path / "uploads"
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path

    @pytest.fixture
    def adapter(self, temp_storage_path):
        """Create LocalStorageAdapter instance."""
        return LocalStorageAdapter(base_path=str(temp_storage_path))

    @pytest.fixture
    def sample_image_data(self):
        """Sample image data for testing."""
        # Minimal valid PNG header
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00"

    @pytest.mark.asyncio
    async def test_save_image_creates_directory(self, adapter, sample_image_data):
        """Test that save_image creates necessary directories."""
        path = await adapter.save_image(sample_image_data, "test.png")

        # Verify the file exists
        full_path = adapter.base_path / path
        assert full_path.exists()
        assert full_path.is_file()

    @pytest.mark.asyncio
    async def test_save_image_organizes_by_date(self, adapter, sample_image_data):
        """Test that images are organized in YYYY/MM structure."""
        from datetime import datetime

        now = datetime.now()
        expected_path_prefix = f"images/{now.year}/{now.month:02d}/"

        path = await adapter.save_image(sample_image_data, "test.png")

        # Normalize path separators for Windows compatibility
        normalized_path = path.replace("\\", "/")
        assert normalized_path.startswith(expected_path_prefix)

    @pytest.mark.asyncio
    async def test_save_image_sanitizes_filename(self, adapter, sample_image_data):
        """Test that filenames are sanitized."""
        dangerous_name = "../../../etc/passwd"
        path = await adapter.save_image(sample_image_data, dangerous_name)

        # Should not contain path traversal
        assert ".." not in path
        assert "etc" not in path
        assert "passwd" in path  # The filename part should be preserved

    @pytest.mark.asyncio
    async def test_save_image_adds_timestamp(self, adapter, sample_image_data):
        """Test that timestamp is added to avoid collisions."""
        path1 = await adapter.save_image(sample_image_data, "test.png")
        path2 = await adapter.save_image(sample_image_data, "test.png")

        # Paths should be different due to timestamp
        assert path1 != path2

    @pytest.mark.asyncio
    async def test_save_image_preserves_content(self, adapter, sample_image_data):
        """Test that saved image content matches original."""
        path = await adapter.save_image(sample_image_data, "test.png")

        full_path = adapter.base_path / path
        with open(full_path, "rb") as f:
            saved_data = f.read()

        assert saved_data == sample_image_data

    @pytest.mark.asyncio
    async def test_delete_image_success(self, adapter, sample_image_data):
        """Test successful image deletion."""
        # First save an image
        path = await adapter.save_image(sample_image_data, "test.png")

        # Verify it exists
        full_path = adapter.base_path / path
        assert full_path.exists()

        # Delete it
        result = await adapter.delete_image(path)

        assert result is True
        assert not full_path.exists()

    @pytest.mark.asyncio
    async def test_delete_image_not_found(self, adapter):
        """Test deletion of non-existent image."""
        result = await adapter.delete_image("images/2026/02/nonexistent.png")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_image_url(self, adapter):
        """Test URL generation for local images."""
        path = "images/2026/02/test_12345.png"
        url = await adapter.get_image_url(path)

        assert "uploads" in url
        assert path in url
        assert url.startswith("http")


class TestS3StorageAdapter:
    """Tests for S3StorageAdapter."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create mock S3 client."""
        client = Mock()
        client.put_object = Mock()
        client.delete_object = Mock()
        return client

    @pytest.fixture
    def adapter(self, mock_s3_client):
        """Create S3StorageAdapter instance with mocked client."""
        with patch("adapters.storage.image_storage.boto3.client", return_value=mock_s3_client):
            adapter = S3StorageAdapter(
                bucket="test-bucket",
                region="us-east-1",
                access_key="test-key",
                secret_key="test-secret",
            )
        return adapter

    @pytest.fixture
    def sample_image_data(self):
        """Sample image data for testing."""
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00"

    @pytest.mark.asyncio
    async def test_save_image_uploads_to_s3(self, adapter, sample_image_data):
        """Test that save_image uploads to S3."""
        url = await adapter.save_image(sample_image_data, "test.png")

        # Verify put_object was called
        adapter.s3_client.put_object.assert_called_once()

        # Check the call arguments
        call_args = adapter.s3_client.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["Body"] == sample_image_data
        assert call_args[1]["ContentType"] == "image/png"
        # ACL is no longer set — images are private, served via presigned URLs
        assert "ACL" not in call_args[1]

        # save_image now returns the S3 key (not the full URL)
        assert "images/" in url

    @pytest.mark.asyncio
    async def test_save_image_sets_correct_content_type(self, adapter, sample_image_data):
        """Test that content type is set correctly for different formats."""
        # Test JPEG
        await adapter.save_image(sample_image_data, "test.jpg")
        call_args = adapter.s3_client.put_object.call_args
        assert call_args[1]["ContentType"] == "image/jpeg"

        # Test WebP
        await adapter.save_image(sample_image_data, "test.webp")
        call_args = adapter.s3_client.put_object.call_args
        assert call_args[1]["ContentType"] == "image/webp"

        # Test GIF
        await adapter.save_image(sample_image_data, "test.gif")
        call_args = adapter.s3_client.put_object.call_args
        assert call_args[1]["ContentType"] == "image/gif"

    @pytest.mark.asyncio
    async def test_save_image_organizes_by_date(self, adapter, sample_image_data):
        """Test that S3 keys are organized by date."""
        from datetime import datetime

        now = datetime.now()
        expected_prefix = f"images/{now.year}/{now.month:02d}/"

        url = await adapter.save_image(sample_image_data, "test.png")

        # Extract key from URL
        assert expected_prefix in url

    @pytest.mark.asyncio
    async def test_save_image_handles_no_credentials(self, sample_image_data):
        """Test error handling when credentials are missing."""
        with patch("adapters.storage.image_storage.boto3.client") as mock_client:
            mock_client.return_value.put_object.side_effect = NoCredentialsError()

            adapter = S3StorageAdapter(
                bucket="test-bucket",
                region="us-east-1",
                access_key="key",
                secret_key="secret",
            )

            with pytest.raises(RuntimeError, match="credentials"):
                await adapter.save_image(sample_image_data, "test.png")

    @pytest.mark.asyncio
    async def test_save_image_handles_client_error(self, adapter, sample_image_data):
        """Test error handling for S3 client errors."""
        adapter.s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "PutObject"
        )

        with pytest.raises(RuntimeError, match="Failed to upload to S3"):
            await adapter.save_image(sample_image_data, "test.png")

    @pytest.mark.asyncio
    async def test_delete_image_success(self, adapter):
        """Test successful image deletion from S3."""
        s3_key = "images/2026/02/test.png"
        result = await adapter.delete_image(s3_key)

        assert result is True
        adapter.s3_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key=s3_key)

    @pytest.mark.asyncio
    async def test_delete_image_from_url(self, adapter):
        """Test deletion using full S3 URL."""
        url = "https://test-bucket.s3.us-east-1.amazonaws.com/images/2026/02/test.png"
        result = await adapter.delete_image(url)

        assert result is True
        # Should extract key from URL
        adapter.s3_client.delete_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_image_handles_error(self, adapter):
        """Test error handling during deletion."""
        adapter.s3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}}, "DeleteObject"
        )

        result = await adapter.delete_image("images/2026/02/test.png")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_image_url_format(self, adapter):
        """Test S3 presigned URL generation."""
        s3_key = "images/2026/02/test_12345.png"
        # Mock generate_presigned_url to return a known URL
        adapter.s3_client.generate_presigned_url = Mock(
            return_value=f"https://test-bucket.s3.us-east-1.amazonaws.com/{s3_key}?X-Amz-Signature=abc"
        )
        url = await adapter.get_image_url(s3_key)

        adapter.s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": s3_key},
            ExpiresIn=604800,
        )
        assert s3_key in url


class TestDownloadImage:
    """Tests for download_image helper function."""

    @pytest.mark.asyncio
    async def test_download_image_success(self):
        """Test successful image download."""
        test_url = "https://example.com/image.png"
        test_data = b"fake image data"

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "image/png"}
        mock_response.read = AsyncMock(return_value=test_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "adapters.storage.image_storage.aiohttp.ClientSession", return_value=mock_session
        ):
            result = await download_image(test_url)

        assert result == test_data

    @pytest.mark.asyncio
    async def test_download_image_http_error(self):
        """Test handling of HTTP errors."""
        test_url = "https://example.com/notfound.png"

        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "adapters.storage.image_storage.aiohttp.ClientSession", return_value=mock_session
        ):
            with pytest.raises(RuntimeError, match="Status: 404"):
                await download_image(test_url)

    @pytest.mark.asyncio
    async def test_download_image_network_error(self):
        """Test handling of network errors."""
        test_url = "https://example.com/image.png"

        import aiohttp

        mock_session = MagicMock()
        mock_session.get = Mock(side_effect=aiohttp.ClientError("Network error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "adapters.storage.image_storage.aiohttp.ClientSession", return_value=mock_session
        ):
            with pytest.raises(RuntimeError, match="Network error"):
                await download_image(test_url)


class TestGetStorageAdapter:
    """Tests for get_storage_adapter factory function."""

    def test_get_local_adapter(self):
        """Test factory returns LocalStorageAdapter for 'local' type."""
        with patch("adapters.storage.image_storage.settings") as mock_settings:
            mock_settings.storage_type = "local"
            mock_settings.storage_local_path = "./data/uploads"

            adapter = get_storage_adapter()

            assert isinstance(adapter, LocalStorageAdapter)

    def test_get_s3_adapter(self):
        """Test factory returns S3StorageAdapter for 's3' type."""
        with patch("adapters.storage.image_storage.settings") as mock_settings:
            mock_settings.storage_type = "s3"
            mock_settings.s3_bucket = "test-bucket"
            mock_settings.s3_region = "us-east-1"
            mock_settings.s3_access_key = None
            mock_settings.s3_secret_key = None

            with patch("adapters.storage.image_storage.boto3.client"):
                adapter = get_storage_adapter()

            assert isinstance(adapter, S3StorageAdapter)

    def test_get_adapter_invalid_type(self):
        """Test factory raises error for invalid storage type."""
        with patch("adapters.storage.image_storage.settings") as mock_settings:
            mock_settings.storage_type = "invalid"

            with pytest.raises(ValueError, match="Unknown storage type"):
                get_storage_adapter()
