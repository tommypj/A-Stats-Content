"""
Image storage adapters for local and S3 storage.

Provides abstract base class and concrete implementations for storing
generated images locally or in cloud storage.
"""

import os
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import aiofiles
import aiohttp
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class StorageAdapter(ABC):
    """Abstract base class for storage adapters."""

    @abstractmethod
    async def save_image(self, image_data: bytes, filename: str) -> str:
        """
        Save image data to storage.

        Args:
            image_data: Raw image bytes
            filename: Desired filename (will be sanitized)

        Returns:
            URL or path to the saved image
        """
        pass

    @abstractmethod
    async def delete_image(self, path: str) -> bool:
        """
        Delete an image from storage.

        Args:
            path: Path or URL to the image

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    async def get_image_url(self, path: str) -> str:
        """
        Get the public URL for an image.

        Args:
            path: Internal path to the image

        Returns:
            Public URL to access the image
        """
        pass


class LocalStorageAdapter(StorageAdapter):
    """
    Local filesystem storage adapter.

    Saves images to the local filesystem organized by date.
    Structure: /uploads/images/YYYY/MM/filename.png
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize local storage adapter.

        Args:
            base_path: Base directory for uploads (defaults to settings.storage_local_path)
        """
        self.base_path = Path(base_path or settings.storage_local_path)
        self.base_url = settings.frontend_url

    def _get_date_path(self) -> Path:
        """Get the date-based subdirectory path (YYYY/MM)."""
        now = datetime.now()
        return Path("images") / str(now.year) / f"{now.month:02d}"

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for filesystem
        """
        # IMG-32: Remove null bytes first to prevent bypass
        filename = filename.replace("\x00", "")
        # Remove path components
        filename = os.path.basename(filename)

        # Replace unsafe characters
        unsafe_chars = ['/', '\\', '..', '\0', '\n', '\r', '\t']
        for char in unsafe_chars:
            filename = filename.replace(char, '_')

        # IMG-32: Keep only safe characters (word chars, hyphens, dots)
        import re as _re
        filename = _re.sub(r"[^\w\-.]", "_", filename)

        # Ensure we have a valid extension
        if '.' not in filename:
            filename = f"{filename}.png"

        # Add timestamp to avoid collisions
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"{name}_{timestamp}{ext}"

    async def save_image(self, image_data: bytes, filename: str) -> str:
        """
        Save image to local filesystem.

        Args:
            image_data: Raw image bytes
            filename: Desired filename

        Returns:
            Relative path to the saved image
        """
        try:
            # Create date-based path
            date_path = self._get_date_path()
            full_dir = self.base_path / date_path

            # Create directory if it doesn't exist
            full_dir.mkdir(parents=True, exist_ok=True)

            # Sanitize filename
            safe_filename = self._sanitize_filename(filename)
            file_path = full_dir / safe_filename

            # Save file asynchronously
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(image_data)

            # Return relative path
            relative_path = date_path / safe_filename
            logger.info(f"Saved image to local storage: {relative_path}")
            return str(relative_path)

        except Exception as e:
            logger.error(f"Failed to save image to local storage: {e}")
            raise

    async def delete_image(self, path: str) -> bool:
        """
        Delete image from local filesystem.

        Args:
            path: Relative path to the image

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            file_path = self.base_path / path

            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted image from local storage: {path}")
                return True
            else:
                logger.warning(f"Image not found for deletion: {path}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete image from local storage: {e}")
            return False

    async def get_image_url(self, path: str) -> str:
        """
        Get the public URL for a locally stored image.

        Args:
            path: Relative path to the image

        Returns:
            Public URL (served by the backend)
        """
        # In development, this would be served by the backend API
        # In production, might be served by Nginx/CDN
        api_base = settings.frontend_url.replace(':3000', ':8000')
        return f"{api_base}/uploads/{path}"


class S3StorageAdapter(StorageAdapter):
    """
    AWS S3 storage adapter.

    Saves images to AWS S3 with private access. Public URLs are served
    via presigned URLs (default 7-day expiry) or through a CDN if configured.
    """

    PRESIGNED_URL_EXPIRY = 7 * 24 * 3600  # 7 days in seconds

    def __init__(
        self,
        bucket: Optional[str] = None,
        region: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        """
        Initialize S3 storage adapter.

        Args:
            bucket: S3 bucket name (defaults to settings.s3_bucket)
            region: AWS region (defaults to settings.s3_region)
            access_key: AWS access key (defaults to settings.s3_access_key)
            secret_key: AWS secret key (defaults to settings.s3_secret_key)
        """
        self.bucket = bucket or settings.s3_bucket
        self.region = region or settings.s3_region
        self.access_key = access_key or settings.s3_access_key
        self.secret_key = secret_key or settings.s3_secret_key

        # Initialize S3 client
        try:
            if self.access_key and self.secret_key:
                self.s3_client = boto3.client(
                    's3',
                    region_name=self.region,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                )
            else:
                # Try to use default credentials (IAM role, env vars, etc.)
                self.s3_client = boto3.client('s3', region_name=self.region)

            logger.info(f"S3 storage adapter initialized for bucket: {self.bucket}")
        except Exception as e:
            logger.warning(f"Failed to initialize S3 client: {e}")
            self.s3_client = None

    def _get_s3_key(self, filename: str) -> str:
        """
        Generate S3 key with date-based organization.

        Args:
            filename: Original filename

        Returns:
            S3 key in format: images/YYYY/MM/filename.png
        """
        now = datetime.now()
        date_path = f"images/{now.year}/{now.month:02d}"

        # IMG-28: Strip any path components to prevent path traversal in S3 key
        filename = os.path.basename(filename)
        # Add timestamp to filename to avoid collisions
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_filename = f"{name}_{timestamp}{ext}"

        return f"{date_path}/{safe_filename}"

    async def save_image(self, image_data: bytes, filename: str) -> str:
        """
        Upload image to S3.

        Args:
            image_data: Raw image bytes
            filename: Desired filename

        Returns:
            Public S3 URL
        """
        if not self.s3_client:
            raise RuntimeError("S3 client not initialized. Check AWS credentials.")

        if not self.bucket:
            raise RuntimeError("S3 bucket not configured.")

        try:
            # Generate S3 key
            s3_key = self._get_s3_key(filename)

            # Determine content type
            content_type = 'image/png'
            if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif filename.lower().endswith('.webp'):
                content_type = 'image/webp'
            elif filename.lower().endswith('.gif'):
                content_type = 'image/gif'

            # Upload to S3 with private ACL (default)
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=image_data,
                ContentType=content_type,
            )

            # Return the S3 key — callers use get_image_url() to obtain
            # a time-limited presigned URL when serving to clients.
            logger.info(f"Uploaded image to S3: {s3_key}")
            return s3_key

        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise RuntimeError("AWS credentials not configured")
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise RuntimeError(f"Failed to upload to S3: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            raise

    async def delete_image(self, path: str) -> bool:
        """
        Delete image from S3.

        Args:
            path: S3 key or full URL

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.s3_client or not self.bucket:
            logger.warning("S3 not configured, cannot delete image")
            return False

        try:
            # IMG-30: Always use self.bucket, never parse bucket from URL.
            # IMG-29: Extract S3 key from URL using proper URL parsing (not fragile string split).
            s3_key = path
            if path.startswith('http'):
                # Extract key from URL like https://bucket.s3.amazonaws.com/key/path
                # or https://s3.amazonaws.com/bucket/key/path
                parsed = urlparse(path)
                # Key is the path component without the leading slash
                s3_key = parsed.path.lstrip("/")
                # For path-style URLs (s3.amazonaws.com/bucket/key) strip the bucket prefix
                if s3_key.startswith(self.bucket + "/"):
                    s3_key = s3_key[len(self.bucket) + 1:]
                if not s3_key:
                    raise ValueError(f"IMG-29: Could not extract S3 key from URL: {path}")

            bucket = self.bucket  # IMG-30: always use configured bucket, not parsed from URL
            # Delete from S3
            self.s3_client.delete_object(Bucket=bucket, Key=s3_key)
            logger.info(f"Deleted image from S3: {s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 deletion: {e}")
            return False

    async def get_image_url(self, path: str) -> str:
        """
        Get a presigned S3 URL for an image.

        Args:
            path: S3 key

        Returns:
            Time-limited presigned URL (7-day expiry)
        """
        if not self.s3_client or not self.bucket:
            raise RuntimeError("S3 client or bucket not configured")

        # If a CDN domain is configured, use it directly (CDN handles auth)
        # IMG-31: CDN domain must only come from settings, never from user input
        cdn_domain = getattr(settings, 'cdn_domain', None)
        if cdn_domain:
            return f"https://{cdn_domain}/{path}"

        return self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': path},
            ExpiresIn=self.PRESIGNED_URL_EXPIRY,
        )


