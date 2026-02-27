# Audit Section 6 — Knowledge Vault
**Date**: 2026-02-27
**Status**: Complete

---

## Scope
- Knowledge source upload, processing, and management
- Knowledge query endpoint and chunk retrieval
- Knowledge stats endpoint
- Database models, migrations, and indexing
- Frontend pages: sources list, source detail, query page, upload modal

---

## Files Audited
- `backend/api/routes/knowledge.py`
- `backend/services/knowledge_service.py`
- `backend/services/knowledge_processor.py`
- `backend/infrastructure/database/models/knowledge.py`
- `backend/infrastructure/database/migrations/versions/006_create_knowledge_tables.py`
- `frontend/app/[locale]/(dashboard)/knowledge/` (all pages)
- `frontend/components/knowledge/upload-modal.tsx`
- `frontend/components/knowledge/source-card.tsx`
- `frontend/components/knowledge/query-input.tsx`

---

## Findings

### CRITICAL

#### KV-01 — Source ID enumeration via error message (IDOR discovery)
- **Severity**: CRITICAL
- **File**: `backend/api/routes/knowledge.py:502-506`
- **Description**: When the query endpoint receives a `source_ids` list, it fetches matching sources and compares count: `if len(sources) != len(request.source_ids): raise HTTPException(404, "One or more specified sources not found")`. The difference between a 404 ("sources not found") and a 200 lets any authenticated user enumerate valid source UUIDs belonging to other users by passing arbitrary IDs. The error message leaks that at least one ID was valid if a mixed batch returns 200.
- **Fix**: After fetching sources, do not leak which IDs were valid vs. invalid. Use a generic "You do not have access to one or more requested sources" message and return 403 (not 404, which confirms non-existence).

---

### HIGH

#### KV-02 — No rate limiting on upload or query endpoints
- **Severity**: HIGH
- **File**: `backend/api/routes/knowledge.py` (all endpoint decorators — lines 167, 281, 351, 392, 440, 476, 607, 681)
- **Description**: None of the knowledge vault endpoints have `@limiter.limit()` decorators. The upload endpoint triggers file processing (CPU-intensive extraction + chunking). The query endpoint loads all user chunks into memory and scores them. A user can fire unlimited requests: upload spam causes storage exhaustion and processing queue saturation; query spam causes repeated memory spikes. Confirmed by test file comments: "Rate limiting middleware is not implemented."
- **Fix**: Add `@limiter.limit("5/minute")` on `/upload`, `@limiter.limit("20/minute")` on `/query`, `@limiter.limit("5/hour")` on `/reprocess`. Use per-user limits (not per-IP).

#### KV-03 — Stats endpoint counts queries across all projects (cross-project info leak)
- **Severity**: HIGH
- **File**: `backend/api/routes/knowledge.py:640-645`
- **Description**: The `/stats` endpoint correctly scopes source counts to `current_project_id` via `_build_ownership_filter()`, but the query count section uses only `KnowledgeQuery.user_id == current_user.id` — no project filter. A user in multiple projects sees an aggregated query count across all their projects, not just the current one. This leaks usage information from other projects.
- **Fix**: Apply the same ownership filter to the query count: join `KnowledgeQuery` to `KnowledgeSource` and filter via `KnowledgeSource.project_id == current_user.current_project_id` (or match the personal workspace filter for non-project users).

#### KV-04 — File path not validated before deletion (path traversal risk)
- **Severity**: HIGH
- **File**: `backend/api/routes/knowledge.py:465-466`
- **Description**: The delete endpoint calls `kp.delete_file(source.file_url)` without validating that `file_url` is within the allowed storage directory. The reprocess endpoint at line 722-730 correctly validates the path using `resolved.is_relative_to(KNOWLEDGE_STORAGE_DIR)`, but delete skips this check entirely. If `file_url` in the DB is ever tampered with (via a separate DB vulnerability or admin interface), a path like `../../etc/passwd` could be targeted for deletion.
- **Fix**: Extract the path validation into a shared helper `_validate_file_url(file_url)` and call it in the delete endpoint before `kp.delete_file()`. Consider storing only filename in DB and reconstructing the full path from a known base directory.

