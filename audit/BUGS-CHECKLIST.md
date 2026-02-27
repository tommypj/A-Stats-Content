# Full App Audit — Bugs & Fixes Checklist
**Started**: 2026-02-27
**Sections audited so far**: 13 of 13 — AUDIT COMPLETE

---

## How to use this file
- `[ ]` = not started
- `[~]` = in progress
- `[x]` = fixed and verified

---

## Section 1 — Authentication & Authorization

### Critical
- [ ] **AUTH-01** — Refresh token not invalidated after password change (`backend/api/routes/auth.py:290-330`) — Add `password_changed_at` check to `/refresh` endpoint

### High
- [ ] **AUTH-02** — Tokens stored in localStorage (XSS risk) (`frontend/lib/api.ts`, `auth.ts`, `stores/auth.ts`) — Migrate to HttpOnly cookies *(large change, plan separately with AUTH-10)*
- [ ] **AUTH-03** — Timing attack on login leaks user existence (`auth.py:252`) — Always run bcrypt verify using dummy hash
- [ ] **AUTH-04** — `is_active` check missing from login (`auth.py:252-268`) — Add active status check after credential validation
- [ ] **AUTH-05** — Duplicate `get_current_admin_user()` in both `dependencies.py` and `deps_admin.py` — Remove from `dependencies.py`, update all imports
- [ ] **AUTH-06** — Brand voice update endpoint missing role check (`projects.py:341-379`) — Add `require_project_admin()` call
- [ ] **AUTH-07** — `validate_project_content_creation()` is a no-op (`deps_project.py:248-296`) — Implement or delete and fix call sites

### Medium
- [ ] **AUTH-08** — Email service errors not caught in registration and password reset (`auth.py:227-231, 388-392`) — Wrap in try/except
- [ ] **AUTH-09** — Login form allows 1-char password, inconsistent with register (`login/page.tsx:20-22`) — Change to `min(8)`
- [ ] **AUTH-10** — No CSRF protection (`api.ts`) — Implement alongside AUTH-02
- [ ] **AUTH-11** — DB commit side effect inside `get_current_user` dependency (`auth.py:125-148`) — Remove `await db.commit()` from dependency
- [ ] **AUTH-12** — No rate limiting on public invite token endpoint (`project_invitations.py:409-436`) — Add `@limiter.limit("20/minute")`

### Low
- [ ] **AUTH-13** — No token blacklist on logout/account deletion — Implement Redis-backed blacklist
- [ ] **AUTH-14** — `/refresh` rate limit too loose (10/min vs 5/min for login) — Reduce to 5/min
- [ ] **AUTH-15** — Authorization header parsing fragile (`auth.py:74-81`) — Explicit split + length check
- [ ] **AUTH-16** — Invitation expiry job not scheduled (`services/project_invitations.py`) — Register as daily background task
- [ ] **AUTH-17** — No idle session timeout on frontend — Implement 30-60 min idle logout
- [ ] **AUTH-18** — bcrypt rehash on login not implemented — Call `needs_rehash()` on login

---

## Section 2 — Project & Team Management

### Critical
- [ ] **PROJ-01** — `improve_article` endpoint has no usage limit check — unlimited AI calls bypass monthly limits (`articles.py:1034`)
- [ ] **PROJ-02** — Bulk generation passes extra params to `generate_outline()` — runtime TypeError crash (`bulk_generation.py:162-170`) *(pre-existing known bug)*
- [ ] **PROJ-03** — `ProjectInvitation` model missing soft-delete field — inconsistent with all other models, breaks GDPR
- [ ] **PROJ-04** — Member management endpoints not implemented — no way to remove member, update role, leave project, or transfer ownership via API

### High
- [ ] **PROJ-05** — Duplicate `require_project_admin()` in `project_invitations.py` — remove local copy, import from `deps_project.py`
- [ ] **PROJ-06** — Two independent usage limit systems (`core/plans.py` vs `project_usage.py`) with mismatched values — consolidate into single source of truth
- [ ] **PROJ-07** — Article generation route does not load `brand_voice` from project (`articles.py:551-553`) *(pre-existing known bug)*
- [ ] **PROJ-08** — `regenerate_outline` does not reload `brand_voice` (`outlines.py:532-590`) *(pre-existing known bug)*
- [ ] **PROJ-09** — `ProjectInvitation.invited_by` FK uses CASCADE instead of SET NULL — deleting inviter destroys invitation audit trail
- [ ] **PROJ-10** — Personal workspace deletion returns HTTP 400 instead of 403 (`projects.py:566-570`)
- [ ] **PROJ-11** — Frontend brand voice page has no role-gating — any member sees and can attempt to save

