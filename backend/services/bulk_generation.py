"""
Bulk Content Generation Service.

Handles creation and processing of bulk content generation jobs
for programmatic SEO workflows.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.bulk import BulkJob, BulkJobItem, ContentTemplate
from infrastructure.database.models.content import Outline, Article, ContentStatus
from infrastructure.database.models.project import Project
from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


async def create_bulk_outline_job(
    db: AsyncSession,
    user_id: str,
    project_id: Optional[str],
    keywords: list[dict],
    template_id: Optional[str] = None,
) -> BulkJob:
    """
    Create a bulk outline generation job.
    keywords: list of dicts with 'keyword' and optional 'title', 'target_audience'
    """
    job = BulkJob(
        id=str(uuid4()),
        user_id=user_id,
        project_id=project_id,
        job_type="outline_generation",
        status="pending",
        total_items=len(keywords),
        completed_items=0,
        failed_items=0,
        input_data={"keywords": keywords},
        template_id=template_id,
    )
    db.add(job)

    for kw_data in keywords:
        item = BulkJobItem(
            id=str(uuid4()),
            bulk_job_id=job.id,
            keyword=kw_data.get("keyword", ""),
            title=kw_data.get("title"),
            status="pending",
        )
        db.add(item)

    await db.commit()
    await db.refresh(job)
    return job


async def process_bulk_outline_job(
    db: AsyncSession,
    job_id: str,
    user_id: str,
) -> None:
    """
    Process a bulk outline generation job.
    Generates outlines one by one for each pending item.
    """
    from adapters.ai.anthropic_adapter import content_ai_service
    from services.generation_tracker import GenerationTracker

    # Fetch job
    job_result = await db.execute(
        select(BulkJob).where(and_(BulkJob.id == job_id, BulkJob.user_id == user_id))
    )
    job = job_result.scalar_one_or_none()
    if not job:
        logger.error("Bulk job %s not found", job_id)
        return

    # Mark as processing
    job.status = "processing"
    job.started_at = datetime.now(timezone.utc)
    await db.commit()

    # Load template config if any
    template_config: dict = {}
    if job.template_id:
        tmpl_result = await db.execute(
            select(ContentTemplate).where(ContentTemplate.id == job.template_id)
        )
        template = tmpl_result.scalar_one_or_none()
        if template:
            template_config = template.template_config or {}

    # Load brand voice
    brand_voice: dict = {}
    if job.project_id:
        proj_result = await db.execute(
            select(Project.brand_voice).where(Project.id == job.project_id)
        )
        bv = proj_result.scalar_one_or_none()
        if bv:
            brand_voice = bv

    # Fetch pending items
    items_result = await db.execute(
        select(BulkJobItem)
        .where(and_(BulkJobItem.bulk_job_id == job_id, BulkJobItem.status == "pending"))
        .order_by(BulkJobItem.created_at)
    )
    items = items_result.scalars().all()

    tracker = GenerationTracker(db)

    for item in items:
        item.status = "processing"
        item.processing_started_at = datetime.now(timezone.utc)
        await db.commit()

        start_time = time.time()
        outline_id = str(uuid4())

        try:
            # Check usage limits
            from services.project_usage import ProjectUsageService
            usage_svc = ProjectUsageService(db)
            can_generate = await usage_svc.can_generate(user_id, job.project_id, "outline")
            if not can_generate:
                item.status = "failed"
                item.error_message = "Usage limit reached for outlines this month"
                item.processing_completed_at = datetime.now(timezone.utc)
                job.failed_items += 1
                await db.commit()
                continue

            # Merge template config with brand voice
            tone = template_config.get("tone") or brand_voice.get("tone", "professional")
            target_audience = template_config.get("target_audience") or brand_voice.get("target_audience", "")
            word_count = template_config.get("word_count_target", 1500)
            language = template_config.get("language") or brand_voice.get("language", "en")
            writing_style = template_config.get("writing_style") or brand_voice.get("writing_style", "editorial")
            custom_instructions = template_config.get("custom_instructions") or brand_voice.get("custom_instructions", "")

            # Log start
            gen_log = await tracker.log_start(
                user_id=user_id,
                project_id=job.project_id,
                resource_type="outline",
                resource_id=outline_id,
                input_metadata={"keyword": item.keyword, "bulk_job_id": job_id},
            )

            # Generate outline
            generated = await content_ai_service.generate_outline(
                keyword=item.keyword or "",
                title=item.title,
                tone=tone,
                target_audience=target_audience,
                word_count_target=word_count,
                language=language,
                writing_style=writing_style,
                custom_instructions=custom_instructions,
            )

            # Create outline record
            outline = Outline(
                id=outline_id,
                user_id=user_id,
                project_id=job.project_id,
                title=generated.title,
                keyword=item.keyword or "",
                target_audience=target_audience,
                tone=tone,
                sections=[
                    {
                        "heading": s.heading,
                        "subheadings": s.subheadings,
                        "notes": s.notes,
                        "word_count_target": s.word_count_target,
                    }
                    for s in generated.sections
                ],
                status=ContentStatus.COMPLETED.value,
                word_count_target=word_count,
                estimated_read_time=generated.estimated_read_time,
                ai_model=settings.anthropic_model,
            )
            db.add(outline)

            duration_ms = int((time.time() - start_time) * 1000)
            await tracker.log_success(
                log_id=gen_log.id,
                ai_model=settings.anthropic_model,
                duration_ms=duration_ms,
            )

            item.status = "completed"
            item.resource_type = "outline"
            item.resource_id = outline_id
            item.processing_completed_at = datetime.now(timezone.utc)
            job.completed_items += 1

        except Exception as e:
            logger.error("Bulk outline item %s failed: %s", item.id, str(e))
            item.status = "failed"
            item.error_message = str(e)[:500]
            item.processing_completed_at = datetime.now(timezone.utc)
            job.failed_items += 1

            # Log failure
            try:
                duration_ms = int((time.time() - start_time) * 1000)
                await tracker.log_failure(
                    log_id=gen_log.id,
                    error_message=str(e),
                    duration_ms=duration_ms,
                )
            except Exception:
                pass

        await db.commit()

        # Rate limiting — pause between items to avoid overloading the AI API
        await asyncio.sleep(2)

    # Finalize job
    if job.failed_items == 0:
        job.status = "completed"
    elif job.completed_items == 0:
        job.status = "failed"
    else:
        job.status = "partially_failed"

    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("Bulk job %s finished: %d/%d completed, %d failed",
                job_id, job.completed_items, job.total_items, job.failed_items)


async def get_job_with_items(
    db: AsyncSession,
    job_id: str,
    user_id: str,
) -> Optional[dict]:
    """Fetch a bulk job with all its items."""
    job_result = await db.execute(
        select(BulkJob).where(and_(BulkJob.id == job_id, BulkJob.user_id == user_id))
    )
    job = job_result.scalar_one_or_none()
    if not job:
        return None

    items_result = await db.execute(
        select(BulkJobItem)
        .where(BulkJobItem.bulk_job_id == job_id)
        .order_by(BulkJobItem.created_at)
    )
    items = items_result.scalars().all()

    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "total_items": job.total_items,
        "completed_items": job.completed_items,
        "failed_items": job.failed_items,
        "template_id": job.template_id,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_summary": job.error_summary,
        "created_at": job.created_at.isoformat(),
        "items": [
            {
                "id": item.id,
                "keyword": item.keyword,
                "title": item.title,
                "status": item.status,
                "resource_type": item.resource_type,
                "resource_id": item.resource_id,
                "error_message": item.error_message,
                "processing_started_at": item.processing_started_at.isoformat() if item.processing_started_at else None,
                "processing_completed_at": item.processing_completed_at.isoformat() if item.processing_completed_at else None,
            }
            for item in items
        ],
    }


async def cancel_job(
    db: AsyncSession,
    job_id: str,
    user_id: str,
) -> bool:
    """Cancel pending items in a bulk job."""
    job_result = await db.execute(
        select(BulkJob).where(and_(BulkJob.id == job_id, BulkJob.user_id == user_id))
    )
    job = job_result.scalar_one_or_none()
    if not job or job.status not in ("pending", "processing"):
        return False

    # Cancel all pending items
    await db.execute(
        update(BulkJobItem)
        .where(and_(
            BulkJobItem.bulk_job_id == job_id,
            BulkJobItem.status == "pending",
        ))
        .values(status="cancelled")
    )

    job.status = "cancelled" if job.completed_items == 0 else "partially_failed"
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return True
