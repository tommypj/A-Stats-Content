"""
Shared OAuth state helpers for CSRF protection.

Used by any OAuth flow (social, GSC, etc.) to store and verify the `state`
parameter, preventing CSRF attacks on OAuth callbacks.

Redis is used as the primary store (10-minute TTL). If Redis is unreachable,
an in-memory dict is used as a fallback so that single-process development
environments continue to work.
"""

import asyncio
import json
import logging
import time
from typing import Optional

from fastapi import HTTPException, status

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

# OAuth state TTL (10 minutes)
_OAUTH_STATE_TTL = 600
_OAUTH_MAX_STATES = 1000  # Max in-memory entries before pruning

# In-memory fallback for OAuth state (used only when Redis is unavailable)
_oauth_states: dict[str, dict] = {}
_oauth_states_lock = asyncio.Lock()


def _prune_expired_states() -> None:
    """Remove expired entries from the in-memory state dict.

    Must be called while holding ``_oauth_states_lock``.
    """
    now = time.time()
    expired = [k for k, v in _oauth_states.items() if now - v["created_at"] > _OAUTH_STATE_TTL]
    for k in expired:
        del _oauth_states[k]


async def store_oauth_state(state: str, user_id: str) -> None:
    """Store OAuth state in Redis with a 10-minute TTL.

    Falls back to an in-memory dict when Redis is not reachable so that
    single-process development environments continue to work.
    """
    data = json.dumps({"user_id": str(user_id)})
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.setex(f"oauth_state:{state}", _OAUTH_STATE_TTL, data)
        await r.aclose()
    except (ImportError, OSError, ConnectionError, TypeError, ValueError):
        # Redis unavailable or misconfigured — prune expired entries and enforce size cap
        async with _oauth_states_lock:
            _prune_expired_states()
            if len(_oauth_states) >= _OAUTH_MAX_STATES:
                # Drop oldest entries to make room
                oldest = sorted(_oauth_states, key=lambda k: _oauth_states[k]["created_at"])
                for k in oldest[:len(_oauth_states) - _OAUTH_MAX_STATES + 1]:
                    del _oauth_states[k]
            _oauth_states[state] = {"user_id": str(user_id), "created_at": time.time()}


async def verify_oauth_state(state: str) -> Optional[str]:
    """Verify and consume an OAuth state. Returns user_id or None.

    Attempts Redis first; falls back to the in-memory dict when Redis is
    not reachable.
    """
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        raw = await r.getdel(f"oauth_state:{state}")
        await r.aclose()
        if raw is None:
            return None
        parsed = json.loads(raw)
        return parsed.get("user_id")
    except (ImportError, OSError, ConnectionError, TypeError, ValueError, json.JSONDecodeError, KeyError):
        # Redis unavailable or misconfigured — fallback to in-memory pop with expiry check
        async with _oauth_states_lock:
            entry = _oauth_states.pop(state, None)
        if not entry:
            return None
        if time.time() - entry["created_at"] > _OAUTH_STATE_TTL:
            return None
        return entry["user_id"]


async def require_valid_oauth_state(state: str) -> str:
    """Verify OAuth state and raise 403 if invalid or expired.

    Returns the associated user_id on success.
    """
    user_id = await verify_oauth_state(state)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired OAuth state parameter",
        )
    return user_id