### Medium
- [ ] **PROJ-12** — TOCTOU race condition on usage limit check allows limit overshoot under concurrency
- [ ] **PROJ-13** — Monthly usage reset uses `flush()` instead of `commit()` — concurrent requests can double-reset
- [ ] **PROJ-14** — User-level limit check fails OPEN on exception (allows generation); project fails CLOSED (blocks) — asymmetric and risky
- [ ] **PROJ-15** — `improve_article` not tracked in GenerationLog — no cost attribution or usage stats
- [ ] **PROJ-16** — Bulk job `error_summary` field never populated despite schema defining it
- [ ] **PROJ-17** — `brand_voice` JSON column has no validation schema — malformed data can be stored
- [ ] **PROJ-18** — `current_project_id` auto-set on invitation accept without informing user
- [ ] **PROJ-19** — N+1 queries in project settings page — every member operation reloads all data

### Low
- [ ] **PROJ-20** — Missing composite index on `ProjectInvitation(project_id, email, status)`
- [ ] **PROJ-21** — Inconsistent naming: `logo_url` vs `avatar_url` in projects.py
- [ ] **PROJ-22** — Viewers can see all member email addresses — verify intended design
- [ ] **PROJ-23** — No pagination on project member list
- [ ] **PROJ-24** — `lemonsqueezy_customer_id` unique+nullable constraint — verify PostgreSQL NULL handling

## Section 3 — Content Generation Pipeline

### Critical
- [ ] **GEN-01** — `generate_outline()` hardcodes `writing_style/voice/list_usage` in system prompt — ignores brand_voice and all user generation options (`anthropic_adapter.py:229`)
- [ ] **GEN-02** — Prompt injection: `keyword`, `tone`, `target_audience`, `custom_instructions` interpolated directly into AI prompts with no sanitization or length limits

### High
- [ ] **GEN-03** — Concurrent regenerate race condition — two requests can both run AI on the same outline simultaneously (`outlines.py:562-572`)
- [ ] **GEN-04** — `update_outline` silently ignores `status` field in PUT requests — returns 200 but drops the value (`outlines.py:483`)
- [ ] **GEN-05** — No schema validation on `sections` field in outline update — malformed section data stored silently
- [ ] **GEN-06** — WordPress publish does not set `article.status = PUBLISHED` — no way to distinguish published vs draft (`wordpress.py:594-598`)
- [ ] **GEN-07** — Language parameter missing from article generation UI — backend supports it, form never sends it
- [ ] **GEN-08** — Frontend article form never loads project brand_voice — always defaults to hardcoded balanced/second_person/balanced

### Medium
- [ ] **GEN-09** — Article `status` allows arbitrary transitions via update endpoint — no transition validation (`articles.py:954`)
- [ ] **GEN-10** — `improve_article` is synchronous with no timeout — request hangs if AI hangs (`articles.py:1032`)
- [ ] **GEN-11** — Two divergent SEO scoring systems (backend base-50 vs frontend 10×10) produce different scores *(pre-existing known bug)*
- [ ] **GEN-12** — Generic error messages in generation UI — not using `parseApiError()` project pattern
- [ ] **GEN-13** — Featured image not included in article editor auto-save — image lost on auto-save
- [ ] **GEN-14** — `AIGenerationProgress` phases driven by hardcoded timers, not real backend progress
- [ ] **GEN-15** — `generate_outline()` uses global 4096 token cap — may truncate large outlines
- [ ] **GEN-16** — `regenerate_outline` uses different language fallback than `create_outline` — brand_voice language ignored

### Low
- [ ] **GEN-17** — SEO score keyword matching inconsistent — substring for title/meta, whole-word for density
- [ ] **GEN-18** — JSX typo in article improve buttons — `\>` renders as literal character
- [ ] **GEN-19** — No `aria-live` on auto-save status — screen readers not notified
- [ ] **GEN-20** — No temperature setting in AI adapter — regenerating same outline always produces near-identical result

## Section 4 — Bulk Generation

### Critical
- [ ] **BULK-01** — All bulk outline jobs fail with TypeError — extra params passed to `generate_outline()` (`bulk_generation.py:162-171`) *(pre-existing known bug)*
- [ ] **BULK-02** — No rate limiting on bulk job creation — DoS vector against AI quota (`bulk.py:319`)
- [ ] **BULK-03** — Concurrent retries spawn duplicate background tasks — same keywords processed twice

### High
- [ ] **BULK-04** — Templates and jobs created without verifying project membership (`bulk.py:128-130, 169, 349`)
- [ ] **BULK-05** — In-flight items continue generating after job is cancelled — no cancellation signal
- [ ] **BULK-06** — Usage limits checked inside background task, not at job creation — user finds out too late
- [ ] **BULK-07** — Retry endpoint resets `failed_items=0` without checking job status — corrupts completed jobs
- [ ] **BULK-08** — No loading state on job creation button — double-clicks create duplicate jobs
- [ ] **BULK-09** — Polling fetches only first 20 jobs — active jobs beyond page 1 never update

### Medium
- [ ] **BULK-10** — Background task crash leaves job permanently in `processing` state — `error_summary` never set
- [ ] **BULK-11** — Template `tone`/`writing_style` fields accept any string — no enum validation
- [ ] **BULK-12** — Cancelled items indistinguishable from never-started — no `cancelled_items` counter
- [ ] **BULK-13** — Broad `except Exception` hides AI failure types — can't distinguish transient vs permanent
- [ ] **BULK-14** — Orphaned outlines if process crashes between creation and item status update
- [ ] **BULK-15** — No per-item or job-level timeout on bulk processing — hangs indefinitely on AI hang
- [ ] **BULK-16** — No keyword deduplication — same keyword submitted twice creates duplicate outlines

