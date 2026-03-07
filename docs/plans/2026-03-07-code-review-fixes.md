# Code Review Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 110 remaining findings (30 HIGH, 44 MEDIUM, 36 LOW) from the 6-pass code review.

**Architecture:** Fixes are grouped into 10 parallel-safe batches. Each batch targets a specific subsystem to avoid merge conflicts on shared files. Shared files (api.ts, layout.tsx, breadcrumb.tsx) are handled in a single dedicated batch.

**Tech Stack:** FastAPI, SQLAlchemy async, Next.js 14, TypeScript, Tailwind CSS, PostgreSQL

**Source Reports:** `review-results/01-backend-security.md` through `review-results/06-architecture-integration.md`

**Already Fixed (9 criticals, commit 7a81ba3):** CRIT-01/04, CRIT-02, CRIT-03, DB-R01, DB-R02, SD-01, SD-02, C-01, C-02

---

## Batch 1: Backend Security — HIGH Priority

### Task 1.1: Rate Limits on Unprotected Endpoints

**Findings:** HIGH-01, HIGH-02, HIGH-03, HIGH-04
**Files:**
- Modify: `backend/api/routes/competitor.py` (add rate limits to analyze + delete)
- Modify: `backend/api/routes/tags.py` (add rate limits to delete + assign endpoints)
- Modify: `backend/api/routes/templates.py` (add rate limit to delete)

**Steps:**

1. In `competitor.py`, add `@limiter.limit("3/minute")` to `analyze_competitor` and `@limiter.limit("10/minute")` to `delete_analysis`. Ensure both have `request: Request` parameter.

2. In `tags.py`, add `@limiter.limit("20/minute")` to `delete_tag`, `set_article_tags`, and `set_outline_tags`. Ensure all have `request: Request` parameter.

3. In `templates.py`, add `@limiter.limit("10/minute")` to `delete_template`. Ensure it has `request: Request` parameter.

### Task 1.2: JSON-LD XSS Prevention

**Finding:** HIGH-05
**File:** `backend/services/schema_generator.py`

**Step:** After `json.dumps()` in `schemas_to_html`, escape `</` sequences:
```python
json_str = json.dumps(schema, indent=2, ensure_ascii=False).replace("</", "<\\/")
```

### Task 1.3: DNS Cache TTL in Site Auditor

**Finding:** HIGH-06
**File:** `backend/services/site_auditor.py`

**Step:** Replace the plain dict `_dns_cache` with a TTL-based cache. Add timestamp to entries and expire after 60 seconds:
```python
import time
_dns_cache: dict[str, tuple[bool, float]] = {}
DNS_CACHE_TTL = 60

def _check_dns_cache(hostname: str) -> bool | None:
    if hostname in _dns_cache:
        result, ts = _dns_cache[hostname]
        if time.time() - ts < DNS_CACHE_TTL:
            return result
        del _dns_cache[hostname]
    return None

def _set_dns_cache(hostname: str, safe: bool) -> None:
    _dns_cache[hostname] = (safe, time.time())
```

### Task 1.4: MD5 → SHA-256 for Cache Keys

**Finding:** HIGH-07
**File:** `backend/services/content_pipeline.py`

**Step:** Change `hashlib.md5(...)` to `hashlib.sha256(...)` at the cache key generation line.

### Task 1.5: Sanitize Error Messages in Knowledge Service

**Finding:** HIGH-08
**File:** `backend/services/knowledge_service.py`

**Step:** In the query error handler, replace `f"An error occurred while processing your query: {str(e)}"` with a generic message, and log the actual error:
```python
logger.error("Knowledge query failed: %s", e, exc_info=True)
return {"query": query, "answer": "An error occurred while processing your query. Please try again later.", ...}
```

---

## Batch 2: Backend Security — MEDIUM Priority

### Task 2.1: Redis Connection Pooling

**Finding:** MED-01
**File:** `backend/services/content_pipeline.py`

