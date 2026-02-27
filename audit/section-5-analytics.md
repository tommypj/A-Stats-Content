# Audit Section 5 — Analytics Suite
**Date**: 2026-02-27
**Status**: Complete

---

## Scope
- GSC (Google Search Console) OAuth flow, token storage, data sync
- Keyword rankings, page performance, opportunities endpoints
- Content decay detection service and alerts
- AEO (Answer Engine Optimization) scoring
- Revenue attribution, conversion goals, CSV import
- Frontend analytics pages

---

## Files Audited
- `backend/api/routes/analytics.py`
- `backend/services/content_decay.py`
- `backend/services/aeo_scoring.py`
- `backend/services/revenue_attribution.py`
- `backend/infrastructure/database/models/analytics.py`
- `frontend/app/[locale]/(dashboard)/analytics/` (all pages)
- `frontend/app/[locale]/(dashboard)/analytics/callback/page.tsx`

---

## Findings

### CRITICAL

#### ANA-01 — GSC OAuth callback state parameter not validated (CSRF)
- **Severity**: CRITICAL
- **File**: `backend/api/routes/analytics.py:171` / `frontend/app/[locale]/(dashboard)/analytics/callback/page.tsx`
- **Description**: The GSC OAuth flow generates a `state` parameter on the initiate endpoint and stores it (presumably in session or DB). However, the callback endpoint does not validate that the returned `state` matches the stored one. An attacker can craft a malicious OAuth callback URL and trick a logged-in user into connecting the attacker's GSC property to the victim's account. Both backend route and frontend callback page were confirmed to skip state validation.
- **Attack scenario**: Attacker crafts `GET /analytics/gsc/callback?code=ATTACKER_CODE&state=ANYTHING` and delivers it to victim via CSRF. Victim's account is linked to attacker's GSC data.
- **Fix**: On callback, retrieve the stored state from the user's session (or a short-lived DB record keyed by user_id). Compare with `request.query_params["state"]`. If mismatch or missing, return 400 and abort the OAuth flow. On frontend, read and store `state` in sessionStorage before redirect, verify it on callback before sending to backend.

#### ANA-02 — AEO score refresh endpoint lacks article ownership check
- **Severity**: CRITICAL
- **File**: `backend/api/routes/articles.py:1672` (AEO score trigger)
- **Description**: The endpoint that triggers AEO score recalculation for an article verifies the article exists but does not verify it belongs to the current user's project. Any authenticated user can trigger expensive AEO re-scoring for any article by ID, including articles in other users' projects. This is a horizontal privilege escalation (IDOR) vulnerability and also a cost amplification vector (triggers AI calls per article).
- **Fix**: After loading the article, check `article.project_id == current_user.current_project_id` (or a full project membership check). Return 403 if the article belongs to a different project.

---

### HIGH

#### ANA-03 — GSC token refresh during sync not persisted to DB
- **Severity**: HIGH
- **File**: `backend/api/routes/analytics.py` (sync endpoint, token refresh path)
- **Description**: When the GSC access token expires mid-sync, the analytics service refreshes it using the stored refresh token. The new access token is used for the current sync but is never written back to the database. The next sync will start with the same expired access token, trigger another refresh, and so on. Eventually, when the refresh token itself expires (Google refresh tokens expire after 6 months of non-use or policy refresh), the user loses GSC connection silently — the sync appears to complete but uses stale data.
- **Fix**: After a successful token refresh, immediately persist the new `access_token` (and updated `expires_at`) to the `GSCConnection` record in the DB. Use a separate DB session scoped to the token update to avoid coupling it to the main sync transaction.

#### ANA-04 — N+1 query fetching article titles for decay alerts
- **Severity**: HIGH
- **File**: `backend/api/routes/analytics.py:1520-1523, 1604-1608`
- **Description**: When listing content decay alerts, the code iterates over alert records and for each one issues a separate `SELECT title FROM articles WHERE id = ?` query to fetch the article title. For a project with 100 alerts, this results in 101 database queries per request. The same pattern appears in at least two list endpoints.
- **Fix**: Use a JOIN in the initial alert query to eagerly load article titles: `SELECT alerts.*, articles.title FROM content_decay_alerts JOIN articles ON articles.id = alerts.article_id WHERE ...`. Alternatively use SQLAlchemy `selectinload(ContentDecayAlert.article)` with the relationship configured.

