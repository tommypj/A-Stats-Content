"""
Shared API utility functions.
"""

from sqlalchemy import select
from sqlalchemy.sql import Select


def escape_like(value: str) -> str:
    """Escape LIKE wildcards for safe use in SQL LIKE/ILIKE patterns."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def scoped_query(model, item_id, user, *, extra_filters=None) -> Select:
    """Build an ownership-scoped SELECT query for a soft-deletable model.

    Uses project_id scoping if the user has a current project,
    otherwise falls back to user_id scoping.
    """
    if user.current_project_id:
        query = select(model).where(
            model.id == item_id,
            model.project_id == user.current_project_id,
            model.deleted_at.is_(None),
        )
    else:
        query = select(model).where(
            model.id == item_id,
            model.user_id == user.id,
            model.deleted_at.is_(None),
        )
    if extra_filters:
        for f in extra_filters:
            query = query.where(f)
    return query