### Low
- [ ] **BULK-17** — ContentTemplate hard-deleted (no soft-delete)
- [ ] **BULK-18** — Template delete has no confirmation dialog
- [ ] **BULK-19** — Item list in job detail page not paginated — DOM performance issue at scale
- [ ] **BULK-20** — Missing `project_id` index on BulkJob; `BulkJobItem.resource_id` has no FK constraint

## Section 5 — Analytics Suite

### Critical
- [ ] **ANA-01** — GSC OAuth callback does not validate `state` parameter — CSRF attack possible (`analytics.py:171`, analytics callback frontend) — Verify state on callback against stored session value
- [ ] **ANA-02** — AEO score refresh endpoint lacks article ownership check — IDOR, any user can trigger re-scoring of any article (`articles.py:1672`) — Add project membership check

### High
- [ ] **ANA-03** — GSC token refresh during sync not persisted to DB — every sync re-refreshes same expired token, eventually loses connection — Persist new token after refresh
- [ ] **ANA-04** — N+1 queries fetching article titles for decay alerts (`analytics.py:1520-1523, 1604-1608`) — Use JOIN or selectinload
- [ ] **ANA-05** — Revenue `trend_data` field never populated — always returns `[]`, frontend chart always empty (`revenue_attribution.py`) — Aggregate and populate time-series data
- [ ] **ANA-06** — URL normalization too simplistic — UTM params, fragments, www/non-www, protocol variants all break conversion matching (`revenue_attribution.py`) — Use urllib.parse for full normalization

### Medium
- [ ] **ANA-07** — Content decay dedup query missing `project_id` filter (`content_decay.py:228-243`) — Add project_id filter and composite index
- [ ] **ANA-08** — Concurrent GSC token refresh race condition — two parallel syncs can both attempt refresh, Google may invalidate refresh token — Add atomic refresh lock
- [ ] **ANA-09** — Hard-coded 3-day GSC data lag (`analytics.py`) — Extract to named constant `GSC_DATA_LAG_DAYS`
- [ ] **ANA-10** — Keyword ranking URLs stored with query strings — never match article URLs in frontend (`analytics.py`) — Normalize URLs before storage
- [ ] **ANA-11** — `list_conversion_goals` not scoped to current project — returns goals from all user's projects (`analytics.py`) — Add `project_id` filter
- [ ] **ANA-12** — No scheduled content decay detection job — `detect_content_decay()` only runs on manual API trigger (`content_decay.py`) — Register as daily background task
- [ ] **ANA-13** — AEO composite index mismatch — migration 025 created `(article_id, score_date)` but model defines `(article_id, query, score_date)` — Create corrective migration
- [ ] **ANA-14** — `AEOCitation` model never populated — AEO scores are rule-based heuristics, no actual AI citation checking (`aeo_scoring.py`) — Implement citation checking (backlog)
- [ ] **ANA-15** — `ConversionGoal.goal_type` has no DB-level enum constraint — any string accepted at DB layer — Change to Enum column with migration
- [ ] **ANA-16** — CSV import silently skips rows when revenue amount can't be parsed — no error returned (`revenue_attribution.py`) — Return validation error with row number

### Low
- [ ] **ANA-17** — No rate limiting on any analytics endpoints (sync, decay detect, AEO, reports) — Add `@limiter.limit()` to all compute-heavy endpoints
- [ ] **ANA-18** — `report_type` parameter not validated in `generate_revenue_report()` — Add `Literal` type annotation
- [ ] **ANA-19** — Conversion goal deletion is hard delete — no audit trail, historical attribution broken — Add `deleted_at` soft-delete
- [ ] **ANA-20** — No pagination on `list_conversion_goals` — unbounded response — Add standard page/page_size pagination

## Section 6 — Knowledge Vault

### Critical
- [ ] **KV-01** — Source ID enumeration via 404 error message — any user can probe other users' source IDs (`knowledge.py:502-506`) — Return 403 with generic message

### High
- [ ] **KV-02** — No rate limiting on any knowledge vault endpoints — upload/query DoS vector — Add `@limiter.limit()` to all endpoints
- [ ] **KV-03** — Stats endpoint counts queries across all user projects, not just current — cross-project info leak (`knowledge.py:640-645`) — Scope query count to current project
- [ ] **KV-04** — File path not validated in delete endpoint — path traversal risk (`knowledge.py:465-466`) — Validate path before delete_file()
- [ ] **KV-05** — `knowledge_service.py` loads all sources into memory unbounded — O(N) memory load (`knowledge_service.py:412-431`) — Replace with SQL aggregate queries
- [ ] **KV-06** — `query_knowledge` loads all user chunks unbounded — O(N) memory per query (`knowledge.py:533-536`) — Add keyword pre-filter and LIMIT
- [ ] **KV-07** — Migration 006 doesn't create `project_id` column that model defines — schema drift (`models/knowledge.py:52-57`, `migration 006`) — Create corrective migration 029

