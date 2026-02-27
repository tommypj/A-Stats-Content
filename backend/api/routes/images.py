"""
Image generation and management API routes.
"""

import asyncio
import logging
import math
import time
from typing import Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from api.middleware.rate_limit import limiter
from sqlalchemy import select, func, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.content import (
    ImageGenerateRequest,
    ImageSetFeaturedRequest,
    ImageResponse,
    ImageListResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
)
from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db, async_session_maker
from infrastructure.database.models import GeneratedImage, Article, User, ContentStatus
from adapters.ai.replicate_adapter import image_ai_service
from adapters.storage.image_storage import storage_adapter, download_image
from services.generation_tracker import GenerationTracker
from services.task_queue import task_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

# Limit concurrent AI image generation tasks to prevent resource exhaustion
_image_generation_semaphore = asyncio.Semaphore(3)


# ---------------------------------------------------------------------------
# Background image generation helpers
# ---------------------------------------------------------------------------

async def _run_image_generation(
    image_id: str,
    user_id: str,
    project_id: Optional[str],
    prompt: str,
    style: Optional[str],
    width: Optional[int],
    height: Optional[int],
) -> None:
    """
    Inner implementation of background image generation.

    Opens its own DB session so it can safely run outside the request
    context (mirrors the article generation pattern).
    """
    start_time = time.time()

    async with async_session_maker() as db:
        gen_log = None
        tracker = GenerationTracker(db)

        try:
            # Fetch the image record that was pre-created by the endpoint
            result = await db.execute(
                select(GeneratedImage).where(GeneratedImage.id == image_id)
            )
            image = result.scalar_one_or_none()
            if not image:
                logger.error("Background image generation: record %s not found", image_id)
                return

            # Log generation start
            gen_log = await tracker.log_start(
                user_id=user_id,
                project_id=project_id,
                resource_type="image",
                resource_id=image_id,
                input_metadata={
                    "prompt": prompt,
                    "style": style,
                    "width": width,
                    "height": height,
                },
            )
            await db.commit()

            # Call the AI service (Replicate)
            generated = await asyncio.wait_for(
                image_ai_service.generate_image(
                    prompt=prompt,
                    width=width,
                    height=height,
                    style=style,
                ),
                timeout=120.0,  # 2-minute hard limit
            )

            # Store the external URL immediately
            image.url = generated.url
            image.alt_text = f"AI-generated image: {prompt[:100]}"
            image.model = generated.model if hasattr(generated, "model") else None
            image.status = "completed"

            duration_ms = int((time.time() - start_time) * 1000)
            await tracker.log_success(
                log_id=gen_log.id,
                ai_model=getattr(generated, "model", None),
                duration_ms=duration_ms,
            )
            await db.commit()

            # Try to download and cache locally (non-critical — external URL is the fallback)
            try:
                image_data = await download_image(generated.url)
                filename = f"image_{image_id}.jpg"
                local_path = await storage_adapter.save_image(
                    image_data=image_data,
                    filename=filename,
                )
                try:
                    image.local_path = local_path
                    await db.commit()
                except Exception:
                    # DB commit failed — delete the saved file to prevent orphan
                    try:
                        await storage_adapter.delete_image(local_path)
                    except Exception as cleanup_err:
                        logger.error(
                            "Failed to cleanup orphaned image file %s: %s", local_path, cleanup_err
                        )
                    raise
            except (httpx.HTTPError, OSError, ValueError) as dl_err:
                logger.warning(
                    "Failed to cache image locally for %s: %s", image_id, dl_err
                )

            logger.info("Image %s generated successfully", image_id)

        except Exception as e:
            logger.error(
                "Background image generation failed for %s: %s", image_id, e, exc_info=True
            )
            # Use a fresh session to mark as failed (original session may be broken)
            try:
                async with async_session_maker() as err_db:
                    err_result = await err_db.execute(
                        select(GeneratedImage).where(GeneratedImage.id == image_id)
                    )
                    failed_image = err_result.scalar_one_or_none()
                    if failed_image:
                        failed_image.status = "failed"
                        await err_db.commit()
            except (OSError, SQLAlchemyError) as mark_err:
                logger.error(
                    "Failed to mark image %s as failed: %s", image_id, mark_err, exc_info=True
                )

            # Log failure in a separate session
            if gen_log is not None:
                duration_ms = int((time.time() - start_time) * 1000)
                try:
                    async with async_session_maker() as tracker_db:
                        failure_tracker = GenerationTracker(tracker_db)
                        await failure_tracker.log_failure(
                            log_id=gen_log.id,
                            error_message=str(e),
                            duration_ms=duration_ms,
                        )
                        await tracker_db.commit()
                except (OSError, SQLAlchemyError) as log_err:
                    logger.error(
                        "Failed to log image generation failure for %s", image_id, exc_info=True
                    )


