"""Article template routes."""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.rate_limit import limiter
from api.dependencies import require_tier
from api.routes.auth import get_current_user
from api.schemas.template import (
    TemplateCreateRequest,
    TemplateListResponse,
    TemplateResponse,
    TemplateUpdateRequest,
)
from infrastructure.database.connection import get_db
from infrastructure.database.models import User
from infrastructure.database.models.template import ArticleTemplate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    project_id: str | None = None,
) -> dict:
    require_tier("professional")(current_user)
    base = select(ArticleTemplate).where(
        ArticleTemplate.user_id == current_user.id,
        ArticleTemplate.deleted_at.is_(None),
    )
    if project_id:
        base = base.where(ArticleTemplate.project_id == project_id)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(
        base.order_by(ArticleTemplate.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_template(
    request: Request,
    body: TemplateCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleTemplate:
    require_tier("professional")(current_user)
    # Check uniqueness on (user_id, name)
    existing = await db.execute(
        select(ArticleTemplate).where(
            ArticleTemplate.user_id == current_user.id,
            ArticleTemplate.name == body.name,
            ArticleTemplate.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template '{body.name}' already exists",
        )

    template = ArticleTemplate(
        id=str(uuid4()),
        user_id=current_user.id,
        **body.model_dump(),
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleTemplate:
    require_tier("professional")(current_user)
    result = await db.execute(
        select(ArticleTemplate).where(
            ArticleTemplate.id == template_id,
            ArticleTemplate.user_id == current_user.id,
            ArticleTemplate.deleted_at.is_(None),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


@router.put("/{template_id}", response_model=TemplateResponse)
@limiter.limit("10/minute")
async def update_template(
    request: Request,
    template_id: str,
    body: TemplateUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleTemplate:
    require_tier("professional")(current_user)
    result = await db.execute(
        select(ArticleTemplate).where(
            ArticleTemplate.id == template_id,
            ArticleTemplate.user_id == current_user.id,
            ArticleTemplate.deleted_at.is_(None),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_template(
    request: Request,
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    require_tier("professional")(current_user)
    result = await db.execute(
        select(ArticleTemplate).where(
            ArticleTemplate.id == template_id,
            ArticleTemplate.user_id == current_user.id,
            ArticleTemplate.deleted_at.is_(None),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    template.deleted_at = datetime.now(UTC)
    await db.commit()