# IMG-21: Use only top-level domains to prevent SSRF bypass via deep subdomains.
# e.g. evil.pbxt.replicate.delivery.com would match "pbxt.replicate.delivery" via endswith.
# Restricting to top-level domains means only legitimate Replicate subdomains are allowed.
_TOP_LEVEL_ALLOWED_DOMAINS = {"replicate.delivery", "replicate.com"}
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB


async def download_image(url: str) -> bytes:
    """
    Download an image from a URL.

    Useful for downloading images from Replicate or other image generation services
    and saving them to storage.

    Args:
        url: URL of the image to download

    Returns:
        Raw image bytes

    Raises:
        ValueError: If the URL fails domain or size validation
        RuntimeError: If download fails
    """
    # SSRF: validate domain before fetching — IMG-21: use top-level domain allowlist
    parsed = urlparse(url)
    netloc = parsed.netloc
    if parsed.scheme != "https" or not any(
        netloc == d or netloc.endswith("." + d)
        for d in _TOP_LEVEL_ALLOWED_DOMAINS
    ):
        raise ValueError(f"Image URL failed domain validation: {netloc}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    # IMG-22: Check content-type BEFORE reading the body to avoid
                    # downloading large non-image payloads
                    content_type = response.headers.get("content-type", "").lower()
                    if not content_type.startswith("image/"):
                        raise ValueError(
                            f"Downloaded content is not an image (content-type: {content_type})"
                        )
                    # Size limit: check Content-Length header first to fail fast
                    content_length = response.headers.get("content-length")
                    # IMG-23: Wrap int() conversion to handle malformed Content-Length header
                    try:
                        size = int(content_length) if content_length else None
                    except (ValueError, TypeError):
                        size = None
                    if size is not None and size > MAX_IMAGE_SIZE:
                        raise ValueError(f"Image too large: {content_length} bytes")
                    image_data = await response.read()
                    if len(image_data) > MAX_IMAGE_SIZE:
                        raise ValueError(f"Downloaded image exceeds {MAX_IMAGE_SIZE} bytes")
                    logger.info(f"Downloaded image from {url} ({len(image_data)} bytes)")
                    return image_data
                else:
                    raise RuntimeError(
                        f"Failed to download image. Status: {response.status}"
                    )
    except (ValueError, RuntimeError):
        raise
    except aiohttp.ClientError as e:
        logger.error(f"Network error downloading image from {url}: {e}")
        raise RuntimeError(f"Network error: {e}")
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
        raise RuntimeError(f"Download failed: {e}")


def get_storage_adapter() -> StorageAdapter:
    """
    Factory function to get the appropriate storage adapter.

    Returns the correct storage adapter based on settings.storage_type.

    Returns:
        StorageAdapter instance (LocalStorageAdapter or S3StorageAdapter)

    Raises:
        ValueError: If storage_type is not recognized
    """
    storage_type = settings.storage_type.lower()

    if storage_type == "local":
        return LocalStorageAdapter()
    elif storage_type == "s3":
        return S3StorageAdapter()
    else:
        raise ValueError(
            f"Unknown storage type: {storage_type}. Must be 'local' or 's3'"
        )


# Convenience singleton for quick access
storage_adapter = get_storage_adapter()
