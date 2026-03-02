"""
Social media platform adapters.

Provides unified interface for posting to Twitter, LinkedIn, Facebook,
and Instagram using OAuth 2.0 authentication and platform-specific APIs.
"""

from .base import (
    BaseSocialAdapter,
    MediaUploadResult,
    PostResult,
    SocialAdapterError,
    SocialAPIError,
    SocialAuthError,
    SocialCredentials,
    SocialPlatform,
    SocialRateLimitError,
    SocialValidationError,
)
from .facebook_adapter import FacebookAdapter
from .instagram_adapter import InstagramAdapter
from .linkedin_adapter import LinkedInAdapter
from .twitter_adapter import TwitterAdapter


def get_social_adapter(
    platform: SocialPlatform, mock_mode: bool = False, **kwargs
) -> BaseSocialAdapter:
    """
    Factory function to get platform-specific social media adapter.

    Args:
        platform: Social media platform (twitter, linkedin, facebook, instagram)
        mock_mode: Enable mock mode for development/testing
        **kwargs: Additional adapter-specific arguments

    Returns:
        Platform-specific adapter instance

    Raises:
        ValueError: If platform is not supported

    Examples:
        >>> # Get Twitter adapter
        >>> twitter = get_social_adapter(SocialPlatform.TWITTER)
        >>> auth_url, verifier = twitter.get_authorization_url(state="random_state")

        >>> # Get LinkedIn adapter with custom credentials
        >>> linkedin = get_social_adapter(
        ...     SocialPlatform.LINKEDIN,
        ...     client_id="custom_id",
        ...     client_secret="custom_secret"
        ... )

        >>> # Get Facebook adapter in mock mode
        >>> facebook = get_social_adapter(SocialPlatform.FACEBOOK, mock_mode=True)

        >>> # Get Instagram adapter in mock mode
        >>> instagram = get_social_adapter(SocialPlatform.INSTAGRAM, mock_mode=True)
    """
    adapters = {
        SocialPlatform.TWITTER: TwitterAdapter,
        SocialPlatform.LINKEDIN: LinkedInAdapter,
        SocialPlatform.FACEBOOK: FacebookAdapter,
        SocialPlatform.INSTAGRAM: InstagramAdapter,
    }

    adapter_class = adapters.get(platform)
    if not adapter_class:
        raise ValueError(
            f"Unsupported social platform: {platform}. "
            f"Supported platforms: {', '.join([p.value for p in SocialPlatform])}"
        )

    return adapter_class(mock_mode=mock_mode, **kwargs)


# Convenience instances (can be used directly or via factory)
twitter_adapter = TwitterAdapter()
linkedin_adapter = LinkedInAdapter()
facebook_adapter = FacebookAdapter()
instagram_adapter = InstagramAdapter()


__all__ = [
    # Base classes and enums
    "BaseSocialAdapter",
    "SocialPlatform",
    "SocialCredentials",
    "PostResult",
    "MediaUploadResult",
    # Exceptions
    "SocialAdapterError",
    "SocialAuthError",
    "SocialAPIError",
    "SocialRateLimitError",
    "SocialValidationError",
    # Adapters
    "TwitterAdapter",
    "LinkedInAdapter",
    "FacebookAdapter",
    "InstagramAdapter",
    # Factory
    "get_social_adapter",
    # Convenience instances
    "twitter_adapter",
    "linkedin_adapter",
    "facebook_adapter",
    "instagram_adapter",
]
