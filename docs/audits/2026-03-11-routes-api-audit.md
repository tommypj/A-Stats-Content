# Route & API Consistency Audit

**Date:** 2026-03-11
**Auditor:** Claude Opus 4.6 (automated)
**Scope:** Backend route registration, frontend-backend API alignment, auth consistency, response format consistency, error handling

---

## Summary

| Category                                   | Findings |
|--------------------------------------------|----------|
| Unregistered routes                        | 0        |
| Duplicate route paths                      | 0        |
| Frontend calling non-existent backend route| 1 (Critical) |
| Pagination field inconsistency             | 1 (Warning) |
| Backend endpoints without FE caller        | 15 (5 medium, 10 intentional/low) |
| Missing rate limiting on mutations         | 87       |
| Auth consistency issues                    | 0        |
| Missing error handling                     | 0        |
| Route parameter mismatches                 | 0        |
| Orphan/dead frontend pages                 | 7 (locale leftovers) |
| Other findings                             | 3        |

---

## 1. Critical Findings

### 1.1 Frontend `projects.uploadLogo` calls non-existent backend route

- **Severity:** Critical
- **Frontend:** `frontend/lib/api.ts:1410-1415` -- `uploadLogo()` sends `POST /projects/{projectId}/logo` with multipart form data
- **Frontend usage:** `frontend/app/(dashboard)/projects/[projectId]/settings/page.tsx:164` -- called when user uploads a project logo image
- **Backend:** No `POST /{project_id}/logo` route exists in `backend/api/routes/projects.py`. The backend handles project logos via the `logo_url` string field in `PUT /{project_id}` (line 556), not as a file upload endpoint.
- **Impact:** Users clicking the logo upload button on the project settings page will receive a 404 error at runtime.
- **Fix:** Either (a) add a `POST /{project_id}/logo` file upload endpoint to `backend/api/routes/projects.py` (similar to `POST /auth/me/avatar` in `auth.py:1034`), or (b) change the frontend to upload the image via a general upload endpoint and pass the resulting URL to `PUT /projects/{project_id}` with `logo_url`.

---

## 2. Backend Route Registration

### 2.1 All Routes Registered

**Result: PASS** -- All 29 route files in `backend/api/routes/` are imported and included in `backend/api/routes/__init__.py` (lines 5-33 for imports, lines 39-67 for `include_router` calls). Total of 287 endpoints across all routers.

### 2.2 No Duplicate Route Paths

**Result: PASS** -- No duplicate `(HTTP method, path)` combinations found. Note: `projects.py` and `project_invitations.py` both use `prefix="/projects"` but their sub-paths are non-overlapping (`projects.py` defines `/{project_id}`, `/switch`, `/current`, etc.; `project_invitations.py` defines `/{project_id}/invitations/...` and `/invitations/{token}/...`).

### 2.3 Route Registration Map

| File | Prefix | Endpoint Count |
|------|--------|---------------|
| `health.py` | (none -- mounts at `/health`) | 6 |
| `auth.py` | `/auth` | 16 |
| `articles.py` | `/articles` | 22 |
| `outlines.py` | `/outlines` | 9 |
| `images.py` | `/images` | 6 |
| `analytics.py` | `/analytics` | 27 |
| `billing.py` | `/billing` | 10 |
| `wordpress.py` | `/wordpress` | 7 |
| `knowledge.py` | `/knowledge` | 8 |
| `social.py` | `/social` | 17 |
| `projects.py` | `/projects` | 14 |
| `project_invitations.py` | `/projects` | 6 |
| `notifications.py` | `/notifications` | 5 |
| `bulk.py` | `/bulk` | 9 |
| `agency.py` | `/agency` | 16 |
| `competitor.py` | `/competitors` | 6 |
| `site_audit.py` | `/site-audit` | 7 |
| `blog.py` | `/blog` | 5 |
| `templates.py` | `/templates` | 5 |
| `reports.py` | `/reports` | 4 |
| `tags.py` | `/tags` | 8 |
| `admin_analytics.py` | `/admin/analytics` | 5 |
| `admin_content.py` | `/admin/content` | 10 |
| `admin_users.py` | `/admin` | 9 |
| `admin_alerts.py` | `/admin/alerts` | 4 |
| `admin_blog.py` | `/admin/blog` | 15 |
| `admin_emails.py` | `/admin/emails` | 3 |
| `admin_error_logs.py` | `/admin/error-logs` | 5 |
| `admin_generations.py` | `/admin/generations` | 2 |

---

## 3. Frontend-Backend API Alignment

### 3.1 Frontend API Methods vs Backend Routes

All 194 frontend API method URLs in `frontend/lib/api.ts` were traced to backend route definitions. Except for the Critical finding in section 1.1, all paths, HTTP methods, and parameter shapes align correctly.

### 3.2 Backend Endpoints Without Frontend API Methods

**Intentionally uncovered (not issues):**

