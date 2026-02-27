"""
White-label agency API routes for Phase 5: White-Label Agency Mode.

Provides full CRUD for agency profiles, client workspaces, report templates,
and report generation, plus a public token-based client portal endpoint.
"""

import asyncio
import math
from datetime import date, datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from api.middleware.rate_limit import limiter
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db
from infrastructure.database.models import User
from infrastructure.database.models.agency import (
    AgencyProfile,
    ClientWorkspace,
    ReportTemplate,
    GeneratedReport,
)
from infrastructure.database.models.project import Project, ProjectMember, ProjectMemberRole

router = APIRouter(prefix="/agency", tags=["Agency"])


# ============================================================================
# Request / Response Schemas
# ============================================================================


class AgencyProfileCreate(BaseModel):
    agency_name: str = Field(..., min_length=1, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    brand_colors: Optional[dict] = None
    contact_email: Optional[str] = Field(None, max_length=255)
    footer_text: Optional[str] = None


class AgencyProfileUpdate(BaseModel):
    agency_name: Optional[str] = Field(None, min_length=1, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    brand_colors: Optional[dict] = None
    contact_email: Optional[str] = Field(None, max_length=255)
    footer_text: Optional[str] = None


class AgencyProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    agency_name: str
    logo_url: Optional[str] = None
    brand_colors: Optional[dict] = None
    custom_domain: Optional[str] = None
    contact_email: Optional[str] = None
    footer_text: Optional[str] = None
    max_clients: int
    is_active: bool
    created_at: datetime


class ClientWorkspaceCreate(BaseModel):
    project_id: str
    client_name: str = Field(..., min_length=1, max_length=255)
    client_email: Optional[str] = Field(None, max_length=255)
    client_logo_url: Optional[str] = Field(None, max_length=500)
    allowed_features: Optional[dict] = None


class ClientWorkspaceUpdate(BaseModel):
    client_name: Optional[str] = Field(None, min_length=1, max_length=255)
    client_email: Optional[str] = Field(None, max_length=255)
    client_logo_url: Optional[str] = Field(None, max_length=500)
    is_portal_enabled: Optional[bool] = None
    allowed_features: Optional[dict] = None


class ClientWorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agency_id: str
    project_id: str
    client_name: str
    client_email: Optional[str] = None
    client_logo_url: Optional[str] = None
    is_portal_enabled: bool
    portal_access_token: Optional[str] = None
    allowed_features: Optional[dict] = None
    created_at: datetime


class ReportTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    template_config: dict


class ReportTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    template_config: Optional[dict] = None


class ReportTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agency_id: str
    name: str
    template_config: dict
    created_at: datetime


class GenerateReportRequest(BaseModel):
    client_workspace_id: str
    report_template_id: Optional[str] = None
    report_type: str = Field(default="monthly", max_length=50)
    period_start: date
    period_end: date


class GeneratedReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agency_id: str
    client_workspace_id: str
    report_template_id: Optional[str] = None
    report_type: str
    period_start: date
    period_end: date
    report_data: Optional[dict] = None
    pdf_url: Optional[str] = None
    generated_at: datetime
    created_at: datetime


# ============================================================================
# Helper Functions
# ============================================================================


async def get_agency_profile(user_id: str, db: AsyncSession) -> AgencyProfile:
    """Fetch the agency profile for a user, raising 404 if it does not exist."""
    result = await db.execute(
        select(AgencyProfile).where(AgencyProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agency profile not found. Create one first.",
        )
    return profile


async def get_client_workspace_for_agency(
    workspace_id: str, agency_id: str, db: AsyncSession
) -> ClientWorkspace:
    """Fetch a client workspace belonging to the given agency, raising 404 if missing."""
    result = await db.execute(
        select(ClientWorkspace).where(
            and_(
                ClientWorkspace.id == workspace_id,
                ClientWorkspace.agency_id == agency_id,
            )
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client workspace not found",
        )
    return workspace


# ============================================================================
# Agency Profile Endpoints
# ============================================================================


@router.post(
    "/profile",
    response_model=AgencyProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_agency_profile(
    body: AgencyProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an agency profile for the current user (one per user)."""
    existing = await db.execute(
        select(AgencyProfile).where(AgencyProfile.user_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agency profile already exists for this account",
        )

    profile = AgencyProfile(
        id=str(uuid4()),
        user_id=current_user.id,
        agency_name=body.agency_name,
        logo_url=body.logo_url,
        brand_colors=body.brand_colors,
        contact_email=body.contact_email,
        footer_text=body.footer_text,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/profile", response_model=AgencyProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's agency profile."""
    return await get_agency_profile(current_user.id, db)


@router.put("/profile", response_model=AgencyProfileResponse)
async def update_agency_profile(
    body: AgencyProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's agency profile."""
    profile = await get_agency_profile(current_user.id, db)

    if body.agency_name is not None:
        profile.agency_name = body.agency_name
    if body.logo_url is not None:
        profile.logo_url = body.logo_url
    if body.brand_colors is not None:
        profile.brand_colors = body.brand_colors
    if body.contact_email is not None:
        profile.contact_email = body.contact_email
    if body.footer_text is not None:
        profile.footer_text = body.footer_text

    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("/profile", status_code=status.HTTP_200_OK)
async def delete_agency_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete the current user's agency profile (and all associated data)."""
    profile = await get_agency_profile(current_user.id, db)
    await db.delete(profile)
    await db.commit()
    return {"message": "Agency profile deleted"}


# ============================================================================
# Client Workspace Endpoints
# ============================================================================


@router.get("/clients", response_model=list[ClientWorkspaceResponse])
async def list_client_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all client workspaces belonging to the current user's agency."""
    profile = await get_agency_profile(current_user.id, db)

    result = await db.execute(
        select(ClientWorkspace)
        .where(ClientWorkspace.agency_id == profile.id)
        .order_by(ClientWorkspace.created_at.desc())
    )
    workspaces = result.scalars().all()
    return list(workspaces)


@router.post(
    "/clients",
    response_model=ClientWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_client_workspace(
    body: ClientWorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a client workspace for a project owned by the current user."""
    profile = await get_agency_profile(current_user.id, db)

    # Validate the target project exists and belongs to the current user
    proj_result = await db.execute(
        select(Project).where(
            and_(
                Project.id == body.project_id,
                Project.owner_id == current_user.id,
            )
        )
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not own it",
        )

    # Check that this project is not already wrapped in another workspace
    existing_ws = await db.execute(
        select(ClientWorkspace).where(ClientWorkspace.project_id == body.project_id)
    )
    if existing_ws.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A client workspace already exists for this project",
        )

    # Enforce max_clients limit
    count_result = await db.execute(
        select(func.count(ClientWorkspace.id)).where(
            ClientWorkspace.agency_id == profile.id
        )
    )
    current_count = count_result.scalar() or 0
    if current_count >= profile.max_clients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum client limit of {profile.max_clients} reached",
        )

    workspace = ClientWorkspace(
        id=str(uuid4()),
        agency_id=profile.id,
        project_id=body.project_id,
        client_name=body.client_name,
        client_email=body.client_email,
        client_logo_url=body.client_logo_url,
        allowed_features=body.allowed_features,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.get("/clients/{workspace_id}", response_model=ClientWorkspaceResponse)
async def get_client_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single client workspace by ID."""
    profile = await get_agency_profile(current_user.id, db)
    return await get_client_workspace_for_agency(workspace_id, profile.id, db)


@router.put("/clients/{workspace_id}", response_model=ClientWorkspaceResponse)
async def update_client_workspace(
    workspace_id: str,
    body: ClientWorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a client workspace."""
    profile = await get_agency_profile(current_user.id, db)
    workspace = await get_client_workspace_for_agency(workspace_id, profile.id, db)

    if body.client_name is not None:
        workspace.client_name = body.client_name
    if body.client_email is not None:
        workspace.client_email = body.client_email
    if body.client_logo_url is not None:
        workspace.client_logo_url = body.client_logo_url
    if body.is_portal_enabled is not None:
        workspace.is_portal_enabled = body.is_portal_enabled
    if body.allowed_features is not None:
        workspace.allowed_features = body.allowed_features

    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.delete("/clients/{workspace_id}", status_code=status.HTTP_200_OK)
async def delete_client_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a client workspace."""
    profile = await get_agency_profile(current_user.id, db)
    workspace = await get_client_workspace_for_agency(workspace_id, profile.id, db)
    await db.delete(workspace)
    await db.commit()
    return {"message": "Client workspace deleted"}


@router.post("/clients/{workspace_id}/enable-portal", response_model=ClientWorkspaceResponse)
@limiter.limit("5/minute")
async def enable_client_portal(
    workspace_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a portal access token and enable the client portal."""
    profile = await get_agency_profile(current_user.id, db)
    workspace = await get_client_workspace_for_agency(workspace_id, profile.id, db)

    workspace.portal_access_token = secrets.token_urlsafe(48)  # 64-char base64 token
    workspace.is_portal_enabled = True

    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.post("/clients/{workspace_id}/disable-portal", response_model=ClientWorkspaceResponse)
async def disable_client_portal(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable the client portal and clear the access token."""
    profile = await get_agency_profile(current_user.id, db)
    workspace = await get_client_workspace_for_agency(workspace_id, profile.id, db)

    workspace.is_portal_enabled = False
    workspace.portal_access_token = None

    await db.commit()
    await db.refresh(workspace)
    return workspace


# ============================================================================
# Report Template Endpoints
# ============================================================================


@router.get("/templates", response_model=list[ReportTemplateResponse])
async def list_report_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all report templates for the current agency."""
    profile = await get_agency_profile(current_user.id, db)

    result = await db.execute(
        select(ReportTemplate)
        .where(ReportTemplate.agency_id == profile.id)
        .order_by(ReportTemplate.created_at.desc())
    )
    templates = result.scalars().all()
    return list(templates)


@router.post(
    "/templates",
    response_model=ReportTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_report_template(
    body: ReportTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new report template for the current agency."""
    profile = await get_agency_profile(current_user.id, db)

    template = ReportTemplate(
        id=str(uuid4()),
        agency_id=profile.id,
        name=body.name,
        template_config=body.template_config,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.put("/templates/{template_id}", response_model=ReportTemplateResponse)
async def update_report_template(
    template_id: str,
    body: ReportTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a report template."""
    profile = await get_agency_profile(current_user.id, db)

    result = await db.execute(
        select(ReportTemplate).where(
            and_(
                ReportTemplate.id == template_id,
                ReportTemplate.agency_id == profile.id,
            )
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report template not found",
        )

    if body.name is not None:
        template.name = body.name
    if body.template_config is not None:
        template.template_config = body.template_config

    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_200_OK)
async def delete_report_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a report template."""
    profile = await get_agency_profile(current_user.id, db)

    result = await db.execute(
        select(ReportTemplate).where(
            and_(
                ReportTemplate.id == template_id,
                ReportTemplate.agency_id == profile.id,
            )
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report template not found",
        )

    await db.delete(template)
    await db.commit()
    return {"message": "Report template deleted"}


# ============================================================================
# Report Generation Endpoints
# ============================================================================


@router.post(
    "/reports/generate",
    response_model=GeneratedReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_report(
    body: GenerateReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an analytics report for a client workspace.

    Aggregates DailyAnalytics, PagePerformance, and ContentConversion data
    for the workspace's project over the requested date range and persists the
    result as a GeneratedReport record.
    """
    from infrastructure.database.models.analytics import DailyAnalytics, PagePerformance
    from infrastructure.database.models.revenue import ContentConversion

    profile = await get_agency_profile(current_user.id, db)

    # Validate the client workspace belongs to this agency
    workspace = await get_client_workspace_for_agency(
        body.client_workspace_id, profile.id, db
    )

    # Validate optional template reference
    template = None
    if body.report_template_id:
        tmpl_result = await db.execute(
            select(ReportTemplate).where(
                and_(
                    ReportTemplate.id == body.report_template_id,
                    ReportTemplate.agency_id == profile.id,
                )
            )
        )
        template = tmpl_result.scalar_one_or_none()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report template not found",
            )

    # -----------------------------------------------------------------------
    # Aggregate: daily clicks + impressions from DailyAnalytics
    # DailyAnalytics is keyed by user_id (the project owner), not project_id.
    # We retrieve the project owner to scope the query correctly.
    # -----------------------------------------------------------------------
    proj_result = await db.execute(
        select(Project).where(Project.id == workspace.project_id)
    )
    project = proj_result.scalar_one_or_none()
    project_owner_id = project.owner_id if project else current_user.id

    daily_agg = await db.execute(
        select(
            func.coalesce(func.sum(DailyAnalytics.total_clicks), 0).label("total_clicks"),
            func.coalesce(func.sum(DailyAnalytics.total_impressions), 0).label(
                "total_impressions"
            ),
        ).where(
            and_(
                DailyAnalytics.user_id == project_owner_id,
                DailyAnalytics.date >= body.period_start,
                DailyAnalytics.date <= body.period_end,
            )
        )
    )
    daily_row = daily_agg.one()
    total_clicks = int(daily_row.total_clicks)
    total_impressions = int(daily_row.total_impressions)

    # -----------------------------------------------------------------------
    # Aggregate: conversions + revenue from ContentConversion
    # -----------------------------------------------------------------------
    conv_agg = await db.execute(
        select(
            func.coalesce(func.sum(ContentConversion.conversions), 0).label(
                "total_conversions"
            ),
            func.coalesce(func.sum(ContentConversion.revenue), 0).label("total_revenue"),
        ).where(
            and_(
                ContentConversion.project_id == workspace.project_id,
                ContentConversion.date >= body.period_start,
                ContentConversion.date <= body.period_end,
            )
        )
    )
    conv_row = conv_agg.one()
    total_conversions = int(conv_row.total_conversions)
    total_revenue = float(conv_row.total_revenue)

    # -----------------------------------------------------------------------
    # Top pages by clicks from PagePerformance
    # -----------------------------------------------------------------------
    pages_result = await db.execute(
        select(
            PagePerformance.page_url,
            func.sum(PagePerformance.clicks).label("clicks"),
            func.sum(PagePerformance.impressions).label("impressions"),
        )
        .where(
            and_(
                PagePerformance.user_id == project_owner_id,
                PagePerformance.date >= body.period_start,
                PagePerformance.date <= body.period_end,
            )
        )
        .group_by(PagePerformance.page_url)
        .order_by(desc("clicks"))
        .limit(10)
    )
    top_pages = [
        {
            "page_url": row.page_url,
            "clicks": int(row.clicks),
            "impressions": int(row.impressions),
        }
        for row in pages_result.all()
    ]

    # -----------------------------------------------------------------------
    # Top keywords by clicks from KeywordRanking
    # -----------------------------------------------------------------------
    from infrastructure.database.models.analytics import KeywordRanking

    keywords_result = await db.execute(
        select(
            KeywordRanking.keyword,
            func.sum(KeywordRanking.clicks).label("clicks"),
            func.sum(KeywordRanking.impressions).label("impressions"),
            func.avg(KeywordRanking.position).label("avg_position"),
        )
        .where(
            and_(
                KeywordRanking.user_id == project_owner_id,
                KeywordRanking.date >= body.period_start,
                KeywordRanking.date <= body.period_end,
            )
        )
        .group_by(KeywordRanking.keyword)
        .order_by(desc("clicks"))
        .limit(10)
    )
    top_keywords = [
        {
            "keyword": row.keyword,
            "clicks": int(row.clicks),
            "impressions": int(row.impressions),
            "avg_position": round(float(row.avg_position), 2),
        }
        for row in keywords_result.all()
    ]

    report_data = {
        "total_clicks": total_clicks,
        "total_impressions": total_impressions,
        "total_conversions": total_conversions,
        "total_revenue": total_revenue,
        "top_pages": top_pages,
        "top_keywords": top_keywords,
    }

    now = datetime.now(timezone.utc)
    generated_report = GeneratedReport(
        id=str(uuid4()),
        agency_id=profile.id,
        client_workspace_id=workspace.id,
        report_template_id=template.id if template else None,
        report_type=body.report_type,
        period_start=body.period_start,
        period_end=body.period_end,
        report_data=report_data,
        generated_at=now,
    )
    db.add(generated_report)
    await db.commit()
    await db.refresh(generated_report)
    return generated_report


@router.get("/reports", response_model=list[GeneratedReportResponse])
async def list_generated_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    client_workspace_id: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List generated reports for the current agency (paginated)."""
    profile = await get_agency_profile(current_user.id, db)

    conditions = [GeneratedReport.agency_id == profile.id]
    if client_workspace_id:
        # AGY-04: Validate workspace belongs to THIS agency before filtering (prevents timing oracle).
        ws_check = await db.execute(
            select(ClientWorkspace.id).where(
                and_(
                    ClientWorkspace.id == client_workspace_id,
                    ClientWorkspace.agency_id == profile.id,
                )
            )
        )
        if not ws_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client workspace not found",
            )
        conditions.append(GeneratedReport.client_workspace_id == client_workspace_id)

    result = await db.execute(
        select(GeneratedReport)
        .where(and_(*conditions))
        .order_by(GeneratedReport.generated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    reports = result.scalars().all()
    return list(reports)


@router.get("/reports/{report_id}", response_model=GeneratedReportResponse)
async def get_generated_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single generated report by ID."""
    profile = await get_agency_profile(current_user.id, db)

    result = await db.execute(
        select(GeneratedReport).where(
            and_(
                GeneratedReport.id == report_id,
                GeneratedReport.agency_id == profile.id,
            )
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    return report


# ============================================================================
# Client Portal Endpoint (public — token-based, no auth required)
# ============================================================================


class PortalSummaryResponse(BaseModel):
    """Limited analytics summary returned to the client portal."""

    client_name: str
    agency_name: str
    allowed_features: Optional[dict] = None
    period_days: int
    total_clicks: int
    total_impressions: int
    total_conversions: int
    total_revenue: float
    top_pages: list[dict]
    top_keywords: list[dict]
    # Branding fields for white-label portal customisation
    agency_logo_url: Optional[str] = None
    brand_colors: Optional[dict] = None
    contact_email: Optional[str] = None
    footer_text: Optional[str] = None
    client_logo_url: Optional[str] = None


@router.get("/portal/{token}", response_model=PortalSummaryResponse)
async def get_portal_data(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Public client portal endpoint — no authentication required.

    Accepts a portal_access_token and returns a limited 30-day analytics
    summary for the associated client workspace.
    """
    from infrastructure.database.models.analytics import (
        DailyAnalytics,
        PagePerformance,
        KeywordRanking,
    )
    from infrastructure.database.models.revenue import ContentConversion

    # Look up the workspace by token
    ws_result = await db.execute(
        select(ClientWorkspace).where(ClientWorkspace.portal_access_token == token)
    )
    workspace = ws_result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portal not found",
        )
    if not workspace.is_portal_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client portal is not enabled",
        )

    # Fetch agency profile for branding
    agency_result = await db.execute(
        select(AgencyProfile).where(AgencyProfile.id == workspace.agency_id)
    )
    agency = agency_result.scalar_one_or_none()
    agency_name = agency.agency_name if agency else "Agency"

    # Last 30 days
    period_end = datetime.now(timezone.utc).date()
    period_start = period_end - timedelta(days=30)
    period_days = 30

    # Project owner for analytics queries
    proj_result = await db.execute(
        select(Project).where(Project.id == workspace.project_id)
    )
    project = proj_result.scalar_one_or_none()
    project_owner_id = project.owner_id if project else None

    if not project_owner_id:
        return PortalSummaryResponse(
            client_name=workspace.client_name,
            agency_name=agency_name,
            allowed_features=workspace.allowed_features,
            period_days=period_days,
            total_clicks=0,
            total_impressions=0,
            total_conversions=0,
            total_revenue=0.0,
            top_pages=[],
            top_keywords=[],
            agency_logo_url=agency.logo_url if agency else None,
            brand_colors=agency.brand_colors if agency else None,
            contact_email=agency.contact_email if agency else None,
            footer_text=agency.footer_text if agency else None,
            client_logo_url=workspace.client_logo_url,
        )

    # AGY-05: Run all aggregation queries under a 10-second timeout so a slow DB
    # doesn't hang public portal requests indefinitely.
    async def _aggregate():
        # Daily analytics aggregation
        daily_agg = await db.execute(
            select(
                func.coalesce(func.sum(DailyAnalytics.total_clicks), 0).label("total_clicks"),
                func.coalesce(func.sum(DailyAnalytics.total_impressions), 0).label(
                    "total_impressions"
                ),
            ).where(
                and_(
                    DailyAnalytics.user_id == project_owner_id,
                    DailyAnalytics.date >= period_start,
                    DailyAnalytics.date <= period_end,
                )
            )
        )
        daily_row = daily_agg.one()
        _total_clicks = int(daily_row.total_clicks)
        _total_impressions = int(daily_row.total_impressions)

        # Conversion aggregation
        conv_agg = await db.execute(
            select(
                func.coalesce(func.sum(ContentConversion.conversions), 0).label(
                    "total_conversions"
                ),
                func.coalesce(func.sum(ContentConversion.revenue), 0).label("total_revenue"),
            ).where(
                and_(
                    ContentConversion.project_id == workspace.project_id,
                    ContentConversion.date >= period_start,
                    ContentConversion.date <= period_end,
                )
            )
        )
        conv_row = conv_agg.one()
        _total_conversions = int(conv_row.total_conversions)
        _total_revenue = float(conv_row.total_revenue)

        # Top pages
        pages_result = await db.execute(
            select(
                PagePerformance.page_url,
                func.sum(PagePerformance.clicks).label("clicks"),
                func.sum(PagePerformance.impressions).label("impressions"),
            )
            .where(
                and_(
                    PagePerformance.user_id == project_owner_id,
                    PagePerformance.date >= period_start,
                    PagePerformance.date <= period_end,
                )
            )
            .group_by(PagePerformance.page_url)
            .order_by(desc("clicks"))
            .limit(5)
        )
        _top_pages = [
            {
                "page_url": row.page_url,
                "clicks": int(row.clicks),
                "impressions": int(row.impressions),
            }
            for row in pages_result.all()
        ]

        # Top keywords
        keywords_result = await db.execute(
            select(
                KeywordRanking.keyword,
                func.sum(KeywordRanking.clicks).label("clicks"),
                func.sum(KeywordRanking.impressions).label("impressions"),
                func.avg(KeywordRanking.position).label("avg_position"),
            )
            .where(
                and_(
                    KeywordRanking.user_id == project_owner_id,
                    KeywordRanking.date >= period_start,
                    KeywordRanking.date <= period_end,
                )
            )
            .group_by(KeywordRanking.keyword)
            .order_by(desc("clicks"))
            .limit(5)
        )
        _top_keywords = [
            {
                "keyword": row.keyword,
                "clicks": int(row.clicks),
                "impressions": int(row.impressions),
                "avg_position": round(float(row.avg_position), 2),
            }
            for row in keywords_result.all()
        ]
        return _total_clicks, _total_impressions, _total_conversions, _total_revenue, _top_pages, _top_keywords

    try:
        total_clicks, total_impressions, total_conversions, total_revenue, top_pages, top_keywords = (
            await asyncio.wait_for(_aggregate(), timeout=10.0)
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Portal data temporarily unavailable — please try again shortly",
        )

    return PortalSummaryResponse(
        client_name=workspace.client_name,
        agency_name=agency_name,
        allowed_features=workspace.allowed_features,
        period_days=period_days,
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        total_conversions=total_conversions,
        total_revenue=total_revenue,
        top_pages=top_pages,
        top_keywords=top_keywords,
        agency_logo_url=agency.logo_url if agency else None,
        brand_colors=agency.brand_colors if agency else None,
        contact_email=agency.contact_email if agency else None,
        footer_text=agency.footer_text if agency else None,
        client_logo_url=workspace.client_logo_url,
    )