### Medium
- [ ] **KV-08** — `_process_document` uses multiple separate commits — crash leaves source stuck in PROCESSING (`knowledge.py:79-160`) — Wrap in single transaction
- [ ] **KV-09** — `QueryRequest.project_id` is dead code — ignored by route handler (`schemas/knowledge.py:85`) — Remove unused field
- [ ] **KV-10** — Example query buttons not disabled during active query — double-submit possible (`query/page.tsx:250-265`) — Add `disabled={isQuerying}`
- [ ] **KV-11** — Upload title field missing `maxLength` — backend rejects silently at 500 chars (`upload-modal.tsx:231-237`) — Add `maxLength={500}` + counter
- [ ] **KV-12** — Frontend blocked file types (CSV, JSON) don't match backend — feature gap (`upload-modal.tsx:19-20`) — Add .csv/.json to frontend allowed types
- [ ] **KV-13** — Query input missing character limit — backend enforces 1000 chars (`query-input.tsx:42-50`) — Add `maxLength={1000}` + counter
- [ ] **KV-14** — Source detail polling never terminates for stuck sources — infinite poll (`sources/[id]/page.tsx:64-72`) — Add max poll attempts

### Low
- [ ] **KV-15** — `source.file_type.toLowerCase()` crashes if `file_type` is null (`sources/[id]/page.tsx:148`) — Add optional chaining
- [ ] **KV-16** — Long tag names overflow source card layout (`source-card.tsx:85-101`) — Add `truncate` CSS
- [ ] **KV-17** — No React Error Boundary on knowledge vault pages — blank page on JS error — Add KnowledgeErrorBoundary
- [ ] **KV-18** — `localStorage.setItem()` for query history has no try-catch — crashes on QuotaExceededError (`query/page.tsx:61-62`)
- [ ] **KV-19** — ReactMarkdown renders AI responses without `skipHtml` prop (`query/page.tsx:156-202`)
- [ ] **KV-20** — `formatFileSize()` duplicated across 4 files — extract to `lib/utils.ts`

## Section 7 — Social Media

### Critical
- [ ] **SM-01** — OAuth state parameter not validated on callback — CSRF account hijacking (`social.py:102-125, 243-354`, frontend callback) — Verify state belongs to current user before consuming
- [ ] **SM-02** — `verify_account()` accesses `access_token` instead of `access_token_encrypted` — AttributeError crash, all accounts show as invalid (`social.py:533`) — Fix attribute name

### High
- [ ] **SM-03** — Race condition in scheduled post publishing — two scheduler instances double-publish (`social_scheduler.py:98-102`) — Add DB-level atomic lock
- [ ] **SM-04** — Facebook page tokens stored as plaintext JSON in `account_metadata` — credential exposure (`social_scheduler.py:244-247`) — Encrypt with `encrypt_credential()`
- [ ] **SM-05** — LinkedIn and Facebook `refresh_token()` raises `SocialAuthError` — all posts fail after 60 days (`linkedin_adapter.py:229`, `facebook_adapter.py:295`) — Disable account and notify user on expiry
- [ ] **SM-06** — `list_connected_accounts` not scoped to current project — IDOR, cross-project social account access (`social.py:176, 560`) — Add `project_id` filter
- [ ] **SM-07** — No past-date validation in schedule picker or calendar drag-drop (`schedule-picker.tsx`, `calendar-view.tsx`) — Reject dates in the past
- [ ] **SM-08** — Platform character limits displayed but not enforced on submit (`compose/page.tsx:281-292`) — Validate per platform before API call

### Medium
- [ ] **SM-09** — No rate limiting on OAuth initiation or scheduled post creation (`social.py:187-240, 552-670`) — Add `@limiter.limit()`
- [ ] **SM-10** — `media_urls` not validated before publishing — SSRF vector (`social_scheduler.py:253, 287`) — Validate scheme and block internal IPs
- [ ] **SM-11** — Update endpoint allows arbitrary status transitions — no state machine (`social.py:833-924`) — Only allow DRAFT↔SCHEDULED
- [ ] **SM-12** — LinkedIn post ID parsed from wrong response field — always stored empty (`linkedin_adapter.py:336`) — Parse `result["value"]["id"]`
- [ ] **SM-13** — Facebook multi-image post silently falls back to single image — no user notification (`facebook_adapter.py:489-493`) — Return error or implement carousel
- [ ] **SM-14** — Timezone mismatch in schedule picker — browser local time used regardless of selected timezone (`schedule-picker.tsx`) — Use `date-fns-tz` for proper conversion
- [ ] **SM-15** — No React Error Boundaries on social media pages — blank screen on JS error — Add `SocialErrorBoundary`
- [ ] **SM-16** — No pagination on `list_connected_accounts` — unbounded response (`social.py:168-184`) — Add page/page_size
- [ ] **SM-17** — Calendar drag-drop reschedule accepts past dates (`calendar-view.tsx:119-126`) — Validate date in onDrop handler

