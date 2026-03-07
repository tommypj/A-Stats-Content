"""
Site Audit API routes.
"""

import asyncio
import csv
import io
import logging
import math
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from api.middleware.rate_limit import limiter
from api.routes.auth import get_current_user
from api.schemas.site_audit import (
    AuditIssueListResponse,
    AuditIssueResponse,
    AuditPageListResponse,
    AuditPageResponse,
    SiteAuditListResponse,
    SiteAuditResponse,
    StartAuditRequest,
)
from core.plans import PLANS
from infrastructure.database.connection import get_db
from infrastructure.database.models.site_audit import AuditIssue, AuditPage, SiteAudit
from infrastructure.database.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/site-audit", tags=["site-audit"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_domain(raw: str) -> str:
    """Strip protocol, path, and trailing slash from domain input."""
    d = raw.strip().lower()
    if d.startswith("http://"):
        d = d[7:]
    elif d.startswith("https://"):
        d = d[8:]
    d = d.split("/")[0].split("?")[0].split("#")[0]
    d = d.rstrip(".")
    if not re.match(
        r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$", d
    ):
        raise HTTPException(status_code=422, detail="Invalid domain format")
    return d


def _get_user_tier(user: User) -> str:
    """Resolve the user's effective subscription tier, falling back to free."""
    tier = user.subscription_tier or "free"
    now = datetime.now(UTC)
    if user.subscription_expires and user.subscription_expires < now:
        tier = "free"
    return tier


