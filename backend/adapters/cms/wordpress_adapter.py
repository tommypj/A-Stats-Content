"""
WordPress REST API adapter for publishing articles.

Provides integration with WordPress sites using the WordPress REST API v2
and Application Password authentication.
"""

import base64
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


# Custom Exceptions
class WordPressConnectionError(Exception):
    """Raised when connection to WordPress site fails."""
    pass


class WordPressAuthError(Exception):
    """Raised when authentication with WordPress fails."""
    pass


class WordPressAPIError(Exception):
    """Raised when WordPress API returns an error."""
    pass


@dataclass
class WordPressConnection:
    """WordPress connection credentials."""

    site_url: str
    username: str
    app_password: str
    is_valid: bool = False

    def get_api_base_url(self) -> str:
        """Get the WordPress REST API base URL."""
        # Ensure site_url doesn't end with slash
        site_url = self.site_url.rstrip('/')
        return f"{site_url}/wp-json/wp/v2"


class WordPressAdapter:
    """
    WordPress REST API adapter for content publishing.

    Uses WordPress Application Passwords for authentication via Basic Auth.
    Supports creating posts, uploading media, and managing categories/tags.
    """

    def __init__(
        self,
        site_url: str,
        username: str,
        app_password: str,
        timeout: int = 30,
    ):
        """
        Initialize WordPress adapter.

        Args:
            site_url: WordPress site URL (e.g., "https://example.com")
            username: WordPress username
            app_password: WordPress Application Password (without spaces)
            timeout: Request timeout in seconds (default: 30)
        """
        self.connection = WordPressConnection(
            site_url=site_url.rstrip('/'),
            username=username,
            app_password=app_password.replace(' ', ''),  # Remove spaces from app password
        )
        self.timeout = timeout
        self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client with auth headers."""
        if self._client is None:
            # Create Basic Auth header
            credentials = f"{self.connection.username}:{self.connection.app_password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True,
            )

        return self._client

    async def close(self):
        """Close the HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _build_url(self, endpoint: str) -> str:
        """
        Build full API URL from endpoint.

        Args:
            endpoint: API endpoint (e.g., "posts", "media")

        Returns:
            Full API URL
        """
        base_url = self.connection.get_api_base_url()
        return urljoin(base_url + '/', endpoint)

    async def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON response

        Raises:
            WordPressAuthError: If authentication fails (401, 403)
            WordPressAPIError: If API returns an error
        """
        if response.status_code == 401:
            logger.error("WordPress authentication failed: Invalid credentials")
            raise WordPressAuthError(
                "Authentication failed. Check username and application password."
            )

        if response.status_code == 403:
            logger.error("WordPress authorization failed: Insufficient permissions")
            raise WordPressAuthError(
                "Authorization failed. User doesn't have required permissions."
            )

        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_message = error_data.get('message', 'Unknown error')
                error_code = error_data.get('code', response.status_code)
            except Exception:
                error_message = response.text or f"HTTP {response.status_code}"
                error_code = response.status_code

            logger.error(f"WordPress API error [{error_code}]: {error_message}")
            raise WordPressAPIError(f"API error [{error_code}]: {error_message}")

        try:
            return response.json()
        except Exception as e:
            logger.error(f"Failed to parse WordPress API response: {e}")
            raise WordPressAPIError(f"Invalid JSON response: {e}")

    async def test_connection(self) -> bool:
        """
        Test WordPress connection and credentials.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            client = self._get_client()
            url = self._build_url("users/me")

            logger.info(f"Testing WordPress connection to {self.connection.site_url}")
            response = await client.get(url)

            # Always handle response to get proper error handling
            user_data = await self._handle_response(response)

            logger.info(
                f"WordPress connection successful. "
                f"Authenticated as: {user_data.get('name', 'Unknown')}"
            )
            self.connection.is_valid = True
            return True

        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to WordPress site: {e}")
            raise WordPressConnectionError(
                f"Cannot connect to {self.connection.site_url}. "
                "Check the site URL and network connection."
            )
        except httpx.TimeoutException as e:
            logger.error(f"WordPress connection timeout: {e}")
            raise WordPressConnectionError(
                f"Connection timeout. Site did not respond within {self.timeout} seconds."
            )
        except (WordPressAuthError, WordPressAPIError):
            self.connection.is_valid = False
            raise
        except Exception as e:
            logger.error(f"Unexpected error testing WordPress connection: {e}")
            self.connection.is_valid = False
            raise WordPressConnectionError(f"Connection test failed: {e}")

    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Fetch available WordPress categories.

        Returns:
            List of category objects with id, name, slug, etc.

        Raises:
            WordPressAPIError: If API request fails
        """
        try:
            client = self._get_client()
            url = self._build_url("categories")

            # Fetch all categories (up to 100)
            params = {"per_page": 100, "orderby": "name", "order": "asc"}

            logger.info("Fetching WordPress categories")
            response = await client.get(url, params=params)
            categories = await self._handle_response(response)

            logger.info(f"Retrieved {len(categories)} categories")
            return categories

        except (WordPressAuthError, WordPressAPIError):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch categories: {e}")
            raise WordPressAPIError(f"Failed to fetch categories: {e}")

    async def get_tags(self) -> List[Dict[str, Any]]:
        """
        Fetch available WordPress tags.

        Returns:
            List of tag objects with id, name, slug, etc.

        Raises:
            WordPressAPIError: If API request fails
        """
        try:
            client = self._get_client()
            url = self._build_url("tags")

            # Fetch all tags (up to 100)
            params = {"per_page": 100, "orderby": "name", "order": "asc"}

            logger.info("Fetching WordPress tags")
            response = await client.get(url, params=params)
            tags = await self._handle_response(response)

            logger.info(f"Retrieved {len(tags)} tags")
            return tags

        except (WordPressAuthError, WordPressAPIError):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch tags: {e}")
            raise WordPressAPIError(f"Failed to fetch tags: {e}")

    async def upload_media(
        self,
        image_url: str,
        filename: str,
        alt_text: str = "",
    ) -> Dict[str, Any]:
        """
        Upload an image to WordPress media library.

        Args:
            image_url: URL of the image to download and upload
            filename: Filename for the uploaded image
            alt_text: Alternative text for the image (for accessibility)

        Returns:
            Media object with id, url, source_url, etc.

        Raises:
            WordPressAPIError: If upload fails
        """
        try:
            # Download the image first
            logger.info(f"Downloading image from {image_url}")
            async with httpx.AsyncClient(timeout=self.timeout) as download_client:
                image_response = await download_client.get(image_url)
                image_response.raise_for_status()
                image_data = image_response.content

            logger.info(f"Downloaded {len(image_data)} bytes")

            # Determine content type
            content_type = "image/jpeg"
            if filename.lower().endswith('.png'):
                content_type = "image/png"
            elif filename.lower().endswith('.webp'):
                content_type = "image/webp"
            elif filename.lower().endswith('.gif'):
                content_type = "image/gif"

            # Upload to WordPress
            client = self._get_client()
            url = self._build_url("media")

            # WordPress expects multipart form data for media uploads
            files = {
                'file': (filename, image_data, content_type)
            }

            # Add alt text if provided
            data = {}
            if alt_text:
                data['alt_text'] = alt_text

            logger.info(f"Uploading image to WordPress: {filename}")

            # We need to create a new client for multipart/form-data
            credentials = f"{self.connection.username}:{self.connection.app_password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Authorization": f"Basic {encoded_credentials}",
            }

            async with httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                follow_redirects=True,
            ) as upload_client:
                response = await upload_client.post(url, files=files, data=data)
                media = await self._handle_response(response)

            logger.info(
                f"Media uploaded successfully. "
                f"ID: {media.get('id')}, URL: {media.get('source_url')}"
            )
            return media

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during media upload: {e}")
            raise WordPressAPIError(f"Failed to upload media: {e}")
        except (WordPressAuthError, WordPressAPIError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error during media upload: {e}")
            raise WordPressAPIError(f"Media upload failed: {e}")

    async def create_post(
        self,
        title: str,
        content: str,
        status: str = "draft",
        categories: Optional[List[int]] = None,
        tags: Optional[List[int]] = None,
        featured_media_id: Optional[int] = None,
        meta_description: Optional[str] = None,
        excerpt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new WordPress post.

        Args:
            title: Post title
            content: Post content (HTML)
            status: Post status (draft, publish, pending, private)
            categories: List of category IDs
            tags: List of tag IDs
            featured_media_id: Featured image media ID
            meta_description: SEO meta description (requires Yoast or similar)
            excerpt: Post excerpt

        Returns:
            Post object with id, link, status, etc.

        Raises:
            WordPressAPIError: If post creation fails
        """
        try:
            client = self._get_client()
            url = self._build_url("posts")

            # Build post data
            post_data = {
                "title": title,
                "content": content,
                "status": status,
            }

            if categories:
                post_data["categories"] = categories

            if tags:
                post_data["tags"] = tags

            if featured_media_id:
                post_data["featured_media"] = featured_media_id

            if excerpt:
                post_data["excerpt"] = excerpt

            # Add meta fields (if using Yoast SEO plugin)
            if meta_description:
                post_data["meta"] = {
                    "_yoast_wpseo_metadesc": meta_description,
                }

            logger.info(f"Creating WordPress post: {title} (status: {status})")
            response = await client.post(url, json=post_data)
            post = await self._handle_response(response)

            logger.info(
                f"Post created successfully. "
                f"ID: {post.get('id')}, Link: {post.get('link')}"
            )
            return post

        except (WordPressAuthError, WordPressAPIError):
            raise
        except Exception as e:
            logger.error(f"Failed to create post: {e}")
            raise WordPressAPIError(f"Post creation failed: {e}")

    async def update_post(
        self,
        post_id: int,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Update an existing WordPress post.

        Args:
            post_id: ID of the post to update
            **kwargs: Fields to update (title, content, status, etc.)

        Returns:
            Updated post object

        Raises:
            WordPressAPIError: If update fails
        """
        try:
            client = self._get_client()
            url = self._build_url(f"posts/{post_id}")

            # Filter out None values
            update_data = {k: v for k, v in kwargs.items() if v is not None}

            logger.info(f"Updating WordPress post {post_id}")
            response = await client.post(url, json=update_data)
            post = await self._handle_response(response)

            logger.info(f"Post {post_id} updated successfully")
            return post

        except (WordPressAuthError, WordPressAPIError):
            raise
        except Exception as e:
            logger.error(f"Failed to update post {post_id}: {e}")
            raise WordPressAPIError(f"Post update failed: {e}")

    async def get_post(self, post_id: int) -> Dict[str, Any]:
        """
        Get details of a specific WordPress post.

        Args:
            post_id: ID of the post to retrieve

        Returns:
            Post object with all details

        Raises:
            WordPressAPIError: If retrieval fails
        """
        try:
            client = self._get_client()
            url = self._build_url(f"posts/{post_id}")

            logger.info(f"Retrieving WordPress post {post_id}")
            response = await client.get(url)
            post = await self._handle_response(response)

            logger.info(f"Retrieved post {post_id}: {post.get('title', {}).get('rendered', 'Untitled')}")
            return post

        except (WordPressAuthError, WordPressAPIError):
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve post {post_id}: {e}")
            raise WordPressAPIError(f"Post retrieval failed: {e}")
