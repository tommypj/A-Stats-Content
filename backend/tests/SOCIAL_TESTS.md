# Phase 8: Social Media Scheduling Tests

Comprehensive test suite for the social media scheduling module, covering Twitter/X, LinkedIn, and Facebook integrations.

## Test Coverage Overview

### Unit Tests (3 files, ~85 tests)

1. **test_social_adapters.py** (~35 tests)
   - Twitter OAuth 2.0 with PKCE
   - LinkedIn OAuth 2.0
   - Facebook OAuth 2.0
   - Post creation and media upload
   - Character limit validation
   - Token refresh
   - Rate limit handling

2. **test_social_scheduler.py** (~30 tests)
   - Processing due posts
   - Publishing to platforms
   - Token refresh handling
   - Retry logic
   - Multiple target handling
   - Timezone handling
   - Concurrent publishing

3. **test_post_queue.py** (~20 tests)
   - Scheduling posts
   - Fetching due posts
   - Marking as published
   - Canceling posts
   - Rescheduling
   - Queue statistics

### Integration Tests (1 file, ~45 tests)

1. **test_social_api.py** (~45 tests)
   - Account connection and management
   - Post scheduling and management
   - Calendar views
   - Publishing workflow
   - Statistics endpoints

**Total: ~130 tests for Phase 8**

---

## Running Tests

### Run All Social Media Tests
```bash
# From backend directory
cd backend

# All social tests
pytest tests/unit/test_social_adapters.py tests/unit/test_social_scheduler.py tests/unit/test_post_queue.py tests/integration/test_social_api.py -v

# Or by pattern
pytest tests/ -k "social" -v
```

### Run Specific Test Suites
```bash
# Twitter adapter only
pytest tests/unit/test_social_adapters.py::TestTwitterAdapter -v

# LinkedIn adapter only
pytest tests/unit/test_social_adapters.py::TestLinkedInAdapter -v

# Scheduler service
pytest tests/unit/test_social_scheduler.py -v

# Post queue
pytest tests/unit/test_post_queue.py -v

# API integration tests
pytest tests/integration/test_social_api.py -v
```

### Run with Coverage
```bash
pytest tests/ -k "social" --cov=adapters.social --cov=services --cov=api.routes.social --cov-report=html
```

---

## Test Structure

### 1. Social Adapters Tests

#### Twitter Adapter (`TestTwitterAdapter`)

**OAuth Flow:**
- `test_get_authorization_url` - Generates OAuth URL with PKCE challenge
- `test_exchange_code_success` - Exchanges authorization code for tokens
- `test_exchange_code_invalid` - Handles invalid authorization code
- `test_refresh_token` - Refreshes expired access token

**Post Publishing:**
- `test_post_text_success` - Posts text-only tweet
- `test_post_with_media` - Posts tweet with images
- `test_post_text_rate_limited` - Handles 429 rate limit response
- `test_character_limit_validation` - Validates 280 character limit

**User Profile:**
- `test_get_user_profile` - Fetches authenticated user info

#### LinkedIn Adapter (`TestLinkedInAdapter`)

**OAuth Flow:**
- `test_get_authorization_url` - Generates LinkedIn OAuth URL
- `test_exchange_code_success` - Exchanges code for access token

**Post Publishing:**
- `test_post_text_success` - Creates LinkedIn post
- `test_character_limit_validation` - Validates 3000 character limit

**User Profile:**
- `test_get_user_profile` - Fetches user profile

#### Facebook Adapter (`TestFacebookAdapter`)

**OAuth Flow:**
- `test_get_authorization_url` - Generates Facebook OAuth URL
- `test_exchange_code_success` - Exchanges code for access token

**Post Publishing:**
- `test_post_text_success` - Creates Facebook page post
- `test_character_limit_validation` - Validates 63206 character limit

**Page Management:**
- `test_get_pages` - Fetches user's Facebook pages

---

### 2. Scheduler Service Tests

**Post Processing:**
- `test_process_due_posts_finds_pending` - Finds and processes due posts
- `test_process_due_posts_skips_future` - Skips posts scheduled for future

**Publishing:**
- `test_publish_to_platform_success` - Successfully publishes post
- `test_publish_to_platform_failure_updates_status` - Updates status on failure
- `test_publish_with_expired_token_refreshes` - Refreshes expired tokens
- `test_publish_immediately` - Publishes post bypassing schedule

