# Codebase Review Fixes — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 51 findings from the 6-pass codebase review, grouped into 15 tasks ordered by severity and dependency.

**Architecture:** Backend fixes are independent Python edits; frontend fixes touch `api.ts` types and consuming pages. DB index additions go in a single Alembic migration. Redis pooling is a cross-cutting refactor.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Next.js 14, TypeScript, React Query, Redis

---

## Task 1: Fix `check_limit` wrong arguments in bulk retry (CRIT-1)

**Files:**
- Modify: `backend/api/routes/bulk.py:510`

**Step 1: Fix the call**

```python
# Line 510 — change:
can_generate = await tracker.check_limit(str(current_user.id), "article")

# To:
can_generate = await tracker.check_limit(
    current_user.current_project_id, "article", user_id=current_user.id
)
```

**Step 2: Verify no other incorrect `check_limit` calls exist**

Run: `grep -rn "check_limit" backend/api/routes/ backend/services/`

Confirm all other calls pass `project_id` as first arg and `user_id=` as keyword.

**Step 3: Commit**

```
fix: correct check_limit arguments in bulk retry endpoint
```

---

## Task 2: Fix billing portal URL + cancel bypass + unused import (CRIT-2, HIGH-34, LOW-44)

**Files:**
- Modify: `backend/api/routes/billing.py:11,318,351-361`

**Step 1: Fix portal URL (line 318)**

```python
# Change:
portal_url = f"https://{settings.lemonsqueezy_store_id}.lemonsqueezy.com/billing"

# To:
portal_url = f"https://{settings.lemonsqueezy_store_slug}.lemonsqueezy.com/billing"
```

Also add a guard at the top of the endpoint (after the existing `lemonsqueezy_store_id` check):

```python
if not settings.lemonsqueezy_store_slug:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Billing portal not configured.",
    )
```

**Step 2: Replace raw httpx cancel with adapter (lines 351-370)**

Replace the `async with httpx.AsyncClient()` block with:

```python
adapter = LemonSqueezyAdapter()
try:
    await adapter.cancel_subscription(current_user.lemonsqueezy_subscription_id)
except Exception as e:
    logger.error("Failed to cancel subscription for user %s: %s", current_user.id, str(e))
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Failed to cancel subscription. Please try again or contact support.",
    )
```

Ensure `LemonSqueezyAdapter` is imported at the top (it already is for the checkout endpoint).

**Step 3: Remove unused `urlencode` import (line 11)**

Delete: `from urllib.parse import urlencode`

**Step 4: Commit**

```
fix: billing portal URL uses store slug, cancel uses adapter, remove unused import
```

---

## Task 3: Fix webhook idempotency TOCTOU race (CRIT-10)

**Files:**
- Modify: `backend/api/routes/billing.py:656-667`

**Step 1: Replace EXISTS+SETEX with atomic SET NX**

```python
# Replace lines 656-667 with:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url)
            redis_key = f"webhook:processed:{event_id}"
            is_new = await r.set(redis_key, "1", nx=True, ex=86400)
            await r.aclose()
            if not is_new:
                logger.info("Duplicate webhook event %s — skipping", event_id)
                return {"status": "ok", "message": "already processed"}
```

Also remove the duplicate `from infrastructure.config.settings import settings as _settings` on line 657 — use the module-level `settings` already imported.

**Step 2: Commit**

```
fix: atomic webhook idempotency check (SET NX replaces EXISTS+SETEX)
```

---

## Task 4: Fix SocialPost/SocialPostTarget type mismatches (CRIT-3, CRIT-4)

**Files:**
- Modify: `frontend/lib/api.ts:2777-2808`
- Modify: `frontend/app/(dashboard)/social/posts/[id]/page.tsx`
- Modify: `frontend/app/(dashboard)/social/history/page.tsx`

**Step 1: Update `SocialPostTarget` interface to match backend `PostTargetResponse`**

The interface at line 2777 already has the correct field names (`social_account_id`, `is_published`, `published_at`, `platform_post_url` is missing though). Verify and ensure it matches:

```typescript
export interface SocialPostTarget {
  id: string;
  social_account_id: string;
  platform: string;
  platform_username?: string;
  platform_content?: string;
  is_published: boolean;
  published_at?: string;
  platform_post_id?: string;
  platform_post_url?: string;
  publish_error?: string;
  analytics_data?: Record<string, unknown>;
}
```

