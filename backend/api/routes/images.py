"""
Image generation and management API routes.
"""

import logging
import math
import time
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from api.middleware.rate_limit import limiter
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.content import (
    ImageGenerateRequest,
    ImageSetFeaturedRequest,
    ImageResponse,
    ImageListResponse,
)
from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db
from infrastructure.database.models import GeneratedImage, Article, User, ContentStatus
from adapters.ai.replicate_adapter import image_ai_service
from adapters.storage.image_storage import storage_adapter, download_image
from services.generation_tracker import GenerationTracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/generate", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def generate_image(
    request: Request,
    body: ImageGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new image using AI.
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
    project_id = getattr(current_user, 'current_project_id', None)
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
        article_id=body.article_id,
        prompt=body.prompt,
        style=body.style,
        width=body.width,
        height=body.height,
        status="generating",
        url="",  # Will be updated after generation
    )

    db.add(image)

    start_time = time.time()
    gen_log = await tracker.log_start(
        user_id=current_user.id,
        project_id=project_id,
        resource_type="image",
        resource_id=image_id,
        input_metadata={
            "prompt": body.prompt,
            "style": body.style,
            "width": body.width,
            "height": body.height,
        },
    )
    await db.commit()

    # Generate image using Replicate
    try:
        generated = await image_ai_service.generate_image(
            prompt=body.prompt,
            width=body.width,
            height=body.height,
            style=body.style,
        )

        # Store the external URL immediately (always accessible, even if local save fails)
        image.url = generated.url
        image.alt_text = f"AI-generated image: {body.prompt[:100]}"
        image.model = generated.model if hasattr(generated, "model") else None
        image.status = "completed"

        duration_ms = int((time.time() - start_time) * 1000)
        await tracker.log_success(
            log_id=gen_log.id,
            ai_model=getattr(generated, 'model', None),
            duration_ms=duration_ms,
        )

        # Try to download and cache locally (non-critical — external URL is the fallback)
        try:
            image_data = await download_image(generated.url)
            filename = f"image_{image_id}.jpg"
            local_path = await storage_adapter.save_image(
                image_data=image_data,
                filename=filename,
            )
            image.local_path = local_path
        except Exception as dl_err:
            # Local caching failed — image is still accessible via external URL
            logger.warning(
                "Failed to cache image locally for %s: %s", image_id, dl_err
            )

    except Exception as e:
        image.status = "failed"
        duration_ms = int((time.time() - start_time) * 1000)
        try:
            await tracker.log_failure(
                log_id=gen_log.id,
                error_message=str(e),
                duration_ms=duration_ms,
            )
        except Exception:
            logger.warning("Failed to log image generation failure for %s", image_id)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate image: {str(e)}",
        )

    await db.commit()
    await db.refresh(image)

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

    # Delete from storage if local path exists
    if image.local_path:
        try:
            await storage_adapter.delete_image(image.local_path)
        except Exception as e:
            # Log error but don't fail the deletion
            pass

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