### Low
- [ ] **SM-18** — No timeout on scheduled post publishing — scheduler hangs on slow adapter (`social_scheduler.py:253`) — Wrap with `asyncio.wait_for(timeout=300)`
- [ ] **SM-19** — No file size or MIME type validation on frontend media upload (`compose/page.tsx:325-339`) — Validate size ≤ 50MB and MIME type
- [ ] **SM-20** — Best posting times uses `published_at` instead of `scheduled_at` — recommendations skewed by queue lag (`social.py:1330-1380`)

## Section 8 — Images

### Critical
- [ ] **IMG-01** — No file size limit on image downloaded from Replicate — disk exhaustion (`images.py:118-131`) — Add 20MB cap before write
- [ ] **IMG-02** — Replicate URL downloaded without scheme/domain validation — SSRF (`images.py:104-131`) — Whitelist Replicate CDN domains before download
- [ ] **IMG-03** — Orphaned files when DB commit fails after storage write (`images.py:118-127`) — Cleanup file on commit failure

### High
- [ ] **IMG-04** — Rate limiting per-IP only — no per-user AI image generation quota (`images.py:199`) — Add daily per-user quota check
- [ ] **IMG-05** — File deletion failure swallowed — DB record deleted but file stays on disk (`images.py:423-427`) — Fail HTTP request if file deletion fails
- [ ] **IMG-06** — Images served via unauthenticated `StaticFiles /uploads` mount — any URL accessible by anyone (`main.py:217`) — Replace with authenticated `GET /images/{id}/file` endpoint
- [ ] **IMG-07** — Admin image deletion missing project scope check — IDOR (`admin_content.py:516-550`) — Add project_id filter for scoped admins
- [ ] **IMG-08** — No timeout on image generation background task — hangs indefinitely on Replicate outage (`images.py:95-152`) — Wrap with `asyncio.wait_for(timeout=120)`
- [ ] **IMG-09** — Generated images served without cache headers — every page load re-fetches immutable files — Add `Cache-Control: immutable`

### Medium
- [ ] **IMG-10** — Admin images page uses raw `image.url` instead of `getImageUrl()` — local images fail to load (`admin/content/images/page.tsx:224`) — Use `getImageUrl(image.url)`
- [ ] **IMG-11** — Image MIME type detected from file extension, not magic bytes — extension spoofing possible (`image_storage.py:287-294`) — Use `python-magic`
- [ ] **IMG-12** — Download handler has no loading state or error feedback (`images/page.tsx:192`) — Add `isDownloading` state and error toast
- [ ] **IMG-13** — Bulk delete uses hardcoded generic error message (`images/page.tsx:255-273`) — Use `parseApiError()` pattern
- [ ] **IMG-14** — Storage adapter error contract inconsistent — LocalAdapter returns `False`, S3Adapter raises (`image_storage.py`) — Standardize to raise `StorageError`
- [ ] **IMG-15** — Downloaded image bytes not validated before storage — corrupted Replicate responses stored silently (`images.py:119-127`) — Validate with Pillow `verify()`

### Low
- [ ] **IMG-16** — No retry logic on transient Replicate download failures — immediate failure on network hiccup — Add exponential backoff
- [ ] **IMG-17** — Alt text auto-generated from prompt, not user-customizable — poor accessibility — Add optional `alt_text` field to request
- [ ] **IMG-18** — No structured error logging for generation failures — can't monitor/alert on failure rates — Add `logger.error()` with structured fields
- [ ] **IMG-19** — No prompt content validation before Replicate call — policy-violating prompts sent directly — Add basic blocklist check
- [ ] **IMG-20** — WordPress image send failure shows generic error — not using `parseApiError()` — Fix error message

## Section 9 — Agency & White-Label Mode

### Critical
- [ ] **AGY-01** — `PortalSummaryResponse` missing branding fields — every client portal shows unbranded (`agency.py:805-817, 982-993`, `portal/[token]/page.tsx:203-240`) — Populate `logo_url`, `brand_colors`, `contact_email`, `footer_text` from `AgencyProfile`
- [ ] **AGY-02** — No rate limiting on portal token endpoint — brute-force and DoS vector (`agency.py:820-993`) — Add `@limiter.limit("20/minute")`, increase token to 64 bytes, cache responses

### High
- [ ] **AGY-03** — Workspace creation missing project membership check — collaborators can create client workspaces (`agency.py:298-357`) — Require OWNER or ADMIN role in project
- [ ] **AGY-04** — IDOR in report list `workspace_id` filter — timing oracle for cross-agency workspace IDs (`agency.py:748-771`) — Validate workspace belongs to current agency before filtering
- [ ] **AGY-05** — Public portal makes 6+ expensive DB aggregations with no caching or timeout (`agency.py:820-993`) — Add Redis cache (10-min TTL) and `asyncio.wait_for(timeout=10)`

