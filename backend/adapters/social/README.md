# Social Media Platform Adapters

Clean Architecture adapters for posting to social media platforms (Twitter/X, LinkedIn, Facebook) with OAuth 2.0 authentication.

## Supported Platforms

- **Twitter/X** - OAuth 2.0 with PKCE, API v2
- **LinkedIn** - OAuth 2.0, Marketing API
- **Facebook** - OAuth 2.0, Graph API v18.0
- **Instagram** - Via Facebook Business API (same adapter)

## Features

- Unified interface across all platforms
- OAuth 2.0 authentication flow
- Text and media posting
- Rate limit handling
- Mock mode for development
- Async/await support with httpx
- Comprehensive error handling

## Quick Start

### 1. Factory Pattern (Recommended)

```python
from adapters.social import get_social_adapter, SocialPlatform

# Get Twitter adapter
twitter = get_social_adapter(SocialPlatform.TWITTER)

# Generate OAuth URL
auth_url, code_verifier = twitter.get_authorization_url(state="random_state")

# Exchange code for credentials
credentials = await twitter.exchange_code(code, code_verifier)

# Post a tweet
result = await twitter.post_text(credentials, "Hello from A-Stats!")
print(f"Posted: {result.post_url}")
```

### 2. Direct Import

```python
from adapters.social import TwitterAdapter, LinkedInAdapter, FacebookAdapter

twitter = TwitterAdapter(mock_mode=True)
linkedin = LinkedInAdapter()
facebook = FacebookAdapter()
```

### 3. Mock Mode (Development)

```python
# Enable mock mode to test without API keys
twitter = get_social_adapter(SocialPlatform.TWITTER, mock_mode=True)

# All operations return fake data
result = await twitter.post_text(mock_credentials, "Test post")
# Returns: PostResult(success=True, post_id="1234567890", ...)
```

## Configuration

Add these to your `.env` file:

```bash
# Twitter/X OAuth 2.0
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret
TWITTER_REDIRECT_URI=http://localhost:8000/api/v1/social/twitter/callback

# LinkedIn OAuth 2.0
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/v1/social/linkedin/callback

# Facebook/Instagram OAuth
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
FACEBOOK_REDIRECT_URI=http://localhost:8000/api/v1/social/facebook/callback
```

## Platform-Specific Details

### Twitter/X

- **Character Limit**: 280
- **OAuth**: OAuth 2.0 with PKCE (code verifier/challenge)
- **API**: Twitter API v2
- **Media**: Up to 4 images per tweet
- **Rate Limits**: Yes (handled automatically)

```python
twitter = get_social_adapter(SocialPlatform.TWITTER)

# OAuth flow with PKCE
auth_url, code_verifier = twitter.get_authorization_url(state="csrf_token")
# Store code_verifier in session for later use

# After user authorizes...
credentials = await twitter.exchange_code(code, code_verifier)

# Post tweet
result = await twitter.post_text(credentials, "Hello Twitter!")

# Post with media
result = await twitter.post_with_media(
    credentials,
    "Check out these images!",
    ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
)
```

### LinkedIn

- **Character Limit**: 3000
- **OAuth**: OAuth 2.0 (no refresh tokens)
- **API**: LinkedIn Marketing API v2
- **Media**: Supports image posts
- **Token Lifespan**: 60 days (no auto-refresh)

```python
linkedin = get_social_adapter(SocialPlatform.LINKEDIN)

# OAuth flow (standard)
auth_url = linkedin.get_authorization_url(state="csrf_token")

# After user authorizes...
credentials = await linkedin.exchange_code(code)

# Post update
result = await linkedin.post_text(credentials, "Hello LinkedIn!")

# Post with media
result = await linkedin.post_with_media(
    credentials,
    "Sharing insights!",
    ["https://example.com/chart.png"]
)
```

### Facebook

- **Character Limit**: 63,206
- **OAuth**: OAuth 2.0 with long-lived tokens
- **API**: Graph API v18.0
- **Media**: Supports photos and albums
- **Pages**: Requires Page access token
- **Token Lifespan**: 60 days (long-lived)

```python
facebook = get_social_adapter(SocialPlatform.FACEBOOK)

# OAuth flow
auth_url = facebook.get_authorization_url(state="csrf_token")

# After user authorizes...
credentials = await facebook.exchange_code(code)

# Get user's pages
pages = await facebook.get_pages(credentials)
# [{"id": "123", "name": "My Page", "access_token": "page_token"}]

# Post to page (requires page ID and page token)
result = await facebook.post_text(
    credentials,
    "Hello Facebook!",
    page_id=pages[0]["id"],
    page_token=pages[0]["access_token"]
)

# Post with media
result = await facebook.post_with_media(
    credentials,
    "Check this out!",
    ["https://example.com/photo.jpg"],
    page_id=pages[0]["id"],
    page_token=pages[0]["access_token"]
)
```

## Data Structures

### SocialCredentials