#### KV-05 — `knowledge_service.py` loads all sources unbounded into memory
- **Severity**: HIGH
- **File**: `backend/services/knowledge_service.py:412-431`
- **Description**: The stats computation in `knowledge_service.py` executes `SELECT * FROM knowledge_sources WHERE user_id=?` with no LIMIT, loading all source objects into Python memory. For a user with 10,000 sources, this is a full table load. Then it counts `completed`, `failed`, etc. by iterating in Python rather than using SQL aggregate functions.
- **Fix**: Replace with DB-level aggregates:
  ```python
  total = await db.scalar(select(func.count(KnowledgeSource.id)).where(filter))
  completed = await db.scalar(select(func.count(KnowledgeSource.id)).where(
      and_(filter, KnowledgeSource.status == "completed")))
  ```

#### KV-06 — `query_knowledge` loads all chunks unbounded — O(N) memory per query
- **Severity**: HIGH
- **File**: `backend/api/routes/knowledge.py:533-536`
- **Description**: When processing a query, the endpoint fetches ALL chunks for ALL of the user's completed sources with no LIMIT: `select(KnowledgeChunk).where(KnowledgeChunk.source_id.in_(source_ids))`. Then `knowledge_processor.search_chunks()` scores every single chunk in Python to find the top-k. For a user with 100 sources × 1000 chunks each = 100K objects loaded into memory per query, then scored sequentially. This is a linear scan through all user content on every search.
- **Fix**: Add a preliminary keyword pre-filter at the DB level before loading chunks (e.g., `ILIKE` or full-text search). Cap maximum chunks loaded (`query.limit(5000)`). Long-term: migrate to vector embeddings with ANN (approximate nearest-neighbor) search.

#### KV-07 — Migration 006 doesn't create `project_id` column that model defines
- **Severity**: HIGH
- **File**: `backend/infrastructure/database/models/knowledge.py:52-57`, `backend/infrastructure/database/migrations/versions/006_create_knowledge_tables.py:26-67`
- **Description**: The `KnowledgeSource` model defines a `project_id` column (FK to projects with CASCADE, indexed). Migration 006 creates the `knowledge_sources` table without this column. The model's `__table_args__` also defines composite indexes on `(user_id, status)` and `(user_id, created_at)` but no `project_id` index. This means: (1) fresh DB installs are missing the column, (2) project-scoped filtering does a full table scan, (3) the model and migration are out of sync.
- **Fix**: Create a corrective migration (029) that adds the `project_id` column with FK and index. Add `Index("ix_knowledge_sources_project_id", "project_id")` and `Index("ix_knowledge_sources_project_status", "project_id", "status")` to the model.

---

### MEDIUM

#### KV-08 — `_process_document` uses multiple separate commits — stuck PROCESSING on crash
- **Severity**: MEDIUM
- **File**: `backend/api/routes/knowledge.py:79-160`
- **Description**: Document processing issues multiple separate `await db.commit()` calls (lines ~95, ~111, ~119, ~148) as it progresses through status updates. If the process crashes between commits (e.g., after setting `status=PROCESSING` but before setting `status=COMPLETED`), the source is permanently stuck in `PROCESSING` state. Retries via the reprocess endpoint see `status=PROCESSING` and may skip the source.
- **Fix**: Wrap the entire processing sequence in a single DB transaction. Use `async with db.begin()`. On exception, roll back and set `status=FAILED` in a separate cleanup session.

#### KV-09 — `QueryRequest.project_id` field is dead code — ignored by route handler
- **Severity**: MEDIUM
- **File**: `backend/api/routes/knowledge.py:476-599`, `backend/schemas/knowledge.py:85`
- **Description**: `QueryRequest` exposes a `project_id: Optional[str]` field in the schema, but the route handler never reads `request.project_id`. The actual project filtering is done via `_build_ownership_filter()` using `current_user.current_project_id`. The dead field creates a misleading API contract — callers who pass `project_id` to target a specific project's sources get silently ignored.
- **Fix**: Remove `project_id` from `QueryRequest` schema. If per-request project targeting is needed, implement and document it properly with a membership check.

