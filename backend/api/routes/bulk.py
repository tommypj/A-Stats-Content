"""
Bulk content generation API routes.
"""

import asyncio
import logging
import math
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps_project import get_project_member
from api.middleware.rate_limit import limiter
from api.routes.auth import get_current_user
from infrastructure.database.connection import async_session_maker, get_db
from infrastructure.database.models import User
from infrastructure.database.models.bulk import BulkJob, BulkJobItem, ContentTemplate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bulk", tags=["bulk"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class KeywordInput(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=500)
    title: str | None = Field(None, max_length=500)
    target_audience: str | None = Field(None, max_length=500)

    @field_validator("keyword")
    @classmethod
    def keyword_not_blank(cls, v):
        if not v or not v.strip():
            raise ValueError("Keyword cannot be empty")
        return v.strip()


class CreateBulkOutlineJobRequest(BaseModel):
    keywords: list[KeywordInput] = Field(..., min_length=1, max_length=50)
    template_id: str | None = None


class TemplateConfigSchema(BaseModel):
    tone: str = "professional"
    writing_style: str = "editorial"
    word_count_target: int = 1500
    target_audience: str = ""
    custom_instructions: str = ""
    include_faq: bool = True
    include_conclusion: bool = True
    language: str = "en"


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    template_config: TemplateConfigSchema


class UpdateTemplateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    template_config: TemplateConfigSchema | None = None


class BulkJobItemResponse(BaseModel):
    id: str
    keyword: str | None = None
    title: str | None = None
    status: Literal["pending", "processing", "completed", "failed"] = "pending"  # GEN-48
    resource_type: str | None = None
    resource_id: str | None = None
    error_message: str | None = None
    processing_started_at: str | None = None
    processing_completed_at: str | None = None


class BulkJobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    total_items: int
    completed_items: int
    failed_items: int
    template_id: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error_summary: str | None = None
    created_at: str


class BulkJobDetailResponse(BulkJobResponse):
    items: list[BulkJobItemResponse] = Field(default_factory=list)


class BulkJobListResponse(BaseModel):
    items: list[BulkJobResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    template_config: dict
    created_at: str
    updated_at: str


class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]
    total: int


