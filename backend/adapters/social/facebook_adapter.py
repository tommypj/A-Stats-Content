"""
Facebook Graph API adapter for social media posting.

Provides integration with Facebook Graph API using OAuth 2.0
for posting to Facebook Pages, uploading media, and managing content.
Supports Instagram posting via Facebook API for business accounts.
"""

import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode, urlparse as _urlparse

import httpx

# SM-23: SSRF protection — only allow media URLs from trusted domains
_ALLOWED_MEDIA_DOMAINS = {
    "replicate.delivery",
    "pbxt.replicate.delivery",
    "cdn.replicate.com",
    "uploads.a-stats.online",
}


def _validate_media_url(url: str) -> None:
    """Raise ValueError if the URL scheme is not HTTPS or domain is not whitelisted."""
    parsed = _urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Media URL must use HTTPS: {url}")
    if not any(
        parsed.netloc == d or parsed.netloc.endswith("." + d)
        for d in _ALLOWED_MEDIA_DOMAINS
    ):
        raise ValueError(f"Media URL domain not allowed: {parsed.netloc}")

from infrastructure.config.settings import settings
from .base import (
    BaseSocialAdapter,
    SocialPlatform,
    SocialCredentials,
    PostResult,
    MediaUploadResult,
    SocialAuthError,
    SocialAPIError,
    SocialRateLimitError,
    SocialValidationError,
)

logger = logging.getLogger(__name__)