async def _generate_image_background(
    image_id: str,
    user_id: str,
    project_id: Optional[str],
    prompt: str,
    style: Optional[str],
    width: Optional[int],
    height: Optional[int],
) -> None:
    """Background task wrapper that acquires the semaphore before calling the inner impl."""
    async with _image_generation_semaphore:
        await _run_image_generation(
            image_id=image_id,
            user_id=user_id,
            project_id=project_id,
            prompt=prompt,
            style=style,
            width=width,
            height=height,
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=ImageResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def generate_image(
    request: Request,
    body: ImageGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enqueue an AI image generation job.

    Returns HTTP 202 immediately with a record in *generating* status.
    The actual Replicate call runs as a background asyncio task.
    Poll GET /images/{id} (status field) or GET /notifications/tasks/{task_id}/status
    to track progress.  The notification bell will also pick up completion.
    """
    # Validate article_id if provided
    if body.article_id:
        result = await db.execute(
            select(Article).where(
                Article.id == body.article_id,
                Article.user_id == current_user.id,
            )
        )
        article = result.scalar_one_or_none()
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found",
            )

    # Check usage limit before creating any records
    project_id = getattr(current_user, "current_project_id", None)
    tracker = GenerationTracker(db)
    if not await tracker.check_limit(project_id, "image", user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly image generation limit reached. Please upgrade your plan.",
        )

    # Create image record in generating status
    image_id = str(uuid4())
    image = GeneratedImage(
        id=image_id,
        user_id=current_user.id,
        project_id=project_id,
        article_id=body.article_id,
        prompt=body.prompt,
        style=body.style,
        width=body.width,
        height=body.height,
        status="generating",
        url="",  # Will be updated when the background task completes
    )

    db.add(image)
    await db.commit()
    await db.refresh(image)

    # Enqueue background generation (non-blocking)
    await task_queue.enqueue(
        image_id,
        _generate_image_background(
            image_id=image_id,
            user_id=current_user.id,
            project_id=project_id,
            prompt=body.prompt,
            style=body.style,
            width=body.width,
            height=body.height,
        ),
    )

    return image


@router.get("", response_model=ImageListResponse)
async def list_images(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    article_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List user's images with pagination and optional filtering.
    """
    # Base query
    if current_user.current_project_id:
        query = select(GeneratedImage).where(GeneratedImage.project_id == current_user.current_project_id)
    else:
        query = select(GeneratedImage).where(
            GeneratedImage.user_id == current_user.id,
            GeneratedImage.project_id.is_(None),
        )

    # Apply filters
    if article_id:
        query = query.where(GeneratedImage.article_id == article_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Apply pagination
    query = query.order_by(GeneratedImage.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    images = result.scalars().all()

    return ImageListResponse(
        items=images,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_images(
    body: BulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete multiple images in a single request.

    All supplied IDs must belong to the current user's active project scope.
    Only images that pass the ownership check are deleted; IDs that do not
    exist or belong to a different project are silently ignored.
    Returns the number of rows actually deleted.

    Note: local file cleanup is skipped for bulk operations to keep the
    response fast.  Orphaned local files will be cleaned up by the
    periodic storage maintenance task.
    """
    if not body.ids:
        return BulkDeleteResponse(deleted=0)

    if current_user.current_project_id:
        stmt = (
            delete(GeneratedImage)
            .where(
                GeneratedImage.id.in_(body.ids),
                GeneratedImage.project_id == current_user.current_project_id,
            )
        )
    else:
        stmt = (
            delete(GeneratedImage)
            .where(
                GeneratedImage.id.in_(body.ids),
                GeneratedImage.user_id == current_user.id,
                GeneratedImage.project_id.is_(None),
            )
        )

    result = await db.execute(stmt)
    await db.commit()

    return BulkDeleteResponse(deleted=result.rowcount)


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific image by ID.
    """
    if current_user.current_project_id:
        query = select(GeneratedImage).where(
            GeneratedImage.id == image_id,
            GeneratedImage.project_id == current_user.current_project_id,
        )
    else:
        query = select(GeneratedImage).where(
            GeneratedImage.id == image_id,
            GeneratedImage.user_id == current_user.id,
        )
    result = await db.execute(query)
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    return image


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an image and its associated files from storage.
    """
    if current_user.current_project_id:
        query = select(GeneratedImage).where(
            GeneratedImage.id == image_id,
            GeneratedImage.project_id == current_user.current_project_id,
        )
    else:
        query = select(GeneratedImage).where(
            GeneratedImage.id == image_id,
            GeneratedImage.user_id == current_user.id,
        )
    result = await db.execute(query)
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Delete from storage if local path exists — IMG-05: fail the request if deletion fails.
    if image.local_path:
        try:
            await storage_adapter.delete_image(image.local_path)
        except Exception as del_err:
            logger.error("Failed to delete local image file %s: %s", image.local_path, del_err)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete image file from storage. Image record not deleted.",
            )

    # Delete from database
    await db.delete(image)
    await db.commit()


@router.post("/{image_id}/set-featured", response_model=ImageResponse)
async def set_featured_image(
    image_id: str,
    request: ImageSetFeaturedRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Set an image as the featured image for an article.
    """
    # Verify image exists and belongs to user or project
    if current_user.current_project_id:
        image_query = select(GeneratedImage).where(
            GeneratedImage.id == image_id,
            GeneratedImage.project_id == current_user.current_project_id,
        )
    else:
        image_query = select(GeneratedImage).where(
            GeneratedImage.id == image_id,
            GeneratedImage.user_id == current_user.id,
        )
    image_result = await db.execute(image_query)
    image = image_result.scalar_one_or_none()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Verify article exists and belongs to user or project
    if current_user.current_project_id:
        article_query = select(Article).where(
            Article.id == request.article_id,
            Article.project_id == current_user.current_project_id,
        )
    else:
        article_query = select(Article).where(
            Article.id == request.article_id,
            Article.user_id == current_user.id,
        )
    article_result = await db.execute(article_query)
    article = article_result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found",
        )

    # Update article's featured image
    article.featured_image_id = image_id

    # If image doesn't have article_id set, set it
    if not image.article_id:
        image.article_id = request.article_id

    await db.commit()
    await db.refresh(image)

    return image