**Multi-Platform:**
- `test_retry_failed_target` - Retries failed post target
- `test_multiple_targets_partial_success` - Handles partial success
- `test_media_post_uploads_first` - Uploads media before posting

**Edge Cases:**
- `test_max_retry_limit` - Respects max retry count
- `test_timezone_handling` - Handles different timezones
- `test_concurrent_publishing` - Prevents duplicate publishing
- `test_delete_scheduled_post` - Deletes pending posts
- `test_update_scheduled_post` - Updates post content/time

---

### 3. Post Queue Tests

**Queue Operations:**
- `test_schedule_post_adds_to_queue` - Adds post to queue
- `test_schedule_post_with_multiple_accounts` - Schedules to multiple platforms
- `test_get_due_posts_returns_correct` - Fetches posts due for publishing

**Status Management:**
- `test_mark_published_removes_from_queue` - Marks post as published
- `test_cancel_post_removes_from_queue` - Cancels pending post
- `test_cancel_published_post_fails` - Cannot cancel published posts

**Rescheduling:**
- `test_reschedule_updates_timestamp` - Updates scheduled time
- `test_reschedule_published_post_fails` - Cannot reschedule published posts

**Queries:**
- `test_get_user_posts_paginated` - Fetches posts with pagination
- `test_filter_posts_by_status` - Filters by status
- `test_get_post_by_id` - Fetches specific post
- `test_get_post_wrong_user_fails` - Enforces user ownership

**Management:**
- `test_update_post_content` - Updates pending post content
- `test_get_queue_statistics` - Returns queue stats
- `test_delete_old_published_posts` - Cleanup old posts

---

### 4. API Integration Tests

#### Account Endpoints (`TestAccountsEndpoint`)

**Listing:**
- `test_list_accounts_empty` - Returns empty list initially
- `test_list_accounts_with_connected` - Lists connected accounts
- `test_list_accounts_unauthorized` - Requires authentication

**Connection:**
- `test_initiate_connection_returns_auth_url` - Returns OAuth URL
- `test_initiate_connection_invalid_platform` - Validates platform
- `test_oauth_callback_success` - Saves account after OAuth

**Disconnection:**
- `test_disconnect_account` - Removes account
- `test_disconnect_wrong_account_fails` - Enforces ownership

#### Post Endpoints (`TestPostsEndpoint`)

**Creation:**
- `test_create_post_success` - Creates scheduled post
- `test_create_post_invalid_account` - Validates account_id
- `test_create_post_content_too_long` - Validates content length
- `test_create_post_past_time_fails` - Rejects past scheduled times

**Listing:**
- `test_list_posts_paginated` - Returns paginated list
- `test_list_posts_filter_by_status` - Filters by status
- `test_get_post_by_id` - Fetches specific post

**Updates:**
- `test_update_pending_post` - Updates pending post
- `test_update_posted_fails` - Cannot edit published posts
- `test_delete_post` - Deletes pending post

**Publishing:**
- `test_publish_now` - Publishes immediately
- `test_retry_failed_post` - Retries failed post

#### Calendar Endpoint (`TestCalendarEndpoint`)

- `test_get_calendar_range` - Returns posts in date range
- `test_get_calendar_empty_range` - Handles empty ranges
- `test_calendar_grouped_by_day` - Groups posts by day

#### Stats Endpoint (`TestStatsEndpoint`)

- `test_get_statistics` - Returns queue statistics
- `test_stats_by_platform` - Breaks down by platform

#### Media Upload (`TestMediaUpload`)

- `test_create_post_with_media` - Creates post with media URLs
- `test_upload_media_file` - Uploads media file

---

## Fixtures

### Social Account Fixtures

```python
@pytest.fixture
async def connected_twitter_account(db_session, test_user):
    """Creates connected Twitter account."""

@pytest.fixture
async def connected_linkedin_account(db_session, test_user):
    """Creates connected LinkedIn account."""

@pytest.fixture
async def connected_facebook_account(db_session, test_user):
    """Creates connected Facebook account."""

@pytest.fixture
async def connected_accounts(db_session, test_user, ...):
    """Creates multiple connected accounts (Twitter + LinkedIn)."""
```

### Post Fixtures

