"""
API dependencies for authentication and authorization.

NOTE: get_current_admin_user has been consolidated into api/deps_admin.py.
All admin routes should import from there.
"""

from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status

from infrastructure.database.models.user import User

# Tier hierarchy (index = rank)
TIER_ORDER = ["free", "starter", "professional", "enterprise"]


def get_effective_tier(user: User) -> str:
    """Resolve the user's effective subscription tier, falling back to free."""
    tier = user.subscription_tier or "free"
    if user.subscription_expires and user.subscription_expires < datetime.now(UTC):
        tier = "free"
    return tier


def _check_tier(user: User, minimum_tier: str) -> None:
    """Raise 403 if the user's tier is below minimum_tier."""
    min_rank = TIER_ORDER.index(minimum_tier)
    tier = get_effective_tier(user)
    rank = TIER_ORDER.index(tier) if tier in TIER_ORDER else 0
    if rank < min_rank:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This feature requires the {minimum_tier.title()} plan or higher. "
            f"You are currently on the {tier.title()} plan.",
        )


def require_tier(minimum_tier: str):
    """
    Returns a callable that checks the user's subscription tier.

    Usage — call directly inside a route function body:

        require_tier("starter")(current_user)
    """
    def _check(user: User) -> None:
        _check_tier(user, minimum_tier)
    return _check
