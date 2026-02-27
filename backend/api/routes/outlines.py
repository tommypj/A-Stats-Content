"""
Outline API routes.
"""

import csv
import io
import json
import logging
import math
import re
import time
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.responses import StreamingResponse
from api.middleware.rate_limit import limiter
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.content import (
    OutlineCreateRequest,
    OutlineUpdateRequest,
    OutlineResponse,
    OutlineListResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
)
from api.routes.auth import get_current_user
from api.utils import escape_like
from infrastructure.database.connection import get_db
from infrastructure.database.models import Outline, User, ContentStatus
from infrastructure.database.models.project import Project
from adapters.ai.anthropic_adapter import content_ai_service
from infrastructure.config.settings import settings
from services.generation_tracker import GenerationTracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/outlines", tags=["outlines"])


@router.post("", response_model=OutlineResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_outline(
    request: Request,
    body: OutlineCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new outline, optionally auto-generating with AI.
    """
    outline_id = str(uuid4())
    project_id = getattr(current_user, 'current_project_id', None)

    # Load brand voice defaults from the current project (if any)
    brand_voice: dict = {}
    if project_id:
        proj_result = await db.execute(
            select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
        )
        proj = proj_result.scalar_one_or_none()
        if proj and isinstance(proj.brand_voice, dict):
            brand_voice = proj.brand_voice

    # Apply brand voice defaults when the caller did not supply explicit values
    effective_tone = body.tone or brand_voice.get("tone")
    effective_target_audience = body.target_audience or brand_voice.get("target_audience")
    effective_language = body.language or brand_voice.get("language") or current_user.language or "en"

    # Check usage limit before creating any records
    if body.auto_generate:
        tracker = GenerationTracker(db)
        if not await tracker.check_limit(project_id, "outline", user_id=current_user.id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Monthly outline generation limit reached. Please upgrade your plan.",
            )

    # Create base outline (use effective values that may include brand voice defaults)
    outline = Outline(
        id=outline_id,
        user_id=current_user.id,
        project_id=project_id,
        title=f"Article about {body.keyword}",
        keyword=body.keyword,
        target_audience=effective_target_audience,
        tone=effective_tone,
        word_count_target=body.word_count_target,
        status=ContentStatus.GENERATING.value if body.auto_generate else ContentStatus.DRAFT.value,
    )

    try:
        db.add(outline)
        await db.commit()
        await db.refresh(outline)
    except Exception:
        await db.rollback()
        raise

    # Auto-generate with AI if requested
    if body.auto_generate:
        tracker = GenerationTracker(db)

        start_time = time.time()
        gen_log = await tracker.log_start(
            user_id=current_user.id,
            project_id=project_id,
            resource_type="outline",
            resource_id=outline_id,
            input_metadata={"keyword": body.keyword, "tone": effective_tone},
        )
        await db.commit()

        try:
            generated = await content_ai_service.generate_outline(
                keyword=body.keyword,
                target_audience=effective_target_audience,
                tone=effective_tone,
                word_count_target=body.word_count_target,
                language=effective_language,
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
    if current_user.current_project_id:
        query = select(Outline).where(Outline.project_id == current_user.current_project_id)
    else:
        query = select(Outline).where(
            Outline.user_id == current_user.id,
            Outline.project_id.is_(None),
        )

    # Apply filters
    if status:
        VALID_STATUSES = {s.value for s in ContentStatus}
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status value: {status}")
        query = query.where(Outline.status == status)
    if keyword:
        query = query.where(Outline.keyword.ilike(f"%{escape_like(keyword)}%"))

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


@router.get("/export")
async def export_all_outlines(
    format: str = Query("csv", pattern="^(csv)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export all outlines for the current project as CSV.
    """
    if current_user.current_project_id:
        query = select(Outline).where(Outline.project_id == current_user.current_project_id)
    else:
        query = select(Outline).where(
            Outline.user_id == current_user.id,
            Outline.project_id.is_(None),
        )
    query = query.order_by(Outline.created_at.desc()).limit(1000)
    result = await db.execute(query)
    outlines = result.scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "title", "keyword", "status", "tone", "word_count_target", "estimated_read_time", "created_at", "updated_at"])
    for o in outlines:
        writer.writerow([
            o.id,
            o.title,
            o.keyword,
            o.status,
            o.tone or "",
            o.word_count_target or 0,
            o.estimated_read_time or 0,
            o.created_at.isoformat() if o.created_at else "",
            o.updated_at.isoformat() if o.updated_at else "",
        ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=outlines.csv"},
    )


def _outline_to_markdown(outline) -> str:
    """Convert an Outline ORM object to a Markdown string."""
    lines = []
    lines.append(f"# {outline.title}")
    lines.append("")
    if outline.keyword:
        lines.append(f"**Keyword:** {outline.keyword}")
    if outline.tone:
        lines.append(f"**Tone:** {outline.tone}")
    if outline.target_audience:
        lines.append(f"**Target Audience:** {outline.target_audience}")
    if outline.word_count_target:
        lines.append(f"**Word Count Target:** {outline.word_count_target}")
    lines.append("")

    for section in (outline.sections or []):
        heading = section.get("heading", "")
        lines.append(f"## {heading}")
        for sub in section.get("subheadings", []):
            lines.append(f"### {sub}")
        if section.get("notes"):
            lines.append("")
            lines.append(f"*Notes: {section['notes']}*")
        lines.append("")

    return "\n".join(lines)


def _outline_to_html(outline) -> str:
    """Convert an Outline ORM object to an HTML string."""
    parts = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en"><head><meta charset="UTF-8"><title>')
    parts.append(outline.title or "Outline")
    parts.append("</title></head><body>")
    parts.append(f"<h1>{outline.title}</h1>")
    if outline.keyword:
        parts.append(f"<p><strong>Keyword:</strong> {outline.keyword}</p>")
    if outline.tone:
        parts.append(f"<p><strong>Tone:</strong> {outline.tone}</p>")
    if outline.target_audience:
        parts.append(f"<p><strong>Target Audience:</strong> {outline.target_audience}</p>")
    if outline.word_count_target:
        parts.append(f"<p><strong>Word Count Target:</strong> {outline.word_count_target}</p>")

    for section in (outline.sections or []):
        heading = section.get("heading", "")
        parts.append(f"<h2>{heading}</h2>")
        for sub in section.get("subheadings", []):
            parts.append(f"<h3>{sub}</h3>")
        if section.get("notes"):
            parts.append(f"<p><em>Notes: {section['notes']}</em></p>")

    parts.append("</body></html>")
    return "".join(parts)


@router.get("/{outline_id}/export")
async def export_outline(
    outline_id: str,
    format: str = Query("markdown", pattern="^(markdown|html|csv)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export a single outline in the requested format (markdown, html, or csv).
    """
    if current_user.current_project_id:
        query = select(Outline).where(
            Outline.id == outline_id,
            Outline.project_id == current_user.current_project_id,
        )
    else:
        query = select(Outline).where(
            Outline.id == outline_id,
            Outline.user_id == current_user.id,
        )
    result = await db.execute(query)
    outline = result.scalar_one_or_none()

    if not outline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outline not found")

    safe_title = re.sub(r"[^\w\-]", "_", outline.title or "outline")[:80]

    if format == "markdown":
        content = _outline_to_markdown(outline)
        return StreamingResponse(
            iter([content]),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.md"'},
        )

    if format == "html":
        content = _outline_to_html(outline)
        return StreamingResponse(
            iter([content]),
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.html"'},
        )

    # csv
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "title", "keyword", "status", "tone", "word_count_target", "estimated_read_time", "created_at", "updated_at"])
    writer.writerow([
        outline.id,
        outline.title,
        outline.keyword,
        outline.status,
        outline.tone or "",
        outline.word_count_target or 0,
        outline.estimated_read_time or 0,
        outline.created_at.isoformat() if outline.created_at else "",
        outline.updated_at.isoformat() if outline.updated_at else "",
    ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.csv"'},
    )


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_outlines(
    body: BulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete multiple outlines in a single request.

    All supplied IDs must belong to the current user's active project scope.
    Only outlines that pass the ownership check are deleted; IDs that do not
    exist or belong to a different project are silently ignored.
    Returns the number of rows actually deleted.
    """
    if not body.ids:
        return BulkDeleteResponse(deleted=0)

    if current_user.current_project_id:
        stmt = (
            delete(Outline)
            .where(
                Outline.id.in_(body.ids),
                Outline.project_id == current_user.current_project_id,
            )
        )
    else:
        stmt = (
            delete(Outline)
            .where(
                Outline.id.in_(body.ids),
                Outline.user_id == current_user.id,
                Outline.project_id.is_(None),
            )
        )

    result = await db.execute(stmt)
    await db.commit()

    return BulkDeleteResponse(deleted=result.rowcount)


@router.get("/{outline_id}", response_model=OutlineResponse)
async def get_outline(
    outline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific outline by ID.
    """
    if current_user.current_project_id:
        query = select(Outline).where(
            Outline.id == outline_id,
            Outline.project_id == current_user.current_project_id,
        )
    else:
        query = select(Outline).where(
            Outline.id == outline_id,
            Outline.user_id == current_user.id,
        )
    result = await db.execute(query)
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
    if current_user.current_project_id:
        query = select(Outline).where(
            Outline.id == outline_id,
            Outline.project_id == current_user.current_project_id,
        )
    else:
        query = select(Outline).where(
            Outline.id == outline_id,
            Outline.user_id == current_user.id,
        )
    result = await db.execute(query)
    outline = result.scalar_one_or_none()

    if not outline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outline not found",
        )

    # GEN-04: Include "status" so PUT requests can change outline status (e.g., mark as reviewed).
    ALLOWED_UPDATE_FIELDS = {"title", "keyword", "target_audience", "tone", "sections", "word_count_target", "status"}
    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field not in ALLOWED_UPDATE_FIELDS:
            continue
        if field == "sections" and value is not None:
            # GEN-05: Validate section structure before storing
            if not isinstance(value, list):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="sections must be a list",
                )
            validated = []
            for i, s in enumerate(value):
                s_dict = s.model_dump() if hasattr(s, "model_dump") else s
                if not isinstance(s_dict, dict):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"sections[{i}] must be an object",
                    )
                if "heading" not in s_dict or not isinstance(s_dict.get("heading"), str):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"sections[{i}] must have a string 'heading' field",
                    )
                validated.append(s_dict)
            value = validated
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
    if current_user.current_project_id:
        query = select(Outline).where(
            Outline.id == outline_id,
            Outline.project_id == current_user.current_project_id,
        )
    else:
        query = select(Outline).where(
            Outline.id == outline_id,
            Outline.user_id == current_user.id,
        )
    result = await db.execute(query)
    outline = result.scalar_one_or_none()

    if not outline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outline not found",
        )

    await db.delete(outline)
    await db.commit()


@router.post("/{outline_id}/regenerate", response_model=OutlineResponse)
@limiter.limit("10/minute")
async def regenerate_outline(
    request: Request,
    outline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Regenerate an outline using AI.

    # GEN-43: Note — keyword can be changed on regeneration; this is intentional but may confuse users
    """
    if current_user.current_project_id:
        query = select(Outline).where(
            Outline.id == outline_id,
            Outline.project_id == current_user.current_project_id,
        )
    else:
        query = select(Outline).where(
            Outline.id == outline_id,
            Outline.user_id == current_user.id,
        )
    result = await db.execute(query)
    outline = result.scalar_one_or_none()

    if not outline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outline not found",
        )

    # GEN-03: Prevent concurrent regeneration — reject if already in progress.
    if outline.status == ContentStatus.GENERATING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Outline is already being regenerated. Please wait for it to complete.",
        )

    # Check usage limit before changing status
    project_id = getattr(current_user, 'current_project_id', None)
    tracker = GenerationTracker(db)
    if not await tracker.check_limit(project_id, "outline", user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly outline generation limit reached. Please upgrade your plan.",
        )

    # PROJ-08: Load brand_voice from current project for regeneration defaults.
    brand_voice: dict = {}
    if project_id:
        proj_result = await db.execute(
            select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
        )
        proj = proj_result.scalar_one_or_none()
        if proj and isinstance(proj.brand_voice, dict):
            brand_voice = proj.brand_voice

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
            language=brand_voice.get("language") or current_user.language or "en",
            writing_style=brand_voice.get("writing_style") or "balanced",
            voice=brand_voice.get("voice") or "second_person",
            list_usage=brand_voice.get("list_usage") or "balanced",
            custom_instructions=brand_voice.get("custom_instructions"),
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
