# Team Content Routes Implementation Guide

This document outlines the changes needed to support team ownership in all content routes for Phase 10 Multi-tenancy.

## Overview

All content routes need to be updated to support both **personal content** (team_id=NULL) and **team content** (team_id set). This ensures backward compatibility while enabling team collaboration.

## Key Principles

1. **Nullable team_id**: All content can be either personal or team-owned
2. **Backward Compatible**: Existing content remains personal by default
3. **Cascade Delete**: Team content is deleted when team is deleted
4. **Access Control**: Team members can access team content; owners can access personal content
5. **Query Parameter**: Routes accept optional `?team_id=xxx` to filter team content

## Common Pattern for All Routes

### 1. List/Query Endpoints

**Current Pattern:**
```python
@router.get("/articles")
async def list_articles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    stmt = select(Article).where(Article.user_id == current_user.id)
    # ... pagination logic
```

**Updated Pattern:**
```python
from api.deps_team import apply_content_filters, verify_team_membership

@router.get("/articles")
async def list_articles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    team_id: Optional[str] = None,  # NEW: Optional team filter
    page: int = 1,
    page_size: int = 20,
):
    # Verify team membership if team_id provided
    if team_id:
        is_member = await verify_team_membership(db, current_user, team_id)
        if not is_member:
            raise HTTPException(403, "You are not a member of this team")

    # Apply content filters (personal or team)
    stmt = select(Article)
    stmt = apply_content_filters(stmt, current_user, team_id)

    # ... rest of pagination logic
```

### 2. Create Endpoints

**Current Pattern:**
```python
@router.post("/articles")
async def create_article(
    data: ArticleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    article = Article(
        user_id=current_user.id,
        title=data.title,
        # ...
    )
```

**Updated Pattern:**
```python
from api.deps_team import validate_team_content_creation, verify_team_membership

@router.post("/articles")
async def create_article(
    data: ArticleCreate,  # ArticleCreate schema now has optional team_id
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate team content creation
    if data.team_id:
        is_member = await verify_team_membership(db, current_user, data.team_id)
        if not is_member:
            raise HTTPException(403, "You are not a member of this team")

    article = Article(
        user_id=current_user.id,
        team_id=data.team_id,  # NEW: Set team_id from request
        title=data.title,
        # ...
    )
    db.add(article)
    await db.commit()
```

### 3. Get Detail Endpoints

**Current Pattern:**
```python
@router.get("/articles/{article_id}")
async def get_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(404, "Article not found")
```

**Updated Pattern:**
```python
from api.deps_team import verify_content_access

@router.get("/articles/{article_id}")
async def get_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    # Verify access (personal or team)
    await verify_content_access(db, article, current_user)

    return article
```

### 4. Update Endpoints

**Current Pattern:**
```python
@router.put("/articles/{article_id}")
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(404, "Article not found")
```

**Updated Pattern:**
```python
from api.deps_team import verify_content_edit

@router.put("/articles/{article_id}")
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    # Verify edit permission (personal owner or team member)
    await verify_content_edit(db, article, current_user)

    # Update fields (but don't allow changing team_id)
    article.title = data.title
    # ... other fields
    # NOTE: Do NOT allow changing team_id in update

    await db.commit()
```

### 5. Delete Endpoints

**Current Pattern:**
```python
@router.delete("/articles/{article_id}")
async def delete_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if not article or article.user_id != current_user.id:
        raise HTTPException(404, "Article not found")
```

**Updated Pattern:**
```python
from api.deps_team import verify_content_edit

@router.delete("/articles/{article_id}")
async def delete_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    # Verify delete permission (same as edit)
    await verify_content_edit(db, article, current_user)

    await db.delete(article)
    await db.commit()
```

## Route-Specific Changes

### Articles Routes (`backend/api/routes/articles.py`)

#### Endpoints to Update:
1. `GET /articles` - Add `team_id` query param, use `apply_content_filters`
2. `POST /articles` - Add `team_id` to `ArticleCreate` schema, validate team membership
3. `GET /articles/{id}` - Use `verify_content_access`
4. `PUT /articles/{id}` - Use `verify_content_edit`
5. `DELETE /articles/{id}` - Use `verify_content_edit`
6. `POST /articles/{id}/publish` - Use `verify_content_edit`