### Medium
- [ ] **AGY-06** — Agency hard-deleted with no soft-delete, no audit trail, no confirmation (`agency.py:259-268`) — Add `deleted_at`, audit log, two-step confirmation
- [ ] **AGY-07** — N+1 queries in workspace list — no eager loading of related `Project` (`agency.py:276-290`) — Add `selectinload(ClientWorkspace.project)`
- [ ] **AGY-08** — Logo URLs used without scheme validation in portal — `javascript:` URI possible (`portal/[token]/page.tsx:387-388`) — Validate `https://` prefix before using in `<img src>`
- [ ] **AGY-09** — Portal tokens never expire — leaked link grants permanent access — Add `portal_token_expires_at` field and 410 Gone response on expiry

### Low
- [ ] **AGY-10** — No access logging on client portal visits — agencies can't see who viewed their portal — Create `PortalAccessLog` table
- [ ] **AGY-11** — No pagination on generated reports list (`agency.py:748-771`) — Add page/page_size pagination
- [ ] **AGY-12** — No limit on client workspaces per agency — unlimited workspace creation bloats DB — Add per-plan workspace count limit

## Section 10 — Billing & Subscriptions

### Critical
- [ ] **BILL-01** — Expired subscriptions not enforced in `check_limit()` — cancelled users continue generating at old plan limits (`generation_tracker.py:146-212`) — Add `subscription_expires` check in `check_limit()`
- [ ] **BILL-02** — `user_id` in checkout webhook not validated against webhook email — subscription assignable to arbitrary user (`billing.py:174-178, 494-503`) — Cross-validate `user.email` against webhook payload email
- [ ] **BILL-03** — No idempotency on webhook events — duplicate delivery causes double-processing (`billing.py:406-626`) — Add `WebhookEvent` table with unique `event_id` deduplication

### High
- [ ] **BILL-04** — Plan downgrade doesn't revoke features immediately — combined with BILL-01, downgraded users retain pro features (`billing.py:538-550`) — On downgrade, set `subscription_expires = now()` instead of `renews_at`
- [ ] **BILL-05** — Invalid JSON in webhook returns HTTP 200 — LemonSqueezy stops retrying, payload silently dropped (`billing.py:445-451`) — Return HTTP 400 on JSON parse failure
- [ ] **BILL-06** — Missing webhook secret returns 503 — triggers aggressive LemonSqueezy retries (`billing.py:426-443`) — Return 403 Forbidden instead
- [ ] **BILL-07** — `ProjectSubscriptionResponse.variant_id` populated with `subscription_id` instead of variant — breaks upgrade UI (`project_billing.py:162`) — Add `lemonsqueezy_variant_id` field to `Project` model

### Medium
- [ ] **BILL-08** — `subscription_status` field never written by webhook handler — frontend always shows "active" (`billing.py:527-598`) — Add `user.subscription_status = subscription_status` in webhook handler
- [ ] **BILL-09** — No row-level lock on concurrent webhook updates — race condition corrupts subscription state (`billing.py:604-618`) — Add `.with_for_update()` to User query in webhook handler
- [ ] **BILL-10** — No rate limiting on billing endpoints — checkout/cancel can be spammed (`billing.py`, `project_billing.py`) — Add `@limiter.limit("5/minute")` to checkout/cancel, `30/minute` to reads
- [ ] **BILL-11** — Checkout URL lacks CSRF protection — attacker can initiate checkout on behalf of user (`billing.py:136-185`) — Add short-lived checkout session token validated in webhook

### Low
- [ ] **BILL-12** — `_parse_iso_datetime()` returns `datetime.now()` on failure — malformed date immediately expires subscription (`billing.py:41-47`) — Return `None` on failure; don't update expiry
- [ ] **BILL-13** — Personal project subscription sync silently skips if personal project missing — no warning logged (`billing.py:603-615`) — Add `logger.warning()` in `else` branch
- [ ] **BILL-14** — Variant ID → tier mapping duplicated in `billing.py` and `project_billing.py` — Extract to `core/plans.py` shared function
- [ ] **BILL-15** — Subscription cancel updates DB even if LemonSqueezy API call fails — state desync (`billing.py:237-254`) — Only update DB after confirmed API success

## Section 11 — Admin Panel

### Critical
- [ ] **ADM-01** — Regular admin can modify/suspend super_admin accounts — privilege escalation (`admin_users.py:253-363`) — Add role-hierarchy check: modifying admin/super_admin requires super_admin caller
- [ ] **ADM-02** — Admin route protection is client-side only — admin UI briefly visible before useEffect runs (`layout.tsx:87-112`) — Add `/admin` protection to `middleware.ts` with JWT role check

### High
- [ ] **ADM-03** — Bulk delete uses single commit after loop — per-item savepoints needed for safe partial failure (`admin_content.py:732-837`) — Wrap each item in `async with db.begin_nested()`
- [ ] **ADM-04** — Bulk delete on content pages has no confirmation dialog — irreversible mass deletion with one click (`admin/content/*/page.tsx`) — Add `AlertDialog` with item count and "cannot be undone" warning
- [ ] **ADM-05** — `mark-all-read` creates no audit log; some bulk op logs created after commit (`admin_alerts.py:178-188`) — Move audit logs inside transaction; add mark-all-read audit entry
- [ ] **ADM-06** — Self-demotion check is non-atomic — two concurrent requests can both pass role check (`admin_users.py:282-296`) — Use `SELECT ... FOR UPDATE` to lock row before check and update
- [ ] **ADM-07** — User suspension sends no email, requires no reason, has no expiry option (`admin_users.py:366-426`) — Require `suspended_reason`, send notification email, add optional `suspension_expires_at`

