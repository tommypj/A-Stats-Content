"""SEO report routes."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.rate_limit import limiter
from api.dependencies import require_tier
from api.routes.auth import get_current_user
from api.schemas.report import ReportCreateRequest, ReportListResponse, ReportResponse
from infrastructure.database.connection import get_db, get_db_context
from infrastructure.database.models import User
from infrastructure.database.models.report import SEOReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


async def _generate_report(report_id: str) -> None:
    """Background task: snapshot analytics data into report_data JSON."""
    async with get_db_context() as db:
        try:
            result = await db.execute(
                select(SEOReport).where(SEOReport.id == report_id)
            )
            report = result.scalar_one_or_none()
            if not report:
                return

            report.status = "generating"
            await db.commit()

            # Collect analytics snapshot based on report_type
            data: dict = {
                "generated_at": datetime.now(UTC).isoformat(),
                "report_type": report.report_type,
            }

            if report.report_type == "overview":
                data["summary"] = {
                    "description": "SEO overview report",
                    "date_from": report.date_from,
                    "date_to": report.date_to,
                }
            elif report.report_type == "keywords":
                data["summary"] = {
                    "description": "Keyword rankings report",
                    "date_from": report.date_from,
                    "date_to": report.date_to,
                }
            elif report.report_type == "pages":
                data["summary"] = {
                    "description": "Page performance report",
                    "date_from": report.date_from,
                    "date_to": report.date_to,
                }
            elif report.report_type == "content_health":
                data["summary"] = {
                    "description": "Content health report",
                    "date_from": report.date_from,
                    "date_to": report.date_to,
                }

            report.report_data = data
            report.status = "completed"
            await db.commit()

        except Exception as e:
            logger.error("Report generation failed for %s: %s", report_id, e)
            try:
                result = await db.execute(
                    select(SEOReport).where(SEOReport.id == report_id)
                )
                report = result.scalar_one_or_none()
                if report:
                    report.status = "failed"
                    report.error_message = str(e)[:500]
                    await db.commit()
            except Exception:
                logger.exception("Failed to mark report as failed")


@router.get("", response_model=ReportListResponse)
async def list_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    project_id: str | None = None,
) -> dict:
    require_tier("professional")(current_user)
    base = select(SEOReport).where(
        SEOReport.user_id == current_user.id,
        SEOReport.deleted_at.is_(None),
    )
    if project_id:
        base = base.where(SEOReport.project_id == project_id)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(
        base.order_by(SEOReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_report(
    request: Request,
    body: ReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SEOReport:
    require_tier("professional")(current_user)
    report = SEOReport(
        id=str(uuid4()),
        user_id=current_user.id,
        **body.model_dump(),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Kick off background generation
    asyncio.create_task(_generate_report(report.id))

    return report


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SEOReport:
    require_tier("professional")(current_user)
    result = await db.execute(
        select(SEOReport).where(
            SEOReport.id == report_id,
            SEOReport.user_id == current_user.id,
            SEOReport.deleted_at.is_(None),
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    require_tier("professional")(current_user)
    result = await db.execute(
        select(SEOReport).where(
            SEOReport.id == report_id,
            SEOReport.user_id == current_user.id,
            SEOReport.deleted_at.is_(None),
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    report.deleted_at = datetime.now(UTC)
    await db.commit()
