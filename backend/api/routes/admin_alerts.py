"""
Admin alerts API routes.
"""

import logging
from typing import Optional
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import get_db
from infrastructure.database.models.user import User
from infrastructure.database.models.generation import AdminAlert
from api.deps_admin import get_current_admin_user
from api.schemas.generation import (
    AdminAlertResponse,
    AdminAlertListResponse,
    AdminAlertCountResponse,
    AdminAlertUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/alerts", tags=["Admin - Alerts"])


@router.get("/count", response_model=AdminAlertCountResponse)
async def get_alert_count(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get unread and critical alert counts (for notification badge)."""
    unread_result = await db.execute(
        select(func.count()).select_from(AdminAlert).where(AdminAlert.is_read == False)
    )
    unread_count = unread_result.scalar() or 0

    critical_result = await db.execute(
        select(func.count()).select_from(AdminAlert).where(
            AdminAlert.is_read == False,
            AdminAlert.severity == "critical",
        )
    )
    critical_count = critical_result.scalar() or 0

    return AdminAlertCountResponse(
        unread_count=unread_count,
        critical_count=critical_count,
    )


@router.get("", response_model=AdminAlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    severity: Optional[str] = Query(None, description="Filter: info, warning, critical"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List admin alerts with pagination and filters."""
    query = select(AdminAlert)

    if is_read is not None:
        query = query.where(AdminAlert.is_read == is_read)
    if severity:
        query = query.where(AdminAlert.severity == severity)
    if alert_type:
        query = query.where(AdminAlert.alert_type == alert_type)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(desc(AdminAlert.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    alerts = result.scalars().all()

    # Get user info
    user_ids = list(set(a.user_id for a in alerts if a.user_id))
    users_dict = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_dict = {u.id: u for u in users_result.scalars().all()}

    items = []
    for alert in alerts:
        user = users_dict.get(alert.user_id) if alert.user_id else None
        items.append(AdminAlertResponse(
            id=alert.id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            message=alert.message,
            resource_type=alert.resource_type,
            resource_id=alert.resource_id,
            user_id=alert.user_id,
            project_id=alert.project_id,
            is_read=alert.is_read,
            is_resolved=alert.is_resolved,
            created_at=alert.created_at,
            user_email=user.email if user else None,
            user_name=user.name if user else None,
        ))

    return AdminAlertListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.put("/{alert_id}", response_model=AdminAlertResponse)
async def update_alert(
    alert_id: str,
    request: AdminAlertUpdateRequest,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an alert (mark as read/resolved)."""
    result = await db.execute(
        select(AdminAlert).where(AdminAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    if request.is_read is not None:
        alert.is_read = request.is_read
    if request.is_resolved is not None:
        alert.is_resolved = request.is_resolved

    await db.commit()
    await db.refresh(alert)

    # Look up user info if available
    user_email = None
    user_name = None
    if alert.user_id:
        user_result = await db.execute(
            select(User).where(User.id == alert.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            user_email = user.email
            user_name = user.name

    return AdminAlertResponse(
        id=alert.id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        title=alert.title,
        message=alert.message,
        resource_type=alert.resource_type,
        resource_id=alert.resource_id,
        user_id=alert.user_id,
        project_id=alert.project_id,
        is_read=alert.is_read,
        is_resolved=alert.is_resolved,
        created_at=alert.created_at,
        user_email=user_email,
        user_name=user_name,
    )


@router.post("/mark-all-read")
async def mark_all_read(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all alerts as read."""
    await db.execute(
        sql_update(AdminAlert).where(AdminAlert.is_read == False).values(is_read=True)
    )
    await db.commit()
    return {"message": "All alerts marked as read"}