#### ANA-05 — Revenue trend data never populated in API response
- **Severity**: HIGH
- **File**: `backend/services/revenue_attribution.py` (generate_revenue_report)
- **Description**: The `RevenueReport` response schema includes a `trend_data` field (list of time-series revenue data points). The `generate_revenue_report()` function constructs the response object but never populates `trend_data` — it is always returned as an empty list `[]`. The frontend revenue chart that displays this trend has no data to render, so it always shows a flat/empty graph regardless of actual conversion data in the DB.
- **Fix**: After fetching `ContentConversion` records for the date range, group them by day/week/month and aggregate `revenue_amount`. Populate `trend_data` with the resulting time series before returning the response.

#### ANA-06 — URL normalization too simplistic for conversion import matching
- **Severity**: HIGH
- **File**: `backend/services/revenue_attribution.py` (URL normalization / CSV import)
- **Description**: The URL normalization function strips trailing slashes and lowercases the URL, but does not handle: (1) query string parameters (`?utm_source=...`), (2) URL fragments (`#section`), (3) protocol differences (`http://` vs `https://`), (4) `www` vs non-www variants, (5) encoded characters (`%20` vs ` `). A conversion imported with URL `https://example.com/blog/seo/?ref=newsletter` will never match an article stored with URL `https://example.com/blog/seo/`. This causes systematic zero-attribution for UTM-tracked traffic.
- **Fix**: Expand normalization: parse with `urllib.parse.urlparse`, strip scheme, normalize hostname (lowercase, strip `www.`), normalize path (strip trailing slash, decode `%xx`), strip query string and fragment entirely. Apply consistently to both stored article URLs and imported conversion URLs.

---

### MEDIUM

#### ANA-07 — Missing project isolation in content decay deduplication query
- **Severity**: MEDIUM
- **File**: `backend/services/content_decay.py:228-243`
- **Description**: The deduplication query that checks whether a decay alert already exists for an article uses only `article_id` as the key, without filtering by `project_id`. In theory, article IDs are globally unique UUIDs so this wouldn't cause cross-project data leakage. However, if the dedup query ever expands to use keyword or URL matching (which is being considered per comments in the code), the missing project filter becomes a true isolation bug. Additionally, the query hits all projects' alerts on a full table scan.
- **Fix**: Add `project_id` to the deduplication query filter as a defence-in-depth measure and to improve query performance. Add a composite index on `(project_id, article_id, alert_type)` to the ContentDecayAlert model.

#### ANA-08 — Concurrent GSC token refresh race condition
- **Severity**: MEDIUM
- **File**: `backend/api/routes/analytics.py` (token refresh path)
- **Description**: If two GSC sync requests are triggered simultaneously for the same project (e.g., manual sync + scheduled sync), both may detect the expired access token and both attempt to refresh it. Google's OAuth server may invalidate the refresh token after the first use (depending on access type). The second refresh call may fail with `invalid_grant`, permanently disconnecting the GSC integration with no user notification.
- **Fix**: Use a DB-level advisory lock or an `UPDATE gsc_connections SET refresh_in_progress=TRUE WHERE id=? AND refresh_in_progress=FALSE` atomic check before attempting token refresh. If already in progress, wait briefly and re-read the token from DB.

#### ANA-09 — Hard-coded 3-day GSC data delay not configurable
- **Severity**: MEDIUM
- **File**: `backend/api/routes/analytics.py` (date range calculation)
- **Description**: GSC data has a ~3-day processing lag. The sync endpoint subtracts 3 days from `datetime.now()` as the end date for data fetching — this is hardcoded as a magic number with no constant definition or configuration. The actual GSC delay varies (2-4 days) and Google occasionally changes it. If the delay changes, outdated data will be fetched or recent data missed.
- **Fix**: Extract to a named constant `GSC_DATA_LAG_DAYS = 3` in settings or a constants file. Consider making it an admin-configurable setting.

#### ANA-10 — URL normalization doesn't handle query strings in keyword ranking URLs
- **Severity**: MEDIUM
- **File**: `backend/api/routes/analytics.py` (keyword ranking storage)
- **Description**: GSC returns `page` URLs that sometimes include query string parameters (e.g., faceted navigation, tracking parameters). These are stored as-is in the `KeywordRanking.page_url` field. When the frontend matches ranking data to articles, the URL comparison fails for pages with query strings. This results in some ranking data being "orphaned" — stored in the DB but never shown in the article analytics panel.
- **Fix**: Normalize `page_url` before storage using the same normalization function as ANA-06. Strip query strings and fragments from URLs when storing keyword ranking records.

