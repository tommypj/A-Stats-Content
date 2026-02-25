"""
Twitter/X API v2 adapter for social media posting.

Provides integration with Twitter API v2 using OAuth 2.0 with PKCE
for posting tweets, uploading media, and managing content.
"""

import logging
import hashlib
import base64
import secrets
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode

import httpx

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


class TwitterAdapter(BaseSocialAdapter):
    """
    Twitter/X API v2 adapter for posting tweets.

    Uses OAuth 2.0 with PKCE for authentication and Twitter API v2
    for all operations. Supports text tweets and tweets with media.
    """

    platform = SocialPlatform.TWITTER

    # OAuth 2.0 endpoints
    OAUTH_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
    OAUTH_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
    OAUTH_REVOKE_URL = "https://api.twitter.com/2/oauth2/revoke"

    # API endpoints
    API_BASE_URL = "https://api.twitter.com/2"
    UPLOAD_BASE_URL = "https://upload.twitter.com/1.1"

    # OAuth scopes
    SCOPES = [
        "tweet.read",
        "tweet.write",
        "users.read",
        "offline.access",  # For refresh token
    ]

    # Character limit
    CHARACTER_LIMIT = 280

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        timeout: int = 30,
        mock_mode: bool = False,
    ):
        """
        Initialize Twitter adapter.

        Args:
            client_id: Twitter OAuth client ID
            client_secret: Twitter OAuth client secret
            redirect_uri: OAuth redirect URI
            timeout: Request timeout in seconds
            mock_mode: Enable mock mode for development
        """
        self.client_id = client_id or settings.twitter_client_id
        self.client_secret = client_secret or settings.twitter_client_secret
        self.redirect_uri = redirect_uri or settings.twitter_redirect_uri
        self.timeout = timeout
        self.mock_mode = mock_mode

        if not self.mock_mode and not all([self.client_id, self.client_secret]):
            logger.warning(
                "Twitter OAuth credentials not configured. "
                "Set twitter_client_id and twitter_client_secret in settings."
            )

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """
        Generate PKCE code verifier and challenge.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate random code verifier
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        code_verifier = code_verifier.rstrip('=')

        # Generate code challenge (SHA256 hash of verifier)
        challenge_bytes = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8')
        code_challenge = code_challenge.rstrip('=')

        return code_verifier, code_challenge

    def get_authorization_url(self, state: str, code_verifier: Optional[str] = None) -> tuple[str, str]:
        """
        Generate OAuth 2.0 authorization URL with PKCE.

        Args:
            state: Random state string for CSRF protection
            code_verifier: Optional code verifier (will be generated if not provided)

        Returns:
            Tuple of (authorization_url, code_verifier)

        Raises:
            SocialAuthError: If OAuth credentials are not configured
        """
        if not self.mock_mode and not all([self.client_id, self.redirect_uri]):
            raise SocialAuthError(
                "Twitter OAuth credentials not configured. "
                "Set twitter_client_id and twitter_redirect_uri in settings."
            )

        # Generate PKCE pair if verifier not provided
        if not code_verifier:
            code_verifier, code_challenge = self._generate_pkce_pair()
        else:
            # Regenerate challenge from provided verifier
            challenge_bytes = hashlib.sha256(code_verifier.encode()).digest()
            code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8')
            code_challenge = code_challenge.rstrip('=')

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        authorization_url = f"{self.OAUTH_AUTH_URL}?{urlencode(params)}"
        logger.info("Generated Twitter OAuth authorization URL")
        return authorization_url, code_verifier

    async def exchange_code(
        self,
        code: str,
        code_verifier: Optional[str] = None
    ) -> SocialCredentials:
        """
        Exchange authorization code for access tokens.

        Args:
            code: Authorization code from OAuth callback
            code_verifier: PKCE code verifier used in authorization

        Returns:
            Social media credentials

        Raises:
            SocialAuthError: If token exchange fails
        """
        if self.mock_mode:
            logger.info("Mock mode: Returning fake Twitter credentials")
            return SocialCredentials(
                platform=SocialPlatform.TWITTER,
                access_token="mock_twitter_access_token",
                refresh_token="mock_twitter_refresh_token",
                token_expiry=None,
                account_id="123456789",
                account_name="Mock User",
                account_username="mockuser",
                profile_image_url="https://example.com/profile.jpg",
            )

        try:
            data = {
                "client_id": self.client_id,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": code_verifier,
            }

            # Add client secret for confidential clients
            if self.client_secret:
                data["client_secret"] = self.client_secret

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info("Exchanging Twitter authorization code for tokens")
                response = await client.post(
                    self.OAUTH_TOKEN_URL,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error_description", "Token exchange failed")
                    logger.error(f"Twitter token exchange failed: {error_msg}")
                    raise SocialAuthError(f"Token exchange failed: {error_msg}")

                token_data = response.json()

            # Get user profile
            user_profile = await self._get_user_profile(token_data["access_token"])

            credentials = SocialCredentials(
                platform=SocialPlatform.TWITTER,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_expiry=None,  # Twitter doesn't provide expiry in response
                account_id=user_profile["id"],
                account_name=user_profile["name"],
                account_username=user_profile["username"],
                profile_image_url=user_profile.get("profile_image_url"),
            )

            logger.info(f"Twitter authentication successful: @{credentials.account_username}")
            return credentials

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during Twitter token exchange: {e}")
            raise SocialAuthError(f"Token exchange failed: {e}")
        except SocialAuthError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Twitter token exchange: {e}")
            raise SocialAuthError(f"Token exchange failed: {e}")

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
                f"{self.API_BASE_URL}/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"user.fields": "profile_image_url,username"},
            )

            if response.status_code != 200:
                raise SocialAPIError("Failed to fetch user profile")

            data = response.json().get("data")
            if not data:
                raise SocialAPIError("Twitter API returned no user data")
            return data

    async def refresh_token(self, credentials: SocialCredentials) -> SocialCredentials:
        """
        Refresh expired access token.

        Args:
            credentials: Current credentials with refresh token

        Returns:
            Updated credentials

        Raises:
            SocialAuthError: If token refresh fails
        """
        if self.mock_mode:
            logger.info("Mock mode: Returning refreshed Twitter credentials")
            return credentials

        if not credentials.refresh_token:
            raise SocialAuthError("No refresh token available")

        try:
            data = {
                "client_id": self.client_id,
                "grant_type": "refresh_token",
                "refresh_token": credentials.refresh_token,
            }

            # Add client secret for confidential clients
            if self.client_secret:
                data["client_secret"] = self.client_secret

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info("Refreshing Twitter access token")
                response = await client.post(
                    self.OAUTH_TOKEN_URL,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error_description", "Token refresh failed")
                    logger.error(f"Twitter token refresh failed: {error_msg}")
                    raise SocialAuthError(f"Token refresh failed: {error_msg}")

                token_data = response.json()

            # Update credentials with new tokens
            credentials.access_token = token_data["access_token"]
            if "refresh_token" in token_data:
                credentials.refresh_token = token_data["refresh_token"]

            logger.info("Twitter token refreshed successfully")
            return credentials

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during Twitter token refresh: {e}")
            raise SocialAuthError(f"Token refresh failed: {e}")
        except SocialAuthError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Twitter token refresh: {e}")
            raise SocialAuthError(f"Token refresh failed: {e}")

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

    async def post_text(self, credentials: SocialCredentials, text: str) -> PostResult:
        """
        Post a tweet.

        Args:
            credentials: Account credentials
            text: Tweet text

        Returns:
            Post result with tweet ID and URL

        Raises:
            SocialValidationError: If text exceeds 280 characters
            SocialAPIError: If tweet creation fails
        """
        # Validate text length
        self.validate_text_length(text)

        if self.mock_mode:
            logger.info(f"Mock mode: Would post tweet: {text[:50]}...")
            return PostResult(
                success=True,
                post_id="1234567890",
                post_url="https://twitter.com/mockuser/status/1234567890",
            )

        try:
            tweet_data = {"text": text}

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Posting tweet: {text[:50]}...")
                response = await client.post(
                    f"{self.API_BASE_URL}/tweets",
                    headers={
                        "Authorization": f"Bearer {credentials.access_token}",
                        "Content-Type": "application/json",
                    },
                    json=tweet_data,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get("x-rate-limit-reset", "unknown")
                    logger.error(f"Twitter rate limit exceeded. Reset at: {retry_after}")
                    raise SocialRateLimitError(f"Rate limit exceeded. Reset at: {retry_after}")

                if response.status_code != 201:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("detail", "Tweet creation failed")
                    logger.error(f"Twitter API error: {error_msg}")
                    raise SocialAPIError(f"Tweet creation failed: {error_msg}")

                result = response.json()
                tweet_id = result["data"]["id"]
                tweet_url = f"https://twitter.com/{credentials.account_username}/status/{tweet_id}"

                logger.info(f"Tweet posted successfully: {tweet_url}")
                return PostResult(
                    success=True,
                    post_id=tweet_id,
                    post_url=tweet_url,
                )

        except (SocialValidationError, SocialRateLimitError, SocialAPIError):
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during tweet posting: {e}")
            return PostResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error during tweet posting: {e}")
            return PostResult(success=False, error_message=str(e))

    async def post_with_media(
        self,
        credentials: SocialCredentials,
        text: str,
        media_urls: List[str]
    ) -> PostResult:
        """
        Post a tweet with media attachments.

        Args:
            credentials: Account credentials
            text: Tweet text
            media_urls: List of media URLs (up to 4 images)

        Returns:
            Post result

        Raises:
            SocialValidationError: If validation fails
            SocialAPIError: If posting fails
        """
        # Validate text length
        self.validate_text_length(text)

        # Validate media count
        if len(media_urls) > 4:
            raise SocialValidationError("Twitter allows maximum 4 images per tweet")

        if self.mock_mode:
            logger.info(f"Mock mode: Would post tweet with {len(media_urls)} media")
            return PostResult(
                success=True,
                post_id="1234567890",
                post_url="https://twitter.com/mockuser/status/1234567890",
            )

        try:
            # Upload all media first
            media_ids = []
            for media_url in media_urls:
                # Download media
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    media_response = await client.get(media_url)
                    media_response.raise_for_status()
                    media_bytes = media_response.content

                # Determine media type
                content_type = media_response.headers.get("content-type", "image/jpeg")

                # Upload to Twitter
                upload_result = await self.upload_media(
                    credentials,
                    media_bytes,
                    content_type,
                )
                media_ids.append(upload_result.media_id)

            # Create tweet with media
            tweet_data = {
                "text": text,
                "media": {"media_ids": media_ids},
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Posting tweet with {len(media_ids)} media attachments")
                response = await client.post(
                    f"{self.API_BASE_URL}/tweets",
                    headers={
                        "Authorization": f"Bearer {credentials.access_token}",
                        "Content-Type": "application/json",
                    },
                    json=tweet_data,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get("x-rate-limit-reset", "unknown")
                    raise SocialRateLimitError(f"Rate limit exceeded. Reset at: {retry_after}")

                if response.status_code != 201:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("detail", "Tweet creation failed")
                    raise SocialAPIError(f"Tweet creation failed: {error_msg}")

                result = response.json()
                tweet_id = result["data"]["id"]
                tweet_url = f"https://twitter.com/{credentials.account_username}/status/{tweet_id}"

                logger.info(f"Tweet with media posted successfully: {tweet_url}")
                return PostResult(
                    success=True,
                    post_id=tweet_id,
                    post_url=tweet_url,
                )

        except (SocialValidationError, SocialRateLimitError, SocialAPIError):
            raise
        except Exception as e:
            logger.error(f"Error posting tweet with media: {e}")
            return PostResult(success=False, error_message=str(e))

    async def upload_media(
        self,
        credentials: SocialCredentials,
        media_bytes: bytes,
        media_type: str,
        filename: Optional[str] = None
    ) -> MediaUploadResult:
        """
        Upload media to Twitter.

        Args:
            credentials: Account credentials
            media_bytes: Raw media data
            media_type: MIME type
            filename: Optional filename

        Returns:
            Upload result with media ID

        Raises:
            SocialAPIError: If upload fails
        """
        if self.mock_mode:
            logger.info("Mock mode: Returning fake media ID")
            return MediaUploadResult(
                media_id="1234567890",
                media_type="image",
            )

        try:
            # Use Twitter Upload API v1.1 (media upload endpoint)
            async with httpx.AsyncClient(timeout=60) as client:
                logger.info("Uploading media to Twitter")

                # Simple upload for images < 5MB
                files = {"media": media_bytes}
                response = await client.post(
                    f"{self.UPLOAD_BASE_URL}/media/upload.json",
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                    files=files,
                )

                if response.status_code != 200:
                    errors = response.json().get("errors") or []
                    error_msg = errors[0].get("message", "Upload failed") if errors else "Upload failed"
                    raise SocialAPIError(f"Media upload failed: {error_msg}")

                result = response.json()
                media_id = str(result["media_id"])

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

    async def delete_post(self, credentials: SocialCredentials, post_id: str) -> bool:
        """
        Delete a tweet.

        Args:
            credentials: Account credentials
            post_id: Tweet ID

        Returns:
            True if successful

        Raises:
            SocialAPIError: If deletion fails
        """
        if self.mock_mode:
            logger.info(f"Mock mode: Would delete tweet {post_id}")
            return True

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Deleting tweet {post_id}")
                response = await client.delete(
                    f"{self.API_BASE_URL}/tweets/{post_id}",
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                )

                if response.status_code == 200:
                    logger.info(f"Tweet {post_id} deleted successfully")
                    return True
                else:
                    error_msg = response.json().get("detail", "Deletion failed")
                    raise SocialAPIError(f"Tweet deletion failed: {error_msg}")

        except SocialAPIError:
            raise
        except Exception as e:
            logger.error(f"Error deleting tweet: {e}")
            raise SocialAPIError(f"Tweet deletion failed: {e}")

    def get_character_limit(self) -> int:
        """Get Twitter character limit."""
        return self.CHARACTER_LIMIT
