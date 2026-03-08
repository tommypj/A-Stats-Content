"""
Admin error logs API routes.
"""

import logging
from datetime import datetime, timedelta, timezone
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, cast, Date, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps_admin import get_current_admin_user
from api.schemas.error_log import (
    ErrorLogListResponse,
    ErrorLogResolveRequest,
    ErrorLogResponse,
    ErrorServiceStat,
    ErrorStatsResponse,
    ErrorTrend,
    ErrorTypeStat,
)
from infrastructure.database.connection import get_db
from infrastructure.database.models.error_log import SystemErrorLog
from infrastructure.database.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/error-logs", tags=["Admin - Error Logs"])


def _build_error_response(error: SystemErrorLog, users_dict: dict) -> ErrorLogResponse:
    """Build an ErrorLogResponse from a SystemErrorLog with user info."""
    user = users_dict.get(error.user_id) if error.user_id else None
    resolver = users_dict.get(error.resolved_by) if error.resolved_by else None
    return ErrorLogResponse(
        id=error.id,
        error_type=error.error_type,
        error_code=error.error_code,
        severity=error.severity,
        title=error.title,
        message=error.message,
        stack_trace=error.stack_trace,
        service=error.service,
        endpoint=error.endpoint,
        http_method=error.http_method,
        http_status=error.http_status,
        request_id=error.request_id,
        user_id=error.user_id,
        project_id=error.project_id,
        resource_type=error.resource_type,
        resource_id=error.resource_id,
        context=error.context,
        user_agent=error.user_agent,
        ip_address=error.ip_address,
        occurrence_count=error.occurrence_count,
        first_seen_at=error.first_seen_at,
        last_seen_at=error.last_seen_at,
        is_resolved=error.is_resolved,
        resolved_at=error.resolved_at,
        resolved_by=error.resolved_by,
        resolution_notes=error.resolution_notes,
        error_fingerprint=error.error_fingerprint,
        created_at=error.created_at,
        user_email=user.email if user else None,
        user_name=user.name if user else None,
        resolver_email=resolver.email if resolver else None,
        resolver_name=resolver.name if resolver else None,
    )


@router.get("", response_model=ErrorLogListResponse)
async def list_error_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: str | None = Query(None, description="Filter: warning, error, critical"),
    error_type: str | None = Query(None, description="Filter by error type"),
    service: str | None = Query(None, description="Filter by service"),
    is_resolved: bool | None = Query(None, description="Filter by resolution status"),
    search: str | None = Query(None, description="Search in title and message"),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List system error logs with pagination and filters."""
    # Build filter conditions
    conditions = []
    if severity:
        conditions.append(SystemErrorLog.severity == severity)
    if error_type:
        conditions.append(SystemErrorLog.error_type == error_type)
    if service:
        conditions.append(SystemErrorLog.service == service)
    if is_resolved is not None:
        conditions.append(SystemErrorLog.is_resolved == is_resolved)
    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            SystemErrorLog.title.ilike(search_pattern)
            | SystemErrorLog.message.ilike(search_pattern)
        )

    query = select(SystemErrorLog)
    count_query = select(func.count(SystemErrorLog.id))
    for cond in conditions:
        query = query.where(cond)
        count_query = count_query.where(cond)
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate, order by last_seen descending (most recent activity first)
    query = query.order_by(desc(SystemErrorLog.last_seen_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    errors = result.scalars().all()

    # Get user info
    user_ids = set()
    for e in errors:
        if e.user_id:
            user_ids.add(e.user_id)
        if e.resolved_by:
            user_ids.add(e.resolved_by)
    users_dict = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(list(user_ids))))
        users_dict = {u.id: u for u in users_result.scalars().all()}

    items = [_build_error_response(e, users_dict) for e in errors]

    return ErrorLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/filters/options")
async def get_filter_options(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get distinct values for filter dropdowns."""
    types_result = await db.execute(
        select(SystemErrorLog.error_type)
        .distinct()
        .order_by(SystemErrorLog.error_type)
    )
    error_types = [row[0] for row in types_result.all()]

    services_result = await db.execute(
        select(SystemErrorLog.service)
        .where(SystemErrorLog.service.isnot(None))
        .distinct()
        .order_by(SystemErrorLog.service)
    )
    services = [row[0] for row in services_result.all()]

    return {
        "error_types": error_types,
        "services": services,
        "severities": ["warning", "error", "critical"],
    }


