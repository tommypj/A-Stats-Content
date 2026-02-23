"""
Shared API utility functions.
"""


def escape_like(value: str) -> str:
    """Escape LIKE wildcards for safe use in SQL LIKE/ILIKE patterns."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
