# Security Audit Report - 2026-03-11

**Auditor**: Claude Opus 4.6 (automated)
**Scope**: Full codebase (Next.js 14 frontend + FastAPI backend + PostgreSQL)
**Focus**: Exploitable vulnerabilities, not theoretical risks

---

## Summary

The codebase demonstrates strong security fundamentals from prior audit rounds: parameterised queries (no SQL injection), DOMPurify on all `dangerouslySetInnerHTML`, HMAC webhook verification, SSRF domain allowlists, path traversal protection, OAuth state CSRF protection, HttpOnly cookie auth, token blacklisting, rate limiting, and structured log redaction. However, several real findings remain.

**Findings**: 8 total (0 Critical, 2 High, 4 Medium, 2 Low)

---

## Findings

### HIGH

- **H-01: Token blacklist hash truncated to 16 hex characters (64 bits) -- collision risk**
  - **File**: `backend/api/routes/auth.py`, lines 72 and 92
  - **Detail**: `_blacklist_token` and `_is_token_blacklisted` truncate the SHA-256 hash to 16 hex characters (`hexdigest()[:16]`), giving only 64 bits of collision resistance. The same truncation is used in `_register_session` (line 130) and `_revoke_session` (line 154). An attacker with ~2^32 tokens in circulation could trigger a birthday collision to either (a) blacklist a legitimate user's token (denial of service) or (b) cause `_is_token_blacklisted` to return a false positive/negative. While not trivially exploitable today, the truncation provides no benefit (Redis keys are cheap) and unnecessarily weakens the security boundary. **Recommendation**: Use the full SHA-256 hash (64 hex chars) or at least 32 hex chars (128 bits).

- **H-02: Login response leaks tokens in JSON body alongside HttpOnly cookies**
  - **File**: `backend/api/routes/auth.py`, lines 541-546 (login) and 624-629 (refresh)
  - **Detail**: Both the `/auth/login` and `/auth/refresh` endpoints return `access_token` and `refresh_token` in the JSON response body in addition to setting HttpOnly cookies. This defeats the XSS protection that HttpOnly cookies provide -- any XSS vulnerability in the frontend (or a browser extension) can read the JSON response and exfiltrate both tokens. The comment says "backward compat" but the frontend `api.ts` already uses `withCredentials: true` and `getAuthHeaders()` returns `{}`, confirming no frontend code reads tokens from the body. **Recommendation**: Remove `access_token` and `refresh_token` from the JSON body. Return only `token_type` and `expires_in`. If API clients need body tokens, gate it behind a request header or separate endpoint.

### MEDIUM

- **M-01: IDOR on single image get/delete -- missing `project_id IS NULL` filter in personal mode**
  - **File**: `backend/api/routes/images.py`, lines 395-404 (get_image) and 426-435 (delete_image)
  - **Detail**: When the user is in personal mode (`current_project_id` is None), the query filters by `GeneratedImage.user_id == current_user.id` but does NOT add `GeneratedImage.project_id.is_(None)`. In contrast, `list_images` (line 314-317) and `bulk_delete_images` (line 374-378) correctly add this filter. This means a user who was removed from a project can still GET or DELETE images they originally created for that project, bypassing project membership checks. **Recommendation**: Add `GeneratedImage.project_id.is_(None)` to the personal-mode branch in `get_image` and `delete_image`, matching the pattern used in `list_images`.

- **M-02: Missing Content-Security-Policy header**
  - **File**: `backend/main.py`, line 494
  - **Detail**: The `add_security_headers` middleware sets `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` but explicitly defers CSP with a TODO comment. Without CSP, any XSS vulnerability gains full access to inline scripts, eval, and third-party resource loading. The API serves uploaded images at `/uploads/` which compounds this risk. **Recommendation**: Add a restrictive CSP. At minimum: `default-src 'self'; script-src 'none'; style-src 'none'; img-src 'self' data: https:; frame-ancestors 'none'` for the API. The frontend (Vercel) should have its own CSP via `next.config.js`.

- **M-03: `python-jose` JWT library is unmaintained -- known CVEs**
  - **File**: `backend/pyproject.toml`, line 29; `backend/core/security/tokens.py`, line 8
  - **Detail**: The project uses `python-jose[cryptography]>=3.3.0` for JWT handling. `python-jose` has been effectively unmaintained since 2022 and has known issues (e.g., CVE-2024-33664 for algorithm confusion when using ECDSA). While the codebase only uses HS256 (not affected by the ECDSA CVE), relying on an unmaintained library for the authentication core is a supply-chain risk. **Recommendation**: Migrate to `PyJWT>=2.8.0` (actively maintained, same API surface) or `joserfc`. The `email_journey_unsubscribe.py` already uses `PyJWT` directly (`import jwt`), creating an inconsistency.

- **M-04: Next.js 14.1.0 is outdated -- known security patches in later releases**
  - **File**: `frontend/package.json`, line 30
  - **Detail**: Next.js 14.1.0 (January 2024) has multiple security fixes in later 14.x releases, including server-side request forgery mitigations and Server Actions security patches. The current version is over two years old. **Recommendation**: Update to the latest Next.js 14.2.x (or 15.x) to pick up security patches.

### LOW

