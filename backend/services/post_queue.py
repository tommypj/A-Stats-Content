"""
Post Queue Manager using Redis.

Provides Redis-based queue management for more reliable scheduling.
Falls back to database polling if Redis is unavailable.
Uses the centralized Redis pool from infrastructure/redis.py.
"""

import logging
from datetime import UTC, datetime

from infrastructure.redis import get_redis_text, redis_key

logger = logging.getLogger(__name__)


class PostQueueManager:
    """
    Manages post scheduling queue using Redis Sorted Sets.

    Uses Redis ZSET with timestamp as score for efficient time-based queries.
    Falls back gracefully if Redis is not available.
    """

    @property
    def QUEUE_KEY(self) -> str:
        return redis_key("social:post_queue")

    @property
    def SCHEDULED_SET(self) -> str:
        return redis_key("social:scheduled_posts")

    @property
    def PROCESSING_SET(self) -> str:
        return redis_key("social:processing_posts")

    async def _get_redis(self):
        """Get a Redis connection from the centralized pool."""
        return await get_redis_text()

    @property
    def is_connected(self) -> bool:
        """Check if Redis is likely available (always True; actual check is per-call)."""
        return True

    async def connect(self):
        """Verify Redis connectivity via the centralized pool."""
        try:
            r = await self._get_redis()
            if r is None:
                logger.warning("Redis not configured. Post queue falling back to database polling.")
                return
            await r.ping()
            logger.info("Redis connection verified for post queue (centralized pool)")
        except Exception as e:
            logger.warning("Redis not reachable for post queue: %s. Falling back to database polling.", e)

    async def disconnect(self):
        """No-op — connection lifecycle managed by centralized pool."""
        pass

    async def schedule_post(self, post_id: str, scheduled_at: datetime) -> bool:
        """Add post to scheduled set with score = timestamp."""
        try:
            r = await self._get_redis()
            if r is None:
                return False
            score = scheduled_at.timestamp()
            result = await r.zadd(self.SCHEDULED_SET, {post_id: score})
            logger.debug("Scheduled post %s for %s (score: %s)", post_id, scheduled_at, score)
            return result > 0
        except Exception as e:
            logger.error("Failed to schedule post in Redis: %s", e)
            return False

    async def get_due_posts(self, limit: int = 100) -> list[str]:
        """Get posts that are due for publishing."""
        try:
            r = await self._get_redis()
            if r is None:
                return []
            now = datetime.now(UTC).timestamp()
            posts = await r.zrangebyscore(
                self.SCHEDULED_SET,
                min="-inf",
                max=now,
                start=0,
                num=limit,
            )
            if posts:
                logger.debug("Found %d due posts in Redis queue", len(posts))
            return posts
        except Exception as e:
            logger.error("Failed to get due posts from Redis: %s", e)
            return []

    async def mark_processing(self, post_id: str) -> bool:
        """Move post from scheduled to processing set."""
        try:
            r = await self._get_redis()
            if r is None:
                return False
            async with r.pipeline() as pipe:
                await pipe.zrem(self.SCHEDULED_SET, post_id)
                await pipe.sadd(self.PROCESSING_SET, post_id)
                await pipe.execute()
            logger.debug("Marked post %s as processing", post_id)
            return True
        except Exception as e:
            logger.error("Failed to mark post as processing: %s", e)
            return False

    async def mark_published(self, post_id: str) -> bool:
        """Remove post from all sets after successful publication."""
        try:
            r = await self._get_redis()
            if r is None:
                return False
            async with r.pipeline() as pipe:
                await pipe.zrem(self.SCHEDULED_SET, post_id)
                await pipe.srem(self.PROCESSING_SET, post_id)
                await pipe.execute()
            logger.debug("Removed post %s from queue (published)", post_id)
            return True
        except Exception as e:
            logger.error("Failed to mark post as published: %s", e)
            return False

    async def cancel_post(self, post_id: str) -> bool:
        """Cancel a scheduled post by removing it from the queue."""
        try:
            r = await self._get_redis()
            if r is None:
                return False
            removed = await r.zrem(self.SCHEDULED_SET, post_id)
            if removed:
                logger.info("Cancelled scheduled post %s", post_id)
            return removed > 0
        except Exception as e:
            logger.error("Failed to cancel post: %s", e)
            return False

    async def reschedule_post(self, post_id: str, new_time: datetime) -> bool:
        """Update schedule time for a post."""
        try:
            r = await self._get_redis()
            if r is None:
                return False
            score = new_time.timestamp()
            result = await r.zadd(
                self.SCHEDULED_SET,
                {post_id: score},
                xx=True,
            )
            if result > 0:
                logger.info("Rescheduled post %s to %s", post_id, new_time)
                return True
            else:
                await self.schedule_post(post_id, new_time)
                return True
        except Exception as e:
            logger.error("Failed to reschedule post: %s", e)
            return False

    async def get_scheduled_count(self) -> int:
        """Get count of scheduled posts in queue."""
        try:
            r = await self._get_redis()
            if r is None:
                return 0
            return await r.zcard(self.SCHEDULED_SET)
        except Exception as e:
            logger.error("Failed to get scheduled count: %s", e)
            return 0

    async def get_processing_count(self) -> int:
        """Get count of posts currently being processed."""
        try:
            r = await self._get_redis()
            if r is None:
                return 0
            return await r.scard(self.PROCESSING_SET)
        except Exception as e:
            logger.error("Failed to get processing count: %s", e)
            return 0

    async def recover_stale_posts(self, max_age_minutes: int = 30) -> int:
        """Move stale posts from processing back to scheduled."""
        try:
            r = await self._get_redis()
            if r is None:
                return 0
            processing_posts = await r.smembers(self.PROCESSING_SET)
            if not processing_posts:
                return 0
            recovered = 0
            for post_id in processing_posts:
                await r.srem(self.PROCESSING_SET, post_id)
                await self.schedule_post(post_id, datetime.now(UTC))
                recovered += 1
            if recovered > 0:
                logger.warning("Recovered %d stale posts from processing set", recovered)
            return recovered
        except Exception as e:
            logger.error("Failed to recover stale posts: %s", e)
            return 0


# Singleton instance
post_queue = PostQueueManager()