#### ANA-11 — `list_conversion_goals` returns goals across all user projects
- **Severity**: MEDIUM
- **File**: `backend/api/routes/analytics.py` (list_conversion_goals endpoint)
- **Description**: The conversion goals listing endpoint filters by `user_id` but not by `project_id`. A user who is a member of multiple projects sees all conversion goals from all their projects in a single list. This is confusing UX and could lead to accidentally assigning a goal from Project A to revenue data in Project B. It is also inconsistent with every other entity in the app (articles, outlines, etc.) which are always scoped to `current_project_id`.
- **Fix**: Add `project_id=current_user.current_project_id` filter to the conversion goals query. Update the frontend to re-fetch goals when the user switches projects.

#### ANA-12 — No scheduled content decay detection job
- **Severity**: MEDIUM
- **File**: `backend/services/content_decay.py`
- **Description**: `detect_content_decay()` is a well-implemented function that checks articles for traffic drops, ranking declines, and CTR deterioration. However, it is only triggered by a manual API call (`POST /analytics/decay/detect`). There is no background job or cron schedule that runs this detection automatically. Users who don't manually trigger it will never see decay alerts, defeating the purpose of the feature.
- **Fix**: Register `detect_content_decay()` as a daily scheduled task (using APScheduler or a Celery beat schedule). Scope it to run once per project that has GSC data synced in the last 7 days.

#### ANA-13 — AEO composite index mismatch between migration and model
- **Severity**: MEDIUM
- **File**: `backend/infrastructure/database/models/analytics.py`, `backend/infrastructure/database/migrations/versions/025_*.py`
- **Description**: The `AEOScore` model defines a composite index on `(article_id, query, score_date)`. Migration 025 creates an index on `(article_id, score_date)` without `query`. These are different indexes. The model's intended index (including `query`) was never actually created in the database. Queries filtering by `article_id + query` will do a full table scan on large datasets.
- **Fix**: Create a new migration (029) that drops the incorrect index and creates the one matching the model definition: `CREATE INDEX ix_aeo_scores_article_query_date ON aeo_scores (article_id, query, score_date)`.

#### ANA-14 — AEOCitation model exists but is never populated
- **Severity**: MEDIUM
- **File**: `backend/services/aeo_scoring.py`
- **Description**: The `AEOCitation` model stores which AI answers cited a given article/URL. The `aeo_scoring.py` service computes AEO scores from rule-based heuristics (headings, FAQ sections, structured data) but never actually checks AI search results for citations. The `AEOCitation` table is always empty. The feature is scaffolded but unimplemented — users see an AEO score but it doesn't reflect actual AI search citation status.
- **Fix**: Implement citation checking by querying AI search APIs (e.g., Perplexity API, or scraping "People Also Ask" results) for the article's target keyword. Store actual citation events in `AEOCitation`. This is a significant feature gap that should be tracked as a backlog item.

#### ANA-15 — `goal_type` not validated at the database layer
- **Severity**: MEDIUM
- **File**: `backend/infrastructure/database/models/analytics.py` (ConversionGoal model)
- **Description**: `ConversionGoal.goal_type` is a `String` column with no DB-level enum constraint. The route validates it as a Pydantic literal (`"page_view" | "form_submit" | "purchase" | "custom"`), but if the validation is bypassed (e.g., direct DB access, future admin endpoint), any string can be stored. Downstream reporting code that switch-cases on `goal_type` will silently miss unknown values.
- **Fix**: Change the column to `Enum("page_view", "form_submit", "purchase", "custom", name="goal_type_enum")` in the model and add a migration.

#### ANA-16 — CSV header detection can silently skip valid data rows
- **Severity**: MEDIUM
- **File**: `backend/services/revenue_attribution.py` (CSV import)
- **Description**: The CSV import function uses a heuristic to detect and skip header rows: if the first row's `revenue_amount` cell cannot be parsed as a float, it assumes the row is a header and skips it. If a user's first data row has a typo (`$1,234` instead of `1234`), the import silently skips it along with all subsequent rows that also use currency formatting. No error is returned to the user — the import "succeeds" with fewer records than expected.
- **Fix**: Try to parse the first row as data. If parsing fails, check if it looks like a header (strings in numeric columns). If it's a header, skip it and continue. If it's data that failed to parse, return a validation error with the row number and the offending value, not a silent skip.