- **L-01: OAuth in-memory state fallback is not safe for multi-worker deployments**
  - **File**: `backend/api/oauth_helpers.py`, lines 28-77
  - **Detail**: When Redis is unavailable, OAuth state is stored in a process-local `dict`. In a multi-worker deployment (e.g., `workers > 1` in settings), the state created by one worker will not be visible to another, causing OAuth callbacks to fail with "Invalid or expired OAuth state." More critically, if Redis goes down mid-flow in production, the fallback silently activates with no alarm beyond a debug log, and states are not shared across workers. **Recommendation**: Either (a) fail hard when Redis is unavailable in production (raise an error on the initiate endpoint) or (b) log at CRITICAL level when falling back to in-memory storage in production, similar to the rate-limiter pattern in `rate_limit.py`.

- **L-02: Refund race condition between webhook and refund endpoint**
  - **File**: `backend/api/routes/billing.py`, lines 476-488 and 714-715
  - **Detail**: The `/billing/refund` endpoint performs the refund, then cancels, then updates the user record (lines 476-488). However, the cancellation triggers a `subscription_updated` webhook from LemonSqueezy. Although the webhook handler checks for `subscription_status == "refunded"` (line 724), there is a window between the refund API call returning and the `db.commit()` on line 488 where the webhook could arrive and be processed before the user's status is set to "refunded". The webhook handler does use `with_for_update()` (line 715), but the refund endpoint does NOT lock the user row. If the webhook processes first and sets `subscription_tier` to the paid tier (via the `subscription_updated` event), the refund endpoint's subsequent commit would overwrite it to free -- which is correct -- but if the order is reversed, the webhook could re-upgrade the user after the refund. The existing `"refunded"` status check mitigates most scenarios, but the lack of a row lock in the refund endpoint leaves a narrow window. **Recommendation**: Add `with_for_update()` when loading the user in the refund endpoint, or set `subscription_status = "refunded"` and commit before calling the LemonSqueezy API.

---

## Areas Reviewed and Found Secure

These areas were audited and found to have adequate security controls:

- **SQL Injection**: All queries use SQLAlchemy ORM with parameterised binds. `escape_like()` properly escapes LIKE wildcards. `text()` fragments use `.bindparams()`. No f-string SQL found.
- **XSS**: All `dangerouslySetInnerHTML` usages are protected by DOMPurify.sanitize() with explicit ALLOWED_TAGS/ALLOWED_ATTR. JSON-LD uses `JSON.stringify()` (safe). Blog content is sanitized client-side.
- **Authentication**: JWT tokens verified with `algorithms=[self._algorithm]` (no algorithm confusion). Token type validated (access vs refresh). Blacklisting on logout/refresh rotation. `password_changed_at` invalidates old tokens. Rate limiting on auth endpoints.
- **Authorization**: Admin routes use `get_current_admin_user` / `get_current_super_admin_user` dependencies. Content queries use `scoped_query()` or manual user_id/project_id filters. Privilege escalation prevented (only super_admin can assign admin roles).
- **CORS**: Configured with explicit `cors_origins_list` from settings (not `*`). `allow_credentials=True` with specific origins. Custom `X-Requested-With` header forces CORS preflight.
- **CSRF**: SameSite cookie policy (None+Secure in production, Lax in development). `X-Requested-With: XMLHttpRequest` header on all API requests forces preflight. OAuth state parameter for all OAuth flows with TTL and single-use consumption.
- **Webhook Security**: LemonSqueezy webhook signature verified with HMAC-SHA256 + `hmac.compare_digest`. Rejects when secret is not configured. Idempotency via Redis. Customer ID cross-check prevents spoofed user_id in webhook payloads.
- **File Upload**: Avatar upload validates content type, magic bytes, and size. Image storage sanitizes filenames (null bytes, path components, unsafe chars). Path traversal check on deletion with `resolve()` + prefix comparison.
- **SSRF**: WordPress URL validates against private/loopback IP ranges. Image download has domain allowlist (`replicate.delivery`, `replicate.com`), content-type check, and size limit.
- **Sensitive Data**: No secrets in code (all from env vars). Logging filter redacts Bearer tokens, API keys, passwords, and secrets. Production startup validator rejects weak/missing secrets. No `.env` files committed (only `.env.example`).
- **Encryption**: WordPress credentials encrypted with Fernet (AES-128-CBC with HMAC). Key derived from SHA-256 of secret_key.
- **Rate Limiting**: All sensitive endpoints have per-endpoint limits. IP extraction validates against private IP spoofing. Redis-backed in production with in-memory fallback warning.
- **Account Deletion**: Hard cascade delete with confirmation phrase. Transaction rollback on partial failure. Token blacklisting on logout.

---

## Dependency Notes

| Package | Version | Status |
|---------|---------|--------|
| python-jose | >=3.3.0 | Unmaintained since 2022 (M-03) |
| next | 14.1.0 | Outdated, security patches available (M-04) |
| fastapi | >=0.109.0 | OK (latest 0.115+) |
| sqlalchemy | >=2.0.25 | OK |
| anthropic | >=0.18.0 | OK |
| dompurify | ^3.3.1 | OK (latest) |
| axios | ^1.6.5 | OK |
