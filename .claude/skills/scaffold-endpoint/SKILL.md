---
name: scaffold-endpoint
description: Scaffold a new full-stack feature — backend endpoint, Pydantic schema, SQLAlchemy model, Alembic migration stub, frontend API client method, Next.js page, breadcrumb entry, and middleware regex. Use when user says "scaffold", "new endpoint", "new feature", "add CRUD for", or "create resource".
disable-model-invocation: true
---

# Scaffold Full-Stack Endpoint

Create all layers for a new feature in one pass. Ask the user for:
- **Resource name** (e.g., "report", "campaign")
- **Fields/schema** (or infer from context)
- **Tier gating** (free / starter / professional / agency — default: free)

## Step 1: Backend — SQLAlchemy Model

Create `backend/infrastructure/database/models/<resource>.py`:

```python
"""<Resource> database model."""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from infrastructure.database.base import Base


class <Resource>(Base):
    __tablename__ = "<resources>"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    # ... fields ...
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    user = relationship("User", back_populates="<resources>")
```

**Rules:**
- FK columns referencing `users.id` MUST use `UUID(as_uuid=True)`, never `VARCHAR(36)` (Railway will fail)
- Import and register model in `backend/infrastructure/database/models/__init__.py`

## Step 2: Backend — Pydantic Schemas

Create `backend/schemas/<resource>.py`:

```python
"""<Resource> request/response schemas."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class <Resource>Create(BaseModel):
    # ... input fields ...
    pass


class <Resource>Update(BaseModel):
    # ... optional update fields ...
    pass


class <Resource>Response(BaseModel):
    id: UUID
    # ... response fields ...
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class <Resource>ListResponse(BaseModel):
    items: list[<Resource>Response]
    total: int
    page: int
    total_pages: int
```

**Rules:**
- Unannotated class variables need `ClassVar[Set[str]]` (Pydantic v2 requirement)
- Use `model_config = {"from_attributes": True}` not the old `orm_mode`

## Step 3: Backend — FastAPI Router

Create `backend/api/routes/<resource>.py`:

```python
"""<Resource> endpoints."""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from infrastructure.database import get_db
from infrastructure.database.models.user import User
from schemas.<resource> import <Resource>Create, <Resource>Response, <Resource>ListResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=<Resource>ListResponse)
async def list_<resources>(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List <resources> for the current user."""
    # Implementation ...
    pass


@router.post("/", response_model=<Resource>Response, status_code=status.HTTP_201_CREATED)
async def create_<resource>(
    data: <Resource>Create,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new <resource>."""
    # Implementation ...
    pass


@router.get("/{<resource>_id}", response_model=<Resource>Response)
async def get_<resource>(
    <resource>_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific <resource>."""
    # Implementation ...
    pass
```

**Rules:**
- Register router in `backend/api/routes/__init__.py` or the main app router
- For slowapi rate limiting: first param must be `request: Request`, then `body` param
- Auth via `current_user: User = Depends(get_current_user)`

## Step 4: Backend — Alembic Migration

Create `backend/infrastructure/database/migrations/versions/<NNN>_add_<resource>.py`:

```python
"""Add <resource> table

Revision ID: <NNN>
Revises: <NNN-1>
Create Date: <today>
"""
from alembic import op

revision = "<NNN>"
down_revision = "<NNN-1>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = '<resources>'
        ) THEN
            CREATE TABLE <resources> (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id),
                -- ... columns ...
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ
            );
            CREATE INDEX idx_<resources>_user_id ON <resources> (user_id);
        END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS <resources>;")
```

**Rules:**
- ALL DDL wrapped in `DO $$ BEGIN IF NOT EXISTS ... END $$;` for idempotency
- Check the latest migration number: `ls backend/infrastructure/database/migrations/versions/*.py | sort -t_ -k1 -n | tail -1`
- `down_revision` must match the previous migration's `revision`

## Step 5: Frontend — API Client Method

Add to `frontend/lib/api.ts` in the appropriate section:

```typescript
// In the api object:
<resources>: {
  list: (params?: { page?: number; page_size?: number }) =>
    apiRequest<<Resource>ListResponse>({
      url: "/<resources>",
      params,
    }),
  get: (id: string) =>
    apiRequest<<Resource>Response>({
      url: `/<resources>/${id}`,
    }),
  create: (data: Create<Resource>Input) =>
    apiRequest<<Resource>Response>({
      method: "POST",
      url: "/<resources>",
      data,
    }),
},
```

Also add the TypeScript types at the top of `api.ts`:

```typescript
export interface <Resource>Response {
  id: string;
  // ... fields matching backend schema ...
  created_at: string;
  updated_at: string | null;
}

export interface <Resource>ListResponse {
  items: <Resource>Response[];
  total: number;
  page: number;
  total_pages: number;
}

export interface Create<Resource>Input {
  // ... fields ...
}
```

## Step 6: Frontend — Dashboard Page

Create `frontend/app/(dashboard)/<resources>/page.tsx`:

**Design rules (MANDATORY):**
- Use `bg-surface`, `bg-surface-secondary`, `bg-surface-tertiary` — NEVER `bg-white`
- Use `text-text-primary`, `text-text-secondary`, `text-text-muted` — NEVER `gray-*`
- Use `border-surface-tertiary` for borders
- Use `rounded-2xl` for cards, `shadow-soft` for elevation
- Errors: `toast.error(parseApiError(err).message)`
- If tier-gated, wrap with `<TierGate requiredTier="starter">` from `components/ui/tier-gate`

## Step 7: Wire Up Dashboard Route

Three files MUST be updated:

### 7a. Middleware exclusion (`frontend/middleware.ts`)
Add the route slug to the negative lookahead regex on line ~19:
```
...|site-audit|templates|reports|tags|<resources>).*)"
```

### 7b. Breadcrumb label (`frontend/components/ui/breadcrumb.tsx`)
Add to the `PATH_LABELS` map:
```typescript
"<resources>": "<Resource Display Name>",
```

### 7c. Sidebar navigation (`frontend/app/(dashboard)/layout.tsx`)
Add to the `navigation` array, either as a top-level item or submenu entry:
```typescript
{ name: "<Resource Display Name>", href: "/<resources>", icon: <LucideIcon> },
// If tier-gated:
{ name: "<Resource Display Name>", href: "/<resources>", icon: <LucideIcon>, minTier: "starter" },
```

## Checklist

Before marking complete, verify ALL of these exist:
- [ ] SQLAlchemy model created and registered
- [ ] Pydantic schemas (Create, Update, Response, ListResponse)
- [ ] FastAPI router with CRUD endpoints
- [ ] Router registered in app
- [ ] Alembic migration (idempotent DDL)
- [ ] TypeScript types in `api.ts`
- [ ] API client methods in `api.ts`
- [ ] Dashboard page component
- [ ] Middleware regex updated
- [ ] Breadcrumb PATH_LABELS updated
- [ ] Sidebar navigation entry added