async def _get_audit_or_404(
    audit_id: str, user_id: str, db: AsyncSession
) -> SiteAudit:
    """Fetch an audit owned by the user or raise 404."""
    result = await db.execute(
        select(SiteAudit).where(
            SiteAudit.id == audit_id,
            SiteAudit.user_id == user_id,
        )
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit


def _generate_csv(issues_with_urls: list) -> str:
    """Render audit issues as a CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["URL", "Issue Type", "Severity", "Message", "Details"])
    for row in issues_with_urls:
        writer.writerow([
            row.url or "Site-wide",
            row.issue_type,
            row.severity,
            row.message,
            str(row.details or ""),
        ])
    output.seek(0)
    return output.getvalue()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/start", response_model=SiteAuditResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
async def start_audit(
    body: StartAuditRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a site audit for the given domain."""
    domain = _normalize_domain(body.domain)

    # ---- Tier gate --------------------------------------------------------
    tier = _get_user_tier(current_user)
    plan = PLANS.get(tier, PLANS["free"])
    limits = plan.get("limits", {})
    audits_per_month = limits.get("site_audits_per_month", 0)

    if audits_per_month == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Site audit is a premium feature. Upgrade to access.",
        )

    # ---- Monthly usage check ----------------------------------------------
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count_result = await db.execute(
        select(func.count()).select_from(
            select(SiteAudit)
            .where(
                SiteAudit.user_id == current_user.id,
                SiteAudit.created_at >= month_start,
            )
            .subquery()
        )
    )
    monthly_count = count_result.scalar() or 0

    if audits_per_month != -1 and monthly_count >= audits_per_month:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Monthly audit limit reached ({audits_per_month}). Upgrade for more.",
        )

    # ---- Check for in-progress audit on same domain -----------------------
    in_progress_result = await db.execute(
        select(SiteAudit).where(
            SiteAudit.user_id == current_user.id,
            SiteAudit.domain == domain,
            SiteAudit.status.in_(["pending", "crawling", "analyzing"]),
        ).order_by(SiteAudit.created_at.desc()).limit(1)
    )
    existing = in_progress_result.scalar_one_or_none()
    if existing:
        return existing

    # ---- Create audit row -------------------------------------------------
    audit = SiteAudit(
        id=str(uuid4()),
        user_id=current_user.id,
        project_id=getattr(current_user, "current_project_id", None),
        domain=domain,
        status="pending",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    # ---- Launch background crawl ------------------------------------------
    from services.site_auditor import run_site_audit

    asyncio.create_task(run_site_audit(audit.id))
    logger.info(
        "Started site audit %s for domain %s (user: %s)",
        audit.id, domain, current_user.id,
    )

    return audit


@router.get("/audits", response_model=SiteAuditListResponse)
async def list_audits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    audit_status: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's site audits, newest first."""
    base_query = select(SiteAudit).where(SiteAudit.user_id == current_user.id)

    if audit_status:
        base_query = base_query.where(SiteAudit.status == audit_status)

    # Count
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    # Fetch page
    items_result = await db.execute(
        base_query.order_by(SiteAudit.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = items_result.scalars().all()

    return SiteAuditListResponse(
        items=[SiteAuditResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/audits/{audit_id}", response_model=SiteAuditResponse)
async def get_audit(
    audit_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single site audit by ID."""
    audit = await _get_audit_or_404(audit_id, current_user.id, db)
    return SiteAuditResponse.model_validate(audit)


@router.get("/audits/{audit_id}/pages", response_model=AuditPageListResponse)
async def list_audit_pages(
    audit_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    has_issues: bool | None = Query(None),
    min_status_code: int | None = Query(None, ge=100, le=599),
    max_status_code: int | None = Query(None, ge=100, le=599),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List crawled pages for an audit, ordered by URL."""
    await _get_audit_or_404(audit_id, current_user.id, db)

    base_query = select(AuditPage).where(AuditPage.audit_id == audit_id)

    if has_issues is True:
        base_query = base_query.where(AuditPage.issues_json.isnot(None))
    elif has_issues is False:
        base_query = base_query.where(AuditPage.issues_json.is_(None))

    if min_status_code is not None:
        base_query = base_query.where(AuditPage.status_code >= min_status_code)
    if max_status_code is not None:
        base_query = base_query.where(AuditPage.status_code <= max_status_code)

    # Count
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    # Fetch page
    items_result = await db.execute(
        base_query.order_by(AuditPage.url.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = items_result.scalars().all()

    items = []
    for p in rows:
        resp = AuditPageResponse.model_validate(p)
        # Map the model's issues_json attribute to the schema's issues field
        resp.issues = p.issues_json
        items.append(resp)

    return AuditPageListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/audits/{audit_id}/issues", response_model=AuditIssueListResponse)
async def list_audit_issues(
    audit_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: str | None = Query(None),
    issue_type: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List issues for an audit, ordered by severity (critical first)."""
    await _get_audit_or_404(audit_id, current_user.id, db)

    base_query = select(
        AuditIssue,
        AuditPage.url.label("page_url"),
    ).outerjoin(
        AuditPage, AuditIssue.page_id == AuditPage.id
    ).where(
        AuditIssue.audit_id == audit_id
    )

    if severity:
        base_query = base_query.where(AuditIssue.severity == severity)
    if issue_type:
        base_query = base_query.where(AuditIssue.issue_type == issue_type)

    # Count
    count_sub = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_sub)
    total = count_result.scalar() or 0

    # Severity ordering: critical=0, warning=1, info=2
    severity_order = case(
        (AuditIssue.severity == "critical", 0),
        (AuditIssue.severity == "warning", 1),
        else_=2,
    )

    items_result = await db.execute(
        base_query.order_by(severity_order, AuditIssue.created_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = items_result.all()

    items = []
    for issue, page_url in rows:
        resp = AuditIssueResponse.model_validate(issue)
        resp.page_url = page_url
        items.append(resp)

    return AuditIssueListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.delete("/audits/{audit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit(
    audit_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a site audit and all associated pages/issues (cascade)."""
    audit = await _get_audit_or_404(audit_id, current_user.id, db)
    await db.delete(audit)
    await db.commit()


@router.get("/audits/{audit_id}/export")
async def export_audit_csv(
    audit_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all audit issues as a downloadable CSV."""
    audit = await _get_audit_or_404(audit_id, current_user.id, db)

    result = await db.execute(
        select(
            AuditIssue.issue_type,
            AuditIssue.severity,
            AuditIssue.message,
            AuditIssue.details,
            AuditPage.url,
        )
        .outerjoin(AuditPage, AuditIssue.page_id == AuditPage.id)
        .where(AuditIssue.audit_id == audit_id)
        .order_by(AuditIssue.severity, AuditIssue.created_at)
    )
    rows = result.all()

    csv_content = _generate_csv(rows)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    filename = f"site-audit-{audit.domain}-{today}.csv"

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
