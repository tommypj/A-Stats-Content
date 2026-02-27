# Audit Section 9 — Agency & White-Label Mode
**Date**: 2026-02-27
**Status**: Complete

---

## Scope
- Agency profile management (setup, branding, settings)
- Client workspace creation and management
- Client portal (public-facing, token-gated)
- Automated report generation for clients
- White-label domain and branding configuration

---

## Files Audited
- `backend/api/routes/agency.py`
- `backend/infrastructure/database/models/agency.py`
- `frontend/app/portal/[token]/page.tsx`
- `frontend/app/[locale]/(dashboard)/agency/` (all pages)
- `frontend/lib/api.ts` (agency/portal methods)
- `frontend/middleware.ts` (route exclusion check)

---

## Findings

### CRITICAL

#### AGY-01 — Client portal branding fields missing from PortalSummaryResponse — portals always unbranded
- **Severity**: CRITICAL
- **Files**: `backend/api/routes/agency.py:805-817, 982-993`, `frontend/app/portal/[token]/page.tsx:203-240, 387-399`
- **Description**: The backend correctly fetches the `AgencyProfile` object during portal data retrieval, but the `PortalSummaryResponse` only includes `agency_name` — not `logo_url`, `brand_colors`, `contact_email`, or `footer_text`. The frontend `PortalData` interface declares these fields and the portal page renders them (agency logo, client logo, accent color, footer), but they are always `undefined` at runtime. Every client portal shows as completely unbranded regardless of the agency's settings.
- **Fix**: Update `PortalSummaryResponse` to include all branding fields. Populate them from the fetched `AgencyProfile` and `ClientWorkspace` objects in the `get_portal_data` endpoint.

#### AGY-02 — Portal token no rate limiting — brute-force attack feasible
- **Severity**: CRITICAL
- **File**: `backend/api/routes/agency.py:422, 820-993`
- **Description**: `GET /agency/portal/{token}` is a public endpoint with no authentication and no rate limiting. Portal tokens use `secrets.token_urlsafe(32)` (252 bits entropy — adequate, but at the lower end). Without rate limiting, an attacker can send unlimited requests probing tokens. The endpoint also makes multiple expensive DB aggregation queries per request (keyword rankings, conversion data, analytics), making it a viable DoS vector even without finding a valid token.
- **Fix**: (1) Add `@limiter.limit("20/minute")` per-IP on the portal endpoint. (2) Increase token to `secrets.token_urlsafe(64)`. (3) Cache portal responses for 5-10 minutes — portal data doesn't need real-time freshness.

---

### HIGH

#### AGY-03 — Client workspace creation missing project membership check
- **Severity**: HIGH
- **File**: `backend/api/routes/agency.py:298-357`
- **Description**: The `create_client_workspace` endpoint checks `Project.owner_id == current_user.id` but the platform supports shared project membership via `ProjectMember`. A project collaborator who is an EDITOR or VIEWER can set their `current_project_id` to a shared project and create client workspaces for that project — which only the OWNER/ADMIN should be able to do. Agency workspace creation is an ownership-level action.
- **Fix**: After checking project existence, verify `current_user` has OWNER or ADMIN role in the project: query `ProjectMember` for `(project_id, current_user.id, role IN [OWNER, ADMIN])`. Return 403 if not found.

#### AGY-04 — IDOR: workspace_id filter not validated against current agency in report list
- **Severity**: HIGH
- **File**: `backend/api/routes/agency.py:748-771`
- **Description**: `list_generated_reports` accepts an optional `client_workspace_id` filter but does not validate that the workspace belongs to the current user's agency before adding it to the query. The `agency_id` filter prevents actual data leakage (reports from other agencies are excluded), but an attacker can enumerate valid workspace IDs via timing differences — a workspace that belongs to another agency still causes a filtered query vs. an invalid UUID which may short-circuit differently.
- **Fix**: If `client_workspace_id` is provided, validate it belongs to the current agency: `SELECT id FROM client_workspaces WHERE id=? AND agency_id=?`. Return 404 if not found, before adding to filter conditions.

#### AGY-05 — No rate limiting on public portal — DB DoS via analytics aggregations
- **Severity**: HIGH
- **File**: `backend/api/routes/agency.py:820-993`
- **Description**: The public portal endpoint makes 6+ expensive database aggregation queries per request (DailyAnalytics, PagePerformance, KeywordRanking, ContentConversion — lines 620-720) with no rate limiting, no caching, and no query timeout. Any attacker can repeatedly hit the endpoint for a valid portal token and exhaust database connection pool capacity. There is also no `asyncio.wait_for()` timeout protecting against slow DB queries.
- **Fix**: (1) Add `@limiter.limit("20/minute")` per-IP. (2) Cache portal responses in Redis with 10-minute TTL. (3) Add `asyncio.wait_for()` with 10s timeout on the full data aggregation block.

---

### MEDIUM

#### AGY-06 — Agency deleted with no soft-delete, no audit trail, no data warning
- **Severity**: MEDIUM
- **File**: `backend/api/routes/agency.py:259-268`
- **Description**: `delete_agency_profile` executes `await db.delete(profile)` which hard-deletes the agency and cascade-deletes all client workspaces, report templates, and generated reports. No confirmation is required, no audit log is created, no user warning lists what will be deleted. This is the highest-impact single action a user can take and it's permanent and immediate.
- **Fix**: (1) Add `deleted_at` soft-delete to `AgencyProfile`. (2) Create an audit log entry listing counts of associated records. (3) Add a two-step confirmation (requires typing agency name or passing `?confirm=true`).