#### KV-10 — Example query buttons not disabled during query execution (double-submit)
- **Severity**: MEDIUM
- **File**: `frontend/app/[locale]/(dashboard)/knowledge/query/page.tsx:250-265`
- **Description**: While `isQuerying` state prevents the main submit button from double-firing, the "example query" clickable items in the suggestions panel are never disabled while a query is in flight. Clicking an example query during a pending query fires a second API call, creating concurrent requests and potential state race conditions.
- **Fix**: Add `disabled={isQuerying}` and `pointer-events-none opacity-50` to all example query buttons/chips when `isQuerying === true`.

#### KV-11 — Upload title field missing maxLength frontend validation
- **Severity**: MEDIUM
- **File**: `frontend/components/knowledge/upload-modal.tsx:231-237`
- **Description**: The title `<Input>` has no `maxLength` prop. Backend enforces `max_length=500` in the schema. A user who types a 2000-character title gets no frontend warning; the backend rejects it with a validation error that may not surface clearly in the UI.
- **Fix**: Add `maxLength={500}` to the title Input and a character counter display (e.g., "123/500").

#### KV-12 — Frontend allowed file types don't match backend (CSV, JSON blocked by UI)
- **Severity**: MEDIUM
- **File**: `frontend/components/knowledge/upload-modal.tsx:19-20`
- **Description**: Frontend `ALLOWED_EXTENSIONS = [".pdf", ".txt", ".md", ".html", ".docx"]`. Backend `ALLOWED_EXTENSIONS = {"pdf", "txt", "md", "docx", "html", "csv", "json"}`. Users cannot upload `.csv` or `.json` files despite the backend supporting them — the file picker rejects them with "file type not supported" before the request is even made.
- **Fix**: Add `".csv"` and `".json"` to the frontend `ALLOWED_EXTENSIONS` array.

#### KV-13 — Query input missing character limit display (backend enforces 1000 chars)
- **Severity**: MEDIUM
- **File**: `frontend/components/knowledge/query-input.tsx:42-50`
- **Description**: The query textarea has no `maxLength` and no character counter. Backend validates `max_length=1000`. Users who type a long query get a backend error with no frontend indication that a limit exists.
- **Fix**: Add `maxLength={1000}` and a character counter. Disable submit when query exceeds 1000 characters.

#### KV-14 — Source polling never terminates for sources stuck in processing state
- **Severity**: MEDIUM
- **File**: `frontend/app/[locale]/(dashboard)/knowledge/sources/[id]/page.tsx:64-72`
- **Description**: The source detail page polls every 3 seconds while `status === "processing" || status === "pending"`. If the backend bug (KV-08) leaves a source permanently in PROCESSING, this polling runs indefinitely — no maximum attempt count, no timeout, no user warning. A tab left open will poll forever.
- **Fix**: Add a max poll count (e.g., 200 attempts = ~10 minutes). After max attempts, stop polling and show: "Processing is taking longer than expected. Please try reprocessing."

---

### LOW

#### KV-15 — `file_type` property accessed without null check on source detail page
- **Severity**: LOW
- **File**: `frontend/app/[locale]/(dashboard)/knowledge/sources/[id]/page.tsx:148`
- **Description**: `FILE_TYPE_ICONS[source.file_type.toLowerCase()]` — if `source.file_type` is `undefined` or `null` (possible for legacy records or API changes), `.toLowerCase()` throws a runtime error, crashing the source detail page.
- **Fix**: Use optional chaining: `FILE_TYPE_ICONS[source.file_type?.toLowerCase() ?? ""] || FileIcon`.

#### KV-16 — Long tag names overflow source card layout
- **Severity**: LOW
- **File**: `frontend/components/knowledge/source-card.tsx:85-101`
- **Description**: Tags are rendered without truncation. A tag name longer than the card width (e.g., "this-is-an-extremely-long-tag-name") breaks the card layout, causing overflow or misalignment in the sources grid.
- **Fix**: Add `max-w-[120px] truncate` CSS classes to tag span elements.