class FacebookAdapter(BaseSocialAdapter):
    """
    Facebook Graph API adapter for posting to pages.

    Uses OAuth 2.0 for authentication and Facebook Graph API v18.0
    for all operations. Supports text posts and posts with media.
    Also supports Instagram posting via Facebook Business API.
    """

    platform = SocialPlatform.FACEBOOK

    # OAuth 2.0 endpoints
    OAUTH_AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
    OAUTH_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"

    # API endpoints
    API_BASE_URL = "https://graph.facebook.com/v18.0"

    # OAuth scopes
    SCOPES = [
        "pages_manage_posts",      # Post to pages
        "pages_read_engagement",   # Read page data
        "pages_show_list",         # List pages
        "instagram_basic",         # Instagram basic access
        "instagram_content_publish", # Publish to Instagram
        "public_profile",          # Read public profile
    ]

    # Character limit (Facebook allows up to 63,206 characters)
    CHARACTER_LIMIT = 63206

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        timeout: int = 30,
        mock_mode: bool = False,
    ):
        """
        Initialize Facebook adapter.

        Args:
            app_id: Facebook App ID
            app_secret: Facebook App Secret
            redirect_uri: OAuth redirect URI
            timeout: Request timeout in seconds
            mock_mode: Enable mock mode for development
        """
        self.app_id = app_id or settings.facebook_app_id
        self.app_secret = app_secret or settings.facebook_app_secret
        self.redirect_uri = redirect_uri or settings.facebook_redirect_uri
        self.timeout = timeout
        self.mock_mode = mock_mode

        if not self.mock_mode and not all([self.app_id, self.app_secret]):
            logger.warning(
                "Facebook OAuth credentials not configured. "
                "Set facebook_app_id and facebook_app_secret in settings."
            )

    def get_authorization_url(self, state: str) -> str:
        """
        Generate OAuth 2.0 authorization URL.

        Args:
            state: Random state string for CSRF protection

        Returns:
            Authorization URL to redirect user to

        Raises:
            SocialAuthError: If OAuth credentials are not configured
        """
        if not self.mock_mode and not all([self.app_id, self.redirect_uri]):
            raise SocialAuthError(
                "Facebook OAuth credentials not configured. "
                "Set facebook_app_id and facebook_redirect_uri in settings."
            )

        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": ",".join(self.SCOPES),
            "state": state,
        }

        authorization_url = f"{self.OAUTH_AUTH_URL}?{urlencode(params)}"
        logger.info("Generated Facebook OAuth authorization URL")
        return authorization_url

    async def exchange_code(self, code: str) -> SocialCredentials:
        """
        Exchange authorization code for access tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Social media credentials

        Raises:
            SocialAuthError: If token exchange fails
        """
        if self.mock_mode:
            logger.info("Mock mode: Returning fake Facebook credentials")
            return SocialCredentials(
                platform=SocialPlatform.FACEBOOK,
                access_token="mock_facebook_access_token",
                refresh_token=None,  # Facebook uses long-lived tokens
                token_expiry=None,
                account_id="123456789",
                account_name="Mock Facebook User",
                account_username=None,
                profile_image_url="https://example.com/profile.jpg",
            )

        try:
            params = {
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "redirect_uri": self.redirect_uri,
                "code": code,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info("Exchanging Facebook authorization code for tokens")
                response = await client.get(
                    self.OAUTH_TOKEN_URL,
                    params=params,
                )

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error", {}).get("message", "Token exchange failed")
                    logger.error(f"Facebook token exchange failed: {error_msg}")
                    raise SocialAuthError(f"Token exchange failed: {error_msg}")

                token_data = response.json()
                access_token = token_data["access_token"]

                # Exchange for long-lived token (60 days)
                long_lived_token = await self._get_long_lived_token(access_token)

                # Get user profile
                user_profile = await self._get_user_profile(long_lived_token)

                credentials = SocialCredentials(
                    platform=SocialPlatform.FACEBOOK,
                    access_token=long_lived_token,
                    refresh_token=None,  # Facebook doesn't use refresh tokens
                    token_expiry=None,  # Long-lived tokens last 60 days
                    account_id=user_profile["id"],
                    account_name=user_profile.get("name", "Unknown"),
                    account_username=None,
                    profile_image_url=user_profile.get("picture", {}).get("data", {}).get("url"),
                )

                logger.info(f"Facebook authentication successful: {credentials.account_name}")
                return credentials

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during Facebook token exchange: {e}")
            raise SocialAuthError(f"Token exchange failed: {e}")
        except SocialAuthError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Facebook token exchange: {e}")
            raise SocialAuthError(f"Token exchange failed: {e}")

    async def _get_long_lived_token(self, short_lived_token: str) -> str:
        """
        Exchange short-lived token for long-lived token.

        Args:
            short_lived_token: Short-lived access token

        Returns:
            Long-lived access token (60 days)
        """
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_lived_token,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.OAUTH_TOKEN_URL,
                params=params,
            )

            if response.status_code != 200:
                logger.warning("Failed to get long-lived token, using short-lived token")
                return short_lived_token

            token_data = response.json()
            return token_data.get("access_token", short_lived_token)

    async def _get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """
        Get authenticated user's profile information.

        Args:
            access_token: OAuth access token

        Returns:
            User profile data
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.API_BASE_URL}/me",
                params={
                    "fields": "id,name,picture",
                    "access_token": access_token,
                },
            )

            if response.status_code != 200:
                raise SocialAPIError("Failed to fetch user profile")

            return response.json()

    async def get_pages(self, credentials: SocialCredentials) -> List[Dict[str, Any]]:
        """
        Get list of Facebook Pages the user manages.

        Args:
            credentials: Account credentials

        Returns:
            List of page objects with page tokens
        """
        if self.mock_mode:
            return [
                {
                    "id": "123456789",
                    "name": "Mock Page",
                    "access_token": "mock_page_token",
                }
            ]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.API_BASE_URL}/me/accounts",
                    params={
                        "fields": "id,name,access_token",
                        "access_token": credentials.access_token,
                    },
                )

                if response.status_code != 200:
                    raise SocialAPIError("Failed to fetch pages")

                result = response.json()
                return result.get("data", [])

        except Exception as e:
            logger.error(f"Error fetching Facebook pages: {e}")
            raise SocialAPIError(f"Failed to fetch pages: {e}")

    async def refresh_token(self, credentials: SocialCredentials) -> SocialCredentials:
        """
        Refresh expired access token.

        Note: Facebook uses long-lived tokens that don't auto-refresh.
        Users must re-authenticate when token expires.

        Args:
            credentials: Current credentials

        Returns:
            Same credentials (cannot refresh)

        Raises:
            SocialAuthError: Always raises since refresh not supported
        """
        raise SocialAuthError(
            "Facebook uses long-lived tokens (60 days). "
            "User must re-authenticate when token expires."
        )

    async def verify_credentials(self, credentials: SocialCredentials) -> bool:
        """
        Verify credentials are still valid.

        Args:
            credentials: Credentials to verify

        Returns:
            True if valid
        """
        if self.mock_mode:
            return True

        try:
            await self._get_user_profile(credentials.access_token)
            return True
        except Exception:
            return False

    async def post_text(
        self,
        credentials: SocialCredentials,
        text: str,
        page_id: Optional[str] = None,
        page_token: Optional[str] = None
    ) -> PostResult:
        """
        Post to Facebook page.

        Args:
            credentials: Account credentials
            text: Post text
            page_id: Facebook Page ID (required)
            page_token: Page access token (required)

        Returns:
            Post result

        Raises:
            SocialValidationError: If page_id or page_token missing
            SocialAPIError: If post creation fails
        """
        # Validate text length
        self.validate_text_length(text)

        if not page_id or not page_token:
            raise SocialValidationError("page_id and page_token are required for Facebook posting")

        if self.mock_mode:
            logger.info(f"Mock mode: Would post to Facebook page: {text[:50]}...")
            return PostResult(
                success=True,
                post_id="123456789_987654321",
                post_url=f"https://www.facebook.com/{page_id}/posts/987654321",
            )

        try:
            post_data = {
                "message": text,
                "access_token": page_token,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Posting to Facebook page {page_id}: {text[:50]}...")
                response = await client.post(
                    f"{self.API_BASE_URL}/{page_id}/feed",
                    data=post_data,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    logger.error("Facebook rate limit exceeded")
                    raise SocialRateLimitError("Rate limit exceeded")

                if response.status_code not in [200, 201]:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error", {}).get("message", "Post creation failed")
                    logger.error(f"Facebook API error: {error_msg}")
                    raise SocialAPIError(f"Post creation failed: {error_msg}")

                result = response.json()
                post_id = result.get("id", "")
                post_url = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}"

                logger.info(f"Facebook post created successfully: {post_url}")
                return PostResult(
                    success=True,
                    post_id=post_id,
                    post_url=post_url,
                )

        except (SocialValidationError, SocialRateLimitError, SocialAPIError):
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during Facebook posting: {e}")
            return PostResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error during Facebook posting: {e}")
            return PostResult(success=False, error_message=str(e))

    async def post_with_media(
        self,
        credentials: SocialCredentials,
        text: str,
        media_urls: List[str],
        page_id: Optional[str] = None,
        page_token: Optional[str] = None
    ) -> PostResult:
        """
        Post to Facebook page with media.

        Args:
            credentials: Account credentials
            text: Post text
            media_urls: List of media URLs
            page_id: Facebook Page ID (required)
            page_token: Page access token (required)

        Returns:
            Post result

        Raises:
            SocialValidationError: If validation fails
            SocialAPIError: If posting fails
        """
        # Validate text length
        self.validate_text_length(text)

        if not page_id or not page_token:
            raise SocialValidationError("page_id and page_token are required for Facebook posting")

        if self.mock_mode:
            logger.info(f"Mock mode: Would post to Facebook page with {len(media_urls)} media")
            return PostResult(
                success=True,
                post_id="123456789_987654321",
                post_url=f"https://www.facebook.com/{page_id}/posts/987654321",
            )

        try:
            # For single image, use photos endpoint
            if len(media_urls) == 1:
                # SM-23: Validate media URL before passing to Facebook API (SSRF protection)
                try:
                    _validate_media_url(media_urls[0])
                except ValueError as e:
                    logger.warning("Rejecting media URL due to SSRF validation failure: %s", e)
                    raise SocialValidationError(f"Media URL not allowed: {e}") from e
                post_data = {
                    "url": media_urls[0],
                    "message": text,
                    "access_token": page_token,
                }

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.info(f"Posting photo to Facebook page {page_id}")
                    response = await client.post(
                        f"{self.API_BASE_URL}/{page_id}/photos",
                        data=post_data,
                    )

                    if response.status_code == 429:
                        raise SocialRateLimitError("Rate limit exceeded")

                    if response.status_code not in [200, 201]:
                        error_data = response.json() if response.text else {}
                        error_msg = error_data.get("error", {}).get("message", "Post creation failed")
                        raise SocialAPIError(f"Post creation failed: {error_msg}")

                    result = response.json()
                    post_id = result.get("post_id", result.get("id", ""))
                    post_url = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}"

                    logger.info(f"Facebook photo post created successfully: {post_url}")
                    return PostResult(
                        success=True,
                        post_id=post_id,
                        post_url=post_url,
                    )
            else:
                # For multiple images, need to upload each as unpublished, then create album
                # This is a simplified version - full implementation would handle album creation
                logger.warning("Multiple image posting requires album creation - posting first image only")
                return await self.post_with_media(credentials, text, [media_urls[0]], page_id, page_token)

        except (SocialValidationError, SocialRateLimitError, SocialAPIError):
            raise
        except Exception as e:
            logger.error(f"Error posting to Facebook with media: {e}")
            return PostResult(success=False, error_message=str(e))

    async def upload_media(
        self,
        credentials: SocialCredentials,
        media_bytes: bytes,
        media_type: str,
        filename: Optional[str] = None,
        page_id: Optional[str] = None,
        page_token: Optional[str] = None
    ) -> MediaUploadResult:
        """
        Upload media to Facebook page.

        Args:
            credentials: Account credentials
            media_bytes: Raw media data
            media_type: MIME type
            filename: Optional filename
            page_id: Facebook Page ID (required)
            page_token: Page access token (required)

        Returns:
            Upload result with media ID

        Raises:
            SocialValidationError: If page info missing
            SocialAPIError: If upload fails
        """
        if not page_id or not page_token:
            raise SocialValidationError("page_id and page_token are required for media upload")

        # SM-27: Validate image size before attempting upload
        if len(media_bytes) > 10 * 1024 * 1024:
            raise ValueError("Image too large for Facebook upload (max 10MB)")

        if self.mock_mode:
            logger.info("Mock mode: Returning fake Facebook media ID")
            return MediaUploadResult(
                media_id="123456789",
                media_type="image",
            )

        try:
            files = {
                "source": (filename or "image.jpg", media_bytes, media_type)
            }

            data = {
                "published": "false",  # Upload as unpublished
                "access_token": page_token,
            }

            async with httpx.AsyncClient(timeout=60) as client:
                logger.info("Uploading media to Facebook page")
                response = await client.post(
                    f"{self.API_BASE_URL}/{page_id}/photos",
                    files=files,
                    data=data,
                )

                if response.status_code not in [200, 201]:
                    error_msg = response.json().get("error", {}).get("message", "Upload failed")
                    raise SocialAPIError(f"Media upload failed: {error_msg}")

                result = response.json()
                media_id = result.get("id", "")

                logger.info(f"Media uploaded successfully: {media_id}")
                return MediaUploadResult(
                    media_id=media_id,
                    media_type="image",
                )

        except SocialAPIError:
            raise
        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            raise SocialAPIError(f"Media upload failed: {e}")

    async def delete_post(
        self,
        credentials: SocialCredentials,
        post_id: str,
        page_token: Optional[str] = None
    ) -> bool:
        """
        Delete a Facebook post.

        Args:
            credentials: Account credentials
            post_id: Post ID
            page_token: Page access token (required)

        Returns:
            True if successful

        Raises:
            SocialValidationError: If page_token missing
            SocialAPIError: If deletion fails
        """
        if not page_token:
            raise SocialValidationError("page_token is required for post deletion")

        if self.mock_mode:
            logger.info(f"Mock mode: Would delete Facebook post {post_id}")
            return True

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Deleting Facebook post {post_id}")
                response = await client.delete(
                    f"{self.API_BASE_URL}/{post_id}",
                    params={"access_token": page_token},
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        logger.info(f"Facebook post {post_id} deleted successfully")
                        return True

                error_msg = response.json().get("error", {}).get("message", "Deletion failed")
                raise SocialAPIError(f"Post deletion failed: {error_msg}")

        except SocialAPIError:
            raise
        except Exception as e:
            logger.error(f"Error deleting Facebook post: {e}")
            raise SocialAPIError(f"Post deletion failed: {e}")

    def get_character_limit(self) -> int:
        """Get Facebook character limit."""
        return self.CHARACTER_LIMIT