#### AGY-07 — Client workspace list missing eager loading — N+1 queries for project data
- **Severity**: MEDIUM
- **File**: `backend/api/routes/agency.py:276-290`
- **Description**: `list_client_workspaces` fetches all workspaces with a simple SELECT but doesn't eager-load the related `Project`. If the response or downstream processing accesses `workspace.project` (for project name, slug, etc.), this triggers a separate SELECT per workspace. 50 workspaces = 51 queries.
- **Fix**: Add `selectinload(ClientWorkspace.project)` to the query if the `ClientWorkspace` model has the relationship defined. Include project name in the response schema to avoid N+1 on the frontend.

#### AGY-08 — Portal `footer_text` rendered without HTML sanitization — XSS if agency admin is compromised
- **Severity**: MEDIUM
- **File**: `frontend/app/portal/[token]/page.tsx:387-388`
- **Description**: Agency `footer_text` and `contact_email` are rendered in the client portal via JSX (`<span>{data.footer_text}</span>`). JSX escapes these correctly in normal use. However, `agency_logo_url` and `client_logo_url` are used directly in `<img src={...}>` without URL validation. If an agency admin account is compromised, an attacker could inject a `javascript:` URL in the logo field, which some browsers execute.
- **Fix**: Validate that `agency_logo_url` and `client_logo_url` start with `https://` before using as `<img>` src. Consider using CSS `background-image` with sanitized URLs or the Next.js `<Image>` component with `domains` allowlist.

#### AGY-09 — Portal token never expires — once shared, access is permanent
- **Severity**: MEDIUM
- **File**: `backend/api/routes/agency.py` (portal token generation)
- **Description**: Portal access tokens have no expiration date. Once a client portal URL is shared, it remains accessible indefinitely — even if the client relationship ends, the agency is deleted (though CASCADE handles the record), or the token is leaked. There is no mechanism to rotate or expire tokens except deleting the entire portal record.
- **Fix**: Add `portal_token_expires_at: Optional[datetime]` to `ClientWorkspace`. Add an agency setting for default portal link expiry (e.g., 90 days). On the portal endpoint, check token expiry before returning data and return 410 Gone if expired.

---

### LOW

#### AGY-10 — No access logging on client portal visits
- **Severity**: LOW
- **File**: `backend/api/routes/agency.py:820-993`
- **Description**: There is no record of when and how many times a client portal is accessed. Agencies cannot see if a client has viewed their portal, making it impossible to know if the portal link was shared with unintended parties.
- **Fix**: Create a `PortalAccessLog` table recording `(workspace_id, accessed_at, ip_address, user_agent)`. Log each portal visit. Expose an "access history" panel in the agency dashboard.

#### AGY-11 — No pagination on generated reports list
- **Severity**: LOW
- **File**: `backend/api/routes/agency.py:748-771`
- **Description**: `list_generated_reports` returns reports without pagination. An agency with many historical reports gets an unbounded response. The frontend would need to load all reports at once.
- **Fix**: Add `page`/`page_size` pagination consistent with other list endpoints.

#### AGY-12 — No limit on number of client workspaces per agency
- **Severity**: LOW
- **File**: `backend/api/routes/agency.py:298-357`
- **Description**: An agency can create unlimited client workspaces. While each workspace is tied to a project (and project creation may be plan-limited), there's no explicit per-agency workspace count limit. An adversarial user could create thousands of workspaces to bloat DB storage.
- **Fix**: Add a configurable `max_client_workspaces` per plan (e.g., 10 for starter, 50 for professional, unlimited for agency plan). Enforce at workspace creation time.

---

## What's Working Well
- Tenant isolation enforced: agency endpoints always filter by `agency_id == profile.id`
- `get_client_workspace_for_agency()` correctly verifies workspace ↔ agency relationship
- Portal endpoint has no auth requirement (correct for public sharing)
- `ClientWorkspace.portal_enabled` flag correctly gates portal access
- CASCADE deletes on `agency_id` FK ensure workspace/report cleanup when agency is deleted
- Middleware correctly excludes `/portal` and `/agency` from i18n redirect logic

---

## Fix Priority Order
1. AGY-01 — Missing branding in portal response (CRITICAL)
2. AGY-02 — Portal token no rate limiting, no DoS protection (CRITICAL)
3. AGY-03 — Missing project membership check at workspace creation (HIGH)
4. AGY-04 — IDOR in report filter via workspace_id (HIGH)
5. AGY-05 — Public portal no rate limiting, no caching, no timeout (HIGH)
6. AGY-06 — Agency hard-delete no soft-delete or audit trail (MEDIUM)
7. AGY-07 — N+1 queries in workspace list (MEDIUM)
8. AGY-08 — Logo URLs used without scheme validation (MEDIUM)
9. AGY-09 — Portal tokens never expire (MEDIUM)
10. AGY-10 through AGY-12 — Low severity (LOW)
