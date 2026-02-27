# Audit Section 4 — Bulk Generation
**Date**: 2026-02-27
**Status**: Complete

---

## Scope
- Bulk job creation, queueing, and background processing
- Template system CRUD
- Job status tracking, cancellation, retry
- Error handling and partial failure recovery
- Frontend bulk hub, job detail, templates pages
- Integration with usage limits and content generation pipeline

---

## Files Audited
- `backend/api/routes/bulk.py`
- `backend/services/bulk_generation.py`
- `backend/infrastructure/database/models/bulk.py`
- `frontend/app/[locale]/(dashboard)/bulk/page.tsx`
- `frontend/app/[locale]/(dashboard)/bulk/jobs/[id]/page.tsx`
- `frontend/app/[locale]/(dashboard)/bulk/templates/page.tsx`
- `frontend/lib/api.ts` (bulk section)

---

## Findings

### CRITICAL

#### BULK-01 — All bulk outline jobs fail with TypeError (extra params bug) — CONFIRMED
- **Severity**: CRITICAL
- **File**: `backend/services/bulk_generation.py:162-171`
- **Description**: Confirmed from code: `process_bulk_outline_job()` calls `content_ai_service.generate_outline()` with three parameters (`title`, `writing_style`, `custom_instructions`) that don't exist in the method signature. Every single bulk outline job item will fail immediately with `TypeError: generate_outline() got unexpected keyword arguments`. The exception is caught at line 211 and the item is marked failed — so the job always ends as `status="failed"` with 0 completed items.
- **Fix**: Remove the three extra parameters from the call at lines 162-171. The cleaned call:
  ```python
  generated = await content_ai_service.generate_outline(
      keyword=item.keyword or "",
      tone=tone,
      target_audience=target_audience,
      word_count_target=word_count,
      language=language,
  )
  ```
  Note: `writing_style` and `custom_instructions` extracted from template config but `generate_outline()` doesn't support them yet — this must be fixed alongside GEN-01 (add those params to generate_outline).

#### BULK-02 — No rate limiting on bulk job creation
- **Severity**: CRITICAL
- **File**: `backend/api/routes/bulk.py:319`
- **Description**: The `POST /bulk/jobs/outlines` endpoint has no per-user or per-project rate limit. Only the global 100 requests/minute per-IP fallback applies. A user can create 100 bulk jobs in 60 seconds (100 × 50 keywords = 5,000 outline generation requests), each spawning a background task. This is a viable DoS vector against the AI API quota and the database.
- **Fix**: Add `@limiter.limit("5/hour")` (per user, not per IP) to the create job endpoint. Also add a pre-flight check: if the user already has N jobs in `pending`/`processing` status, reject with 429.

#### BULK-03 — Concurrent retry spawns duplicate processing tasks
- **Severity**: CRITICAL
- **File**: `backend/api/routes/bulk.py:392-429`
- **Description**: The retry endpoint resets failed items to pending and spawns a new background task, but performs no check on the current job status first. Two rapid retries:
  1. Both reset failed items to pending
  2. Both set `job.status = "processing"` and `job.failed_items = 0`
  3. Both spawn `process_bulk_outline_job()` background tasks
  4. Both iterate the same pending items and generate duplicate outlines
  There is no locking or idempotency guard.
- **Fix**: Before resetting items, check `job.status` is `"failed"` or `"partially_failed"` (not already `"processing"`). Use an atomic `UPDATE ... WHERE status IN ('failed', 'partially_failed')` that returns rowcount to detect concurrent calls.

---

### HIGH

#### BULK-04 — Templates and jobs not verified against project membership
- **Severity**: HIGH
- **Files**: `backend/api/routes/bulk.py:128-130, 169, 349`
- **Description**: Template listing and creation use `current_project_id` without verifying the user is an active member of that project. A user who knows any project UUID can set their `current_project_id` to it (via the switch endpoint) and create or access templates for that project. Similarly, bulk jobs are created with `project_id=current_user.current_project_id` without a membership check.
- **Fix**: In template list/create and job create endpoints, add an explicit `verify_project_membership(db, current_user, current_project_id)` call matching the pattern used in the articles/outlines routes.

