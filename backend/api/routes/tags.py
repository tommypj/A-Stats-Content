"""Tag routes — CRUD plus assign/unassign to articles and outlines."""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.rate_limit import limiter
from api.dependencies import require_tier
from api.routes.auth import get_current_user
from api.schemas.tag import (
    TagAssignRequest,
    TagCreateRequest,
    TagListResponse,
    TagResponse,
    TagUpdateRequest,
)
from infrastructure.database.connection import get_db
from infrastructure.database.models import Article, Outline, User
from infrastructure.database.models.tag import ArticleTag, OutlineTag, Tag

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tags", tags=["Tags"])


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=TagListResponse)
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
    project_id: str | None = None,
) -> dict:
    require_tier("professional")(current_user)
    base = select(Tag).where(
        Tag.user_id == current_user.id,
        Tag.deleted_at.is_(None),
    )
    if project_id:
        base = base.where(Tag.project_id == project_id)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(
        base.order_by(Tag.name.asc())
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


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_tag(
    request: Request,
    body: TagCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tag:
    require_tier("professional")(current_user)
    # Check uniqueness (case-insensitive)
    existing = await db.execute(
        select(Tag).where(
            Tag.user_id == current_user.id,
            func.lower(Tag.name) == body.name.lower(),
            Tag.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tag '{body.name}' already exists",
        )

    tag = Tag(id=str(uuid4()), user_id=current_user.id, **body.model_dump())
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.put("/{tag_id}", response_model=TagResponse)
@limiter.limit("20/minute")
async def update_tag(
    request: Request,
    tag_id: str,
    body: TagUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tag:
    require_tier("professional")(current_user)
    result = await db.execute(
        select(Tag).where(
            Tag.id == tag_id,
            Tag.user_id == current_user.id,
            Tag.deleted_at.is_(None),
        )
    )
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    update_data = body.model_dump(exclude_unset=True)

    # If renaming, check uniqueness (case-insensitive)
    if "name" in update_data and update_data["name"] != tag.name:
        dup = await db.execute(
            select(Tag).where(
                Tag.user_id == current_user.id,
                func.lower(Tag.name) == update_data["name"].lower(),
                Tag.deleted_at.is_(None),
                Tag.id != tag_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tag '{update_data['name']}' already exists",
            )

    for key, value in update_data.items():
        setattr(tag, key, value)

    await db.commit()
    await db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def delete_tag(
    request: Request,
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    require_tier("professional")(current_user)
    result = await db.execute(
        select(Tag).where(
            Tag.id == tag_id,
            Tag.user_id == current_user.id,
            Tag.deleted_at.is_(None),
        )
    )
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    tag.deleted_at = datetime.now(UTC)
    await db.commit()


# ── Assign / unassign ─────────────────────────────────────────────────────────

@router.put("/articles/{article_id}", response_model=list[TagResponse])
@limiter.limit("20/minute")
async def set_article_tags(
    request: Request,
    article_id: str,
    body: TagAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Tag]:
    require_tier("professional")(current_user)
    # Verify article ownership
    art = await db.execute(
        select(Article).where(
            Article.id == article_id,
            Article.user_id == current_user.id,
        )
    )
    if not art.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    # Verify all tags belong to user
    tags_result = await db.execute(
        select(Tag).where(
            Tag.id.in_(body.tag_ids),
            Tag.user_id == current_user.id,
            Tag.deleted_at.is_(None),
        )
    )
    valid_tags = tags_result.scalars().all()
    valid_ids = {t.id for t in valid_tags}

    # Replace all associations
    await db.execute(delete(ArticleTag).where(ArticleTag.article_id == article_id))
    for tid in valid_ids:
        db.add(ArticleTag(article_id=article_id, tag_id=tid))
    await db.commit()

    return list(valid_tags)


@router.get("/articles/{article_id}", response_model=list[TagResponse])
async def get_article_tags(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Tag]:
    require_tier("professional")(current_user)
    result = await db.execute(
        select(Tag)
        .join(ArticleTag, ArticleTag.tag_id == Tag.id)
        .where(
            ArticleTag.article_id == article_id,
            Tag.user_id == current_user.id,
            Tag.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


@router.put("/outlines/{outline_id}", response_model=list[TagResponse])
@limiter.limit("20/minute")
async def set_outline_tags(
    request: Request,
    outline_id: str,
    body: TagAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Tag]:
    require_tier("professional")(current_user)
    out = await db.execute(
        select(Outline).where(
            Outline.id == outline_id,
            Outline.user_id == current_user.id,
        )
    )
    if not out.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outline not found")

    tags_result = await db.execute(
        select(Tag).where(
            Tag.id.in_(body.tag_ids),
            Tag.user_id == current_user.id,
            Tag.deleted_at.is_(None),
        )
    )
    valid_tags = tags_result.scalars().all()
    valid_ids = {t.id for t in valid_tags}

    await db.execute(delete(OutlineTag).where(OutlineTag.outline_id == outline_id))
    for tid in valid_ids:
        db.add(OutlineTag(outline_id=outline_id, tag_id=tid))
    await db.commit()

    return list(valid_tags)


@router.get("/outlines/{outline_id}", response_model=list[TagResponse])
async def get_outline_tags(
    outline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Tag]:
    require_tier("professional")(current_user)
    result = await db.execute(
        select(Tag)
        .join(OutlineTag, OutlineTag.tag_id == Tag.id)
        .where(
            OutlineTag.outline_id == outline_id,
            Tag.user_id == current_user.id,
            Tag.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())
