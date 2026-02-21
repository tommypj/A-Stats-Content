"""
Outline API routes.
"""

import math
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.content import (
    OutlineCreateRequest,
    OutlineUpdateRequest,
    OutlineResponse,
    OutlineListResponse,
)
from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db
from infrastructure.database.models import Outline, User, ContentStatus
from adapters.ai.anthropic_adapter import content_ai_service
from infrastructure.config.settings import settings

router = APIRouter(prefix="/outlines", tags=["outlines"])


@router.post("", response_model=OutlineResponse, status_code=status.HTTP_201_CREATED)
async def create_outline(
    request: OutlineCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new outline, optionally auto-generating with AI.
    """
    outline_id = str(uuid4())

    # Create base outline
    outline = Outline(
        id=outline_id,
        user_id=current_user.id,
        title=f"Article about {request.keyword}",
        keyword=request.keyword,
        target_audience=request.target_audience,
        tone=request.tone,
        word_count_target=request.word_count_target,
        status=ContentStatus.GENERATING.value if request.auto_generate else ContentStatus.DRAFT.value,
    )

    db.add(outline)
    await db.commit()

    # Auto-generate with AI if requested
    if request.auto_generate:
        try:
            generated = await content_ai_service.generate_outline(
                keyword=request.keyword,
                target_audience=request.target_audience,
                tone=request.tone,
                word_count_target=request.word_count_target,
            )

            # Update outline with generated content
            outline.title = generated.title
            outline.sections = [
                {
                    "heading": s.heading,
                    "subheadings": s.subheadings,
                    "notes": s.notes,
                    "word_count_target": s.word_count_target,
                }
                for s in generated.sections
            ]
            outline.estimated_read_time = generated.estimated_read_time
            outline.ai_model = settings.anthropic_model
            outline.status = ContentStatus.COMPLETED.value

        except Exception as e:
            outline.status = ContentStatus.FAILED.value
            outline.generation_error = str(e)

        await db.commit()

    await db.refresh(outline)
    return outline


@router.get("", response_model=OutlineListResponse)
async def list_outlines(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List user's outlines with pagination and filtering.
    """
    # Base query
    query = select(Outline).where(Outline.user_id == current_user.id)

    # Apply filters
    if status:
        query = query.where(Outline.status == status)
    if keyword:
        query = query.where(Outline.keyword.ilike(f"%{keyword}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Apply pagination
    query = query.order_by(Outline.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    outlines = result.scalars().all()

    return OutlineListResponse(
        items=outlines,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{outline_id}", response_model=OutlineResponse)
async def get_outline(
    outline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific outline by ID.
    """
    result = await db.execute(
        select(Outline).where(
            Outline.id == outline_id,
            Outline.user_id == current_user.id,
        )
    )
    outline = result.scalar_one_or_none()

    if not outline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outline not found",
        )

    return outline


@router.put("/{outline_id}", response_model=OutlineResponse)
async def update_outline(
    outline_id: str,
    request: OutlineUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an outline.
    """
    result = await db.execute(
        select(Outline).where(
            Outline.id == outline_id,
            Outline.user_id == current_user.id,
        )
    )
    outline = result.scalar_one_or_none()

    if not outline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outline not found",
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "sections" and value is not None:
            # Convert Pydantic models to dicts
            value = [s.model_dump() if hasattr(s, "model_dump") else s for s in value]
        setattr(outline, field, value)

    await db.commit()
    await db.refresh(outline)

    return outline


@router.delete("/{outline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outline(
    outline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an outline.
    """
    result = await db.execute(
        select(Outline).where(
            Outline.id == outline_id,
            Outline.user_id == current_user.id,
        )
    )
    outline = result.scalar_one_or_none()

    if not outline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outline not found",
        )

    await db.delete(outline)
    await db.commit()


@router.post("/{outline_id}/regenerate", response_model=OutlineResponse)
async def regenerate_outline(
    outline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate an outline using AI.
    """
    result = await db.execute(
        select(Outline).where(
            Outline.id == outline_id,
            Outline.user_id == current_user.id,
        )
    )
    outline = result.scalar_one_or_none()

    if not outline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outline not found",
        )

    outline.status = ContentStatus.GENERATING.value
    await db.commit()

    try:
        generated = await content_ai_service.generate_outline(
            keyword=outline.keyword,
            target_audience=outline.target_audience,
            tone=outline.tone,
            word_count_target=outline.word_count_target,
        )

        outline.title = generated.title
        outline.sections = [
            {
                "heading": s.heading,
                "subheadings": s.subheadings,
                "notes": s.notes,
                "word_count_target": s.word_count_target,
            }
            for s in generated.sections
        ]
        outline.estimated_read_time = generated.estimated_read_time
        outline.ai_model = settings.anthropic_model
        outline.status = ContentStatus.COMPLETED.value
        outline.generation_error = None

    except Exception as e:
        outline.status = ContentStatus.FAILED.value
        outline.generation_error = str(e)

    await db.commit()
    await db.refresh(outline)

    return outline
