"""
Centralized error logging service.

Captures errors from anywhere in the application and stores them
in the system_error_logs table for admin review and analytics.
"""

import hashlib
import logging
import traceback
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.error_log import SystemErrorLog

logger = logging.getLogger(__name__)


def _compute_fingerprint(
    error_type: str,
    service: str | None,
    endpoint: str | None,
    title: str,
) -> str:
    """Create a fingerprint to group duplicate errors."""
    raw = f"{error_type}:{service or ''}:{endpoint or ''}:{title}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


async def log_error(
    db: AsyncSession,
    *,
    error_type: str,
    title: str,
    message: str | None = None,
    severity: str = "error",
    error_code: str | None = None,
    stack_trace: str | None = None,
    service: str | None = None,
    endpoint: str | None = None,
    http_method: str | None = None,
    http_status: int | None = None,
    request_id: str | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    context: dict | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
    auto_commit: bool = True,
) -> SystemErrorLog | None:
    """
    Log a system error to the database.

    If a matching error (same fingerprint) exists and is unresolved,
    increments the occurrence count instead of creating a duplicate.
    """
    try:
        fingerprint = _compute_fingerprint(error_type, service, endpoint, title)
        now = datetime.now(timezone.utc)

        # Try to find an existing unresolved error with the same fingerprint
        result = await db.execute(
            select(SystemErrorLog).where(
                SystemErrorLog.error_fingerprint == fingerprint,
                SystemErrorLog.is_resolved == False,  # noqa: E712
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Increment occurrence count and update last_seen
            existing.occurrence_count += 1
            existing.last_seen_at = now
            # Update message/stack_trace with latest occurrence
            if message:
                existing.message = message
            if stack_trace:
                existing.stack_trace = stack_trace
            if context:
                existing.context = context
            if auto_commit:
                await db.commit()
            return existing

        # Create new error log
        error_log = SystemErrorLog(
            id=str(uuid4()),
            error_type=error_type,
            error_code=error_code,
            severity=severity,
            title=title,
            message=message,
            stack_trace=stack_trace,
            service=service,
            endpoint=endpoint,
            http_method=http_method,
            http_status=http_status,
            request_id=request_id,
            user_id=user_id,
            project_id=project_id,
            resource_type=resource_type,
            resource_id=resource_id,
            context=context,
            user_agent=user_agent,
            ip_address=ip_address,
            occurrence_count=1,
            first_seen_at=now,
            last_seen_at=now,
            error_fingerprint=fingerprint,
        )
        db.add(error_log)
        if auto_commit:
            await db.commit()
        return error_log

    except Exception as exc:
        # Never let error logging crash the application
        logger.error("Failed to log system error: %s", exc)
        if auto_commit:
            try:
                await db.rollback()
            except Exception:
                pass
        return None


async def log_exception(
    db: AsyncSession,
    exc: Exception,
    *,
    service: str | None = None,
    endpoint: str | None = None,
    http_method: str | None = None,
    http_status: int | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    context: dict | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
    severity: str = "error",
) -> SystemErrorLog | None:
    """
    Log a Python exception to the system error log.
    Extracts error type, message, and stack trace from the exception.
    """
    error_type = type(exc).__name__
    title = str(exc)[:500]
    message = str(exc)
    stack = traceback.format_exception(type(exc), exc, exc.__traceback__)
    stack_trace = "".join(stack)

    # Extract error code from common exception types
    error_code = None
    if hasattr(exc, "status_code"):
        error_code = str(exc.status_code)
        http_status = http_status or getattr(exc, "status_code", None)
    elif hasattr(exc, "status"):
        error_code = str(exc.status)

    return await log_error(
        db,
        error_type=error_type,
        title=title,
        message=message,
        severity=severity,
        error_code=error_code,
        stack_trace=stack_trace,
        service=service,
        endpoint=endpoint,
        http_method=http_method,
        http_status=http_status,
        user_id=user_id,
        project_id=project_id,
        resource_type=resource_type,
        resource_id=resource_id,
        context=context,
        user_agent=user_agent,
        ip_address=ip_address,
    )
