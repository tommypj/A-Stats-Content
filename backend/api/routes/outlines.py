"""
Outline API routes.
"""

import logging
import math
import time
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
from services.generation_tracker import GenerationTracker

logger = logging.getLogger(__name__)

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
    project_id = getattr(current_user, 'current_project_id', None)

    # Check usage limit before creating any records
    if request.auto_generate:
        tracker = GenerationTracker(db)
        if not await tracker.check_limit(project_id, "outline"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Monthly outline generation limit reached. Please upgrade your plan.",
            )

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
        tracker = GenerationTracker(db)

        start_time = time.time()
        gen_log = await tracker.log_start(
            user_id=current_user.id,
            project_id=project_id,
            resource_type="outline",
            resource_id=outline_id,
            input_metadata={"keyword": request.keyword, "tone": request.tone},
        )
        await db.commit()

        try:
            generated = await content_ai_service.generate_outline(
                keyword=request.keyword,
                target_audience=request.target_audience,
                tone=request.tone,
                word_count_target=request.word_count_target,
                language=request.language or current_user.language or "en",
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

            duration_ms = int((time.time() - start_time) * 1000)
            await tracker.log_success(
                log_id=gen_log.id,
                ai_model=settings.anthropic_model,
                duration_ms=duration_ms,
            )

        except Exception as e:
            outline.status = ContentStatus.FAILED.value
            outline.generation_error = str(e)

            # Log failure in a separate session to avoid corrupting the main session
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                from infrastructure.database.connection import async_session_maker
                async with async_session_maker() as tracker_db:
                    fail_tracker = GenerationTracker(tracker_db)
                    await fail_tracker.log_failure(
                        log_id=gen_log.id,
                        error_message=str(e),
                        duration_ms=duration_ms,
                    )
                    await tracker_db.commit()
            except Exception:
                logger.warning("Failed to log outline generation failure for %s", outline_id)

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

    # Check usage limit before changing status
    project_id = getattr(current_user, 'current_project_id', None)
    tracker = GenerationTracker(db)
    if not await tracker.check_limit(project_id, "outline"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly outline generation limit reached. Please upgrade your plan.",
        )

    outline.status = ContentStatus.GENERATING.value
    await db.commit()

    start_time = time.time()
    gen_log = await tracker.log_start(
        user_id=current_user.id,
        project_id=project_id,
        resource_type="outline",
        resource_id=outline_id,
        input_metadata={"keyword": outline.keyword, "tone": outline.tone},
    )
    await db.commit()

    try:
        generated = await content_ai_service.generate_outline(
            keyword=outline.keyword,
            target_audience=outline.target_audience,
            tone=outline.tone,
            word_count_target=outline.word_count_target,
            language=current_user.language or "en",
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

        duration_ms = int((time.time() - start_time) * 1000)
        await tracker.log_success(
            log_id=gen_log.id,
            ai_model=settings.anthropic_model,
            duration_ms=duration_ms,
        )

    except Exception as e:
        outline.status = ContentStatus.FAILED.value
        outline.generation_error = str(e)

        # Log failure in a separate session to avoid corrupting the main session
        duration_ms = int((time.time() - start_time) * 1000)
        try:
            from infrastructure.database.connection import async_session_maker
            async with async_session_maker() as tracker_db:
                fail_tracker = GenerationTracker(tracker_db)
                await fail_tracker.log_failure(
                    log_id=gen_log.id,
                    error_message=str(e),
                    duration_ms=duration_ms,
                )
                await tracker_db.commit()
        except Exception:
            logger.warning("Failed to log outline regeneration failure for %s", outline_id)

    await db.commit()
    await db.refresh(outline)

    return outline
