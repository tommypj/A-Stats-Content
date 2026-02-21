# Social Media Scheduler Service

The Social Media Scheduler Service handles automatic publishing of scheduled social media posts at their designated times.

## Architecture

### Components

1. **SocialSchedulerService** (`social_scheduler.py`)
   - Main scheduler service that runs in the background
   - Polls database every 60 seconds for due posts
   - Publishes posts to multiple platforms
   - Handles token refresh and error tracking

2. **PostQueueManager** (`post_queue.py`)
   - Optional Redis-based queue for more efficient scheduling
   - Falls back to database polling if Redis unavailable
   - Uses sorted sets for time-based queries

3. **Social Adapters** (`adapters/social/`)
   - Platform-specific implementations (Twitter, LinkedIn, Facebook, Instagram)
   - Base adapter interface in `base.py`
   - Factory function: `get_social_adapter(platform)`

## How It Works

### Scheduling Flow

1. User creates a scheduled post via API:
   ```python
   scheduled_post = ScheduledPost(
       user_id=user.id,
       content="Check out our new article!",
       media_urls=["https://example.com/image.jpg"],
       scheduled_at=datetime(2026, 2, 21, 10, 0, 0),
       timezone="America/New_York",
       status=PostStatus.PENDING
   )
   ```

2. Post targets are created linking to social accounts:
   ```python
   target = PostTarget(
       post_id=scheduled_post.id,
       account_id=twitter_account.id,
       status=PostTargetStatus.PENDING
   )
   ```

3. Scheduler checks every minute for posts where:
   - `scheduled_at <= now()`
   - `status == 'pending'`

4. For each due post:
   - Update status to 'posting'
   - For each target account:
     - Decrypt OAuth tokens
     - Refresh token if expired
     - Publish via platform adapter
     - Update target with result (post_id, post_url, error)
   - Update post status based on results:
     - 'posted' if all targets succeeded
     - 'posted' if some succeeded (partial success)
     - 'failed' if all targets failed

### Token Management

The scheduler automatically handles OAuth token refresh:

```python
# Check if token expired
if credentials.token_expiry < datetime.utcnow():
    credentials = await adapter.refresh_token(credentials)
    await self._update_account_tokens(account, credentials, db)
```

### Error Handling

- **Rate Limits**: Posts remain in 'pending' status to retry later
- **API Errors**: Target marked as 'failed' with error message
- **Content Validation**: Adapter validates before posting
- **Token Errors**: Logged and target marked as failed

## Usage

### Starting the Scheduler

The scheduler starts automatically with the FastAPI application via the lifespan handler in `main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await post_queue.connect()  # Optional Redis
    scheduler_task = asyncio.create_task(scheduler_service.start())

    yield

    # Shutdown
    await scheduler_service.stop()
    scheduler_task.cancel()
    await post_queue.disconnect()
```

### Manual Post Publishing

Publish a post immediately (bypass schedule):

```python
from services.social_scheduler import scheduler_service

result = await scheduler_service.publish_post_immediately(
    post_id="uuid-here",
    db=db_session
)

# Result:
{
    "success": True,
    "post_status": "posted",
    "published_count": 2,
    "failed_count": 0,
    "targets": [
        {
            "account": "My Twitter",
            "platform": "twitter",
            "status": "posted",
            "post_url": "https://twitter.com/...",
            "error": None
        }
    ]
}
```

### Retrying Failed Targets

Retry a specific failed target:

```python
result = await scheduler_service.retry_failed_target(
    target_id="uuid-here",
    db=db_session
)
```

## Redis Queue (Optional)

If Redis is available, the PostQueueManager provides more efficient scheduling:

### Features

- **Sorted Sets**: Uses Redis ZSET with timestamp scores
- **Atomic Operations**: Move posts between states atomically
- **Stale Recovery**: Detect and recover stuck posts
- **Queue Statistics**: Monitor scheduled and processing counts

### Operations

```python
from services.post_queue import post_queue

# Schedule a post
await post_queue.schedule_post(post_id, scheduled_at)

# Get due posts
due_posts = await post_queue.get_due_posts(limit=100)

# Mark as published
await post_queue.mark_published(post_id)

# Cancel scheduled post
await post_queue.cancel_post(post_id)

# Reschedule
await post_queue.reschedule_post(post_id, new_time)
```

## Database Schema

### Social Accounts

Stores connected social media accounts with encrypted OAuth tokens:

- `id`, `user_id`, `platform`
- `account_id`, `account_name`, `account_username`
- `access_token_encrypted`, `refresh_token_encrypted`, `token_expiry`
- `is_active`, `last_used`