---

### LOW

#### ANA-17 — No rate limiting on any analytics endpoints
- **Severity**: LOW
- **File**: `backend/api/routes/analytics.py`
- **Description**: The GSC sync endpoint, decay detection endpoint, AEO recalculation, and revenue report generation all make external API calls and/or perform heavy DB aggregations. None of them have `@limiter.limit()` decorators. A user can trigger unlimited sync/compute cycles per minute, exhausting AI API quota and external GSC API rate limits.
- **Fix**: Add rate limits: `5/hour` on GSC sync, `10/hour` on decay detection, `5/minute` on AEO recalculation, `20/minute` on revenue report generation.

#### ANA-18 — `report_type` parameter not validated in revenue report
- **Severity**: LOW
- **File**: `backend/services/revenue_attribution.py`
- **Description**: `generate_revenue_report()` accepts a `report_type` string parameter that is passed directly into the report object and used in conditional logic. The Pydantic route model validates it, but if called internally with an invalid value, the function silently produces an empty report with no error.
- **Fix**: Add a `Literal["summary", "detailed", "attribution"]` type annotation (or equivalent Enum) to the function signature.

#### ANA-19 — Conversion goal deletion is hard delete
- **Severity**: LOW
- **File**: `backend/api/routes/analytics.py` (delete_conversion_goal endpoint)
- **Description**: Deleting a conversion goal permanently removes the record. Any `ContentConversion` records that reference the deleted goal via FK will be orphaned (or cascade-deleted, depending on FK config). Historical attribution reports that referenced the goal by name become inaccurate.
- **Fix**: Add `deleted_at` soft-delete to `ConversionGoal`. Filter out soft-deleted goals in list/get endpoints. Keep historical conversions intact.

#### ANA-20 — No pagination on `list_conversion_goals`
- **Severity**: LOW
- **File**: `backend/api/routes/analytics.py`
- **Description**: The conversion goals listing endpoint returns all goals without pagination. A project with many goals (common in large agencies) will return an unbounded list in a single response.
- **Fix**: Add standard `page`/`page_size` pagination consistent with other list endpoints in the app.

---

## What's Working Well
- GSC access token encrypted at rest using Fernet symmetric encryption — not stored as plaintext
- Keyword ranking data correctly attributed to articles by URL matching
- Content decay detection uses multiple signals (traffic drop, ranking decline, CTR drop) with configurable thresholds
- AEO scoring rule-based checks (FAQ sections, structured data markers, question headings) are reasonable heuristics
- Revenue attribution correctly tracks content-assisted conversions (first-touch, last-touch, linear)
- CSV import handles multiple encodings (UTF-8, Latin-1 fallback)
- GSC data sync correctly handles pagination (fetches all rows, not just first page)
- Opportunity scoring (keyword gap analysis) correctly excludes already-tracked keywords
- `ContentDecayAlert.is_resolved` correctly hides resolved alerts from active list

---

## Fix Priority Order
1. ANA-01 — GSC OAuth state not validated (CSRF) *(CRITICAL)*
2. ANA-02 — AEO refresh endpoint IDOR — no ownership check *(CRITICAL)*
3. ANA-03 — Token refresh not persisted to DB *(HIGH)*
4. ANA-04 — N+1 queries for decay alert titles *(HIGH)*
5. ANA-05 — Revenue trend data never populated *(HIGH)*
6. ANA-06 — Simplistic URL normalization breaks conversion matching *(HIGH)*
7. ANA-07 — Missing project_id in decay dedup query *(MEDIUM)*
8. ANA-08 — Concurrent token refresh race condition *(MEDIUM)*
9. ANA-09 — Hard-coded GSC delay *(MEDIUM)*
10. ANA-10 — Query strings in keyword ranking URLs *(MEDIUM)*
11. ANA-11 — Conversion goals not scoped to current project *(MEDIUM)*
12. ANA-12 — No scheduled decay detection job *(MEDIUM)*
13. ANA-13 — AEO index mismatch *(MEDIUM)*
14. ANA-14 — AEOCitation never populated *(MEDIUM)*
15. ANA-15 — goal_type not validated at DB layer *(MEDIUM)*
16. ANA-16 — CSV header detection silently skips data *(MEDIUM)*
17. ANA-17 through ANA-20 — Low severity items *(LOW)*
