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
import re

from starlette.requests import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from infrastructure.config.settings import settings

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


def _get_real_ip(request: Request) -> str:
    """Extract real client IP from proxy headers, falling back to remote address.

    Railway (and most reverse proxies) set X-Forwarded-For.  Without this,
    all requests appear to come from the proxy's internal IP, which means
    every user shares a single rate-limit bucket.

    The extracted IP is validated to prevent header injection attacks where
    an attacker injects crafted values to bypass rate limiting.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For can be a comma-separated list; first entry is the client
        candidate = forwarded.split(",")[0].strip()
        if _is_valid_ip(candidate):
            return candidate
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        candidate = real_ip.strip()
        if _is_valid_ip(candidate):
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