### Scheduled Posts

Posts scheduled for future publishing:

- `id`, `user_id`, `content`, `media_urls`
- `scheduled_at`, `timezone`, `status`
- `article_id` (optional link to article)

### Post Targets

Links posts to specific social accounts:

- `id`, `post_id`, `account_id`
- `status`, `platform_post_id`, `platform_post_url`
- `error_message`, `posted_at`

### Post Analytics

Tracks engagement metrics (fetched periodically):

- `id`, `post_target_id`
- `likes`, `comments`, `shares`, `impressions`, `clicks`
- `recorded_at`

## Configuration

Environment variables:

```env
# Social Media OAuth
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_secret
TWITTER_REDIRECT_URI=http://localhost:8000/api/v1/social/twitter/callback

LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/v1/social/linkedin/callback

FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_secret
FACEBOOK_REDIRECT_URI=http://localhost:8000/api/v1/social/facebook/callback

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Encryption
SECRET_KEY=your-secret-key-for-token-encryption
```

## Logging

The scheduler logs all operations:

```python
import logging
logger = logging.getLogger(__name__)

# Examples:
logger.info("Social scheduler started - checking for posts every 60 seconds")
logger.info(f"Found {len(due_posts)} posts due for publishing")
logger.warning(f"Rate limit hit for twitter: {e}")
logger.error(f"Failed to publish to linkedin: {e}", exc_info=True)
```

## Platform Adapters

Each platform requires a specific adapter implementation:

### Base Adapter Interface

```python
class BaseSocialAdapter(ABC):
    @abstractmethod
    async def post_text(self, credentials, text) -> PostResult:
        pass

    @abstractmethod
    async def post_with_media(self, credentials, text, media_urls) -> PostResult:
        pass

    @abstractmethod
    async def refresh_token(self, credentials) -> SocialCredentials:
        pass
```

### Implementing a Platform Adapter

1. Create adapter class: `backend/adapters/social/twitter_adapter.py`
2. Inherit from `BaseSocialAdapter`
3. Implement all abstract methods
4. Register in `__init__.py`:
   ```python
   from .twitter_adapter import TwitterAdapter
   register_adapter(SocialPlatform.TWITTER, TwitterAdapter)
   ```

## Retry Logic

The scheduler implements intelligent retry logic:

- **Rate Limits**: Keep status as 'pending' to retry automatically
- **Transient Errors**: Retry with exponential backoff (future enhancement)
- **Content Errors**: Don't retry (mark as failed permanently)

## Future Enhancements

- [ ] Exponential backoff for rate limits
- [ ] Batch processing for high-volume users
- [ ] Platform-specific rate limit tracking
- [ ] Analytics fetching service
- [ ] Post performance notifications
- [ ] Advanced scheduling (optimal posting times)
- [ ] Multi-image/video support
- [ ] Thread/carousel posting
- [ ] Draft approval workflow

## Testing

Test the scheduler:

```python
# backend/tests/integration/test_scheduler.py
async def test_scheduler_processes_due_posts():
    # Create scheduled post
    post = ScheduledPost(
        user_id=user.id,
        content="Test post",
        scheduled_at=datetime.utcnow(),
        status=PostStatus.PENDING
    )

    # Create target
    target = PostTarget(
        post_id=post.id,
        account_id=account.id
    )

    # Run scheduler
    await scheduler_service.process_due_posts()

    # Verify
    assert post.status == PostStatus.POSTED
    assert target.status == PostTargetStatus.POSTED
```

## Monitoring

Monitor scheduler health:

- Check log output for errors
- Monitor post status distribution
- Track average time to publish
- Alert on high failure rates
- Monitor Redis queue depth (if enabled)

## Troubleshooting

### Posts not publishing

1. Check scheduler is running: Look for "Social scheduler started" in logs
2. Check post status: Should be 'pending' with `scheduled_at` in the past
3. Check social account tokens: Verify not expired and account active
4. Check adapter registration: Ensure platform adapter is registered
5. Check logs: Look for error messages with post ID

### Token refresh failures

1. Verify OAuth credentials in environment
2. Check account `refresh_token_encrypted` is not null
3. Verify platform refresh token endpoint
4. Check token expiry is set correctly

### Rate limit issues

1. Posts should remain in 'pending' status
2. Check error_message for rate limit details
3. Implement platform-specific backoff
4. Consider spreading posts across time

## Security

- OAuth tokens encrypted at rest using Fernet
- Tokens decrypted only in memory during publishing
- Token refresh updates encrypted storage
- All database access uses async sessions
- CSRF protection on OAuth callbacks