@router.get("/stats", response_model=ErrorStatsResponse)
async def get_error_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated error statistics for the dashboard."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Total counts
    total_result = await db.execute(select(func.count(SystemErrorLog.id)))
    total_errors = total_result.scalar() or 0

    unresolved_result = await db.execute(
        select(func.count(SystemErrorLog.id)).where(
            SystemErrorLog.is_resolved == False  # noqa: E712
        )
    )
    unresolved_errors = unresolved_result.scalar() or 0

    critical_result = await db.execute(
        select(func.count(SystemErrorLog.id)).where(
            SystemErrorLog.severity == "critical",
            SystemErrorLog.is_resolved == False,  # noqa: E712
        )
    )
    critical_errors = critical_result.scalar() or 0

    today_result = await db.execute(
        select(func.count(SystemErrorLog.id)).where(
            SystemErrorLog.created_at >= today_start
        )
    )
    errors_today = today_result.scalar() or 0

    week_result = await db.execute(
        select(func.count(SystemErrorLog.id)).where(
            SystemErrorLog.created_at >= week_ago
        )
    )
    errors_this_week = week_result.scalar() or 0

    month_result = await db.execute(
        select(func.count(SystemErrorLog.id)).where(
            SystemErrorLog.created_at >= month_ago
        )
    )
    errors_this_month = month_result.scalar() or 0

    # By error type (top 10)
    type_result = await db.execute(
        select(
            SystemErrorLog.error_type,
            func.count(SystemErrorLog.id).label("count"),
            func.max(SystemErrorLog.last_seen_at).label("latest"),
        )
        .group_by(SystemErrorLog.error_type)
        .order_by(desc("count"))
        .limit(10)
    )
    by_type = [
        ErrorTypeStat(error_type=row.error_type, count=row.count, latest=row.latest)
        for row in type_result.all()
    ]

    # By service (top 10)
    service_result = await db.execute(
        select(
            func.coalesce(SystemErrorLog.service, "unknown").label("service"),
            func.count(SystemErrorLog.id).label("count"),
            func.max(SystemErrorLog.last_seen_at).label("latest"),
        )
        .group_by(SystemErrorLog.service)
        .order_by(desc("count"))
        .limit(10)
    )
    by_service = [
        ErrorServiceStat(service=row.service, count=row.count, latest=row.latest)
        for row in service_result.all()
    ]

    # Daily trend (past 30 days)
    trend_result = await db.execute(
        select(
            cast(SystemErrorLog.created_at, Date).label("date"),
            func.count(SystemErrorLog.id).label("count"),
            func.sum(
                case((SystemErrorLog.severity == "critical", 1), else_=0)
            ).label("critical"),
            func.sum(
                case((SystemErrorLog.severity == "error", 1), else_=0)
            ).label("error_count"),
            func.sum(
                case((SystemErrorLog.severity == "warning", 1), else_=0)
            ).label("warning"),
        )
        .where(SystemErrorLog.created_at >= month_ago)
        .group_by(cast(SystemErrorLog.created_at, Date))
        .order_by(cast(SystemErrorLog.created_at, Date))
    )
    daily_trend = [
        ErrorTrend(
            date=row.date,
            count=row.count,
            critical=row.critical or 0,
            error=row.error_count or 0,
            warning=row.warning or 0,
        )
        for row in trend_result.all()
    ]

    # Top recurring errors (by occurrence count, unresolved)
    recurring_result = await db.execute(
        select(SystemErrorLog)
        .where(
            SystemErrorLog.is_resolved == False,  # noqa: E712
            SystemErrorLog.occurrence_count > 1,
        )
        .order_by(desc(SystemErrorLog.occurrence_count))
        .limit(5)
    )
    recurring_errors = recurring_result.scalars().all()

    # Get user info for recurring errors
    recurring_user_ids = set()
    for e in recurring_errors:
        if e.user_id:
            recurring_user_ids.add(e.user_id)
    recurring_users_dict = {}
    if recurring_user_ids:
        ru_result = await db.execute(
            select(User).where(User.id.in_(list(recurring_user_ids)))
        )
        recurring_users_dict = {u.id: u for u in ru_result.scalars().all()}

    top_recurring = [
        _build_error_response(e, recurring_users_dict) for e in recurring_errors
    ]

    return ErrorStatsResponse(
        total_errors=total_errors,
        unresolved_errors=unresolved_errors,
        critical_errors=critical_errors,
        errors_today=errors_today,
        errors_this_week=errors_this_week,
        errors_this_month=errors_this_month,
        by_type=by_type,
        by_service=by_service,
        daily_trend=daily_trend,
        top_recurring=top_recurring,
    )


@router.get("/{error_id}", response_model=ErrorLogResponse)
async def get_error_log(
    error_id: str,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single error log by ID."""
    result = await db.execute(
        select(SystemErrorLog).where(SystemErrorLog.id == error_id)
    )
    error = result.scalar_one_or_none()
    if not error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error log not found",
        )

    user_ids = set()
    if error.user_id:
        user_ids.add(error.user_id)
    if error.resolved_by:
        user_ids.add(error.resolved_by)
    users_dict = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(list(user_ids))))
        users_dict = {u.id: u for u in users_result.scalars().all()}

    return _build_error_response(error, users_dict)


@router.put("/{error_id}", response_model=ErrorLogResponse)
async def update_error_log(
    error_id: str,
    request: ErrorLogResolveRequest,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve or unresolve an error log."""
    result = await db.execute(
        select(SystemErrorLog).where(SystemErrorLog.id == error_id)
    )
    error = result.scalar_one_or_none()
    if not error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error log not found",
        )

    error.is_resolved = request.is_resolved
    if request.is_resolved:
        error.resolved_at = datetime.now(timezone.utc)
        error.resolved_by = admin_user.id
    else:
        error.resolved_at = None
        error.resolved_by = None

    if request.resolution_notes is not None:
        error.resolution_notes = request.resolution_notes

    await db.commit()
    await db.refresh(error)

    user_ids = set()
    if error.user_id:
        user_ids.add(error.user_id)
    if error.resolved_by:
        user_ids.add(error.resolved_by)
    users_dict = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(list(user_ids))))
        users_dict = {u.id: u for u in users_result.scalars().all()}

    return _build_error_response(error, users_dict)