#### BULK-05 — In-flight items continue generating after job is cancelled
- **Severity**: HIGH
- **File**: `backend/services/bulk_generation.py:298-324`
- **Description**: The cancel endpoint marks only `pending` items as cancelled. Any item currently in `processing` state continues running in the background — the asyncio task has no cancellation mechanism. After cancellation, the background task may continue to create outlines, increment usage counters, and update job counters, resulting in items that show `completed` in a `cancelled` job.
- **Fix**: Add a cancellation flag: store a `CancellationToken` or a DB flag (`job.cancel_requested=True`) that the processing loop checks at the start of each item iteration. If set, break the loop and finalize the job as cancelled.

#### BULK-06 — Usage limit not checked at job creation time
- **Severity**: HIGH
- **File**: `backend/api/routes/bulk.py:319-373`, `backend/services/bulk_generation.py:135-142`
- **Description**: Usage limits are checked per-item inside the background task. A user can create a bulk job with 50 keywords and the job starts processing before any limit check occurs. After 10 items, the limit is hit and the remaining 40 fail. The user is never told upfront that they can't generate 50 outlines this month.
- **Fix**: Before creating the job, call `check_project_limit()` once and estimate if the full job fits within remaining quota. Reject at creation time with a 429 and a message like "You have 8 outlines remaining this month. Reduce your keyword count or upgrade your plan."

#### BULK-07 — Retry endpoint doesn't check job status before resetting
- **Severity**: HIGH
- **File**: `backend/api/routes/bulk.py:392-429`
- **Description**: The retry handler resets `failed_items = 0` unconditionally and sets `job.status = "processing"` without checking if the job is actually in a retryable state (failed/partially_failed). A `completed` or `cancelled` job can be retried, corrupting its final state. Additionally, `failed_items = 0` is a hard reset — if 20 items were completed and 30 failed, after retry the counter shows 0 failed even though all 30 may fail again, making progress reporting misleading.
- **Fix**: Add a status check (`if job.status not in ("failed", "partially_failed"): raise 409`). Query the actual count of failed items to reset the counter rather than hardcoding 0.

#### BULK-08 — No loading state on job creation button
- **Severity**: HIGH
- **File**: `frontend/app/[locale]/(dashboard)/bulk/page.tsx`
- **Description**: When a user clicks "Generate N Outlines", the API call fires but the form shows no spinner or disabled state. If the request takes more than a few hundred milliseconds (common for a cold server), the user may click again, creating duplicate jobs. The optimistic update adds a fake job entry but it won't reflect the real job if the request fails.
- **Fix**: Add a `isSubmitting` state, disable the button and show a spinner during the API call. Roll back the optimistic entry if the request fails.

#### BULK-09 — Polling fetches only first 20 jobs — active jobs beyond page 1 never update
- **Severity**: HIGH
- **File**: `frontend/app/[locale]/(dashboard)/bulk/page.tsx:54-87`
- **Description**: The 5-second polling interval always requests `page_size: 20`. If the user has more than 20 jobs, older active jobs are never polled and their status never updates in the UI. A user who has run many bulk jobs will see stale `processing` indicators on older jobs.
- **Fix**: Either increase the page_size or poll active jobs separately: fetch `GET /bulk/jobs?status=processing&status=pending` without pagination to catch all in-flight jobs.

---

### MEDIUM

#### BULK-10 — Background task crash never updates job.error_summary
- **Severity**: MEDIUM
- **File**: `backend/api/routes/bulk.py:354-359`
- **Description**: The background task is spawned with `asyncio.create_task(_run())`. If the outer `_run()` function throws an unhandled exception (e.g., DB connection lost), the job stays permanently in `processing` state with no error recorded. The `error_summary` field (confirmed never populated in any code path) remains NULL.
- **Fix**: Wrap the background task in a try/except that writes to `job.error_summary` and sets `job.status = "failed"` on unhandled exceptions. Populate `error_summary` with aggregated per-item error counts on normal job completion.

