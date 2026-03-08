"""User notification API routes."""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user
from api.schemas.notification_preferences import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
)
from infrastructure.database.connection import get_db
from infrastructure.database.models import NotificationPreferences, User
from services.task_queue import task_queue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/generation-status")
async def get_generation_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 10,
    hours: int = 24,
):
    """Check for recently completed or failed generations.

    Returns a flat list of notification objects for articles, outlines, and
    images that transitioned to 'completed' or 'failed' within the past
    ``hours`` hours (default 24).  The list is sorted by updated_at descending
    and paginated with ``page``/``page_size`` parameters.
    """
    from infrastructure.database.models import Article, GeneratedImage, Outline
    from infrastructure.database.models.content import ContentStatus

    # Clamp inputs
    hours = max(1, min(hours, 168))  # 1 hour to 7 days
    page = max(1, page)
    page_size = max(1, min(page_size, 50))

    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    # Articles that completed / failed recently
    articles_result = await db.execute(
        select(
            Article.id,
            Article.title,
            Article.status,
            Article.updated_at,
        )
        .where(
            Article.user_id == current_user.id,
            Article.status.in_([ContentStatus.COMPLETED.value, ContentStatus.FAILED.value]),
            Article.updated_at >= cutoff,
        )
        .order_by(Article.updated_at.desc())
        .limit(page_size * page + 1)  # +1 to detect has_more
    )

    # Outlines that completed / failed recently
    outlines_result = await db.execute(
        select(
            Outline.id,
            Outline.title,
            Outline.status,
            Outline.updated_at,
        )
        .where(
            Outline.user_id == current_user.id,
            Outline.status.in_([ContentStatus.COMPLETED.value, ContentStatus.FAILED.value]),
            Outline.updated_at >= cutoff,
        )
        .order_by(Outline.updated_at.desc())
        .limit(page_size * page + 1)
    )

    # Images that completed / failed recently
    images_result = await db.execute(
        select(
            GeneratedImage.id,
            GeneratedImage.prompt,
            GeneratedImage.status,
            GeneratedImage.updated_at,
        )
        .where(
            GeneratedImage.user_id == current_user.id,
            GeneratedImage.status.in_([ContentStatus.COMPLETED.value, ContentStatus.FAILED.value]),
            GeneratedImage.updated_at >= cutoff,
        )
        .order_by(GeneratedImage.updated_at.desc())
        .limit(page_size * page + 1)
    )

    notifications = []

    for row in articles_result.all():
        ts = row.updated_at
        if ts is not None and ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        notifications.append(
            {
                "id": f"article-{row.id}",
                "type": "article",
                "resource_id": str(row.id),
                "title": row.title or "Untitled article",
                "status": row.status,
                "timestamp": ts.isoformat() if ts else None,
            }
        )

    for row in outlines_result.all():
        ts = row.updated_at
        if ts is not None and ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        notifications.append(
            {
                "id": f"outline-{row.id}",
                "type": "outline",
                "resource_id": str(row.id),
                "title": row.title or "Untitled outline",
                "status": row.status,
                "timestamp": ts.isoformat() if ts else None,
            }
        )

    for row in images_result.all():
        ts = row.updated_at
        if ts is not None and ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        # Use a truncated prompt as the display title (max 60 chars)
        prompt_preview = (row.prompt or "Image")[:60]
        if len(row.prompt or "") > 60:
            prompt_preview += "..."
        notifications.append(
            {
                "id": f"image-{row.id}",
                "type": "image",
                "resource_id": str(row.id),
                "title": prompt_preview,
                "status": row.status,
                "timestamp": ts.isoformat() if ts else None,
            }
        )

    # Sort all notifications by timestamp descending, then paginate
    notifications.sort(
        key=lambda x: x["timestamp"] or "",
        reverse=True,
    )

    total = len(notifications)
    offset = (page - 1) * page_size
    page_items = notifications[offset : offset + page_size]
    has_more = total > page * page_size

    return {
        "notifications": page_items,
        "total": min(total, page_size * page),  # total seen so far
        "page": page,
        "page_size": page_size,
        "has_more": has_more,
    }


@router.get("/tasks/{task_id}/status", tags=["Tasks"])
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Return the current status of a background task.

    Status values: running | completed | failed

    This endpoint is intentionally generic — it works for any task enqueued
    through the in-memory TaskQueue (article generation, image generation, etc.).
    The resource-specific DB record (Article / GeneratedImage) is the source of
    truth for the *final* result; this endpoint gives a fast in-memory snapshot
    that is useful before the DB record is committed.
    """
    info = task_queue.get_status(task_id)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or has expired",
        )
    return info


# ---------------------------------------------------------------------------
# Notification Preferences
# ---------------------------------------------------------------------------


async def _get_or_create_preferences(
    db: AsyncSession, user_id: str
) -> NotificationPreferences:
    """Return existing preferences or create defaults."""
    result = await db.execute(
        select(NotificationPreferences).where(
            NotificationPreferences.user_id == user_id
        )
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        prefs = NotificationPreferences(user_id=user_id)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's notification preferences."""
    prefs = await _get_or_create_preferences(db, current_user.id)
    return prefs


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    body: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's notification preferences.

    Only fields present in the request body are updated; omitted fields
    keep their current values.
    """
    prefs = await _get_or_create_preferences(db, current_user.id)

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(prefs, field, value)

    await db.commit()
    await db.refresh(prefs)
    return prefs