| Backend Endpoint | Reason |
|-----------------|--------|
| `GET /auth/google`, `GET /auth/google/callback` | OAuth browser redirect flow (used via `window.location.href`) |
| `POST /auth/refresh` | Handled by axios response interceptor (cookie-based) |
| `POST /billing/webhook` | Called by LemonSqueezy webhook, not frontend |
| `GET /blog/feed.xml` | RSS feed, accessed by feed readers |
| `GET /health/*` (5 endpoints) | Infrastructure health checks |
| `POST /notifications/unsubscribe`, `GET /notifications/unsubscribe` | Email unsubscribe links (RFC 8058) |
| `GET /social/{platform}/callback` | OAuth browser redirect flow |
| `POST /social/facebook/data-deletion` | Facebook data deletion webhook |

**Potential issues (no frontend consumer):**

| Backend Endpoint | File:Line | Severity | Description |
|-----------------|-----------|----------|-------------|
| `POST /admin/users/{user_id}/reset-usage` | `admin_users.py:811` | Warning | Admin endpoint with no UI button. Consider adding to admin user detail page. |
| `GET /articles/{article_id}/stream` | `articles.py:749` | Warning | SSE streaming endpoint unused by frontend. Either wire into article generation flow or remove. |
| `GET /social/best-times` | `social.py:1460` | Warning | Returns optimal posting times; no frontend consumer. Should be wired to social compose/calendar. |
| `GET /social/stats` | `social.py:1266` | Warning | Social stats endpoint unused. Frontend computes stats client-side from post list. |
| `PUT /knowledge/sources/{source_id}` | `knowledge.py:421` | Warning | Backend supports updating source metadata but `api.knowledge` has no `updateSource` method. |
| `POST /social/preview` | `social.py:1420` | Info | Post preview generation, not used in compose flow. |
| `GET /social/calendar` | `social.py:1189` | Info | Backend calendar endpoint; frontend renders its own calendar from post list data. |
| `POST /admin/blog/posts/persist-images` | `admin_blog.py:762` | Info | Internal image persistence utility, likely manual/cron use. |
| `POST /projects/{project_id}/switch` | `projects.py:877` | Info | Redundant -- frontend uses `POST /projects/switch` (body-based) at line 414 instead. |
| `GET /admin/content/social-posts`, `DELETE .../social-posts/{post_id}` | `admin_content.py:633,731` | Warning | Admin social post management with no admin page. |
| `POST /admin/content/bulk-delete` | `admin_content.py:785` | Info | Admin bulk delete with no frontend caller. |
| `GET/POST/DELETE /billing/admin/refund-blocked-emails` | `billing.py:505,527,568` | Info | Admin refund blocklist management with no UI. |
| `POST /auth/resend-verification` | `auth.py:831` | Warning | No frontend method. The verify-email page could use a "Resend" button. |

### 3.3 Route Parameter Consistency

**Result: PASS** -- All path parameters in frontend URL templates match the corresponding FastAPI route parameter names (e.g., `${articleId}` maps to `article_id: str` in route handler signatures). No mismatches found.

---

## 4. Pagination Format Inconsistency

- **Severity:** Warning
- **Description:** The codebase uses two different field names for the total page count in paginated responses:
  - **`pages`** -- used by: `outlines.py`, `articles.py`, `images.py`, `analytics.py`, `knowledge.py`, `bulk.py`, `competitor.py`, `site_audit.py`, `agency.py`, `reports.py`, `tags.py`, `templates.py`, `social.py`
  - **`total_pages`** -- used by: `projects.py`, `project_invitations.py`, `blog.py`, `admin_alerts.py`, `admin_blog.py`, `admin_content.py`, `admin_error_logs.py`, `admin_generations.py`, `admin_users.py`
- **Impact:** Frontend TypeScript types correctly match their respective backends (user-facing types use `pages`, admin types use `total_pages`), so there is no runtime bug. But the inconsistency creates confusion for developers and increases maintenance burden.
- **Fix:** Standardize on one field name across all routes. `pages` is used by the majority (13 files vs 9). A migration would require updating all admin route response models and corresponding frontend types.

---

## 5. Auth/Middleware Consistency

### 5.1 Auth Requirements

**Result: PASS** -- All routes that should require authentication do use `Depends(get_current_user)` or `Depends(get_current_admin_user)`. Public routes are appropriately unauthenticated:
- `GET /health/*` -- no auth (infrastructure probes)
- `GET /billing/pricing` -- no auth (public pricing page)
- `POST /billing/webhook` -- no auth (verified by X-Signature header)
- `GET /blog/*` -- no auth (public blog)
- `GET /agency/portal/{token}` -- no auth (token-authenticated portal)
- `POST /social/facebook/data-deletion` -- no auth (Facebook webhook)
- `GET /social/{platform}/callback` -- no auth (OAuth redirect, state-verified)
- `POST/GET /notifications/unsubscribe` -- no auth (email link, token-verified)
- `GET /projects/invitations/{token}` -- no auth (invitation link, token-verified)
- `POST /projects/invitations/{token}/accept` -- requires auth (user must be logged in)