#### KV-17 — Missing React Error Boundary on knowledge pages
- **Severity**: LOW
- **File**: All `frontend/app/[locale]/(dashboard)/knowledge/**/*.tsx`
- **Description**: No Error Boundary wraps the knowledge vault pages. A runtime JavaScript error (e.g., KV-15 null crash) causes the entire page to go blank with no recovery UI or "Something went wrong" message.
- **Fix**: Create a `<KnowledgeErrorBoundary>` component and wrap knowledge page content. Show a friendly error with a "Reload" button.

#### KV-18 — `localStorage.setItem()` for query history has no try-catch
- **Severity**: LOW
- **File**: `frontend/app/[locale]/(dashboard)/knowledge/query/page.tsx:61-62`
- **Description**: `localStorage.setItem("knowledge_query_history", ...)` can throw `QuotaExceededError` if storage is full (common in privacy-focused browsers or after heavy use). This would crash the query page silently.
- **Fix**: Wrap in try-catch. On `QuotaExceededError`, clear old history or skip saving without crashing.

#### KV-19 — ReactMarkdown renders AI response without explicit HTML skipping
- **Severity**: LOW
- **File**: `frontend/app/[locale]/(dashboard)/knowledge/query/page.tsx:156-202`
- **Description**: AI-generated query answers are rendered via `<ReactMarkdown>` without the `skipHtml` prop. ReactMarkdown does not enable dangerous HTML by default, but explicit `skipHtml` is best practice when rendering untrusted/AI-generated content.
- **Fix**: Add `skipHtml` prop: `<ReactMarkdown skipHtml>{response.answer}</ReactMarkdown>`.

#### KV-20 — `formatFileSize()` helper duplicated across 4 files
- **Severity**: LOW
- **Files**: `source-card.tsx:34`, source detail page line ~116, `upload-modal.tsx:193`, sources list page ~61
- **Description**: The file size formatting function (bytes → KB/MB/GB string) is copy-pasted across four files. Any bug fix or formatting change must be replicated in all four locations.
- **Fix**: Extract to `frontend/lib/utils.ts` as a shared named export `formatFileSize(bytes: number): string`.

---

## What's Working Well
- File validation at upload: extension whitelist + MIME type check (dual validation)
- 10MB file size limit enforced at route level
- Path traversal prevention at upload: filename sanitized via `secure_filename()`
- Path traversal check in reprocess endpoint using `is_relative_to(STORAGE_DIR)`
- Ownership filtering via `_build_ownership_filter()` correctly handles both personal and project-scoped sources
- Chunk-based document processing with configurable chunk size and overlap
- Failed document status set correctly on extraction errors
- `KnowledgeQuery` records stored for each query (query history/audit trail)
- Source deletion correctly cleans up both DB records and physical files

---

## Fix Priority Order
1. KV-01 — Source ID enumeration via error message (CRITICAL)
2. KV-02 — No rate limiting on upload/query (HIGH)
3. KV-03 — Cross-project query count in stats (HIGH)
4. KV-04 — Missing path validation in delete (HIGH)
5. KV-05 — Unbounded source load in knowledge_service (HIGH)
6. KV-06 — Unbounded chunk load in query_knowledge (HIGH)
7. KV-07 — Migration/model mismatch for project_id (HIGH)
8. KV-08 — Multiple commits without transaction in _process_document (MEDIUM)
9. KV-09 — Dead project_id field in QueryRequest (MEDIUM)
10. KV-10 — Example query buttons not disabled during query (MEDIUM)
11. KV-11 — Upload title field no maxLength (MEDIUM)
12. KV-12 — Frontend file type list doesn't match backend (MEDIUM)
13. KV-13 — Query input no character limit (MEDIUM)
14. KV-14 — Source polling never terminates (MEDIUM)
15. KV-15 through KV-20 — Low severity items (LOW)