**Step:** Create a module-level Redis connection pool instead of creating new connections per cache operation:
```python
_redis_pool: aioredis.Redis | None = None

async def _get_redis() -> aioredis.Redis | None:
    global _redis_pool
    if _redis_pool is None:
        try:
            _redis_pool = aioredis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            return None
    return _redis_pool
```

### Task 2.2: Remove Redundant GenerationTracker

**Finding:** MED-02
**File:** `backend/services/bulk_generation.py`

**Step:** Remove the redundant `tracker = GenerationTracker(db)` at line 134 inside the loop. The one at line 121 is sufficient.

### Task 2.3: Fix f-string Logging

**Finding:** MED-03
**File:** `backend/services/social_scheduler.py`

**Step:** Replace all `logger.xxx(f"...")` with `logger.xxx("...", ...)` using `%s` placeholders throughout the file.

### Task 2.4: Path Traversal Protection

**Findings:** MED-05, MED-08
**Files:**
- `backend/services/knowledge_processor.py`
- `backend/adapters/storage/image_storage.py`

**Step:** Add `.resolve()` + `is_relative_to()` check in both `delete_file` and `delete_image` functions before unlinking.

### Task 2.5: WordPress URL Validation in Content Scheduler

**Finding:** MED-06
**File:** `backend/services/content_scheduler.py`

**Step:** Import `_validate_wp_url` from `api.routes.wordpress` and call it before making WordPress API requests in the auto-publish flow.

### Task 2.6: SSRF Protection in Competitor Analyzer

**Finding:** MED-07
**File:** `backend/services/competitor_analyzer.py`

**Step:** Add SSRF validation before HTTP requests. Import or replicate `_is_safe_url()` from `site_auditor.py`.

### Task 2.7: flush → commit in Revenue Attribution

**Finding:** MED-09
**File:** `backend/services/revenue_attribution.py`

**Step:** Change `await db.flush()` to `await db.commit()` in `generate_revenue_report`.

### Task 2.8: Competitor Analysis Timeout

**Finding:** MED-10
**File:** `backend/services/competitor_analyzer.py`

**Step:** Add `MAX_ANALYSIS_TIME = 600` constant and wrap the main analysis loop in `asyncio.wait_for(timeout=MAX_ANALYSIS_TIME)`.

### Task 2.9: Prompt Input Sanitization in Content Decay

**Finding:** MED-12
**File:** `backend/services/content_decay.py`

**Step:** Apply `_sanitize_prompt_input()` to keyword, URL, and title values before inserting into AI prompts in `generate_recovery_suggestions`.

---

## Batch 3: Backend LOW Priority

### Task 3.1: Case-Insensitive Tag Uniqueness

**Finding:** LOW-06
**File:** `backend/api/routes/tags.py`

**Step:** Change `Tag.name == body.name` to `func.lower(Tag.name) == body.name.lower()` in both create and update uniqueness checks.

### Task 3.2: Template Name Uniqueness Check

**Finding:** LOW-07
**File:** `backend/api/routes/templates.py`

**Step:** Add uniqueness check on `(user_id, name)` before creating, similar to tags.

### Task 3.3: Background Task References

**Finding:** LOW-09
**Files:** `backend/api/routes/articles.py`, `backend/api/routes/images.py`, `backend/api/routes/competitor.py`, `backend/api/routes/reports.py`

**Step:** Add a module-level `_background_tasks: set[asyncio.Task] = set()` and helper function. Use it for all `asyncio.create_task()` calls.

### Task 3.4: Image Storage URL Hack

**Finding:** LOW-08
**File:** `backend/adapters/storage/image_storage.py`

**Step:** Add `api_base_url` to Settings instead of the `:3000` → `:8000` hack. If not feasible now, add a TODO comment.

### Task 3.5: Prompt Loader Encapsulation

**Finding:** LOW-02
**File:** `backend/services/content_pipeline.py`

**Step:** Replace `prompt_loader._get_manifest()` with a public method. Add `has_prompt(name)` to the prompt loader.

---