#### Schema Changes:
```python
# In backend/api/schemas/content.py
class ArticleCreate(BaseModel):
    title: str
    keyword: str
    team_id: Optional[str] = None  # NEW
    # ... other fields

class ArticleResponse(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str] = None  # NEW
    title: str
    # ... other fields
```

---

### Outlines Routes (`backend/api/routes/outlines.py`)

#### Endpoints to Update:
1. `GET /outlines` - Add `team_id` query param, use `apply_content_filters`
2. `POST /outlines` - Add `team_id` to `OutlineCreate` schema, validate team membership
3. `GET /outlines/{id}` - Use `verify_content_access`
4. `PUT /outlines/{id}` - Use `verify_content_edit`
5. `DELETE /outlines/{id}` - Use `verify_content_edit`
6. `POST /outlines/{id}/generate-article` - Use `verify_content_access`

#### Schema Changes:
```python
# In backend/api/schemas/content.py
class OutlineCreate(BaseModel):
    title: str
    keyword: str
    team_id: Optional[str] = None  # NEW
    # ... other fields

class OutlineResponse(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str] = None  # NEW
    title: str
    # ... other fields
```

---

### Images Routes (`backend/api/routes/images.py`)

#### Endpoints to Update:
1. `GET /images` - Add `team_id` query param, use `apply_content_filters`
2. `POST /images/generate` - Add `team_id` to request, validate team membership
3. `GET /images/{id}` - Use `verify_content_access`
4. `DELETE /images/{id}` - Use `verify_content_edit`

#### Schema Changes:
```python
# In backend/api/schemas/content.py
class ImageGenerateRequest(BaseModel):
    prompt: str
    team_id: Optional[str] = None  # NEW
    # ... other fields

class ImageResponse(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str] = None  # NEW
    url: str
    # ... other fields
```

---

### Social Media Routes (`backend/api/routes/social.py`)

#### Endpoints to Update:
1. `GET /social/accounts` - Add `team_id` query param, use `apply_content_filters`
2. `POST /social/{platform}/connect` - Add `team_id` to connection flow
3. `GET /social/posts` - Add `team_id` query param, use `apply_content_filters`
4. `POST /social/posts` - Add `team_id` to `CreatePostRequest` schema
5. `GET /social/posts/{id}` - Use `verify_content_access`
6. `PUT /social/posts/{id}` - Use `verify_content_edit`
7. `DELETE /social/posts/{id}` - Use `verify_content_edit`

#### Schema Changes:
```python
# In backend/api/schemas/social.py
class CreatePostRequest(BaseModel):
    content: str
    team_id: Optional[str] = None  # NEW
    # ... other fields

class SocialAccountResponse(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str] = None  # NEW
    platform: str
    # ... other fields

class ScheduledPostResponse(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str] = None  # NEW
    content: str
    # ... other fields
```

---

### Knowledge Vault Routes (`backend/api/routes/knowledge.py`)

#### Endpoints to Update:
1. `GET /knowledge/sources` - Add `team_id` query param, use `apply_content_filters`
2. `POST /knowledge/upload` - Add `team_id` to upload request
3. `GET /knowledge/sources/{id}` - Use `verify_content_access`
4. `DELETE /knowledge/sources/{id}` - Use `verify_content_edit`
5. `POST /knowledge/query` - Add `team_id` to query request (searches team sources)

#### Schema Changes:
```python
# In backend/api/schemas/knowledge.py
class SourceUploadRequest(BaseModel):
    title: str
    team_id: Optional[str] = None  # NEW
    # ... other fields

class KnowledgeSourceResponse(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str] = None  # NEW
    title: str
    # ... other fields

class QueryRequest(BaseModel):
    query_text: str
    team_id: Optional[str] = None  # NEW: Search team sources
    # ... other fields
```

---

### Analytics Routes (`backend/api/routes/analytics.py`)

#### Endpoints to Update:
1. `GET /analytics/gsc/status` - Add `team_id` query param
2. `GET /analytics/gsc/auth-url` - Add `team_id` query param
3. `POST /analytics/gsc/disconnect` - Add `team_id` query param
4. `GET /analytics/gsc/keywords` - Add `team_id` query param, use `apply_content_filters`
5. `GET /analytics/gsc/pages` - Add `team_id` query param, use `apply_content_filters`
6. `GET /analytics/gsc/daily` - Add `team_id` query param, use `apply_content_filters`