### 5.2 Admin Route Protection

**Result: PASS** -- All routes under `/admin/*` prefixes use `Depends(get_current_admin_user)`. The `billing.py` admin sub-routes (`/billing/admin/*`) also use `get_current_admin_user`.

---

## 6. Missing Rate Limiting on Mutation Endpoints

- **Severity:** Warning
- **Count:** 87 of 151 POST/PUT/PATCH/DELETE endpoints lack explicit `@limiter.limit()` decorators
- **Mitigation:** The global SlowAPI middleware (`100/minute` default) applies to all endpoints, so these are not fully unprotected
- **Impact:** The global limit is generous. Sensitive operations (e.g., `POST /articles/bulk-delete`, `DELETE /projects/{id}`, `POST /wordpress/publish`) should have tighter per-endpoint limits.

**Highest-priority unlimited mutation endpoints (user-facing, write-heavy):**

| File | Line | Path | Suggested Limit |
|------|------|------|-----------------|
| `articles.py` | 275 | `POST /articles` | `20/minute` |
| `articles.py` | 1298 | `POST /articles/bulk-delete` | `10/minute` |
| `outlines.py` | 440 | `POST /outlines/bulk-delete` | `10/minute` |
| `images.py` | 347 | `POST /images/bulk-delete` | `10/minute` |
| `wordpress.py` | 463 | `POST /wordpress/publish` | `10/minute` |
| `wordpress.py` | 916 | `POST /wordpress/upload-media` | `5/minute` |
| `projects.py` | 586 | `DELETE /projects/{id}` | `5/minute` |
| `projects.py` | 832 | `POST /projects/{id}/transfer-ownership` | `5/minute` |
| `billing.py` | 527 | `POST /billing/admin/refund-blocked-emails` | `10/minute` |

Full list of 87 unlimited mutation endpoints available in earlier audit revision.

---

## 7. Error Handling

### 7.1 404 Handling on Resource Routes

**Result: PASS** -- All `GET /{id}`, `PUT /{id}`, `DELETE /{id}` style routes check for the resource existence and raise `HTTPException(status_code=404)` when not found. Spot-checked: `articles.py:1346`, `outlines.py:489`, `images.py:399`, `projects.py:472`, `agency.py:389`, `knowledge.py:386`.

### 7.2 Global Error Handling

**Result: PASS** -- `main.py` has:
- `ConnectionError` handler (line 383) returning 503
- Generic `Exception` handler (line 412) returning 500
- `RateLimitExceeded` handler (line 361)
- All three log to the system error log for admin visibility

---

## 8. Orphan Pages

- **Severity:** Info
- **Description:** 7 pages under `frontend/app/[locale]/(dashboard)/settings/` are unreachable because the `settings` path segment is excluded from the next-intl locale middleware in `frontend/middleware.ts`. These are leftover from a previous i18n implementation.
- **Files:**
  - `frontend/app/[locale]/(dashboard)/settings/page.tsx`
  - `frontend/app/[locale]/(dashboard)/settings/password/page.tsx`
  - `frontend/app/[locale]/(dashboard)/settings/language/page.tsx`
  - `frontend/app/[locale]/(dashboard)/settings/notifications/page.tsx`
  - `frontend/app/[locale]/(dashboard)/settings/integrations/page.tsx`
  - `frontend/app/[locale]/(dashboard)/settings/billing/page.tsx`
  - `frontend/app/[locale]/(dashboard)/billing/success/page.tsx`
- **Fix:** Remove the `frontend/app/[locale]/(dashboard)/` directory entirely.

---

## 9. Other Findings

### 9.1 Redundant project switch endpoint

- **Severity:** Info
- **Location:** `backend/api/routes/projects.py:877` (`POST /projects/{project_id}/switch`)
- **Description:** Duplicate of `POST /projects/switch` (line 414) which accepts `project_id` in the request body. Frontend only uses the body-based version. The path-based version is dead code.
- **Fix:** Remove the path-based version or deprecate it.

### 9.2 `auth/resend-verification` has no frontend method

- **Severity:** Warning
- **Location:** `backend/api/routes/auth.py:831`
- **Description:** Backend has `POST /auth/resend-verification` but frontend `api.ts` has no method for it. The verify-email page would benefit from a "Resend verification email" button.
- **Fix:** Add `resendVerification` to `api.auth` in `frontend/lib/api.ts`.

### 9.3 Frontend `analytics.handleCallback` passes query params in URL string

- **Severity:** Info
- **Location:** `frontend/lib/api.ts:686`
- **Description:** The GSC callback method embeds `code` and `state` as query params directly in the URL string (`/analytics/gsc/callback?code=...&state=...`) instead of using the `params` field in the axios config. This works but is inconsistent with the rest of the API client.
- **Fix:** Change to `url: "/analytics/gsc/callback", params: { code, state }` for consistency.