## Batch 4: Frontend — HIGH Priority

### Task 4.1: Social OAuth CSRF State

**Finding:** H-01
**Files:**
- `frontend/app/(dashboard)/social/accounts/page.tsx`
- `frontend/app/(dashboard)/social/callback/page.tsx`

**Step:** Store `res.state` in `sessionStorage` before redirect in accounts page. Add state validation in callback page.

### Task 4.2: Fix api.projects.members.list() Return Type

**Finding:** H-02, SD-13
**File:** `frontend/lib/api.ts`

**Steps:**
1. Change `members.list` return type to `{ members: ProjectMember[] }` and destructure at call site.
2. Change `ProjectRole` from `"member"` to `"editor"`.

### Task 4.3: Type-Safe Error Handling in useRequireAuth

**Finding:** H-03
**File:** `frontend/lib/auth.ts`

**Step:** Replace `(error as any)?.response?.status` with `isAxiosError(error)` type guard.

### Task 4.4: Retry Toast Only for Idempotent Requests

**Finding:** H-04
**File:** `frontend/lib/api.ts`

**Step:** Only show retry action for GET/PUT/DELETE/HEAD methods, not POST.

### Task 4.5: GSC OAuth State in Settings/Integrations

**Findings:** H-07, M-05
**Files:**
- `frontend/app/(dashboard)/settings/integrations/page.tsx`
- `frontend/app/(dashboard)/analytics/content-health/page.tsx`

**Step:** Add `sessionStorage.setItem("gsc_oauth_state", state)` before `window.open()` in both files.

### Task 4.6: Remove Unused api.auth.refresh Parameter

**Finding:** M-03, L-06
**File:** `frontend/lib/api.ts`

**Step:** Remove the `api.auth.refresh(refreshToken)` method entirely since it's dead code.

### Task 4.7: Dashboard Error Handling

**Finding:** M-07
**File:** `frontend/app/(dashboard)/dashboard/page.tsx`

**Step:** Replace generic error message with `toast.error(parseApiError(error).message)`.

### Task 4.8: ReactQueryDevtools Guard

**Finding:** M-09
**File:** `frontend/components/providers.tsx`

**Step:** Wrap `<ReactQueryDevtools>` in `{process.env.NODE_ENV === "development" && ...}`.

### Task 4.9: Blob URL Revocation Delay

**Finding:** M-06
**File:** `frontend/lib/api.ts`

**Step:** Change immediate `URL.revokeObjectURL(url)` to `setTimeout(() => URL.revokeObjectURL(url), 1000)` in exportData.

---

## Batch 5: Schema Drift Fixes

### Task 5.1: SocialAccount Field Alignment

**Finding:** SD-03
**File:** `frontend/lib/api.ts`

**Step:** Update `SocialAccount` interface fields:
- `username` → `platform_username`
- `display_name` → `platform_display_name`
- `is_connected` → `is_active`
- `connected_at` → `last_verified_at`
- `last_error` → `verification_error`

Then fix all frontend files that reference the old field names.

### Task 5.2: WordPressPublishResponse Alignment

**Finding:** SD-05
**File:** `frontend/lib/api.ts`

**Step:** Update `WordPressPublishResponse`:
- `post_id` → `wordpress_post_id`
- `post_url` → `wordpress_url`
- Remove `success`, use `status` instead

Fix all frontend references.

### Task 5.3: Other Schema Drift (MEDIUM)

**Findings:** SD-04, SD-06, SD-07, SD-08, SD-10, SD-16, SD-17
**File:** `frontend/lib/api.ts`

**Steps:**
1. Add `total: number` to `SocialAccountListResponse`
2. Add `pages: number` to `KnowledgeSourceList`
3. Add missing fields to `KnowledgeSource`: `file_url`, `processing_started_at`, `processing_completed_at`, `updated_at`
4. Add missing fields to `KnowledgeStats`: `sources_by_type`, `recent_queries`, `avg_query_time_ms`
5. Add `keyword_researches_per_month` to backend `PlanLimits` schema
6. Create `AdminImageListItem` interface with `author` field
7. Align `AdminSystemAnalytics` to match backend `SystemHealthResponse`

