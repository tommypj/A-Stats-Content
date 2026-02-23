"""
Post Queue Manager using Redis.

Provides Redis-based queue management for more reliable scheduling.
Falls back to database polling if Redis is unavailable.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from infrastructure.config import settings

logger = logging.getLogger(__name__)


class PostQueueManager:
    """
    Manages post scheduling queue using Redis Sorted Sets.

    Uses Redis ZSET with timestamp as score for efficient time-based queries.
    Falls back gracefully if Redis is not available.
    """

    QUEUE_KEY = "social:post_queue"
    SCHEDULED_SET = "social:scheduled_posts"
    PROCESSING_SET = "social:processing_posts"

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self):
        """
        Connect to Redis.

        Attempts to establish Redis connection. If connection fails,
        the service will fall back to database polling.
        """
        if not REDIS_AVAILABLE:
            logger.warning(
                "redis.asyncio is not available. "
                "Install with: pip install redis[asyncio]"
            )
            return

        try:
            self.redis = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )

            # Test connection
            await self.redis.ping()
            self._connected = True
            logger.info("Redis connection established for post queue")

        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Falling back to database polling.")
            self.redis = None
            self._connected = False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("Redis connection closed")

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected and self.redis is not None

    async def schedule_post(self, post_id: str, scheduled_at: datetime) -> bool:
        """
        Add post to scheduled set with score = timestamp.

        Args:
            post_id: UUID of the scheduled post
            scheduled_at: When the post should be published

        Returns:
            True if successfully scheduled, False otherwise
        """
        if not self.is_connected:
            logger.debug("Redis not connected, skipping queue scheduling")
            return False

        try:
            score = scheduled_at.timestamp()
            result = await self.redis.zadd(self.SCHEDULED_SET, {post_id: score})
            logger.debug(f"Scheduled post {post_id} for {scheduled_at} (score: {score})")
            return result > 0

        except Exception as e:
            logger.error(f"Failed to schedule post in Redis: {e}")
            return False

    async def get_due_posts(self, limit: int = 100) -> List[str]:
        """
        Get posts that are due for publishing.

        Args:
            limit: Maximum number of posts to retrieve

        Returns:
            List of post IDs that are due
        """
        if not self.is_connected:
            return []

        try:
            now = datetime.now(timezone.utc).timestamp()

            # Get posts with score <= now (sorted by timestamp)
            posts = await self.redis.zrangebyscore(
                self.SCHEDULED_SET,
                min="-inf",
                max=now,
                start=0,
                num=limit,
            )

            if posts:
                logger.debug(f"Found {len(posts)} due posts in Redis queue")

            return posts

        except Exception as e:
            logger.error(f"Failed to get due posts from Redis: {e}")
            return []

    async def mark_processing(self, post_id: str) -> bool:
        """
        Move post from scheduled to processing set.

        Args:
            post_id: UUID of the post being processed

        Returns:
            True if successfully moved, False otherwise
        """
        if not self.is_connected:
            return False

        try:
            # Use pipeline for atomic operation
            async with self.redis.pipeline() as pipe:
                await pipe.zrem(self.SCHEDULED_SET, post_id)
                await pipe.sadd(self.PROCESSING_SET, post_id)
                await pipe.execute()

            logger.debug(f"Marked post {post_id} as processing")
            return True

        except Exception as e:
            logger.error(f"Failed to mark post as processing: {e}")
            return False

    async def mark_published(self, post_id: str) -> bool:
        """
        Remove post from all sets after successful publication.

        Args:
            post_id: UUID of the published post

        Returns:
            True if successfully removed, False otherwise
        """
        if not self.is_connected:
            return False

        try:
            # Remove from both sets
            async with self.redis.pipeline() as pipe:
                await pipe.zrem(self.SCHEDULED_SET, post_id)
                await pipe.srem(self.PROCESSING_SET, post_id)
                await pipe.execute()

            logger.debug(f"Removed post {post_id} from queue (published)")
            return True

        except Exception as e:
            logger.error(f"Failed to mark post as published: {e}")
            return False

    async def cancel_post(self, post_id: str) -> bool:
        """
        Cancel a scheduled post by removing it from the queue.

        Args:
            post_id: UUID of the post to cancel

        Returns:
            True if successfully cancelled, False otherwise
        """
        if not self.is_connected:
            return False

        try:
            removed = await self.redis.zrem(self.SCHEDULED_SET, post_id)
            if removed:
                logger.info(f"Cancelled scheduled post {post_id}")
            return removed > 0

        except Exception as e:
            logger.error(f"Failed to cancel post: {e}")
            return False

    async def reschedule_post(self, post_id: str, new_time: datetime) -> bool:
        """
        Update schedule time for a post.

        Args:
            post_id: UUID of the post
            new_time: New scheduled time

        Returns:
            True if successfully rescheduled, False otherwise
        """
        if not self.is_connected:
            return False

        try:
            score = new_time.timestamp()
            # ZADD with XX flag updates existing member
            result = await self.redis.zadd(
                self.SCHEDULED_SET,
                {post_id: score},
                xx=True,  # Only update existing members
            )

            if result > 0:
                logger.info(f"Rescheduled post {post_id} to {new_time}")
                return True
            else:
                # Post not in set, add it
                await self.schedule_post(post_id, new_time)
                return True

        except Exception as e:
            logger.error(f"Failed to reschedule post: {e}")
            return False

    async def get_scheduled_count(self) -> int:
        """
        Get count of scheduled posts in queue.

        Returns:
            Number of posts in scheduled set
        """
        if not self.is_connected:
            return 0

        try:
            count = await self.redis.zcard(self.SCHEDULED_SET)
            return count

        except Exception as e:
            logger.error(f"Failed to get scheduled count: {e}")
            return 0

    async def get_processing_count(self) -> int:
        """
        Get count of posts currently being processed.

        Returns:
            Number of posts in processing set
        """
        if not self.is_connected:
            return 0

        try:
            count = await self.redis.scard(self.PROCESSING_SET)
            return count

        except Exception as e:
            logger.error(f"Failed to get processing count: {e}")
            return 0

    async def recover_stale_posts(self, max_age_minutes: int = 30) -> int:
        """
        Move stale posts from processing back to scheduled.

        Args:
            max_age_minutes: Maximum age before considering a post stale

        Returns:
            Number of posts recovered
        """
        if not self.is_connected:
            return 0

        try:
            # Get all processing posts
            processing_posts = await self.redis.smembers(self.PROCESSING_SET)

            if not processing_posts:
                return 0

            # For each post, check if it's stale and recover
            # (In production, you'd store processing start time in a hash)
            recovered = 0
            for post_id in processing_posts:
                # Simple recovery: move back to scheduled with current time
                # A more sophisticated approach would check actual processing time
                await self.redis.srem(self.PROCESSING_SET, post_id)
                await self.schedule_post(post_id, datetime.now(timezone.utc))
                recovered += 1

            if recovered > 0:
                logger.warning(f"Recovered {recovered} stale posts from processing set")

            return recovered

        except Exception as e:
            logger.error(f"Failed to recover stale posts: {e}")
            return 0


# Singleton instance
post_queue = PostQueueManager()
