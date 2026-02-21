"""
LinkedIn API adapter for social media posting.

Provides integration with LinkedIn Marketing API using OAuth 2.0
for posting updates, uploading media, and managing content.
"""

import logging
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


class LinkedInAdapter(BaseSocialAdapter):
    """
    LinkedIn API adapter for posting updates.

    Uses OAuth 2.0 for authentication and LinkedIn Marketing API
    for all operations. Supports text posts and posts with media.
    """

    platform = SocialPlatform.LINKEDIN

    # OAuth 2.0 endpoints
    OAUTH_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    OAUTH_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

    # API endpoints
    API_BASE_URL = "https://api.linkedin.com/v2"

    # OAuth scopes
    SCOPES = [
        "w_member_social",  # Post on behalf of user
        "r_liteprofile",    # Read basic profile
        "r_emailaddress",   # Read email
    ]

    # Character limit
    CHARACTER_LIMIT = 3000

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        timeout: int = 30,
        mock_mode: bool = False,
    ):
        """
        Initialize LinkedIn adapter.

        Args:
            client_id: LinkedIn OAuth client ID
            client_secret: LinkedIn OAuth client secret
            redirect_uri: OAuth redirect URI
            timeout: Request timeout in seconds
            mock_mode: Enable mock mode for development
        """
        self.client_id = client_id or settings.linkedin_client_id
        self.client_secret = client_secret or settings.linkedin_client_secret
        self.redirect_uri = redirect_uri or settings.linkedin_redirect_uri
        self.timeout = timeout
        self.mock_mode = mock_mode

        if not self.mock_mode and not all([self.client_id, self.client_secret]):
            logger.warning(
                "LinkedIn OAuth credentials not configured. "
                "Set linkedin_client_id and linkedin_client_secret in settings."
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
        if not self.mock_mode and not all([self.client_id, self.redirect_uri]):
            raise SocialAuthError(
                "LinkedIn OAuth credentials not configured. "
                "Set linkedin_client_id and linkedin_redirect_uri in settings."
            )

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "state": state,
        }

        authorization_url = f"{self.OAUTH_AUTH_URL}?{urlencode(params)}"
        logger.info("Generated LinkedIn OAuth authorization URL")
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
            logger.info("Mock mode: Returning fake LinkedIn credentials")
            return SocialCredentials(
                platform=SocialPlatform.LINKEDIN,
                access_token="mock_linkedin_access_token",
                refresh_token=None,  # LinkedIn doesn't provide refresh tokens
                token_expiry=None,
                account_id="mock_linkedin_id",
                account_name="Mock LinkedIn User",
                account_username=None,
                profile_image_url="https://example.com/profile.jpg",
            )

        try:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info("Exchanging LinkedIn authorization code for tokens")
                response = await client.post(
                    self.OAUTH_TOKEN_URL,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("error_description", "Token exchange failed")
                    logger.error(f"LinkedIn token exchange failed: {error_msg}")
                    raise SocialAuthError(f"Token exchange failed: {error_msg}")

                token_data = response.json()

            # Get user profile
            user_profile = await self._get_user_profile(token_data["access_token"])

            credentials = SocialCredentials(
                platform=SocialPlatform.LINKEDIN,
                access_token=token_data["access_token"],
                refresh_token=None,  # LinkedIn tokens don't refresh
                token_expiry=None,  # Tokens expire in 60 days but no auto-refresh
                account_id=user_profile["id"],
                account_name=f"{user_profile.get('localizedFirstName', '')} {user_profile.get('localizedLastName', '')}".strip(),
                account_username=None,
                profile_image_url=user_profile.get("profilePicture", {}).get("displayImage~", {}).get("elements", [{}])[0].get("identifiers", [{}])[0].get("identifier"),
            )

            logger.info(f"LinkedIn authentication successful: {credentials.account_name}")
            return credentials

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during LinkedIn token exchange: {e}")
            raise SocialAuthError(f"Token exchange failed: {e}")
        except SocialAuthError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during LinkedIn token exchange: {e}")
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
                f"{self.API_BASE_URL}/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
            )

            if response.status_code != 200:
                raise SocialAPIError("Failed to fetch user profile")

            return response.json()

    async def refresh_token(self, credentials: SocialCredentials) -> SocialCredentials:
        """
        Refresh expired access token.

        Note: LinkedIn doesn't support token refresh. Users must re-authenticate.

        Args:
            credentials: Current credentials

        Returns:
            Same credentials (cannot refresh)

        Raises:
            SocialAuthError: Always raises since refresh not supported
        """
        raise SocialAuthError(
            "LinkedIn does not support token refresh. "
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

    async def post_text(self, credentials: SocialCredentials, text: str) -> PostResult:
        """
        Post a LinkedIn update.

        Args:
            credentials: Account credentials
            text: Post text

        Returns:
            Post result

        Raises:
            SocialValidationError: If text exceeds character limit
            SocialAPIError: If post creation fails
        """
        # Validate text length
        self.validate_text_length(text)

        if self.mock_mode:
            logger.info(f"Mock mode: Would post LinkedIn update: {text[:50]}...")
            return PostResult(
                success=True,
                post_id="urn:li:share:1234567890",
                post_url="https://www.linkedin.com/feed/update/urn:li:share:1234567890",
            )

        try:
            # Create UGC post
            post_data = {
                "author": f"urn:li:person:{credentials.account_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Posting LinkedIn update: {text[:50]}...")
                response = await client.post(
                    f"{self.API_BASE_URL}/ugcPosts",
                    headers={
                        "Authorization": f"Bearer {credentials.access_token}",
                        "Content-Type": "application/json",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                    json=post_data,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    logger.error("LinkedIn rate limit exceeded")
                    raise SocialRateLimitError("Rate limit exceeded")

                if response.status_code not in [200, 201]:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("message", "Post creation failed")
                    logger.error(f"LinkedIn API error: {error_msg}")
                    raise SocialAPIError(f"Post creation failed: {error_msg}")

                result = response.json()
                post_id = result.get("id", "")
                post_url = f"https://www.linkedin.com/feed/update/{post_id}"

                logger.info(f"LinkedIn post created successfully: {post_url}")
                return PostResult(
                    success=True,
                    post_id=post_id,
                    post_url=post_url,
                )

        except (SocialValidationError, SocialRateLimitError, SocialAPIError):
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during LinkedIn posting: {e}")
            return PostResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error during LinkedIn posting: {e}")
            return PostResult(success=False, error_message=str(e))

    async def post_with_media(
        self,
        credentials: SocialCredentials,
        text: str,
        media_urls: List[str]
    ) -> PostResult:
        """
        Post a LinkedIn update with media.

        Args:
            credentials: Account credentials
            text: Post text
            media_urls: List of media URLs

        Returns:
            Post result

        Raises:
            SocialValidationError: If validation fails
            SocialAPIError: If posting fails
        """
        # Validate text length
        self.validate_text_length(text)

        if self.mock_mode:
            logger.info(f"Mock mode: Would post LinkedIn update with {len(media_urls)} media")
            return PostResult(
                success=True,
                post_id="urn:li:share:1234567890",
                post_url="https://www.linkedin.com/feed/update/urn:li:share:1234567890",
            )

        try:
            # Upload all media first
            media_assets = []
            for media_url in media_urls:
                # Download media
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    media_response = await client.get(media_url)
                    media_response.raise_for_status()
                    media_bytes = media_response.content

                # Determine media type
                content_type = media_response.headers.get("content-type", "image/jpeg")

                # Upload to LinkedIn
                upload_result = await self.upload_media(
                    credentials,
                    media_bytes,
                    content_type,
                )
                media_assets.append({
                    "status": "READY",
                    "media": upload_result.media_id
                })

            # Create UGC post with media
            post_data = {
                "author": f"urn:li:person:{credentials.account_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "IMAGE",
                        "media": media_assets
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Posting LinkedIn update with {len(media_assets)} media attachments")
                response = await client.post(
                    f"{self.API_BASE_URL}/ugcPosts",
                    headers={
                        "Authorization": f"Bearer {credentials.access_token}",
                        "Content-Type": "application/json",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                    json=post_data,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    raise SocialRateLimitError("Rate limit exceeded")

                if response.status_code not in [200, 201]:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get("message", "Post creation failed")
                    raise SocialAPIError(f"Post creation failed: {error_msg}")

                result = response.json()
                post_id = result.get("id", "")
                post_url = f"https://www.linkedin.com/feed/update/{post_id}"

                logger.info(f"LinkedIn post with media created successfully: {post_url}")
                return PostResult(
                    success=True,
                    post_id=post_id,
                    post_url=post_url,
                )

        except (SocialValidationError, SocialRateLimitError, SocialAPIError):
            raise
        except Exception as e:
            logger.error(f"Error posting LinkedIn update with media: {e}")
            return PostResult(success=False, error_message=str(e))

    async def upload_media(
        self,
        credentials: SocialCredentials,
        media_bytes: bytes,
        media_type: str,
        filename: Optional[str] = None
    ) -> MediaUploadResult:
        """
        Upload media to LinkedIn.

        Args:
            credentials: Account credentials
            media_bytes: Raw media data
            media_type: MIME type
            filename: Optional filename

        Returns:
            Upload result with media URN

        Raises:
            SocialAPIError: If upload fails
        """
        if self.mock_mode:
            logger.info("Mock mode: Returning fake LinkedIn media URN")
            return MediaUploadResult(
                media_id="urn:li:digitalmediaAsset:1234567890",
                media_type="image",
            )

        try:
            # Step 1: Register upload
            register_data = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": f"urn:li:person:{credentials.account_id}",
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ]
                }
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info("Registering LinkedIn media upload")
                response = await client.post(
                    f"{self.API_BASE_URL}/assets?action=registerUpload",
                    headers={
                        "Authorization": f"Bearer {credentials.access_token}",
                        "Content-Type": "application/json",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                    json=register_data,
                )

                if response.status_code not in [200, 201]:
                    error_msg = response.json().get("message", "Upload registration failed")
                    raise SocialAPIError(f"Media upload registration failed: {error_msg}")

                register_result = response.json()
                upload_url = register_result["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
                asset_id = register_result["value"]["asset"]

                # Step 2: Upload binary data
                logger.info("Uploading media binary to LinkedIn")
                upload_response = await client.put(
                    upload_url,
                    headers={"Authorization": f"Bearer {credentials.access_token}"},
                    content=media_bytes,
                )

                if upload_response.status_code not in [200, 201]:
                    raise SocialAPIError("Media binary upload failed")

                logger.info(f"Media uploaded successfully: {asset_id}")
                return MediaUploadResult(
                    media_id=asset_id,
                    media_type="image",
                )

        except SocialAPIError:
            raise
        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            raise SocialAPIError(f"Media upload failed: {e}")

    async def delete_post(self, credentials: SocialCredentials, post_id: str) -> bool:
        """
        Delete a LinkedIn post.

        Args:
            credentials: Account credentials
            post_id: Post URN

        Returns:
            True if successful

        Raises:
            SocialAPIError: If deletion fails
        """
        if self.mock_mode:
            logger.info(f"Mock mode: Would delete LinkedIn post {post_id}")
            return True

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Deleting LinkedIn post {post_id}")
                response = await client.delete(
                    f"{self.API_BASE_URL}/ugcPosts/{post_id}",
                    headers={
                        "Authorization": f"Bearer {credentials.access_token}",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                )

                if response.status_code == 204:
                    logger.info(f"LinkedIn post {post_id} deleted successfully")
                    return True
                else:
                    error_msg = response.json().get("message", "Deletion failed")
                    raise SocialAPIError(f"Post deletion failed: {error_msg}")

        except SocialAPIError:
            raise
        except Exception as e:
            logger.error(f"Error deleting LinkedIn post: {e}")
            raise SocialAPIError(f"Post deletion failed: {e}")

    def get_character_limit(self) -> int:
        """Get LinkedIn character limit."""
        return self.CHARACTER_LIMIT