---

## Batch 6: Database Fixes

### Task 6.1: Migration 053 — password_hash Type + Indexes

**Findings:** DB-R03, DB-R07, DB-R09
**File:** Create `backend/infrastructure/database/migrations/versions/053_fix_column_types_and_indexes.py`

**Step:** Idempotent migration:
- ALTER `users.password_hash` from VARCHAR(255) to TEXT
- CREATE INDEX on `site_audits.project_id`
- CREATE INDEX on `users.status`

### Task 6.2: Soft-Delete Leak Fixes

**Findings:** DB-R04, DB-R05, DB-R06
**Files:**
- `backend/api/routes/auth.py` — add `deleted_at.is_(None)` to KnowledgeSource query in data export
- `backend/api/routes/wordpress.py` — add `Project.deleted_at.is_(None)` to all Project queries
- `backend/api/routes/agency.py` — same
- `backend/api/routes/articles.py` — add `deleted_at.is_(None)` + `project_id` scope to slug check

### Task 6.3: Model JSON → JSONB

**Finding:** DB-R10
**Files:**
- `backend/infrastructure/database/models/template.py` — change `JSON` to `JSONB`
- `backend/infrastructure/database/models/report.py` — change `JSON` to `JSONB`

### Task 6.4: Tag Unique Constraint Fix

**Finding:** DB-R20
**File:** Include in migration 053 — drop existing constraint, create partial unique index with `WHERE deleted_at IS NULL`.

### Task 6.5: Template/Report deleted_at Indexes

**Findings:** DB-R21, DB-R22
**File:** Include in migration 053.

---

## Batch 7: UI/UX Fixes — HIGH Priority

### Task 7.1: Standardize Page Heading Sizes

**Finding:** UX-1.1
**Files:** ~15 dashboard pages using `text-3xl`

**Step:** Find-and-replace `text-3xl` to `text-2xl` in all dashboard page h1 headings. Ensure `font-display` is present on all.

### Task 7.2: Remove Social Module Layout Wrappers

**Finding:** UX-1.2
**Files:** 8 social/content-calendar pages

**Step:** Remove `container mx-auto p-6` wrappers. Replace with `<div className="space-y-6">`.

### Task 7.3: Inline Modals → Dialog Component

**Finding:** UX-8.1
**Files:** `outlines/page.tsx`, `agency/page.tsx`, `agency/clients/page.tsx`, `templates/page.tsx`, `tags/page.tsx`, `reports/page.tsx`

**Step:** Replace inline modal markup with `<Dialog>` component for Escape key, focus trap, ARIA attributes.

### Task 7.4: Replace btn-primary/btn-secondary CSS

**Finding:** UX-11.1
**Files:** `confirm-dialog.tsx`, `error.tsx` (2), `settings/page.tsx`, landing page components

**Step:** Replace `className="btn-primary"` with `<Button>` and `className="btn-secondary"` with `<Button variant="secondary">`.

---

## Batch 8: CSS/Tailwind Fixes

### Task 8.1: Remove Duplicate Toaster

**Finding:** CSS-5
**File:** `frontend/app/[locale]/layout.tsx`

**Step:** Remove the `<Toaster>` component from `[locale]/layout.tsx` (root layout already provides it).

### Task 8.2: bg-white → bg-surface

**Findings:** CSS-2, UX-1.4
**Files:** ~38 files

**Step:** Global find-and-replace `bg-white` with `bg-surface` in all dashboard and admin components. Keep `bg-white` only in portal pages.

### Task 8.3: Create Chart Colors Constants

**Finding:** CSS-1
**File:** Create `frontend/lib/chart-colors.ts`

**Step:** Extract all hardcoded hex values from chart components into a shared constants file.

### Task 8.4: Dead CSS Cleanup

