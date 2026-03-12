"""Centralized Redis connection pool.

Provides two shared pools:
- get_redis()       → raw bytes (decode_responses=False) — for token ops, webhooks, etc.
- get_redis_text()  → decoded strings (decode_responses=True) — for caching, pub/sub, keyword research

Both are lazy-initialized singletons reusing the same underlying TCP connection pool,
replacing the 20+ inline aioredis.from_url() calls that previously created a new
connection per request.
"""

import logging
from typing import Optional

import redis.asyncio as aioredis

from infrastructure.config import get_settings

logger = logging.getLogger(__name__)

_pool: Optional[aioredis.Redis] = None
_pool_text: Optional[aioredis.Redis] = None


def redis_key(key: str) -> str:
    """Prefix a Redis key with the environment namespace.

    All Redis keys should use this helper to prevent collisions when
    multiple environments (dev, staging, prod) share the same Redis instance.
    """
    settings = get_settings()
    return f"{settings.redis_key_prefix}:{key}"


async def get_redis() -> Optional[aioredis.Redis]:
    """Get or create a shared Redis connection pool (decode_responses=False)."""
    global _pool
    settings = get_settings()
    if not settings.redis_url:
        return None
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            socket_timeout=5,
            socket_connect_timeout=5,
            decode_responses=False,
            max_connections=20,
        )
    return _pool


async def get_redis_text() -> Optional[aioredis.Redis]:
    """Get or create a shared Redis connection pool (decode_responses=True).

    Use this variant for caching, pub/sub, and keyword research where
    string values are expected.
    """
    global _pool_text
    settings = get_settings()
    if not settings.redis_url:
        return None
    if _pool_text is None:
        _pool_text = aioredis.from_url(
            settings.redis_url,
            socket_timeout=5,
            socket_connect_timeout=5,
            decode_responses=True,
            max_connections=20,
        )
    return _pool_text


async def close_redis() -> None:
    """Close all shared Redis pools on shutdown."""
    global _pool, _pool_text
    if _pool is not None:
        try:
            await _pool.aclose()
        except Exception:
            pass
        _pool = None
    if _pool_text is not None:
        try:
            await _pool_text.aclose()
        except Exception:
            pass
        _pool_text = None
