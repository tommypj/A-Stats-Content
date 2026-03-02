"""
Base classes and interfaces for social media platform adapters.

Provides abstract base class, data structures, and exceptions for
integrating with various social media platforms (Twitter, LinkedIn, Facebook).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SocialPlatform(StrEnum):
    """Supported social media platforms."""

    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


@dataclass
class SocialCredentials:
    """OAuth credentials for a social media platform."""

    platform: SocialPlatform
    access_token: str
    refresh_token: str | None
    token_expiry: datetime | None
    account_id: str
    account_name: str
    account_username: str | None = None
    profile_image_url: str | None = None

    def to_dict(self) -> dict:
        """Convert credentials to dictionary format."""
        return {
            "platform": self.platform.value,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expiry": self.token_expiry.isoformat() if self.token_expiry else None,
            "account_id": self.account_id,
            "account_name": self.account_name,
            "account_username": self.account_username,
            "profile_image_url": self.profile_image_url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SocialCredentials":
        """Create credentials from dictionary format."""
        return cls(
            platform=SocialPlatform(data["platform"]),
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_expiry=datetime.fromisoformat(data["token_expiry"])
            if data.get("token_expiry")
            else None,
            account_id=data["account_id"],
            account_name=data["account_name"],
            account_username=data.get("account_username"),
            profile_image_url=data.get("profile_image_url"),
        )


@dataclass
class PostResult:
    """Result of a social media post operation."""

    success: bool
    post_id: str | None = None
    post_url: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "post_id": self.post_id,
            "post_url": self.post_url,
            "error_message": self.error_message,
        }


@dataclass
class MediaUploadResult:
    """Result of media upload operation."""

    media_id: str
    media_type: str  # image, video, gif
    media_url: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "media_id": self.media_id,
            "media_type": self.media_type,
            "media_url": self.media_url,
        }


# Custom Exceptions
class SocialAdapterError(Exception):
    """Base exception for social media adapter errors."""

    pass


class SocialAuthError(SocialAdapterError):
    """Raised when OAuth authentication fails."""

    pass


class SocialAPIError(SocialAdapterError):
    """Raised when social media API returns an error."""

    pass


class SocialRateLimitError(SocialAdapterError):
    """Raised when API rate limit is exceeded."""

    pass


class SocialValidationError(SocialAdapterError):
    """Raised when post content validation fails."""

    pass


class BaseSocialAdapter(ABC):
    """
    Abstract base class for social media platform adapters.

    All platform-specific adapters must implement these methods
    to provide consistent interface across different platforms.
    """

    platform: SocialPlatform

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            state: Random state string for CSRF protection

        Returns:
            Authorization URL to redirect user to

        Raises:
            SocialAuthError: If OAuth credentials are not configured
        """
        pass

    @abstractmethod
    async def exchange_code(self, code: str) -> SocialCredentials:
        """
        Exchange authorization code for access tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Social media credentials with tokens and account info

        Raises:
            SocialAuthError: If token exchange fails
            SocialAPIError: If API request fails
        """
        pass

    @abstractmethod
    async def refresh_token(self, credentials: SocialCredentials) -> SocialCredentials:
        """
        Refresh expired access token.

        Args:
            credentials: Current credentials with refresh token

        Returns:
            Updated credentials with new access token

        Raises:
            SocialAuthError: If token refresh fails
        """
        pass

    @abstractmethod
    async def verify_credentials(self, credentials: SocialCredentials) -> bool:
        """
        Verify credentials are still valid.

        Args:
            credentials: Credentials to verify

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    async def post_text(self, credentials: SocialCredentials, text: str) -> PostResult:
        """
        Post text content to social media platform.

        Args:
            credentials: Account credentials
            text: Text content to post

        Returns:
            Result with post ID and URL

        Raises:
            SocialValidationError: If text exceeds character limit
            SocialAPIError: If post creation fails
            SocialRateLimitError: If rate limit is exceeded
        """
        pass

    @abstractmethod
    async def post_with_media(
        self, credentials: SocialCredentials, text: str, media_urls: list[str]
    ) -> PostResult:
        """
        Post content with media attachments.

        Args:
            credentials: Account credentials
            text: Text content to post
            media_urls: List of media URLs to attach

        Returns:
            Result with post ID and URL

        Raises:
            SocialValidationError: If validation fails
            SocialAPIError: If post creation fails
            SocialRateLimitError: If rate limit is exceeded
        """
        pass

    @abstractmethod
    async def upload_media(
        self,
        credentials: SocialCredentials,
        media_bytes: bytes,
        media_type: str,
        filename: str | None = None,
    ) -> MediaUploadResult:
        """
        Upload media for later use in posts.

        Args:
            credentials: Account credentials
            media_bytes: Raw media data
            media_type: MIME type (image/jpeg, image/png, video/mp4, etc.)
            filename: Optional filename

        Returns:
            Upload result with media ID

        Raises:
            SocialValidationError: If media validation fails
            SocialAPIError: If upload fails
        """
        pass

    @abstractmethod
    async def delete_post(self, credentials: SocialCredentials, post_id: str) -> bool:
        """
        Delete a post.

        Args:
            credentials: Account credentials
            post_id: ID of the post to delete

        Returns:
            True if successful

        Raises:
            SocialAPIError: If deletion fails
        """
        pass

    @abstractmethod
    def get_character_limit(self) -> int:
        """
        Get platform character limit.

        Returns:
            Maximum characters allowed in a post
        """
        pass

    def validate_text_length(self, text: str) -> None:
        """
        Validate text length against platform limit.

        Args:
            text: Text to validate

        Raises:
            SocialValidationError: If text exceeds limit
        """
        limit = self.get_character_limit()
        if len(text) > limit:
            raise SocialValidationError(
                f"Text exceeds {self.platform.value} character limit ({len(text)} > {limit})"
            )