**Findings:** CSS-7, CSS-8
**File:** `frontend/app/globals.css`

**Steps:**
1. Remove unused `.label` and `.input` classes
2. Change `<Card>` component shadow from `shadow-sm` to `shadow-soft`

### Task 8.5: Toaster Styling Fix

**Finding:** CSS-11
**File:** `frontend/app/layout.tsx`

**Step:** Change Toaster `background: "white"` to `background: "#fdfcfa"`.

---

## Batch 9: Breadcrumb + Navigation + Dead Code

### Task 9.1: Add Missing Breadcrumb Labels

**Findings:** UX-6.1, BC-01, BC-02
**File:** `frontend/components/ui/breadcrumb.tsx`

**Step:** Add entries: `"site-audit": "Site Audit"`, `"competitor-analysis": "Competitor Analysis"`, `"generate": "Generate"`, `"goals": "Goals"`, `"posts": "Posts"`, `"sources": "Sources"`, `"jobs": "Jobs"`, `"reports": "Reports"`.

### Task 9.2: Console-Only Error Fixes

**Finding:** UX-4.1
**Files:** `analytics/page.tsx`, `analytics/articles/[id]/page.tsx`, `analytics/articles/page.tsx`, `settings/integrations/page.tsx`

**Step:** Replace `console.error(...)` with `toast.error("Failed to load data")` in catch blocks.

### Task 9.3: Icon Button aria-labels

**Findings:** M-02, UX-12.1
**Files:** `project-members-list.tsx`, `project-invitations-list.tsx`, `query-input.tsx`, `images/generate/page.tsx`, `outlines/[id]/page.tsx`

**Step:** Add `aria-label` to all icon-only buttons.

### Task 9.4: Remove Dead Code

**Findings:** DC-01, DC-02, DC-03, DC-04, DC-06
**Files:**
- Delete: `frontend/components/language-switcher.tsx`
- Delete: `frontend/components/admin/activity-feed.tsx`
- Delete: `frontend/components/ui/tag-picker.tsx`
- Remove unused `ConnectSocialAccountInput` from `api.ts`
- Remove unused `UsageLimitWarning` export

---

## Batch 10: Remaining LOW Items

### Task 10.1: Error Boundary Button

**Finding:** UX-4.2
**File:** `frontend/components/ui/error-boundary.tsx`

**Step:** Replace inline button with `<Button>` component.

### Task 10.2: Unused CSS Variables

**Finding:** CSS-12
**File:** `frontend/app/globals.css`

**Step:** Remove 9 unused CSS custom properties from `:root`.

### Task 10.3: Social Brand Colors

**Finding:** CSS-9
**File:** `frontend/tailwind.config.ts`

**Step:** Add `social: { twitter, linkedin, facebook, instagram, wordpress }` colors.

### Task 10.4: f-string Logging Cleanup (Backend)

**Findings:** LOW-03, MED-03
**Files:** Multiple files in `backend/adapters/social/`, `backend/services/`

**Step:** Replace `logger.xxx(f"...")` with `logger.xxx("...", ...)` using `%s` placeholders.

### Task 10.5: Non-Idempotent Migration Documentation

**Finding:** DB-R08
**File:** Create `docs/known-tech-debt.md`

**Step:** Document that migrations 001-029 are not idempotent. No code change needed.

---

## Execution Strategy

**Parallel-safe batches (no shared file conflicts):**
- Group A: Batch 1 + Batch 2 + Batch 3 (all backend, different files)
- Group B: Batch 6 (database, isolated files)
- Group C: Batch 4 + Batch 5 (frontend api.ts shared — run sequentially)
- Group D: Batch 7 + Batch 8 (frontend pages — different files)
- Group E: Batch 9 + Batch 10 (misc cleanup)

**Recommended execution: 3 parallel agents**
- Agent 1: Group A (backend security + medium + low)
- Agent 2: Group B + C (database + frontend types)
- Agent 3: Group D + E (UI/UX + CSS + cleanup)

**Commit after each batch with descriptive message.**
