"""
Schemas for generation tracking and admin alerts.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

# --- Generation Log Schemas ---


class GenerationLogResponse(BaseModel):
    """Single generation log entry."""

    id: str
    user_id: str
    project_id: str | None = None
    resource_type: str
    resource_id: str
    status: str
    error_message: str | None = None
    ai_model: str | None = None
    duration_ms: int | None = None
    input_metadata: dict | None = None
    cost_credits: int = 0
    created_at: datetime

    # Joined user info
    user_email: str | None = None
    user_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class GenerationLogListResponse(BaseModel):
    """Paginated list of generation logs."""

    items: list[GenerationLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class GenerationStatsResponse(BaseModel):
    """Aggregated generation statistics."""

    total_generations: int = 0
    successful: int = 0
    failed: int = 0
    success_rate: float = 0.0

    # By type
    articles_generated: int = 0
    outlines_generated: int = 0
    images_generated: int = 0

    # By type failures
    articles_failed: int = 0
    outlines_failed: int = 0
    images_failed: int = 0

    # Average duration (ms)
    avg_duration_ms: int | None = None

    # Total credits consumed
    total_credits: int = 0


# --- Admin Alert Schemas ---


class AdminAlertResponse(BaseModel):
    """Single admin alert."""

    id: str
    alert_type: str
    severity: str
    title: str
    message: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    user_id: str | None = None
    project_id: str | None = None
    is_read: bool = False
    is_resolved: bool = False
    created_at: datetime

    # Joined user info
    user_email: str | None = None
    user_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminAlertListResponse(BaseModel):
    """Paginated list of admin alerts."""

    items: list[AdminAlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminAlertCountResponse(BaseModel):
    """Unread alert count for badge."""

    unread_count: int = 0
    critical_count: int = 0


class AdminAlertUpdateRequest(BaseModel):
    """Request to update alert status."""

    is_read: bool | None = None
    is_resolved: bool | None = None