#### BULK-11 — Template config accepts invalid enum values
- **Severity**: MEDIUM
- **File**: `backend/api/routes/bulk.py:42-50`, `frontend/app/[locale]/(dashboard)/bulk/templates/page.tsx`
- **Description**: The `TemplateConfigSchema` has fields for `tone` and `writing_style` but no enum validation — any string is accepted. A template with `tone: "INVALID"` is stored successfully and causes a silent misconfiguration in bulk generation. The frontend template form also has no client-side validation on these select fields.
- **Fix**: Add `Literal["professional", "friendly", "conversational", "informative", "empathetic"]` type annotation for `tone` and `Literal["editorial", "narrative", "listicle", "balanced"]` for `writing_style` in `TemplateConfigSchema`.

#### BULK-12 — Cancelled items indistinguishable from never-started items
- **Severity**: MEDIUM
- **File**: `backend/services/bulk_generation.py:304-324`
- **Description**: When a job is cancelled, pending items are marked `cancelled`. But the `job.total_items` counter includes all items, while `completed + failed` doesn't include cancelled ones. A job showing `completed=20, failed=0, total=50` after cancellation gives no indication that 30 items were cancelled vs. 30 items were never started. The job detail page can't show a "cancelled items" count.
- **Fix**: Add a `cancelled_items` counter to `BulkJob` model, increment it when items are cancelled, and include it in the response schema and frontend display.

#### BULK-13 — Broad exception catch hides AI service failure types
- **Severity**: MEDIUM
- **File**: `backend/services/bulk_generation.py:211`
- **Description**: `except Exception as e:` catches everything identically — rate limit errors, authentication failures, network timeouts, and malformed AI responses are all treated the same. The retry endpoint cannot distinguish transient errors (retry would help) from permanent ones (retry would always fail). Error message truncated to 500 chars (line 214) can lose the most useful debugging information.
- **Fix**: Catch specific exceptions (e.g., `anthropic.RateLimitError`, `anthropic.APIError`) and tag the error message with a type. Increase or remove the 500-char truncation for error messages stored in the DB.

#### BULK-14 — Orphaned outlines if process crashes between creation and item update
- **Severity**: MEDIUM
- **File**: `backend/services/bulk_generation.py:174-207`
- **Description**: The processing loop creates the Outline record and updates the BulkJobItem in the same logical block but two separate DB operations. If the process dies after the Outline is created (line 197) but before `item.status = "completed"` is committed (line 230), the Outline exists in the DB as COMPLETED content but the item remains in `processing` state. On retry, a second Outline is generated for the same keyword.
- **Fix**: Wrap the outline creation and item update in a single DB transaction. If the transaction fails, the outline is also rolled back.

#### BULK-15 — No timeout on bulk job processing (per-item or job-level)
- **Severity**: MEDIUM
- **File**: `backend/services/bulk_generation.py:162-171`
- **Description**: There is no `asyncio.wait_for()` timeout on the `generate_outline()` call per item, and no overall job timeout. If the Claude API hangs on a single item, the entire job (and its background asyncio task) hangs indefinitely. The 2-second inter-item sleep means a 50-item job takes at least 100 seconds even when everything works.
- **Fix**: Wrap each `generate_outline()` call with `asyncio.wait_for(..., timeout=120.0)`. Add a job-level watchdog: if `started_at` is more than 30 minutes ago and status is still `processing`, mark as failed.

#### BULK-16 — Keyword deduplication not performed
- **Severity**: MEDIUM
- **File**: `frontend/app/[locale]/(dashboard)/bulk/page.tsx:89-95`
- **Description**: The frontend parses keywords one-per-line but does not deduplicate. Entering the same keyword twice creates two BulkJobItem rows and generates two identical outlines. No warning is shown to the user.
- **Fix**: Deduplicate keywords in the `parseKeywords()` function and show a toast: "Removed N duplicate keywords."

---

### LOW