```python
@pytest.fixture
async def pending_post(db_session, test_user, connected_twitter_account):
    """Creates pending scheduled post."""

@pytest.fixture
async def posted_post(db_session, test_user, connected_twitter_account):
    """Creates already-published post."""

@pytest.fixture
async def failed_post(db_session, test_user, connected_twitter_account):
    """Creates failed post for retry testing."""

@pytest.fixture
async def multiple_scheduled_posts(db_session, test_user, connected_accounts):
    """Creates multiple posts with various statuses."""
```

### Mock API Fixtures

```python
@pytest.fixture
def mock_twitter_api():
    """Mocks Twitter API responses."""

@pytest.fixture
def mock_linkedin_api():
    """Mocks LinkedIn API responses."""

@pytest.fixture
def mock_facebook_api():
    """Mocks Facebook API responses."""
```

**Note:** All social fixtures are available in `conftest_social_fixtures.py`. To use them, merge this file into the main `conftest.py`.

---

## Mock Patterns

### Twitter API Mock

```python
@pytest.fixture
def mock_twitter_api():
    """Mock Twitter API responses."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()

        async def mock_post(*args, **kwargs):
            mock_response = AsyncMock()
            if "tweets" in str(kwargs.get("url", "")):
                mock_response.status_code = 201
                mock_response.json.return_value = {
                    "data": {
                        "id": "1234567890",
                        "text": kwargs.get("json", {}).get("text", "Test tweet"),
                    }
                }
            elif "oauth2/token" in str(kwargs.get("url", "")):
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "access_token": "new_access_token",
                    "refresh_token": "new_refresh_token",
                    "expires_in": 7200,
                }
            return mock_response

        mock_instance.post = mock_post
        mock_client.return_value.__aenter__.return_value = mock_instance
        yield mock_instance
```

### Using Mocks in Tests

```python
@pytest.mark.asyncio
async def test_post_tweet(twitter_adapter, mock_twitter_api):
    """Test posting tweet with mocked API."""
    with patch('adapters.social.twitter_adapter.TwitterAdapter.post_text') as mock_post:
        mock_post.return_value = {
            "id": "1234567890",
            "text": "Test tweet",
        }

        result = await twitter_adapter.post_text(
            access_token="test_token",
            content="Test tweet",
        )

        assert result["id"] == "1234567890"
```

---

## Key Testing Patterns

### 1. OAuth Flow Testing

All OAuth flows follow this pattern:

```python
# Generate authorization URL
url, state = adapter.get_authorization_url()
assert "oauth" in url

# Exchange code for tokens
tokens = await adapter.exchange_code(code="auth_code")
assert "access_token" in tokens

# Refresh expired token
new_tokens = await adapter.refresh_access_token(refresh_token="refresh")
assert new_tokens["access_token"] != tokens["access_token"]
```

### 2. Post Publishing Testing

```python
# Create post
post = await queue_service.schedule_post(
    content="Test content",
    scheduled_time=future_time,
    account_ids=[account.id],
)

# Process queue
processed = await scheduler_service.process_due_posts(session)

# Verify published
assert post.status == PostStatus.PUBLISHED
assert post.targets[0].platform_post_id is not None
```

### 3. Error Handling Testing

```python
# Mock API failure
mock_adapter.post_text.side_effect = Exception("API Error")

# Attempt publish
result = await scheduler_service.publish_to_platform(
    target=target,
    post=post,
    account=account,
    session=session,
)

# Verify error handling
assert result is False
assert target.status == PostStatus.FAILED
assert "API Error" in target.error_message
```

### 4. Timezone Testing

```python
# Create post with specific timezone
post = ScheduledPost(
    scheduled_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    timezone="America/New_York",
)

# Verify timezone conversion
is_due = scheduler_service.is_post_due(post, current_time)
```

---

## Database State Verification

### Checking Post Status

```python
# After operation
await session.refresh(post)
assert post.status == PostStatus.PUBLISHED
assert post.updated_at > post.created_at
```

### Checking Targets

```python
# Verify all targets processed
for target in post.targets:
    await session.refresh(target)
    assert target.status in [PostStatus.PUBLISHED, PostStatus.FAILED]
    if target.status == PostStatus.PUBLISHED:
        assert target.platform_post_id is not None
        assert target.published_at is not None
```

---

## Common Test Scenarios

