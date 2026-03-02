"""
Instagram Graph API adapter for social media posting.

Provides integration with Instagram via the Facebook Graph API using OAuth 2.0.
Instagram Business accounts connect through Facebook Login and use the
Instagram Content Publishing API for creating posts.

Key differences from FacebookAdapter:
- Instagram does not support text-only posts; all posts require media.
- Posts are created in two steps: create a media container, then publish it.
- Instagram does not expose a post-deletion API; deletion must be done manually.
- Character limit is 2,200 (vs Facebook's 63,206).
"""

import logging
from typing import Any
from urllib.parse import urlparse as _urlparse

import httpx

from infrastructure.config.settings import settings

from .base import (
    BaseSocialAdapter,
    MediaUploadResult,
    PostResult,
    SocialAPIError,
    SocialAuthError,
    SocialCredentials,
    SocialPlatform,
    SocialRateLimitError,
    SocialValidationError,
)

# SM-24: SSRF protection — only allow media URLs from trusted domains
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
        parsed.netloc == d or parsed.netloc.endswith("." + d) for d in _ALLOWED_MEDIA_DOMAINS
    ):
        raise ValueError(f"Media URL domain not allowed: {parsed.netloc}")


logger = logging.getLogger(__name__)


class InstagramAdapter(BaseSocialAdapter):
    """
    Instagram Content Publishing API adapter.

    Authenticates via Facebook Login (the same OAuth dialog used by
    FacebookAdapter) and posts to Instagram Business accounts using the
    Instagram Graph API v21.0.

    Supported operations:
    - post_with_media: Create image posts with a caption via the container flow.
    - verify_credentials / exchange_code / refresh_token: delegated to the
      Facebook Graph API because Instagram business accounts are linked to
      Facebook Pages.

    Unsupported operations (raise appropriate errors):
    - post_text: Instagram requires at least one image or video.
    - delete_post: Instagram does not expose a delete endpoint.
    - upload_media: Instagram publishes media by URL, not binary upload.
    """

    platform = SocialPlatform.INSTAGRAM

    # OAuth endpoints (same as Facebook)
    OAUTH_AUTH_URL = "https://www.facebook.com/v21.0/dialog/oauth"
    OAUTH_TOKEN_URL = "https://graph.facebook.com/v21.0/oauth/access_token"

    # API base (Instagram Graph API is served from the same host)
    API_BASE_URL = "https://graph.facebook.com/v21.0"

    # Instagram OAuth scopes required for business account publishing
    SCOPES = [
        "instagram_basic",  # Read profile info
        "instagram_content_publish",  # Create posts
        "pages_show_list",  # Enumerate linked Facebook Pages
        "pages_read_engagement",  # Read page / IG account data
    ]

    # Instagram caption character limit
    CHARACTER_LIMIT = 2200

    def __init__(
        self,
        app_id: str | None = None,
        app_secret: str | None = None,
        redirect_uri: str | None = None,
        timeout: int = 30,
        mock_mode: bool = False,
    ):
        """
        Initialize Instagram adapter.

        Args:
            app_id: Facebook App ID (also used for Instagram OAuth)
            app_secret: Facebook App Secret
            redirect_uri: OAuth redirect URI
            timeout: Request timeout in seconds
            mock_mode: Enable mock mode for development/testing
        """
        self.app_id = app_id or settings.facebook_app_id
        self.app_secret = app_secret or settings.facebook_app_secret
        self.redirect_uri = redirect_uri or settings.facebook_redirect_uri
        self.timeout = timeout
        self.mock_mode = mock_mode

        if not self.mock_mode and not all([self.app_id, self.app_secret]):
            logger.warning(
                "Instagram OAuth credentials not configured. "
                "Set facebook_app_id and facebook_app_secret in settings."
            )

    # ------------------------------------------------------------------
    # OAuth helpers
    # ------------------------------------------------------------------

    def get_authorization_url(self, state: str) -> str:
        """
        Generate Facebook Login OAuth URL with Instagram-specific scopes.

        Args:
            state: Random state string for CSRF protection

        Returns:
            Authorization URL to redirect user to

        Raises:
            SocialAuthError: If OAuth credentials are not configured
        """
        from urllib.parse import urlencode

        if not self.mock_mode and not all([self.app_id, self.redirect_uri]):
            raise SocialAuthError(
                "Instagram OAuth credentials not configured. "
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
        logger.info("Generated Instagram OAuth authorization URL")
        return authorization_url

    async def exchange_code(self, code: str) -> SocialCredentials:
        """
        Exchange authorization code for access tokens via Facebook Graph API.

        The returned credentials reference the Instagram Business Account ID
        (not the Facebook user/page ID).

        Args:
            code: Authorization code from OAuth callback

        Returns:
            SocialCredentials for the connected Instagram account

        Raises:
            SocialAuthError: If token exchange or IG account lookup fails
        """
        if self.mock_mode:
            logger.info("Mock mode: Returning fake Instagram credentials")
            return SocialCredentials(
                platform=SocialPlatform.INSTAGRAM,
                access_token="mock_instagram_access_token",
                refresh_token=None,
                token_expiry=None,
                account_id="111222333",
                account_name="Mock Instagram Business",
                account_username="mock_ig_user",
                profile_image_url="https://example.com/ig_profile.jpg",
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Step 1: Exchange code for short-lived user access token
                token_resp = await client.get(
                    self.OAUTH_TOKEN_URL,
                    params={
                        "client_id": self.app_id,
                        "client_secret": self.app_secret,
                        "redirect_uri": self.redirect_uri,
                        "code": code,
                    },
                )
                if token_resp.status_code != 200:
                    error_msg = (
                        token_resp.json().get("error", {}).get("message", "Token exchange failed")
                    )
                    logger.error("Instagram token exchange failed: %s", error_msg)
                    raise SocialAuthError(f"Token exchange failed: {error_msg}")

                token_data = token_resp.json()
                short_token = token_data.get("access_token")
                if not short_token:
                    raise SocialAuthError("Token response missing 'access_token'")

                # Step 2: Exchange for long-lived token (60 days)
                long_token_resp = await client.get(
                    self.OAUTH_TOKEN_URL,
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": self.app_id,
                        "client_secret": self.app_secret,
                        "fb_exchange_token": short_token,
                    },
                )
                if long_token_resp.status_code == 200:
                    access_token = long_token_resp.json().get("access_token", short_token)
                else:
                    logger.warning("Failed to get long-lived token, using short-lived token")
                    access_token = short_token

                # Step 3: Resolve Instagram Business Account via linked Facebook Page
                ig_account = await self._get_instagram_account(client, access_token)

                credentials = SocialCredentials(
                    platform=SocialPlatform.INSTAGRAM,
                    access_token=access_token,
                    refresh_token=None,
                    token_expiry=None,
                    account_id=ig_account["id"],
                    account_name=ig_account.get("name", "Instagram Business"),
                    account_username=ig_account.get("username"),
                    profile_image_url=ig_account.get("profile_picture_url"),
                )
                logger.info("Instagram authentication successful: %s", credentials.account_name)
                return credentials

        except (SocialAuthError, SocialAPIError):
            raise
        except httpx.HTTPError as e:
            logger.error("HTTP error during Instagram token exchange: %s", e)
            raise SocialAuthError(f"Token exchange failed: {e}")
        except Exception as e:
            logger.error("Unexpected error during Instagram token exchange: %s", e)
            raise SocialAuthError(f"Token exchange failed: {e}")

    async def _get_instagram_account(
        self, client: httpx.AsyncClient, access_token: str
    ) -> dict[str, Any]:
        """
        Resolve the Instagram Business Account linked to the authenticated user.

        Walks through the user's Facebook Pages and returns the first Instagram
        Business Account found.

        Args:
            client: Active httpx client
            access_token: Long-lived user access token

        Returns:
            Instagram Business Account data dict

        Raises:
            SocialAuthError: If no Instagram Business Account is found
        """
        # List the user's Facebook Pages (needed to reach linked IG accounts)
        pages_resp = await client.get(
            f"{self.API_BASE_URL}/me/accounts",
            params={"access_token": access_token},
        )
        if pages_resp.status_code != 200:
            raise SocialAuthError("Failed to list Facebook Pages for Instagram account lookup")

        pages = pages_resp.json().get("data", [])
        for page in pages:
            page_id = page.get("id")
            page_token = page.get("access_token")
            if not page_id or not page_token:
                continue

            # Check if this page has a linked Instagram Business Account
            ig_resp = await client.get(
                f"{self.API_BASE_URL}/{page_id}",
                params={
                    "fields": "instagram_business_account",
                    "access_token": page_token,
                },
            )
            if ig_resp.status_code != 200:
                continue

            ig_data = ig_resp.json().get("instagram_business_account")
            if not ig_data:
                continue

            ig_id = ig_data.get("id")
            if not ig_id:
                continue

            # Fetch full profile for the IG business account
            profile_resp = await client.get(
                f"{self.API_BASE_URL}/{ig_id}",
                params={
                    "fields": "id,name,username,profile_picture_url",
                    "access_token": page_token,
                },
            )
            if profile_resp.status_code == 200:
                return profile_resp.json()

            # Fall back to minimal data if profile fetch fails
            return {"id": ig_id, "name": page.get("name", "Instagram Business")}

        raise SocialAuthError(
            "No Instagram Business Account found. "
            "Ensure the Facebook Page has a linked Instagram Business Account."
        )

    async def refresh_token(self, credentials: SocialCredentials) -> SocialCredentials:
        """
        Instagram (via Facebook) does not support automatic token refresh.

        Raises:
            SocialAuthError: Always — user must re-authenticate.
        """
        raise SocialAuthError(
            "Instagram uses long-lived tokens (60 days). "
            "User must re-authenticate when token expires."
        )

    async def verify_credentials(self, credentials: SocialCredentials) -> bool:
        """
        Verify the stored access token is still valid.

        Args:
            credentials: Credentials to verify

        Returns:
            True if valid, False otherwise
        """
        if self.mock_mode:
            return True

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.API_BASE_URL}/me",
                    params={"access_token": credentials.access_token},
                )
                return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------

    async def post_text(
        self,
        credentials: SocialCredentials,
        text: str,
        **kwargs,
    ) -> PostResult:
        """
        Instagram does not support text-only posts.

        Raises:
            SocialValidationError: Always — Instagram requires media.
        """
        raise SocialValidationError(
            "Instagram does not support text-only posts. "
            "Use post_with_media() and supply at least one image URL."
        )

    async def post_with_media(
        self,
        credentials: SocialCredentials,
        text: str,
        media_urls: list[str],
        ig_user_id: str | None = None,
        **kwargs,
    ) -> PostResult:
        """
        Publish an image post to Instagram using the Container API flow.

        Instagram publishing is a two-step process:
          1. Create a media container (POST /{ig-user-id}/media)
          2. Publish the container (POST /{ig-user-id}/media_publish)

        Args:
            credentials: Account credentials (access_token, account_id)
            text: Caption text (max 2,200 characters)
            media_urls: List of publicly accessible image URLs.
                        Only the first URL is used; carousel posts are not
                        yet implemented.
            ig_user_id: Instagram Business Account ID. Falls back to
                        credentials.account_id if not supplied.

        Returns:
            PostResult with the published media ID and permalink

        Raises:
            SocialValidationError: If no media URLs are provided or caption is
                                   too long
            SocialAPIError: If container creation or publishing fails
            SocialRateLimitError: If the API rate limit is exceeded
        """
        self.validate_text_length(text)

        if not media_urls:
            raise SocialValidationError(
                "Instagram requires at least one image URL. "
                "Use post_with_media() and supply at least one media_url."
            )

        user_id = ig_user_id or credentials.account_id
        access_token = credentials.access_token
        image_url = media_urls[0]

        # SM-24: Validate media URL before passing to Instagram API (SSRF protection)
        try:
            _validate_media_url(image_url)
        except ValueError as e:
            logger.warning("Rejecting media URL due to SSRF validation failure: %s", e)
            raise SocialValidationError(f"Media URL not allowed: {e}") from e

        if self.mock_mode:
            logger.info("Mock mode: Would post to Instagram account %s: %s...", user_id, text[:50])
            return PostResult(
                success=True,
                post_id="17841234567890123",
                post_url="https://www.instagram.com/p/mock_post_id/",
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Step 1: Create a media container
                logger.info("Creating Instagram media container for account %s", user_id)
                container_resp = await client.post(
                    f"{self.API_BASE_URL}/{user_id}/media",
                    data={
                        "image_url": image_url,
                        "caption": text,
                        "access_token": access_token,
                    },
                )

                if container_resp.status_code == 429:
                    logger.error("Instagram rate limit exceeded during container creation")
                    raise SocialRateLimitError("Instagram rate limit exceeded")

                if container_resp.status_code not in (200, 201):
                    error_data = container_resp.json() if container_resp.text else {}
                    error_msg = error_data.get("error", {}).get(
                        "message", "Container creation failed"
                    )
                    logger.error("Instagram container creation error: %s", error_msg)
                    raise SocialAPIError(f"Instagram container creation failed: {error_msg}")

                creation_id = container_resp.json().get("id")
                if not creation_id:
                    raise SocialAPIError("Instagram container creation response missing 'id'")

                # Step 2: Publish the container
                logger.info("Publishing Instagram media container %s", creation_id)
                publish_resp = await client.post(
                    f"{self.API_BASE_URL}/{user_id}/media_publish",
                    data={
                        "creation_id": creation_id,
                        "access_token": access_token,
                    },
                )

                if publish_resp.status_code == 429:
                    logger.error("Instagram rate limit exceeded during publish")
                    raise SocialRateLimitError("Instagram rate limit exceeded")

                if publish_resp.status_code not in (200, 201):
                    error_data = publish_resp.json() if publish_resp.text else {}
                    error_msg = error_data.get("error", {}).get("message", "Publish failed")
                    logger.error("Instagram publish error: %s", error_msg)
                    raise SocialAPIError(f"Instagram publish failed: {error_msg}")

                media_id = publish_resp.json().get("id", "")
                post_url = f"https://www.instagram.com/p/{media_id}/"

                logger.info("Instagram post published successfully: %s", post_url)
                return PostResult(
                    success=True,
                    post_id=media_id,
                    post_url=post_url,
                )

        except (SocialValidationError, SocialRateLimitError, SocialAPIError):
            raise
        except httpx.HTTPError as e:
            logger.error("HTTP error during Instagram posting: %s", e)
            return PostResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error("Unexpected error during Instagram posting: %s", e)
            return PostResult(success=False, error_message=str(e))

    # ------------------------------------------------------------------
    # Media upload
    # ------------------------------------------------------------------

    async def upload_media(
        self,
        credentials: SocialCredentials,
        media_bytes: bytes,
        media_type: str,
        filename: str | None = None,
        **kwargs,
    ) -> MediaUploadResult:
        """
        Instagram publishes media by public URL, not by binary upload.

        Binary upload is not supported by the Instagram Content Publishing API.
        Host the media at a publicly accessible URL and pass that URL to
        post_with_media() instead.

        Raises:
            SocialValidationError: Always — binary upload is not supported.
        """
        raise SocialValidationError(
            "Instagram does not support binary media uploads. "
            "Host the image at a publicly accessible URL and pass it to "
            "post_with_media() via the media_urls parameter."
        )

    # ------------------------------------------------------------------
    # Post deletion
    # ------------------------------------------------------------------

    async def delete_post(
        self,
        credentials: SocialCredentials,
        post_id: str,
        **kwargs,
    ) -> bool:
        """
        Instagram does not provide a post-deletion API endpoint.

        Posts must be deleted manually through the Instagram app or Creator
        Studio.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "Instagram does not support post deletion via the API. "
            "Delete the post manually through the Instagram app or "
            "Meta Business Suite."
        )

    # ------------------------------------------------------------------
    # Limits
    # ------------------------------------------------------------------

    def get_character_limit(self) -> int:
        """Return the Instagram caption character limit (2,200)."""
        return self.CHARACTER_LIMIT
