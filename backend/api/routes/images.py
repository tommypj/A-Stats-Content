"""
Image generation and management API routes.
"""

import math
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
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

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/generate", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def generate_image(
    request: ImageGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new image using AI.
    """
    # Validate article_id if provided
    if request.article_id:
        result = await db.execute(
            select(Article).where(
                Article.id == request.article_id,
                Article.user_id == current_user.id,
            )
        )
        article = result.scalar_one_or_none()
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found",
            )

    # Create image record in generating status
    image_id = str(uuid4())
    image = GeneratedImage(
        id=image_id,
        user_id=current_user.id,
        article_id=request.article_id,
        prompt=request.prompt,
        style=request.style,
        width=request.width,
        height=request.height,
        status="generating",
        url="",  # Will be updated after generation
    )

    db.add(image)
    await db.commit()

    # Generate image using Replicate
    try:
        generated = await image_ai_service.generate_image(
            prompt=request.prompt,
            width=request.width,
            height=request.height,
            style=request.style,
        )

        # Store the external URL immediately (always accessible, even if local save fails)
        image.url = generated.url
        image.alt_text = f"AI-generated image: {request.prompt[:100]}"
        image.model = generated.model if hasattr(generated, "model") else None
        image.status = "completed"

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
            import logging
            logging.getLogger(__name__).warning(
                "Failed to cache image locally for %s: %s", image_id, dl_err
            )

    except Exception as e:
        image.status = "failed"
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
    query = select(GeneratedImage).where(GeneratedImage.user_id == current_user.id)

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
    result = await db.execute(
        select(GeneratedImage).where(
            GeneratedImage.id == image_id,
            GeneratedImage.user_id == current_user.id,
        )
    )
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
    result = await db.execute(
        select(GeneratedImage).where(
            GeneratedImage.id == image_id,
            GeneratedImage.user_id == current_user.id,
        )
    )
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
    # Verify image exists and belongs to user
    image_result = await db.execute(
        select(GeneratedImage).where(
            GeneratedImage.id == image_id,
            GeneratedImage.user_id == current_user.id,
        )
    )
    image = image_result.scalar_one_or_none()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Verify article exists and belongs to user
    article_result = await db.execute(
        select(Article).where(
            Article.id == request.article_id,
            Article.user_id == current_user.id,
        )
    )
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
