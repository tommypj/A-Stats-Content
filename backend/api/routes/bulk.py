"""
Bulk content generation API routes.
"""

import asyncio
import logging
import math
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db, async_session_maker
from infrastructure.database.models import User
from infrastructure.database.models.bulk import ContentTemplate, BulkJob, BulkJobItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bulk", tags=["bulk"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class KeywordInput(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=500)
    title: Optional[str] = Field(None, max_length=500)
    target_audience: Optional[str] = Field(None, max_length=500)


class CreateBulkOutlineJobRequest(BaseModel):
    keywords: list[KeywordInput] = Field(..., min_length=1, max_length=50)
    template_id: Optional[str] = None


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
    description: Optional[str] = None
    template_config: TemplateConfigSchema


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    template_config: Optional[TemplateConfigSchema] = None


class BulkJobItemResponse(BaseModel):
    id: str
    keyword: Optional[str] = None
    title: Optional[str] = None
    status: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    error_message: Optional[str] = None
    processing_started_at: Optional[str] = None
    processing_completed_at: Optional[str] = None


class BulkJobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    total_items: int
    completed_items: int
    failed_items: int
    template_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_summary: Optional[str] = None
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
    description: Optional[str] = None
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
        select(ContentTemplate)
        .where(and_(*conditions))
        .order_by(ContentTemplate.created_at.desc())
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

    if body.name is not None:
        template.name = body.name
    if body.description is not None:
        template.description = body.description
    if body.template_config is not None:
        template.template_config = body.template_config.model_dump()

    await db.commit()
    await db.refresh(template)

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

    await db.delete(template)
    await db.commit()
    return {"message": "Template deleted"}


# ============================================================================
# Bulk Job Endpoints
# ============================================================================


@router.get("/jobs", response_model=BulkJobListResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[str] = Query(default=None, alias="status"),
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
async def create_bulk_outline_job(
    body: CreateBulkOutlineJobRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create and start a bulk outline generation job."""
    from services.bulk_generation import create_bulk_outline_job as _create_job
    from services.bulk_generation import process_bulk_outline_job

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
            await process_bulk_outline_job(session, job.id, current_user.id)

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
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a bulk job (stops pending items)."""
    from services.bulk_generation import cancel_job as _cancel

    success = await _cancel(db, job_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel this job")

    return {"message": "Job cancelled"}


@router.post("/jobs/{job_id}/retry-failed")
async def retry_failed_items(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry failed items in a bulk job."""
    from services.bulk_generation import process_bulk_outline_job
    from sqlalchemy import update as sql_update

    job_result = await db.execute(
        select(BulkJob).where(and_(BulkJob.id == job_id, BulkJob.user_id == current_user.id))
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Reset failed items to pending
    await db.execute(
        sql_update(BulkJobItem)
        .where(and_(
            BulkJobItem.bulk_job_id == job_id,
            BulkJobItem.status == "failed",
        ))
        .values(status="pending", error_message=None)
    )
    job.status = "processing"
    job.failed_items = 0
    await db.commit()

    # Process in background
    async def _run():
        async with async_session_maker() as session:
            await process_bulk_outline_job(session, job.id, current_user.id)

    asyncio.create_task(_run())

    return {"message": "Retrying failed items"}