### Medium
- [ ] **ADM-08** — Audit log IP uses `request.client.host` — always proxy IP behind Cloudflare (`admin_users.py:355, 418, 483, 628`) — Create `get_client_ip(request)` helper checking `X-Forwarded-For` first
- [ ] **ADM-09** — Bulk delete failure doesn't log reason per item — inconsistent audit trail (`admin_content.py:770-808`) — Log failure reason in audit record for each failed item
- [ ] **ADM-10** — No rate limiting on admin analytics endpoints — 20+ heavy queries can be spammed (`admin_analytics.py:85-292`) — Add `@limiter.limit("10/minute")` and 5-minute Redis cache
- [ ] **ADM-11** — All admins can list/delete ALL content across ALL projects — no role scoping (`admin_content.py:88-244`) — Scope regular admins to managed projects; super_admin retains full access
- [ ] **ADM-12** — Bulk suspend has no count limit, no self-suspension guard, no admin lockout check (`admin_users.py`) — Add guards: max 100 IDs, reject self, ensure ≥1 active admin remains

### Low
- [ ] **ADM-13** — `update_alert` endpoint doesn't capture `User-Agent` in audit log (`admin_alerts.py:121-175`) — Add `user_agent: Optional[str] = Header(None)` parameter
- [ ] **ADM-14** — `list_all_images` accepts inverted date ranges silently — always-false WHERE returns 0 results (`admin_content.py:429-513`) — Add `start_date <= end_date` validation
- [ ] **ADM-15** — `AuditLog.details` JSON column has no size limit — potentially unbounded (`models/admin.py:105`) — Add 10KB size check before saving

## Section 12 — SEO Scoring & Quality

### Critical
- [ ] **SEO-01** — Keyword density uses substring matching — "react" matches "reactive" (`articles.py:135`) — Use `re.findall(r'\b' + re.escape(kw) + r'\b', content)`

### High
- [ ] **SEO-02** — Two incompatible scoring systems (backend base-50 vs frontend 10×10) — Unify to single system
- [ ] **SEO-03** — Readability score computed and stored but never displayed or used — Remove or surface in UI
- [ ] **SEO-04** — Title/heading keyword check uses substring matching — false positives (`articles.py:39, 61, 185, 194`) — Use whole-word regex
- [ ] **SEO-05** — Alt text check passes articles with zero images — articles with no images should not receive full marks (`articles.py:24-25`) — Return `False` when no images exist

### Medium
- [ ] **SEO-06** — `meta_title` field absent from Article model — frontend scorer reads `undefined` always (`seo-score.ts:60`) — Add field or remove dead reference
- [ ] **SEO-07** — No rate limiting on `/analyze-seo` endpoint — Add `@limiter.limit("10/minute")`
- [ ] **SEO-08** — Word count calculation differs backend vs frontend — normalize whitespace with `re.split(r'\s+', content.strip())`
- [ ] **SEO-09** — Heading structure check requires H3s — valid flat structures penalized (`articles.py:17`) — Relax to H2 count only
- [ ] **SEO-10** — Link detection regex false positives on malformed markdown (`articles.py:20-21`) — Use stricter regex
- [ ] **SEO-11** — Backend base score 50 means unoptimized articles always score 50% — Remove base, start from 0
- [ ] **SEO-12** — Missing `re.escape()` on keyword in some regex paths — `C++` keyword would raise `re.error` — Add `re.escape()` consistently

### Low
- [ ] **SEO-13** — Sentence split includes empty elements — readability score inflated — Filter empty strings post-split
- [ ] **SEO-14** — No staleness detection for stored SEO scores — stale after content edit — Add `seo_analysis_updated_at` timestamp
- [ ] **SEO-15** — SEO analysis not triggered when content first added to empty article — Add trigger on first content write
- [ ] **SEO-16** — Suggestion text inconsistent between backend and frontend — Consolidate to single source
- [ ] **SEO-17** — "Increase keyword usage" suggestion when no keyword is set — Show "Set a focus keyword" instead
- [ ] **SEO-18** — `readability_score` dead storage in `seo_analysis` JSON — Remove if SEO-03 resolved by removal
- [ ] **SEO-19** — Title length check (30-60 chars) in frontend only, absent from backend — Add to backend scorer
- [ ] **SEO-20** — `meta_description` schema max 320 chars but SEO recommends 160 — Align max to 160 or adjust message

## Section 13 — Infrastructure & Cross-Cutting Concerns

### Critical
- [ ] **INFRA-01** — No HTTP security headers — missing CSP, X-Frame-Options, X-Content-Type-Options (`main.py`) — Add security headers middleware
- [ ] **INFRA-02** — `asyncio.get_event_loop()` in ChromaAdapter — crashes in Python 3.12+ (`chroma_adapter.py:328`) — Replace with `asyncio.get_running_loop()`
- [ ] **INFRA-03** — CORS origin validation uses string splitting, not URL parsing — misconfiguration bypass risk (`settings.py:80-92`) — Parse with `urlparse()`, add startup assertion