### 1. Multi-Platform Publishing

```python
# Create post targeting Twitter + LinkedIn
post = await queue_service.schedule_post(
    content="Multi-platform test",
    scheduled_time=future_time,
    account_ids=[twitter_account.id, linkedin_account.id],
)

# Verify targets created
assert len(post.targets) == 2
assert {t.platform for t in post.targets} == {"twitter", "linkedin"}
```

### 2. Partial Failure Handling

```python
# Mock Twitter success, LinkedIn failure
mock_twitter.return_value = {"id": "123"}
mock_linkedin.side_effect = Exception("API Error")

# Process post
await scheduler_service.publish_post(post, session)

# Verify partial success
twitter_target = next(t for t in post.targets if t.platform == "twitter")
linkedin_target = next(t for t in post.targets if t.platform == "linkedin")

assert twitter_target.status == PostStatus.PUBLISHED
assert linkedin_target.status == PostStatus.FAILED
```

### 3. Token Refresh

```python
# Set token as expired
account.token_expires_at = datetime.utcnow() - timedelta(hours=1)

# Mock refresh
mock_refresh.return_value = {"access_token": "new_token"}

# Publish post
await scheduler_service.publish_to_platform(target, post, account, session)

# Verify token refreshed
mock_refresh.assert_called_once()
```

---

## Troubleshooting

### Tests Skipped

If tests are skipped with "not implemented yet":

1. Check that models exist:
   - `infrastructure/database/models/social.py`
   - `SocialAccount`, `ScheduledPost`, `PostTarget`, `PostStatus`

2. Check that adapters exist:
   - `adapters/social/twitter_adapter.py`
   - `adapters/social/linkedin_adapter.py`
   - `adapters/social/facebook_adapter.py`

3. Check that services exist:
   - `services/social_scheduler.py`
   - `services/post_queue.py`

4. Check that routes exist:
   - `api/routes/social.py`

### Import Errors

If you see import errors:

```python
# Check that __init__.py files exist
backend/adapters/social/__init__.py
backend/services/__init__.py

# Check exports in __init__.py
from .twitter_adapter import TwitterAdapter
from .linkedin_adapter import LinkedInAdapter
from .facebook_adapter import FacebookAdapter
```

### Fixture Not Found

If fixture errors occur:

1. Ensure `conftest_social_fixtures.py` is merged into `conftest.py`
2. Check fixture dependencies (e.g., `connected_twitter_account` requires `test_user`)
3. Verify async fixtures use `@pytest.fixture` with `async def`

### Database Errors

If database errors occur:

```python
# Ensure models are imported in Base
from infrastructure.database.models import Base
from infrastructure.database.models.social import SocialAccount, ScheduledPost

# Ensure migrations are run
alembic upgrade head
```

---

## Next Steps

### After Implementation

1. **Run tests to verify implementation:**
   ```bash
   pytest tests/unit/test_social_adapters.py -v
   pytest tests/unit/test_social_scheduler.py -v
   pytest tests/unit/test_post_queue.py -v
   pytest tests/integration/test_social_api.py -v
   ```

2. **Check coverage:**
   ```bash
   pytest tests/ -k "social" --cov=adapters.social --cov=services --cov=api.routes.social --cov-report=html
   open htmlcov/index.html
   ```

3. **Fix failing tests:**
   - Review error messages
   - Check implementation matches expected behavior
   - Update tests if spec changes

### Integration with CI/CD

Add to `.github/workflows/ci.yml`:

```yaml
- name: Run Social Media Tests
  run: |
    cd backend
    pytest tests/unit/test_social_adapters.py -v
    pytest tests/unit/test_social_scheduler.py -v
    pytest tests/unit/test_post_queue.py -v
    pytest tests/integration/test_social_api.py -v
```

---

## Summary

Phase 8 test suite provides comprehensive coverage for:

- **OAuth 2.0 flows** (Twitter PKCE, LinkedIn, Facebook)
- **Post scheduling** and queue management
- **Multi-platform publishing** with partial failure handling
- **Token refresh** and rate limit handling
- **Calendar views** and statistics
- **API endpoints** with authentication and authorization

All tests follow Clean Architecture principles and existing patterns from Phases 5-7 (Analytics, Billing, Knowledge Vault).

**Total Coverage: ~130 tests across 4 files**