#### Notes:
- GSC connection is typically one per user/team
- Analytics data (keywords, pages, daily) should filter by team_id
- Connection status should check team ownership

#### Schema Changes:
```python
# In backend/api/schemas/analytics.py
class GSCStatus(BaseModel):
    is_connected: bool
    team_id: Optional[str] = None  # NEW
    # ... other fields
```

---

## Testing Checklist

For each route file, verify:

- [ ] List endpoints accept `?team_id=xxx` query parameter
- [ ] List endpoints verify team membership before filtering
- [ ] Create endpoints accept `team_id` in request body
- [ ] Create endpoints validate team membership
- [ ] Create endpoints set `team_id` on new records
- [ ] Detail endpoints use `verify_content_access`
- [ ] Update endpoints use `verify_content_edit`
- [ ] Delete endpoints use `verify_content_edit`
- [ ] Schemas include `team_id` in Create and Response models
- [ ] Personal content (team_id=NULL) still works
- [ ] Team content cannot be accessed by non-members
- [ ] Team content can be accessed by team members

## Migration Notes

1. Run migration `011_add_team_ownership.py` to add `team_id` columns
2. Existing content will have `team_id=NULL` (personal content)
3. No data migration needed - backward compatible
4. Team model must exist before routes can create team content

## Implementation Order

Recommended implementation order:

1. **Phase 1**: Update schemas (all `*Create` and `*Response` schemas)
2. **Phase 2**: Update content routes (articles, outlines, images)
3. **Phase 3**: Update social routes (accounts, posts)
4. **Phase 4**: Update knowledge routes (sources, query)
5. **Phase 5**: Update analytics routes (GSC connection, data)
6. **Phase 6**: Test with actual Team model implementation

## Example: Complete Article Routes Update

```python
# backend/api/routes/articles.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.auth import get_current_user
from api.deps_team import (
    apply_content_filters,
    verify_content_access,
    verify_content_edit,
    verify_team_membership,
)
from infrastructure.database.models.user import User
from infrastructure.database.models.content import Article
from api.schemas.content import ArticleCreate, ArticleUpdate, ArticleResponse

router = APIRouter(prefix="/articles", tags=["articles"])

@router.get("/", response_model=list[ArticleResponse])
async def list_articles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    team_id: Optional[str] = Query(None, description="Filter by team ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List articles with optional team filter."""
    # Verify team membership if team_id provided
    if team_id:
        is_member = await verify_team_membership(db, current_user, team_id)
        if not is_member:
            raise HTTPException(403, "You are not a member of this team")

    # Build query with filters
    stmt = select(Article).order_by(Article.created_at.desc())
    stmt = apply_content_filters(stmt, current_user, team_id)

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await db.execute(stmt)
    articles = result.scalars().all()
    return articles

@router.post("/", response_model=ArticleResponse)
async def create_article(
    data: ArticleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new article (personal or team)."""
    # Validate team membership if creating team content
    if data.team_id:
        is_member = await verify_team_membership(db, current_user, data.team_id)
        if not is_member:
            raise HTTPException(403, "You are not a member of this team")

    # Create article
    article = Article(
        user_id=current_user.id,
        team_id=data.team_id,
        title=data.title,
        keyword=data.keyword,
        # ... other fields
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article

@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get article details."""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    # Verify access
    await verify_content_access(db, article, current_user)
    return article

@router.put("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update article."""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    # Verify edit permission
    await verify_content_edit(db, article, current_user)

    # Update fields (exclude team_id from updates)
    update_data = data.dict(exclude_unset=True, exclude={"team_id"})
    for field, value in update_data.items():
        setattr(article, field, value)

    await db.commit()
    await db.refresh(article)
    return article

@router.delete("/{article_id}")
async def delete_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete article."""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    # Verify delete permission
    await verify_content_edit(db, article, current_user)

    await db.delete(article)
    await db.commit()
    return {"message": "Article deleted successfully"}
```

## Summary

This implementation ensures:
- ✅ Backward compatibility (existing personal content works)
- ✅ Multi-tenancy support (team content with team_id)
- ✅ Access control (team membership verification)
- ✅ Consistent patterns across all routes
- ✅ Proper error handling (404 instead of 403 to avoid info leakage)
- ✅ Cascade deletion (team content deleted with team)

Once the Team model is implemented, update `verify_team_membership` in `deps_team.py` to query actual team membership.