### High
- [ ] **INFRA-04** — Request ID not stored in `request.state` or logging context — log correlation impossible (`main.py:198-202`) — Store in `request.state.request_id`, add to log extras
- [ ] **INFRA-05** — Global exception handler logs full stack traces in production — sensitive data exposure (`main.py:162-168`) — Log only exception type/message in production
- [ ] **INFRA-06** — Alembic migration chain missing 009 — `alembic check` fails (`migrations/010:14`) — Create placeholder migration 009
- [ ] **INFRA-07** — Background task cleanup loop has no graceful shutdown — mid-write cancellation possible (`main.py:102-123`) — Add `CancelledError` handling
- [ ] **INFRA-08** — Rate limiter falls back to in-memory in multi-instance deployment — per-process limits, easily bypassed (`rate_limit.py:84-88`) — Require Redis in production

### Medium
- [ ] **INFRA-09** — X-Request-ID header not validated — log injection via malicious header value — Validate UUID format before use
- [ ] **INFRA-10** — OAuth redirect URIs default to `localhost` in production — no startup validation (`settings.py:121-136`) — Validate `https://` + non-localhost in `validate_production_secrets()`
- [ ] **INFRA-11** — No startup Redis connectivity check — app starts silently degraded if Redis is down — Add PING on startup
- [ ] **INFRA-12** — DB pool size not validated for multi-worker — 4 workers × 60 connections = 240 (exceeds many DB limits) — Log total and validate
- [ ] **INFRA-13** — No request body size limit — large JSON bodies accepted unbounded — Add `MaxBodySizeMiddleware` (5MB limit)
- [ ] **INFRA-14** — Docker system packages not pinned — non-reproducible builds (`Dockerfile:13-17`) — Pin versions
- [ ] **INFRA-15** — `database_echo` not validated off in production — SQL queries logged with sensitive data — Add validation in `validate_production_secrets()`
- [ ] **INFRA-16** — `docker-compose.yml` hardcodes default postgres credentials — replace with env var interpolation

### Low
- [ ] **INFRA-17** — Log level can't be changed without restart — Add admin endpoint `PATCH /admin/logging/level`
- [ ] **INFRA-18** — No Prometheus metrics endpoint — application health opaque — Add `prometheus-fastapi-instrumentator`
- [ ] **INFRA-19** — No pool event listeners — connection checkout/invalidate events not logged
- [ ] **INFRA-20** — `alembic.ini` sqlalchemy.url placeholder not guarded — migrations run against wrong DB if env var missing

---

## Pre-existing Known Bugs (from MEMORY.md)
- [ ] **KNOWN-01** — `bulk_generation.py` passes extra params (`title`, `writing_style`, `custom_instructions`) to `generate_outline()` that the method doesn't accept → bulk outline generation fails
- [ ] **KNOWN-02** — Article generation route does NOT load `brand_voice` from project → brand voice defaults not applied for articles
- [ ] **KNOWN-03** — `regenerate_outline` endpoint doesn't re-load `brand_voice` from project
- [ ] **KNOWN-04** — Two separate SEO scoring systems (backend base-50 + frontend 10x10) can diverge

---

## Summary Progress
| Section | Status | Issues Found | Fixed (all sessions) |
|---------|--------|-------------|-------|
| 1 — Auth & Authorization | ✅ Audited | 18 | AUTH-01,03,04,05,06,07,08,11,12,14 |
| 2 — Project & Team | ✅ Audited | 24 | PROJ-01,02,03,04,07,08,09,10,13,14,16 |
| 3 — Content Generation | ✅ Audited | 20 | GEN-01,02,03,04,05,06,09,10 |
| 4 — Bulk Generation | ✅ Audited | 20 | BULK-01,02,03,04,06,07,10 |
| 5 — Analytics | ✅ Audited | 20 | ANA-01,02,03,04,06,07,09,10,11 |
| 6 — Knowledge Vault | ✅ Audited | 20 | KV-01,02,03,04,05,06,07 |
| 7 — Social Media | ✅ Audited | 20 | SM-01(not-a-bug),02,03,04,05,06,09,11,12 |
| 8 — Images | ✅ Audited | 20 | IMG-01,02,03,05,07,08(already-fixed),09 |
| 9 — Agency Mode | ✅ Audited | 12 | AGY-01,02,03(already-fixed),04,05 |
| 10 — Billing | ✅ Audited | 15 | BILL-01,03,04,05,06,07,08,09,10,12,13 |
| 11 — Admin Panel | ✅ Audited | 15 | ADM-01,02,03,05,06,07,08,09,10,14,15 |
| 12 — SEO Scoring | ✅ Audited | 20 | SEO-01,04(via-01),05,07,08,09,11,12(already-done),13 |
| 13 — Infrastructure | ✅ Audited | 20 | INFRA-01,02,04,05,06,07,08,09,10,12,13,15 |