```python
@dataclass
class SocialCredentials:
    platform: SocialPlatform
    access_token: str
    refresh_token: Optional[str]
    token_expiry: Optional[datetime]
    account_id: str
    account_name: str
    account_username: Optional[str]
    profile_image_url: Optional[str]
```

### PostResult

```python
@dataclass
class PostResult:
    success: bool
    post_id: Optional[str]
    post_url: Optional[str]
    error_message: Optional[str]
```

### MediaUploadResult

```python
@dataclass
class MediaUploadResult:
    media_id: str
    media_type: str  # image, video, gif
    media_url: Optional[str]
```

## Error Handling

All adapters raise consistent exceptions:

```python
from adapters.social import (
    SocialAdapterError,      # Base exception
    SocialAuthError,         # OAuth/authentication errors
    SocialAPIError,          # API request errors
    SocialRateLimitError,    # Rate limit exceeded
    SocialValidationError,   # Content validation errors
)

try:
    result = await twitter.post_text(credentials, text)
except SocialRateLimitError as e:
    # Handle rate limiting (retry after cooldown)
    print(f"Rate limited: {e}")
except SocialValidationError as e:
    # Handle validation (text too long, etc.)
    print(f"Validation error: {e}")
except SocialAPIError as e:
    # Handle API errors
    print(f"API error: {e}")
except SocialAuthError as e:
    # Handle auth errors (expired token, etc.)
    print(f"Auth error: {e}")
```

## BaseSocialAdapter Interface

All adapters implement this interface:

```python
class BaseSocialAdapter(ABC):
    platform: SocialPlatform

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL"""

    @abstractmethod
    async def exchange_code(self, code: str) -> SocialCredentials:
        """Exchange authorization code for tokens"""

    @abstractmethod
    async def refresh_token(self, credentials: SocialCredentials) -> SocialCredentials:
        """Refresh expired access token"""

    @abstractmethod
    async def verify_credentials(self, credentials: SocialCredentials) -> bool:
        """Verify credentials are still valid"""

    @abstractmethod
    async def post_text(self, credentials: SocialCredentials, text: str) -> PostResult:
        """Post text content"""

    @abstractmethod
    async def post_with_media(
        self,
        credentials: SocialCredentials,
        text: str,
        media_urls: List[str]
    ) -> PostResult:
        """Post content with media attachments"""

    @abstractmethod
    async def upload_media(
        self,
        credentials: SocialCredentials,
        media_bytes: bytes,
        media_type: str
    ) -> MediaUploadResult:
        """Upload media for later use in posts"""

    @abstractmethod
    async def delete_post(self, credentials: SocialCredentials, post_id: str) -> bool:
        """Delete a post"""

    @abstractmethod
    def get_character_limit(self) -> int:
        """Get platform character limit"""
```

## Testing

Use mock mode for testing without API keys:

```python
import pytest
from adapters.social import get_social_adapter, SocialPlatform

@pytest.mark.asyncio
async def test_twitter_post():
    twitter = get_social_adapter(SocialPlatform.TWITTER, mock_mode=True)

    # Mock credentials
    credentials = await twitter.exchange_code("fake_code")

    # Post (returns fake result)
    result = await twitter.post_text(credentials, "Test tweet")

    assert result.success is True
    assert result.post_id is not None
```

## Architecture Notes

- **Clean Architecture**: Adapters live in infrastructure layer
- **Dependency Injection**: Use factory pattern for flexibility
- **Async/Await**: All network operations are async
- **Error Handling**: Consistent exceptions across platforms
- **Logging**: Comprehensive logging for debugging
- **Type Safety**: Full type hints throughout

## API Rate Limits

Each platform has different rate limits:

- **Twitter**: 300 tweets per 3 hours (user context)
- **LinkedIn**: 100 posts per day per user
- **Facebook**: Varies by app and page

All adapters handle rate limiting by:
1. Detecting 429 status codes
2. Raising `SocialRateLimitError`
3. Including retry-after information when available

## Credential Storage

Credentials should be encrypted before database storage:

```python
from core.security.encryption import encrypt_credentials, decrypt_credentials

# Store credentials
encrypted = encrypt_credentials(credentials.to_dict())
# Save encrypted to database

# Retrieve credentials
decrypted = decrypt_credentials(encrypted)
credentials = SocialCredentials.from_dict(decrypted)
```

## Future Enhancements

- [ ] Thread/Reply support (Twitter threads, LinkedIn comments)
- [ ] Post scheduling
- [ ] Analytics (engagement metrics)
- [ ] Batch posting
- [ ] Video upload support
- [ ] Instagram direct posting (requires Business/Creator account)
- [ ] Poll creation
- [ ] Location tagging

## References

- [Twitter API v2 Documentation](https://developer.twitter.com/en/docs/twitter-api)
- [LinkedIn Marketing API](https://learn.microsoft.com/en-us/linkedin/marketing/)
- [Facebook Graph API](https://developers.facebook.com/docs/graph-api/)
