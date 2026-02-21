# Phase 8 Social Media Scheduling - Test Implementation Guide

This guide helps you implement the Phase 8 Social Media Scheduling module to pass all ~130 tests.

## Prerequisites

Before running tests, ensure you have:

1. **Database Models** (`backend/infrastructure/database/models/social.py`):
   - `SocialAccount` - Stores connected social media accounts
   - `ScheduledPost` - Stores scheduled posts
   - `PostTarget` - Links posts to accounts (many-to-many)
   - `PostStatus` enum - PENDING, PUBLISHING, PUBLISHED, FAILED, CANCELLED

2. **Social Adapters** (`backend/adapters/social/`):
   - `twitter_adapter.py` - TwitterAdapter class
   - `linkedin_adapter.py` - LinkedInAdapter class
   - `facebook_adapter.py` - FacebookAdapter class
   - Each adapter must implement: OAuth flow, post creation, token refresh, user profile

3. **Services** (`backend/services/`):
   - `social_scheduler.py` - SocialSchedulerService for processing queue
   - `post_queue.py` - PostQueueService for queue management

4. **API Routes** (`backend/api/routes/social.py`):
   - Account management endpoints
   - Post scheduling endpoints
   - Calendar and stats endpoints

5. **Test Fixtures** - Merge `conftest_social_fixtures.py` into `conftest.py`

## Implementation Checklist

### Step 1: Database Models & Migration

```bash
# Create migration
cd backend
alembic revision -m "create_social_media_tables"

# In migration file, create tables:
# - social_accounts (id, user_id, platform, account_name, account_id, encrypted_access_token, encrypted_refresh_token, token_expires_at, is_active, metadata, created_at, updated_at)
# - scheduled_posts (id, user_id, content, scheduled_time, timezone, status, media_urls, created_at, updated_at)
# - post_targets (id, post_id, account_id, platform, status, platform_post_id, published_at, error_message, retry_count, created_at, updated_at)

# Run migration
alembic upgrade head
```

### Step 2: Social Adapters

Implement each adapter with:

**Twitter Adapter:**
```python
class TwitterAdapter:
    def get_authorization_url(self) -> Tuple[str, str]:
        # Generate OAuth URL with PKCE
        # Return (url, code_verifier)

    async def exchange_code(self, code: str, code_verifier: str) -> dict:
        # Exchange code for tokens
        # Return {access_token, refresh_token, expires_in, expires_at}

    async def refresh_access_token(self, refresh_token: str) -> dict:
        # Refresh expired token

    async def post_text(self, access_token: str, content: str) -> dict:
        # Post tweet
        # Return {id, text}

    async def post_with_media(self, access_token: str, content: str, media_urls: List[str]) -> dict:
        # Upload media, then post tweet

    def validate_content(self, content: str, raise_error: bool = True) -> bool:
        # Validate 280 character limit

    async def get_user_profile(self, access_token: str) -> dict:
        # Fetch user profile
```

**LinkedIn Adapter:** Similar structure, 3000 character limit

**Facebook Adapter:** Similar structure, 63206 character limit, page management

### Step 3: Services

**PostQueueService:**
```python
class PostQueueService:
    async def schedule_post(self, session, user_id, content, scheduled_time, account_ids, ...) -> ScheduledPost:
        # Create post and targets

    async def get_due_posts(self, session, limit=10) -> List[ScheduledPost]:
        # Fetch posts where scheduled_time <= now and status=PENDING

    async def cancel_post(self, session, post_id, user_id) -> bool:
        # Cancel pending post

    async def reschedule_post(self, session, post_id, user_id, new_scheduled_time) -> bool:
        # Update scheduled time
```

**SocialSchedulerService:**
```python
class SocialSchedulerService:
    async def process_due_posts(self, session) -> int:
        # Fetch due posts and publish them

    async def publish_post(self, post, session):
        # Publish to all targets

    async def publish_to_platform(self, target, post, account, session) -> bool:
        # Publish to single platform
        # Handle token refresh if expired
        # Update target status
```

### Step 4: API Routes

Implement these endpoints:

**Account Management:**
- `GET /api/v1/social/accounts` - List connected accounts
- `POST /api/v1/social/accounts/connect` - Initiate OAuth
- `GET /api/v1/social/accounts/callback` - OAuth callback
- `DELETE /api/v1/social/accounts/{account_id}` - Disconnect

**Post Management:**
- `POST /api/v1/social/posts` - Create scheduled post
- `GET /api/v1/social/posts` - List posts (with pagination, filtering)
- `GET /api/v1/social/posts/{post_id}` - Get post details
- `PUT /api/v1/social/posts/{post_id}` - Update pending post
- `DELETE /api/v1/social/posts/{post_id}` - Delete post
- `POST /api/v1/social/posts/{post_id}/publish` - Publish now
- `POST /api/v1/social/posts/{post_id}/retry` - Retry failed

**Calendar & Stats:**
- `GET /api/v1/social/calendar` - Get posts in date range
- `GET /api/v1/social/stats` - Queue statistics

### Step 5: Merge Test Fixtures

Copy the fixtures from `conftest_social_fixtures.py` into `conftest.py`:

```bash
# Append to conftest.py (or manually merge)
cat backend/tests/conftest_social_fixtures.py >> backend/tests/conftest.py
```

