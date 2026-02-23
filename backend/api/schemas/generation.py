"""
Schemas for generation tracking and admin alerts.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# --- Generation Log Schemas ---

class GenerationLogResponse(BaseModel):
    """Single generation log entry."""
    id: str
    user_id: str
    project_id: Optional[str] = None
    resource_type: str
    resource_id: str
    status: str
    error_message: Optional[str] = None
    ai_model: Optional[str] = None
    duration_ms: Optional[int] = None
    input_metadata: Optional[dict] = None
    cost_credits: int = 0
    created_at: datetime

    # Joined user info
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GenerationLogListResponse(BaseModel):
    """Paginated list of generation logs."""
    items: List[GenerationLogResponse]
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
    avg_duration_ms: Optional[int] = None

    # Total credits consumed
    total_credits: int = 0


# --- Admin Alert Schemas ---

class AdminAlertResponse(BaseModel):
    """Single admin alert."""
    id: str
    alert_type: str
    severity: str
    title: str
    message: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    is_read: bool = False
    is_resolved: bool = False
    created_at: datetime

    # Joined user info
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminAlertListResponse(BaseModel):
    """Paginated list of admin alerts."""
    items: List[AdminAlertResponse]
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
    is_read: Optional[bool] = None
    is_resolved: Optional[bool] = None
