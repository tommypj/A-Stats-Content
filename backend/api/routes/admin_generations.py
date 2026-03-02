"""
Admin generation tracking API routes.
"""

import logging
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps_admin import get_current_admin_user
from api.schemas.generation import (
    GenerationLogListResponse,
    GenerationLogResponse,
    GenerationStatsResponse,
)
from infrastructure.database.connection import get_db
from infrastructure.database.models.generation import GenerationLog
from infrastructure.database.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/generations", tags=["Admin - Generations"])


@router.get("", response_model=GenerationLogListResponse)
async def list_generation_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    resource_type: str | None = Query(None, description="Filter: article, outline, image"),
    status: str | None = Query(None, description="Filter: started, success, failed"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all generation logs with pagination and filters."""
    query = select(GenerationLog)

    if resource_type:
        query = query.where(GenerationLog.resource_type == resource_type)
    if status:
        query = query.where(GenerationLog.status == status)
    if user_id:
        query = query.where(GenerationLog.user_id == user_id)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(desc(GenerationLog.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    # Get user info
    user_ids = list({log.user_id for log in logs})
    users_dict = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_dict = {u.id: u for u in users_result.scalars().all()}

    items = []
    for log in logs:
        user = users_dict.get(log.user_id)
        items.append(
            GenerationLogResponse(
                id=log.id,
                user_id=log.user_id,
                project_id=log.project_id,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                status=log.status,
                error_message=log.error_message,
                ai_model=log.ai_model,
                duration_ms=log.duration_ms,
                input_metadata=log.input_metadata,
                cost_credits=log.cost_credits,
                created_at=log.created_at,
                user_email=user.email if user else None,
                user_name=user.name if user else None,
            )
        )

    return GenerationLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/stats", response_model=GenerationStatsResponse)
async def get_generation_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated generation statistics."""
    # Total counts by status
    stats_query = select(
        func.count().label("total"),
        func.sum(case((GenerationLog.status == "success", 1), else_=0)).label("successful"),
        func.sum(case((GenerationLog.status == "failed", 1), else_=0)).label("failed"),
        # By type - success
        func.sum(
            case(
                (
                    (GenerationLog.resource_type == "article")
                    & (GenerationLog.status == "success"),
                    1,
                ),
                else_=0,
            )
        ).label("articles_generated"),
        func.sum(
            case(
                (
                    (GenerationLog.resource_type == "outline")
                    & (GenerationLog.status == "success"),
                    1,
                ),
                else_=0,
            )
        ).label("outlines_generated"),
        func.sum(
            case(
                ((GenerationLog.resource_type == "image") & (GenerationLog.status == "success"), 1),
                else_=0,
            )
        ).label("images_generated"),
        # By type - failed
        func.sum(
            case(
                (
                    (GenerationLog.resource_type == "article") & (GenerationLog.status == "failed"),
                    1,
                ),
                else_=0,
            )
        ).label("articles_failed"),
        func.sum(
            case(
                (
                    (GenerationLog.resource_type == "outline") & (GenerationLog.status == "failed"),
                    1,
                ),
                else_=0,
            )
        ).label("outlines_failed"),
        func.sum(
            case(
                ((GenerationLog.resource_type == "image") & (GenerationLog.status == "failed"), 1),
                else_=0,
            )
        ).label("images_failed"),
        # Avg duration for successful
        func.avg(
            case((GenerationLog.status == "success", GenerationLog.duration_ms), else_=None)
        ).label("avg_duration"),
        # Total credits
        func.coalesce(func.sum(GenerationLog.cost_credits), 0).label("total_credits"),
    )

    result = await db.execute(stats_query)
    row = result.one()

    total = row.total or 0
    successful = row.successful or 0

    return GenerationStatsResponse(
        total_generations=total,
        successful=successful,
        failed=row.failed or 0,
        success_rate=round((successful / total) * 100, 1) if total > 0 else 0.0,
        articles_generated=row.articles_generated or 0,
        outlines_generated=row.outlines_generated or 0,
        images_generated=row.images_generated or 0,
        articles_failed=row.articles_failed or 0,
        outlines_failed=row.outlines_failed or 0,
        images_failed=row.images_failed or 0,
        avg_duration_ms=int(row.avg_duration) if row.avg_duration else None,
        total_credits=row.total_credits or 0,
    )