# ============================================================================
# Template Endpoints
# ============================================================================


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all content templates for the current user/project."""
    conditions = [ContentTemplate.user_id == current_user.id]
    if current_user.current_project_id:
        conditions.append(ContentTemplate.project_id == current_user.current_project_id)

    count_q = select(func.count(ContentTemplate.id)).where(and_(*conditions))
    total = (await db.execute(count_q)).scalar() or 0

    items_q = (
        select(ContentTemplate).where(and_(*conditions)).order_by(ContentTemplate.created_at.desc())
    )
    result = await db.execute(items_q)
    templates = result.scalars().all()

    return TemplateListResponse(
        items=[
            TemplateResponse(
                id=t.id,
                name=t.name,
                description=t.description,
                template_config=t.template_config,
                created_at=t.created_at.isoformat(),
                updated_at=t.updated_at.isoformat(),
            )
            for t in templates
        ],
        total=total,
    )


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: CreateTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new content template."""
    # BULK-04: Verify project membership before creating resources under it.
    if current_user.current_project_id:
        await get_project_member(current_user.current_project_id, current_user.id, db)

    template = ContentTemplate(
        id=str(uuid4()),
        user_id=current_user.id,
        project_id=current_user.current_project_id,
        name=body.name,
        description=body.description,
        template_config=body.template_config.model_dump(),
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    logger.info(
        "CROSS-02: Template created template_id=%s by user_id=%s", template.id, current_user.id
    )

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        template_config=template.template_config,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    body: UpdateTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a content template."""
    result = await db.execute(
        select(ContentTemplate).where(
            and_(ContentTemplate.id == template_id, ContentTemplate.user_id == current_user.id)
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # BULK-22: Verify the user has access to the project that owns this template.
    if template.project_id:
        await get_project_member(template.project_id, current_user.id, db)

    if body.name is not None:
        template.name = body.name
    if body.description is not None:
        template.description = body.description
    if body.template_config is not None:
        template.template_config = body.template_config.model_dump()

    await db.commit()
    await db.refresh(template)

    logger.info(
        "CROSS-02: Template updated template_id=%s by user_id=%s", template.id, current_user.id
    )

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        template_config=template.template_config,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a content template."""
    result = await db.execute(
        select(ContentTemplate).where(
            and_(ContentTemplate.id == template_id, ContentTemplate.user_id == current_user.id)
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # BULK-22: Verify the user has access to the project that owns this template.
    if template.project_id:
        await get_project_member(template.project_id, current_user.id, db)

    await db.delete(template)
    await db.commit()

    logger.info(
        "CROSS-02: Template deleted template_id=%s by user_id=%s", template_id, current_user.id
    )

    return {"message": "Template deleted"}


# ============================================================================
# Bulk Job Endpoints
# ============================================================================


@router.get("/jobs", response_model=BulkJobListResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List bulk jobs for the current user."""
    conditions = [BulkJob.user_id == current_user.id]
    if status_filter:
        conditions.append(BulkJob.status == status_filter)

    count_q = select(func.count(BulkJob.id)).where(and_(*conditions))
    total = (await db.execute(count_q)).scalar() or 0

    items_q = (
        select(BulkJob)
        .where(and_(*conditions))
        .order_by(BulkJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(items_q)
    jobs = result.scalars().all()

    pages_count = math.ceil(total / page_size) if total > 0 else 0

    return BulkJobListResponse(
        items=[
            BulkJobResponse(
                id=j.id,
                job_type=j.job_type,
                status=j.status,
                total_items=j.total_items,
                completed_items=j.completed_items,
                failed_items=j.failed_items,
                template_id=j.template_id,
                started_at=j.started_at.isoformat() if j.started_at else None,
                completed_at=j.completed_at.isoformat() if j.completed_at else None,
                error_summary=j.error_summary,
                created_at=j.created_at.isoformat(),
            )
            for j in jobs
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages_count,
    )


@router.get("/jobs/{job_id}", response_model=BulkJobDetailResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a bulk job with all its items."""
    from services.bulk_generation import get_job_with_items

    data = await get_job_with_items(db, job_id, current_user.id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return BulkJobDetailResponse(**data)


@router.post("/jobs/outlines", response_model=BulkJobResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_bulk_outline_job(
    body: CreateBulkOutlineJobRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create and start a bulk outline generation job."""
    from services.bulk_generation import create_bulk_outline_job as _create_job
    from services.bulk_generation import process_bulk_outline_job

    # BULK-04: Verify project membership before creating job resources under it.
    if current_user.current_project_id:
        await get_project_member(current_user.current_project_id, current_user.id, db)

    # BULK-06: Check outline usage limits at job creation so the user finds out immediately.
    from services.generation_tracker import GenerationTracker

    tracker = GenerationTracker(db)
    limit_ok = await tracker.check_limit(
        current_user.current_project_id, "outline", user_id=current_user.id
    )
    if not limit_ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly outline generation limit reached. Please upgrade your plan.",
        )

    # Validate template ownership if template_id is provided
    if body.template_id:
        tmpl_result = await db.execute(
            select(ContentTemplate).where(
                and_(
                    ContentTemplate.id == body.template_id,
                    ContentTemplate.user_id == current_user.id,
                )
            )
        )
        if not tmpl_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found",
            )

    keywords = [kw.model_dump() for kw in body.keywords]
    job = await _create_job(
        db=db,
        user_id=current_user.id,
        project_id=current_user.current_project_id,
        keywords=keywords,
        template_id=body.template_id,
    )

    # Start processing in background
    async def _run():
        async with async_session_maker() as session:
            try:
                await process_bulk_outline_job(session, job.id, current_user.id)
            except Exception as _bg_err:
                # BULK-10: mark job failed if the background task crashes unexpectedly
                logger.error("Bulk job %s crashed: %s", job.id, _bg_err, exc_info=True)
                try:
                    async with async_session_maker() as _fail_session:
                        from sqlalchemy import update as _upd

                        await _fail_session.execute(
                            _upd(BulkJob)
                            .where(BulkJob.id == job.id)
                            .values(
                                status="failed",
                                error_summary=str(_bg_err)[:500],
                                completed_at=datetime.now(UTC),
                            )
                        )
                        await _fail_session.commit()
                except Exception as _mark_err:
                    # BULK-25: log instead of silently swallowing — job may be stuck in "processing" state
                    logger.warning("Failed to mark bulk job %s as failed: %s", job.id, _mark_err)

    asyncio.create_task(_run())

    return BulkJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        total_items=job.total_items,
        completed_items=job.completed_items,
        failed_items=job.failed_items,
        template_id=job.template_id,
        started_at=None,
        completed_at=None,
        error_summary=None,
        created_at=job.created_at.isoformat(),
    )


@router.post("/jobs/{job_id}/cancel")
@limiter.limit("10/minute")  # CROSS-01: rate limit bulk operations
async def cancel_job(
    job_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a bulk job (stops pending items)."""
    from services.bulk_generation import cancel_job as _cancel

    success = await _cancel(db, job_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel this job"
        )

    return {"message": "Job cancelled"}


@router.post("/jobs/{job_id}/retry-failed")
@limiter.limit("10/minute")  # CROSS-01: rate limit bulk operations
async def retry_failed_items(
    job_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry failed items in a bulk job."""
    from sqlalchemy import update as sql_update

    from services.bulk_generation import process_bulk_outline_job

    job_result = await db.execute(
        select(BulkJob).where(and_(BulkJob.id == job_id, BulkJob.user_id == current_user.id))
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # BULK-03: Prevent duplicate background tasks for an already-running job
    if job.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is already processing. Wait for it to complete before retrying.",
        )

    # BULK-H2: Check usage limits before allowing retry
    from services.generation_tracker import GenerationTracker

    tracker = GenerationTracker(db)
    can_generate = await tracker.check_limit(str(current_user.id), "article")
    if not can_generate:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly generation limit reached. Upgrade your plan to continue.",
        )

    # BULK-07: Prevent retry when there are no failed items (avoids corrupting completed jobs).
    if job.failed_items == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No failed items to retry.",
        )

    # Reset failed items to pending
    await db.execute(
        sql_update(BulkJobItem)
        .where(
            and_(
                BulkJobItem.bulk_job_id == job_id,
                BulkJobItem.status == "failed",
            )
        )
        .values(status="pending", error_message=None)
    )
    job.status = "processing"
    job.failed_items = 0
    await db.commit()

    # Process in background
    async def _run():
        async with async_session_maker() as session:
            try:
                await process_bulk_outline_job(session, job.id, current_user.id)
            except Exception as _bg_err:
                logger.error("Bulk job %s retry crashed: %s", job.id, _bg_err, exc_info=True)
                try:
                    async with async_session_maker() as _fail_session:
                        from sqlalchemy import update as _upd

                        await _fail_session.execute(
                            _upd(BulkJob)
                            .where(BulkJob.id == job.id)
                            .values(
                                status="failed",
                                error_summary=str(_bg_err)[:500],
                                completed_at=datetime.now(UTC),
                            )
                        )
                        await _fail_session.commit()
                except Exception:
                    pass

    asyncio.create_task(_run())

    return {"message": "Retrying failed items"}
