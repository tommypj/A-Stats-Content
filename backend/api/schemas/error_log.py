"""
Schemas for system error log API.
"""

from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- Error Log Response ---


class ErrorLogResponse(BaseModel):
    """Single system error log entry."""

    id: str
    error_type: str
    error_code: str | None = None
    severity: str
    title: str
    message: str | None = None
    stack_trace: str | None = None
    service: str | None = None
    endpoint: str | None = None
    http_method: str | None = None
    http_status: int | None = None
    request_id: str | None = None
    user_id: str | None = None
    project_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    context: dict | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    occurrence_count: int = 1
    first_seen_at: datetime
    last_seen_at: datetime
    is_resolved: bool = False
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution_notes: str | None = None
    error_fingerprint: str | None = None
    created_at: datetime

    # Joined user info
    user_email: str | None = None
    user_name: str | None = None
    resolver_email: str | None = None
    resolver_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ErrorLogListResponse(BaseModel):
    """Paginated list of error logs."""

    items: list[ErrorLogResponse]
    total: int
    page: int
    page_size: int
    pages: int


# --- Error Log Update ---


class ErrorLogResolveRequest(BaseModel):
    """Request to resolve/unresolve an error."""

    is_resolved: bool
    resolution_notes: str | None = Field(None, max_length=2000)


# --- Error Log Stats ---


class ErrorTypeStat(BaseModel):
    """Error count grouped by type."""

    error_type: str
    count: int
    latest: datetime


class ErrorServiceStat(BaseModel):
    """Error count grouped by service."""

    service: str
    count: int
    latest: datetime


class ErrorTrend(BaseModel):
    """Daily error count for trend charts."""

    date: date_type
    count: int
    critical: int = 0
    error: int = 0
    warning: int = 0


class ErrorStatsResponse(BaseModel):
    """Aggregated error statistics."""

    total_errors: int = 0
    unresolved_errors: int = 0
    critical_errors: int = 0
    errors_today: int = 0
    errors_this_week: int = 0
    errors_this_month: int = 0

    # Breakdowns
    by_type: list[ErrorTypeStat] = Field(default_factory=list)
    by_service: list[ErrorServiceStat] = Field(default_factory=list)

    # Trend (past 30 days)
    daily_trend: list[ErrorTrend] = Field(default_factory=list)

    # Top recurring errors (by fingerprint)
    top_recurring: list[ErrorLogResponse] = Field(default_factory=list)
