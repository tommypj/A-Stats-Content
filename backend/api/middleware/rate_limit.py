"""
Rate limiting middleware using slowapi.

This module provides rate limiting functionality to protect against brute force attacks
and excessive API usage. It uses slowapi (a rate limiting library for FastAPI) with
in-memory storage for simplicity.

Key Features:
- Configurable rate limits per endpoint type
- Automatic 429 Too Many Requests responses
- IP-based rate limiting (can be extended to user-based)

Rate Limits:
- Login: 5 attempts per minute
- Registration: 3 attempts per minute
- Password Reset: 3 attempts per hour
- Email Verification: 5 attempts per hour
- Default: 100 requests per minute
"""

import ipaddress
import logging
import re

from starlette.requests import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

# Simple pattern to quickly reject obviously invalid IPs before parsing
_IP_LIKE = re.compile(r"^[\d.:a-fA-F]+$")


def _is_valid_ip(value: str) -> bool:
    """Return True if *value* looks like a valid IPv4 or IPv6 address."""
    if not _IP_LIKE.match(value):
        return False
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _is_private_ip(value: str) -> bool:
    """Return True if *value* is a private, loopback, or link-local address.

    RATE-LIMIT-02: Private IPs in X-Forwarded-For are untrustworthy — an attacker
    can spoof them to bypass rate limiting by setting X-Forwarded-For: 127.0.0.1.
    """
    try:
        addr = ipaddress.ip_address(value)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


def _get_real_ip(request: Request) -> str:
    """Extract real client IP from proxy headers, falling back to remote address.

    Railway (and most reverse proxies) set X-Forwarded-For.  Without this,
    all requests appear to come from the proxy's internal IP, which means
    every user shares a single rate-limit bucket.

    The extracted IP is validated to prevent header injection attacks where
    an attacker injects crafted values to bypass rate limiting.
    RATE-LIMIT-02: Private/loopback IPs from X-Forwarded-For are rejected and
    fall back to the actual connection IP to prevent spoofed bypass attempts.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For can be a comma-separated list; first entry is the client
        candidate = forwarded.split(",")[0].strip()
        if _is_valid_ip(candidate) and not _is_private_ip(candidate):
            return candidate
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        candidate = real_ip.strip()
        if _is_valid_ip(candidate) and not _is_private_ip(candidate):
            return candidate
    return get_remote_address(request)

# Rate limit configurations
# Format: "count/period" where period can be: second, minute, hour, day
RATE_LIMITS = {
    "login": "5/minute",
    "register": "3/minute",
    "password_reset": "3/hour",
    "email_verification": "5/hour",
    "resend_verification": "5/hour",
    "default": "100/minute",
}

# Create limiter instance with IP-based key function.
# Uses Redis when available, falls back to in-memory storage.
# default_limits applies the 100/minute cap globally to every route via
# SlowAPIMiddleware; per-endpoint @limiter.limit decorators (e.g. "5/minute"
# on /login) override this default for those specific endpoints.
_storage_uri = settings.redis_url if settings.redis_url else "memory://"

# RATE-LIMIT-01: Warn when falling back to in-memory storage — not safe in multi-worker prod
if not settings.redis_url:
    logger.warning(
        "Rate limiter using in-memory storage — not suitable for multi-worker production"
    )
    # INFRA-H2: In production, escalate to CRITICAL when Redis is unavailable for rate limiting
    if settings.environment == "production":
        logger.critical(
            "CRITICAL: Rate limiter cannot connect to Redis in production. "
            "Global rate limiting is NOT active. Set REDIS_URL in environment variables."
            # Uncomment to hard-fail on startup instead of warning:
            # raise RuntimeError("Redis required for production rate limiting")
        )

limiter = Limiter(
    key_func=_get_real_ip,
    storage_uri=_storage_uri,
    default_limits=[RATE_LIMITS["default"]],
)


def get_rate_limit(endpoint: str) -> str:
    """
    Get rate limit configuration for a specific endpoint.

    Args:
        endpoint: The endpoint identifier (e.g., "login", "register")

    Returns:
        str: Rate limit string in format "count/period"

    Example:
        >>> get_rate_limit("login")
        "5/minute"
        >>> get_rate_limit("unknown")
        "100/minute"
    """
    return RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
