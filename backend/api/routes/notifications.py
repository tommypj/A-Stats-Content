"""User notification API routes."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db
from infrastructure.database.models import User
from services.task_queue import task_queue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/generation-status")
async def get_generation_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check for recently completed or failed generations (last 5 minutes).

    Returns a flat list of notification objects for articles, outlines, and
    images that transitioned to 'completed' or 'failed' within the past 5
    minutes.  The list is sorted by updated_at descending and capped at 10
    entries.
    """
    from infrastructure.database.models import Article, Outline, GeneratedImage
    from infrastructure.database.models.content import ContentStatus

    five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)

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
            Article.updated_at >= five_min_ago,
        )
        .order_by(Article.updated_at.desc())
        .limit(10)
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
            Outline.updated_at >= five_min_ago,
        )
        .order_by(Outline.updated_at.desc())
        .limit(10)
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
            GeneratedImage.updated_at >= five_min_ago,
        )
        .order_by(GeneratedImage.updated_at.desc())
        .limit(10)
    )

    notifications = []

    for row in articles_result.all():
        ts = row.updated_at
        if ts is not None and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
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
            ts = ts.replace(tzinfo=timezone.utc)
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
            ts = ts.replace(tzinfo=timezone.utc)
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

    # Sort all notifications by timestamp descending
    notifications.sort(
        key=lambda x: x["timestamp"] or "",
        reverse=True,
    )

    return {"notifications": notifications[:10]}


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
