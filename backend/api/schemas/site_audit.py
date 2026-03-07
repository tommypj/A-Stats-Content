"""
Site Audit API schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# Request schemas


class StartAuditRequest(BaseModel):
    """Request to start a new site audit."""
    domain: str = Field(
        ..., min_length=3, max_length=255,
        description="Domain to audit (e.g. example.com)",
    )


# Response schemas


class SiteAuditResponse(BaseModel):
    """Single site audit summary."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    project_id: str | None = None
    domain: str
    status: str
    pages_crawled: int
    pages_discovered: int
    total_issues: int
    critical_issues: int
    warning_issues: int
    info_issues: int
    score: int
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class SiteAuditListResponse(BaseModel):
    """Paginated list of site audits."""
    items: list[SiteAuditResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AuditPageResponse(BaseModel):
    """Single crawled page from an audit."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    audit_id: str
    url: str
    status_code: int | None = None
    response_time_ms: int | None = None
    content_type: str | None = None
    word_count: int | None = None
    title: str | None = None
    meta_description: str | None = None
    h1_count: int = 0
    has_canonical: bool = False
    has_og_tags: bool = False
    has_structured_data: bool = False
    has_robots_meta: bool = False
    page_size_bytes: int | None = None
    issues: list | None = None
    created_at: datetime


class AuditPageListResponse(BaseModel):
    """Paginated list of audit pages."""
    items: list[AuditPageResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AuditIssueResponse(BaseModel):
    """Single issue found during an audit."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    audit_id: str
    page_id: str | None = None
    issue_type: str
    severity: str
    message: str
    details: dict | None = None
    page_url: str | None = None  # populated via join
    created_at: datetime


class AuditIssueListResponse(BaseModel):
    """Paginated list of audit issues."""
    items: list[AuditIssueResponse]
    total: int
    page: int
    page_size: int
    pages: int