### Step 6: Run Tests

Run tests incrementally as you implement:

```bash
# Start with adapter tests
pytest backend/tests/unit/test_social_adapters.py::TestTwitterAdapter -v

# Then scheduler service
pytest backend/tests/unit/test_social_scheduler.py -v

# Then post queue
pytest backend/tests/unit/test_post_queue.py -v

# Finally integration tests
pytest backend/tests/integration/test_social_api.py -v
```

## Common Implementation Patterns

### OAuth Flow

```python
# 1. Generate authorization URL
url, state = adapter.get_authorization_url()
# Redirect user to url

# 2. User authorizes, gets redirected back with code
code = request.query_params.get("code")

# 3. Exchange code for tokens
tokens = await adapter.exchange_code(code, code_verifier)

# 4. Save to database (encrypted)
account = SocialAccount(
    user_id=user.id,
    platform="twitter",
    encrypted_access_token=encrypt_token(tokens["access_token"]),
    encrypted_refresh_token=encrypt_token(tokens["refresh_token"]),
    token_expires_at=tokens["expires_at"],
)
```

### Publishing Flow

```python
# 1. Fetch due posts
posts = await queue_service.get_due_posts(session)

# 2. For each post
for post in posts:
    # Update status to PUBLISHING
    post.status = PostStatus.PUBLISHING

    # 3. For each target
    for target in post.targets:
        # Get account
        account = await get_account(target.account_id)

        # Refresh token if expired
        if account.token_expires_at < datetime.utcnow():
            await refresh_token(account)

        # Publish
        try:
            result = await adapter.post_text(
                access_token=decrypt_token(account.encrypted_access_token),
                content=post.content
            )

            # Update target
            target.status = PostStatus.PUBLISHED
            target.platform_post_id = result["id"]
            target.published_at = datetime.utcnow()
        except Exception as e:
            target.status = PostStatus.FAILED
            target.error_message = str(e)

    # 4. Update post status
    if all(t.status == PostStatus.PUBLISHED for t in post.targets):
        post.status = PostStatus.PUBLISHED
    elif any(t.status == PostStatus.FAILED for t in post.targets):
        post.status = PostStatus.FAILED
```

### Token Refresh

```python
async def refresh_token_if_expired(account: SocialAccount):
    if account.token_expires_at <= datetime.utcnow():
        refresh_token = decrypt_token(account.encrypted_refresh_token)

        # Call adapter
        new_tokens = await adapter.refresh_access_token(refresh_token)

        # Update account
        account.encrypted_access_token = encrypt_token(new_tokens["access_token"])
        if "refresh_token" in new_tokens:
            account.encrypted_refresh_token = encrypt_token(new_tokens["refresh_token"])
        account.token_expires_at = new_tokens["expires_at"]

        await session.commit()
```

## Debugging Failed Tests

### Test Skipped

If tests show "skipped: not implemented yet":
- Check that models exist: `SocialAccount`, `ScheduledPost`, `PostTarget`, `PostStatus`
- Check that adapters exist: `TwitterAdapter`, `LinkedInAdapter`, `FacebookAdapter`
- Check that services exist: `SocialSchedulerService`, `PostQueueService`
- Check that routes exist: `api/routes/social.py`

### Import Errors

```python
# Ensure __init__.py files export classes
# adapters/social/__init__.py
from .twitter_adapter import TwitterAdapter
from .linkedin_adapter import LinkedInAdapter
from .facebook_adapter import FacebookAdapter

# services/__init__.py
from .social_scheduler import SocialSchedulerService
from .post_queue import PostQueueService
```

### Database Errors

```bash
# Recreate test database
alembic downgrade base
alembic upgrade head
```

### Fixture Errors

```python
# Check fixture dependencies
# connected_twitter_account requires: db_session, test_user
# pending_post requires: db_session, test_user, connected_twitter_account
```

## Test Coverage Goals

After implementation, aim for:
- Unit tests: 100% coverage of adapter methods, service methods
- Integration tests: All API endpoints tested
- Error handling: All error paths tested
- Edge cases: Token expiry, rate limits, partial failures

## Next Steps After Tests Pass

1. **Background Job:** Set up Celery/Redis to run `process_due_posts()` every minute
2. **Cron Job:** Alternative to Celery, use system cron
3. **Monitoring:** Add logging for failed posts, retry counts
4. **Rate Limiting:** Implement per-user/per-platform rate limits
5. **Analytics:** Track post performance (likes, retweets, etc.)
6. **Frontend:** Build post composer UI (already done in Phase 8 frontend)
7. **Notifications:** Email user when posts publish/fail

## Resources

- **Test Documentation:** `SOCIAL_TESTS.md`
- **API Patterns:** See `test_social_api.py` for endpoint signatures
- **Mock Patterns:** See `conftest_social_fixtures.py` for fixture examples
- **Existing Tests:** Check `test_gsc_adapter.py`, `test_billing_api.py` for similar patterns

## Support

If you encounter issues:
1. Check test output for specific error messages
2. Review `SOCIAL_TESTS.md` for troubleshooting section
3. Compare implementation to mock patterns in test files
4. Verify database schema matches model definitions

Good luck implementing Phase 8! 🚀