#### BULK-17 — Template hard-deleted (no soft delete)
- **Severity**: LOW
- **File**: `backend/api/routes/bulk.py:225-243`
- **Description**: Template deletion is a hard DELETE. The `BulkJob.template_id` FK uses `ondelete="SET NULL"` so jobs are unaffected, but there is no audit trail or recovery option. Unlike other entities in the app (Project, Article, Outline) templates have no `deleted_at`.
- **Fix**: Add `deleted_at` soft-delete to ContentTemplate model. Update the delete endpoint to set `deleted_at` instead of deleting the row.

#### BULK-18 — No template delete confirmation dialog
- **Severity**: LOW
- **File**: `frontend/app/[locale]/(dashboard)/bulk/templates/page.tsx:98`
- **Description**: Clicking delete on a template immediately fires the API call with no confirmation dialog. Unlike the project delete modal (which requires typing the name), templates can be deleted with a single click.
- **Fix**: Add a simple confirmation dialog: "Are you sure you want to delete template '{name}'?"

#### BULK-19 — Item list not paginated in job detail page
- **Severity**: LOW
- **File**: `frontend/app/[locale]/(dashboard)/bulk/jobs/[id]/page.tsx:191`
- **Description**: All items for a bulk job are loaded and rendered in a single list. For a 50-item job this is fine, but if bulk article generation is added in future (potentially hundreds of items), this will cause DOM performance issues.
- **Fix**: Add pagination or virtual scrolling to the item list.

#### BULK-20 — Missing project_id index on BulkJob and no FK on BulkJobItem.resource_id
- **Severity**: LOW
- **Files**: `backend/infrastructure/database/models/bulk.py`
- **Description**: Two schema gaps:
  1. `BulkJob.project_id` has no standalone index — project-level job filtering will do a full table scan on large datasets
  2. `BulkJobItem.resource_id` is a UUID column with no FK constraint to Outline or Article — dangling references possible if outlines are deleted
- **Fix**: Add a migration adding `Index("ix_bulk_jobs_project_id", "project_id")` to BulkJob. For resource_id FK constraint, use a polymorphic approach or simply document that it's an unenforceable soft reference.

---

## What's Working Well
- Sequential processing with 2-second inter-item sleep (prevents AI quota exhaustion)
- Per-item usage limit checks with graceful continue (processing doesn't halt on one failure)
- Retry mechanism exists and correctly resets item state
- Template config merged with brand_voice with correct precedence (template > brand_voice > defaults)
- Correct outline → BulkJobItem linkage via resource_type/resource_id
- Job status finalization logic (completed/failed/partially_failed) is correct
- 5-second polling interval in frontend is appropriate
- Composite indexes on (user_id, status) for efficient job filtering
- Template FK uses SET NULL so job records survive template deletion

---

## Fix Priority Order
1. BULK-01 — Extra params TypeError crash on every bulk job *(CRITICAL — pre-existing known bug)*
2. BULK-02 — No rate limiting on bulk job creation *(CRITICAL)*
3. BULK-03 — Concurrent retry spawns duplicate processing *(CRITICAL)*
4. BULK-04 — Templates/jobs not verified against project membership *(HIGH)*
5. BULK-05 — In-flight items continue after cancellation *(HIGH)*
6. BULK-06 — Usage limit not checked at job creation time *(HIGH)*
7. BULK-07 — Retry doesn't check job status before resetting *(HIGH)*
8. BULK-08 — No loading state on job creation button *(HIGH)*
9. BULK-09 — Polling only fetches first 20 jobs *(HIGH)*
10. BULK-10 — Background crash never updates job.error_summary *(MEDIUM)*
11. BULK-11 — Template config accepts invalid enum values *(MEDIUM)*
12. BULK-12 — Cancelled items indistinguishable in counts *(MEDIUM)*
13. BULK-13 — Broad exception catch hides failure types *(MEDIUM)*
14. BULK-14 — Orphaned outlines on crash mid-transaction *(MEDIUM)*
15. BULK-15 — No timeout on per-item or job-level processing *(MEDIUM)*
16. BULK-16 — No keyword deduplication *(MEDIUM)*
17. BULK-17 through BULK-20 — Low severity items *(LOW)*
