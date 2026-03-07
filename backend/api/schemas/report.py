"""SEO report schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    project_id: str | None = None
    report_type: str = Field("overview", pattern=r"^(overview|keywords|pages|content_health)$")
    date_from: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_to: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class ReportResponse(BaseModel):
    id: str
    user_id: str
    project_id: str | None
    name: str
    description: str | None
    report_type: str
    date_from: str | None
    date_to: str | None
    status: str
    error_message: str | None
    report_data: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    page: int
    page_size: int
    pages: int
