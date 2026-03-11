"""JWT-based unsubscribe tokens for email journey emails."""

import logging
from datetime import UTC, datetime, timedelta

import jwt

from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

UNSUBSCRIBE_TOKEN_EXPIRY_DAYS = 30


def generate_unsubscribe_token(user_id: str, category: str) -> str:
    """Generate a JWT token for one-click unsubscribe."""
    settings = get_settings()
    payload = {
        "sub": user_id,
        "cat": category,
        "act": "unsubscribe",
        "exp": datetime.now(UTC) + timedelta(days=UNSUBSCRIBE_TOKEN_EXPIRY_DAYS),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_unsubscribe_token(token: str) -> dict | None:
    """Verify and decode an unsubscribe token.

    Returns {"user_id": ..., "category": ...} or None if invalid.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("act") != "unsubscribe":
            return None
        return {"user_id": payload["sub"], "category": payload["cat"]}
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        logger.warning("Invalid unsubscribe token")
        return None