**Step 2: Remove `platforms` from `SocialPost` (it doesn't exist in backend)**

The `SocialPost` interface should NOT have a `platforms` field. Platforms are derived from `targets`:

```typescript
export interface SocialPost {
  id: string;
  content: string;
  project_id?: string;
  scheduled_at?: string;
  status: SocialPostStatus;
  published_at?: string;
  article_id?: string;
  targets: SocialPostTarget[];
  created_at: string;
  updated_at: string;
}
```

**Step 3: Fix `social/history/page.tsx` — derive platforms from targets**

Find `post.platforms.join(";")` and replace with:

```typescript
// Derive platforms from targets
[...new Set(post.targets?.map(t => t.platform) || [])].join(", ")
```

Find `post.platforms.map(...)` and replace similarly.

**Step 4: Fix `social/posts/[id]/page.tsx` — use correct field names**

Replace any references to:
- `target.status` → derive from `target.is_published` (e.g., `target.is_published ? "posted" : target.publish_error ? "failed" : "pending"`)
- `target.posted_url` → `target.platform_post_url`
- `target.error_message` → `target.publish_error`

**Step 5: Commit**

```
fix: align SocialPost/SocialPostTarget types with backend schema
```

---

## Task 5: Fix ProjectMember stack (CRIT-5, CRIT-6, CRIT-7, MED-IMP3, MED-IMP5)

**Files:**
- Modify: `frontend/lib/api.ts:1421-1435,3458-3470`
- Modify: `frontend/components/project/project-members-list.tsx`
- Modify: `backend/api/routes/projects.py` (add GET members endpoint)

**Step 1: Fix `ProjectMember` interface to match backend field names**

```typescript
export interface ProjectMember {
  id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  user_avatar_url?: string;
  role: ProjectRole;
  joined_at: string;
}
```

**Step 2: Fix PUT → PATCH and return type**

```typescript
update: (projectId: string, userId: string, data: ProjectMemberUpdateRequest) =>
  apiRequest<{ success: boolean; message: string; member_id: string; new_role: string }>({
    method: "PATCH",
    url: `/projects/${projectId}/members/${userId}`,
    data,
  }),
```

**Step 3: Remove dead `add` method (no backend endpoint exists)**

Delete the `add` method and `ProjectMemberAddRequest` type if unused.

**Step 4: Add GET members endpoint to backend**

In `backend/api/routes/projects.py`, add before the PATCH endpoint:

```python
@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
async def list_project_members(
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all members of a project."""
    require_tier("starter")(current_user)
    # Verify caller is a member
    await require_project_member(project_id, current_user, db)

    result = await db.execute(
        select(ProjectMember)
        .options(joinedload(ProjectMember.user))
        .where(ProjectMember.project_id == project_id)
    )
    members = result.scalars().all()
    return [
        ProjectMemberResponse(
            id=str(m.id),
            user_id=str(m.user_id),
            user_email=m.user.email if m.user else "",
            user_name=m.user.full_name if m.user else "",
            user_avatar_url=m.user.avatar_url if m.user else None,
            role=m.role,
            joined_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in members
    ]
```

Verify `require_project_member` helper exists (check `deps_project.py`). If not, use the membership check pattern from other project endpoints.

**Step 5: Fix `project-members-list.tsx` field references**

Replace `member.name` → `member.user_name`, `member.email` → `member.user_email`, `member.avatar_url` → `member.user_avatar_url` throughout.

**Step 6: Commit**

```
fix: project members — add GET endpoint, fix types, fix PUT→PATCH
```

---

## Task 6: Fix LemonSqueezy adapter `ValueError` on missing timestamps (CRIT-8)

**Files:**
- Modify: `backend/adapters/payments/lemonsqueezy_adapter.py:69-74`

**Step 1: Guard `created_at` and `updated_at` parsing**

```python
# Replace lines 69-74 with:
_created = attributes.get("created_at") or ""
_updated = attributes.get("updated_at") or ""
...
created_at=datetime.fromisoformat(_created.replace("Z", "+00:00")) if _created else datetime.now(UTC),
updated_at=datetime.fromisoformat(_updated.replace("Z", "+00:00")) if _updated else None,
```

**Step 2: Commit**

```
fix: guard LemonSqueezy customer timestamp parsing against missing fields
```

---

## Task 7: Fix RSS XML injection (CRIT-9)

**Files:**
- Modify: `backend/api/routes/blog.py:277-278`

**Step 1: Escape author_name and category.name**

```python
# Add import at top of file:
from xml.sax.saxutils import escape as xml_escape

# Replace lines 277-278 with:
author_tag = f"      <author>{xml_escape(post.author_name)}</author>\n" if post.author_name else ""
category_tag = f"      <category>{xml_escape(post.category.name)}</category>\n" if post.category else ""
```

Also replace the manual `.replace()` escaping for `title_esc` and `desc_esc` (lines 275-276) with `xml_escape()` for consistency:

```python
title_esc = xml_escape(post.title)
desc_esc = xml_escape(desc)
```

**Step 2: Commit**

```
fix: escape all XML fields in RSS feed to prevent injection
```

---

## Task 8: Fix content_pipeline IndexError + site_auditor blocking DNS + knowledge ORDER BY (HIGH-15,16,17)

**Files:**
- Modify: `backend/services/content_pipeline.py:521`
- Modify: `backend/services/site_auditor.py:78`
- Modify: `backend/api/routes/knowledge.py:589`

**Step 1: Fix content_pipeline IndexError (line 521)**

```python
# Change:
target_section = body_sections[-1] if body_sections else outline.sections[-2]

# To:
target_section = (
    body_sections[-1]
    if body_sections
    else outline.sections[-2] if len(outline.sections) >= 2 else outline.sections[-1]
)
```

**Step 2: Fix site_auditor blocking DNS (line 78)**

```python
# Add import at top:
import asyncio

# Change line 78:
addrinfos = socket.getaddrinfo(hostname, None)

# To:
loop = asyncio.get_running_loop()
addrinfos = await loop.run_in_executor(None, socket.getaddrinfo, hostname, None)
```

**Step 3: Fix knowledge.py ORDER BY (line 589)**

```python
# Change:
select(KnowledgeChunk).where(KnowledgeChunk.source_id.in_(source_ids)).limit(50)

# To:
select(KnowledgeChunk)
    .where(KnowledgeChunk.source_id.in_(source_ids))
    .order_by(KnowledgeChunk.source_id, KnowledgeChunk.chunk_index)
    .limit(50)
```

**Step 4: Commit**

```
fix: content pipeline IndexError, async DNS resolution, deterministic chunk ordering
```

---

## Task 9: Batch `parseApiError` fix across 20+ dashboard pages (HIGH-18)

**Files:**
- Modify: All dashboard pages listed in Pass 4 findings

**Step 1: Identify all violations**

Run: `grep -rn 'toast\.error("' frontend/app/(dashboard)/ frontend/app/(admin)/ --include="*.tsx" | grep -v "parseApiError"`

**Step 2: For each file, replace `toast.error("Failed to ...")` in API catch blocks**

Pattern: In every `catch` block that catches an API call error, replace:
```typescript
toast.error("Failed to ...");
```
With:
```typescript
toast.error(parseApiError(error).message);
```

Ensure `parseApiError` is imported from `@/lib/api` in each file. Most files already import it.

**Do NOT change** validation-only toasts (e.g., `toast.error("Tag name is required")`) — those are correct.

**Step 3: Commit**

```
fix: use parseApiError for all API error toasts across dashboard pages
```

---

## Task 10: Add missing database indexes (Alembic migration) (HIGH-14,22, MED-31)

**Files:**
- Create: `backend/infrastructure/database/migrations/versions/057_add_performance_indexes.py`

**Step 1: Create migration**

```python
"""Add composite indexes for high-traffic query patterns

Revision ID: 057
Revises: 056
Create Date: 2026-03-10
"""
from alembic import op

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # article_revisions: used by _save_revision() on every article edit
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_article_revisions_article_created'
        ) THEN
            CREATE INDEX ix_article_revisions_article_created
            ON article_revisions (article_id, created_at);
        END IF;
        END $$;
    """)

    # keyword_rankings: used by every analytics query
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_keyword_rankings_user_site_date'
        ) THEN
            CREATE INDEX ix_keyword_rankings_user_site_date
            ON keyword_rankings (user_id, site_url, date);
        END IF;
        END $$;
    """)

    # page_performances: same query pattern as keyword_rankings
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_page_performances_user_site_date'
        ) THEN
            CREATE INDEX ix_page_performances_user_site_date
            ON page_performances (user_id, site_url, date);
        END IF;
        END $$;
    """)

    # site_audits: filtered by status in background tasks
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_site_audits_user_status'
        ) THEN
            CREATE INDEX ix_site_audits_user_status
            ON site_audits (user_id, status);
        END IF;
        END $$;
    """)

    # competitor_analyses: filtered by status in background tasks
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_comp_analyses_user_status'
        ) THEN
            CREATE INDEX ix_comp_analyses_user_status
            ON competitor_analyses (user_id, status);
        END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_article_revisions_article_created;")
    op.execute("DROP INDEX IF EXISTS ix_keyword_rankings_user_site_date;")
    op.execute("DROP INDEX IF EXISTS ix_page_performances_user_site_date;")
    op.execute("DROP INDEX IF EXISTS ix_site_audits_user_status;")
    op.execute("DROP INDEX IF EXISTS ix_comp_analyses_user_status;")
```

**Step 2: Commit**

```
feat: add composite indexes for analytics, revisions, and audit queries
```

---

## Task 11: Fix performance — N+1 queries, unbounded loads, Redis pool (HIGH-11,12,13, MED-23,24,40)

**Files:**
- Modify: `backend/services/generation_tracker.py:84,203`
- Modify: `backend/api/routes/admin_content.py:830`
- Modify: `backend/services/content_decay.py:95`
- Modify: `backend/services/social_scheduler.py:77`

**Step 1: Fix generation_tracker — pass user object through**

In `check_limit` and `log_success`, add optional `user` parameter to avoid re-fetching:

```python
async def check_limit(self, project_id, resource_type, user_id=None, user=None) -> bool:
    if user is None and user_id:
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
    ...
```

Same pattern for `log_success`.

**Step 2: Fix admin_content bulk delete — batch query**

Replace the per-item loop with:

```python
# Fetch all at once
result = await db.execute(select(model).where(model.id.in_(body.ids)))
items = {str(item.id): item for item in result.scalars().all()}
# Validate all exist, then delete in one go
await db.execute(delete(model).where(model.id.in_(body.ids)))
```

**Step 3: Fix content_decay — filter articles by keyword set**

```python
articles_q = select(
    Article.id, Article.keyword, Article.project_id, Article.published_url
).where(
    Article.user_id == user_id,
    Article.keyword.in_(list(current_data.keys())),
    Article.deleted_at.is_(None),
)
```

**Step 4: Fix social_scheduler — reuse Redis connection**

Move `aioredis.from_url()` to `__init__` or `start()` method, store as `self._redis`, reuse across ticks.

**Step 5: Commit**

```
perf: fix N+1 queries, unbounded loads, and Redis connection leaks
```

---

## Task 12: Fix Tags/Reports tier gating in sidebar (MED-41)

**Files:**
- Modify: `frontend/app/(dashboard)/layout.tsx` (sidebar nav)
- Modify: `frontend/app/(dashboard)/tags/page.tsx`
- Modify: `frontend/app/(dashboard)/reports/page.tsx`

**Step 1: Add `minTier` to sidebar entries**

Find Tags and Reports in the `navigation` array and add `minTier: "professional"`.

**Step 2: Add TierGate wrapper to both pages**

```tsx
import { TierGate } from "@/components/ui/tier-gate";

export default function TagsPage() {
  return (
    <TierGate requiredTier="professional">
      {/* existing page content */}
    </TierGate>
  );
}
```

**Step 3: Commit**

```
fix: gate Tags and Reports pages to professional tier in sidebar and UI
```

---

## Task 13: Code quality cleanup — dead code, duplication, conventions (HIGH-19,20,21, MED-35,36,37,38)

**Files:**
- Delete: `backend/adapters/storage/example_usage.py`
- Delete: `backend/adapters/cms/example_usage.py`
- Delete: `backend/adapters/search/example_usage.py`
- Modify: `backend/services/generation_tracker.py:87,232` (deduplicate ALLOWED_USAGE_FIELDS)
- Modify: `backend/api/routes/site_audit.py` (import `get_effective_tier` from dependencies)
- Modify: `frontend/app/(dashboard)/settings/notifications/page.tsx:66` (bg-white → bg-surface)

**Step 1: Delete example_usage.py files**

```bash
rm backend/adapters/storage/example_usage.py
rm backend/adapters/cms/example_usage.py
rm backend/adapters/search/example_usage.py
```

**Step 2: Extract ALLOWED_USAGE_FIELDS to module constant**

In `generation_tracker.py`, add at module level:

```python
_USAGE_FIELD_MAP: dict[str, str] = {
    "article": "articles_generated_this_month",
    "outline": "outlines_generated_this_month",
    "image": "images_generated_this_month",
    "social_post": "social_posts_generated_this_month",
}
```

Replace both inline dicts in `log_success` and `check_limit` with `_USAGE_FIELD_MAP`.

**Step 3: Remove duplicate `_get_user_tier` from site_audit.py**

Import and use `get_effective_tier` from `api.dependencies` instead.

**Step 4: Fix bg-white in notifications toggle**

```typescript
// Change:
"inline-block h-4 w-4 rounded-full bg-white transition-transform shadow-sm"
// To:
"inline-block h-4 w-4 rounded-full bg-surface transition-transform shadow-sm"
```

**Step 5: Commit**

```
chore: remove dead code, deduplicate tier logic and usage fields, fix design token
```

---

## Task 14: Fix remaining performance issues (MED-25,26,27,28,29,30,32)

**Files:**
- Modify: `frontend/app/(dashboard)/analytics/page.tsx` (add debounce)
- Modify: `frontend/app/(dashboard)/analytics/keywords/page.tsx` (server-side sort)
- Modify: `frontend/lib/api.ts:29` (cache eviction O(1))
- Modify: `backend/infrastructure/database/models/project.py:85` (lazy="select")

**Step 1: Add debounce to analytics date range**

In `analytics/page.tsx`, add a 300ms debounce on dateRange before triggering API calls.

**Step 2: Fix keywords page — add sort deps to useEffect, pass to API**

```tsx
useEffect(() => {
  if (isConnected) loadKeywords();
}, [isConnected, currentPage, sortField, sortOrder]);
```

**Step 3: Fix cache eviction in api.ts**

```typescript
// Change:
const firstKey = Array.from(apiCache.keys())[0];
// To:
const firstKey = apiCache.keys().next().value;
```

**Step 4: Fix Project model eager loading**

```python
# Change:
owner = relationship("User", foreign_keys=[owner_id], lazy="joined")
# To:
owner = relationship("User", foreign_keys=[owner_id], lazy="select")
```

Same for `ProjectMember.user` and `ProjectMember.inviter`. Then add explicit `joinedload`/`selectinload` at call sites that actually need the relationship.

**Step 5: Commit**

```
perf: debounce analytics, server-side keyword sort, O(1) cache eviction, lazy relationships
```

---

## Task 15: Remaining low-severity fixes (LOW-42 through LOW-51)

**Files:**
- Modify: `backend/adapters/payments/lemonsqueezy_adapter.py` (remove unused methods, fix logging)
- Modify: `backend/api/routes/admin_blog.py:582` (Field(default_factory=list))
- Modify: `backend/services/content_pipeline.py:576` (use settings for model name)
- Modify: `backend/services/generation_tracker.py:110` (remove unused params from log_failure)
- Modify: `backend/api/routes/agency.py:880` (add rate limit to portal endpoint)

**Step 1: Clean up LemonSqueezy adapter**

- Remove deprecated `get_checkout_url()` method
- Remove broken `get_customer_portal_url()` stub
- Remove unused `create_lemonsqueezy_adapter()` factory
- Convert f-string logging to lazy `%s` style
- Remove checkout URL from log (PII leak)

**Step 2: Fix admin_blog mutable default**

```python
# Change:
secondary_keywords: list[str] = []
entities: list[str] = []
# To:
secondary_keywords: list[str] = Field(default_factory=list)
entities: list[str] = Field(default_factory=list)
```

**Step 3: Fix hardcoded model name**

```python
# Change:
models_used["fact_repair"] = "claude-haiku-4-5-20251001"
# To:
models_used["fact_repair"] = settings.anthropic_haiku_model
```

Verify `settings.anthropic_haiku_model` exists; if not, use the appropriate settings key.

**Step 4: Clean up generation_tracker.log_failure signature**

Remove unused params: `user_id`, `project_id`, `resource_type`, `resource_id`.

**Step 5: Add rate limit to portal endpoint**

```python
@router.get("/portal/{token}", response_model=PortalSummaryResponse)
@limiter.limit("30/minute")
async def get_portal_data(
    request: Request,  # add as first param for slowapi
    token: str,
    db: AsyncSession = Depends(get_db),
):
```

**Step 6: Commit**

```
chore: clean up adapter dead code, fix defaults, add rate limit, remove unused params
```

---

## Execution Order

Tasks are ordered by severity and dependency:

| Task | Severity | Description | Est. Complexity |
|------|----------|-------------|-----------------|
| 1 | CRIT | bulk.py check_limit fix | Trivial |
| 2 | CRIT | billing portal URL + cancel + import | Small |
| 3 | CRIT | webhook idempotency race | Small |
| 4 | CRIT | SocialPost type alignment | Medium |
| 5 | CRIT | ProjectMember full stack fix | Medium-Large |
| 6 | CRIT | LS adapter timestamp guard | Trivial |
| 7 | CRIT | RSS XML injection | Small |
| 8 | HIGH | pipeline/auditor/knowledge fixes | Small |
| 9 | HIGH | parseApiError batch fix | Medium (many files) |
| 10 | HIGH | Database indexes migration | Small |
| 11 | HIGH | N+1 queries + Redis pool | Medium |
| 12 | MED | Tags/Reports tier gating | Small |
| 13 | MED | Dead code + duplication cleanup | Medium |
| 14 | MED | Performance fixes | Medium |
| 15 | LOW | Adapter cleanup + misc | Medium |
