# Audit Section 1 — Authentication & Authorization
**Date**: 2026-02-27
**Status**: Complete

---

## Scope
- Auth flows: login, register, forgot/reset password, email verification
- JWT handling, session management, token expiry
- Role-based access control (admin, project owner, member)
- Route protection (frontend middleware + backend deps)
- Invite flow security

---

## Files Audited
- `backend/api/routes/auth.py`
- `backend/api/dependencies.py`
- `backend/api/deps_admin.py`
- `backend/api/deps_project.py`
- `backend/core/security/tokens.py`
- `backend/infrastructure/database/models/user.py`
- `backend/infrastructure/database/models/project.py`
- `backend/api/routes/project_invitations.py`
- `backend/services/project_invitations.py`
- `backend/api/routes/projects.py` (brand voice endpoint)
- `frontend/middleware.ts`
- `frontend/lib/api.ts`
- `frontend/lib/auth.ts`
- `frontend/stores/auth.ts`
- `frontend/app/[locale]/(auth)/login/page.tsx`
- `frontend/app/[locale]/(auth)/register/page.tsx`
- `frontend/app/[locale]/(auth)/forgot-password/page.tsx`
- `frontend/app/[locale]/(auth)/reset-password/page.tsx`
- `frontend/app/[locale]/(auth)/verify-email/page.tsx`
- `frontend/app/invite/[token]/page.tsx`

---

## Findings

### CRITICAL

#### AUTH-01 — Refresh token not invalidated after password change
- **Severity**: CRITICAL
- **File**: `backend/api/routes/auth.py:290-330`
- **Description**: The `/refresh` endpoint verifies the refresh token's signature and expiry but does NOT check `user.password_changed_at`. The `/me` endpoint and `get_current_user` dependency both check this field and reject tokens issued before the last password change. The inconsistency means an attacker who has stolen a refresh token can keep generating new access tokens indefinitely, even after the legitimate user performs a password reset.
- **Attack scenario**: Account compromised → user resets password → attacker still holds refresh token → attacker calls `/refresh` → gets valid access token → full account access maintained
- **Fix**: In the `/refresh` endpoint (around line 312), after loading the user from DB, add the same `password_changed_at` check that exists in `get_current_user`:
  ```python
  if user.password_changed_at:
      iat = datetime.fromtimestamp(payload.iat, tz=timezone.utc)
      if iat < user.password_changed_at:
          raise HTTPException(status_code=401, detail="Token invalidated due to security event")
  ```

---

### HIGH

#### AUTH-02 — Access and refresh tokens stored in localStorage (XSS risk)
- **Severity**: HIGH
- **Files**: `frontend/lib/api.ts`, `frontend/lib/auth.ts`, `frontend/stores/auth.ts`
- **Description**: Both the access token and refresh token are stored in `localStorage` under the keys `auth_token` and `refresh_token`. Any XSS vulnerability (injected third-party script, dependency chain attack, etc.) can read these tokens with a simple `localStorage.getItem()` call and exfiltrate them. The Zustand auth store also exposes tokens via `useAuthStore().token`.
- **Fix**: Migrate to `HttpOnly` cookies set by the backend on login/refresh. The frontend never needs to read the token directly — the browser sends it automatically. This requires backend changes to `Set-Cookie` on `/login` and `/refresh`, and frontend changes to remove all `localStorage` token reads/writes.
- **Note**: This is a significant architectural change. As an intermediate mitigation, ensure Content Security Policy (CSP) headers are set to restrict script injection.

#### AUTH-03 — Timing attack on login endpoint (user enumeration)
- **Severity**: HIGH
- **File**: `backend/api/routes/auth.py:252`
- **Description**: The login condition is `if not user or not password_hasher.verify(login_data.password, user.password_hash)`. When a user does not exist, the first clause short-circuits immediately (fast path, ~1ms). When a user exists but the password is wrong, bcrypt verify runs (~100-300ms). An attacker can measure response times to determine whether a given email address has a registered account.
- **Fix**: Always run bcrypt verify regardless of whether the user was found:
  ```python
  DUMMY_HASH = "$2b$12$invalidhashfortimingnorealuser..."
  hash_to_check = user.password_hash if user else DUMMY_HASH
  password_ok = password_hasher.verify(login_data.password, hash_to_check)
  if not user or not password_ok:
      raise HTTPException(status_code=401, detail="Invalid credentials")
  ```

#### AUTH-04 — `is_active` check missing from login
- **Severity**: HIGH
- **File**: `backend/api/routes/auth.py:252-268`
- **Description**: The login endpoint checks for SUSPENDED and DELETED user statuses but does not check `user.is_active`. A user with `is_active=False` (status=PENDING, email not yet verified) can successfully log in and receive tokens. The `/me` endpoint blocks such users with a 403, but they hold valid tokens. This is an inconsistent access control state.
- **Fix**: Add an explicit `is_active` check immediately after credential validation:
  ```python
  if not user.is_active:
      raise HTTPException(status_code=403, detail="Account is not active. Please verify your email.")
  ```

#### AUTH-05 — Duplicate `get_current_admin_user()` function definitions
- **Severity**: HIGH
- **Files**: `backend/api/dependencies.py:13-26`, `backend/api/deps_admin.py:13-36`
- **Description**: Both files define a function named `get_current_admin_user`. Depending on which file is imported in a route, a different version runs. If a route accidentally imports from `dependencies.py` instead of `deps_admin.py`, the check may differ subtly. This is a maintainability hazard and a potential admin bypass if the implementations ever diverge.
- **Fix**: Remove `get_current_admin_user` from `dependencies.py` entirely. All admin routes should import exclusively from `deps_admin.py`. Audit all `from api.dependencies import get_current_admin_user` usages and update them.

#### AUTH-06 — Brand voice update missing authorization check
- **Severity**: HIGH
- **File**: `backend/api/routes/projects.py:341-379`
- **Description**: `PUT /projects/current/brand-voice` authenticates the user but performs no role check. Any project member — including VIEWERs and EDITORs — can modify the project's brand voice settings (tone, writing style, target audience, custom instructions). These settings are used directly in AI prompt construction and affect all content generation for the entire project.
- **Fix**: Add a project admin/owner role check before the update:
  ```python
  await require_project_admin(current_user.current_project_id, current_user, db)
  ```

#### AUTH-07 — `validate_project_content_creation()` is a no-op
- **Severity**: HIGH
- **File**: `backend/api/deps_project.py:248-296`
- **Description**: This function exists, has a docstring describing validation behaviour, and is called by routes to validate that a user can create content in a project. However, the implementation returns without performing any checks. Routes relying on this function have a false sense of security — it does not verify project membership before content creation.
- **Fix**: Either implement the validation (check project membership and role) or delete the function and audit all call sites to add explicit membership checks inline.

---

### MEDIUM

#### AUTH-08 — Email service errors not caught during registration and password reset
- **Severity**: MEDIUM
- **File**: `backend/api/routes/auth.py:227-231, 388-392`
- **Description**: After creating a user (registration) or generating a reset token, the code calls the email service without wrapping it in try/except. If the Resend API call fails (network error, quota exceeded, etc.), the user is left in a broken state: registered but unable to verify (status=PENDING), or has a reset token stored but never received the email. The registration endpoint doesn't roll back the user record on email failure.
- **Fix**: Wrap email calls in try/except. On failure, either roll back the transaction (registration) or return a user-friendly error (password reset). Log the exception for monitoring.

#### AUTH-09 — Login form allows password with 1 character (inconsistent with register)
- **Severity**: MEDIUM
- **File**: `frontend/app/[locale]/(auth)/login/page.tsx:20-22`
- **Description**: The login Zod schema validates `password: z.string().min(1)`. The register and reset-password schemas require 8+ characters with uppercase, lowercase, and digit. This inconsistency doesn't directly create a security hole (the backend enforces requirements at registration), but it means users who somehow have weak passwords can log in without any frontend warning.
- **Fix**: Change login schema to `z.string().min(8)` to match. This doesn't need the full complexity check since we're not creating a password here.

#### AUTH-10 — No CSRF protection
- **Severity**: MEDIUM
- **File**: `frontend/lib/api.ts`
- **Description**: The API client sends no CSRF token. Because tokens are currently in localStorage (not cookies), CSRF is low risk — cross-site requests can't automatically include the auth header. However, if tokens are ever migrated to `HttpOnly` cookies (the correct fix for AUTH-02), CSRF becomes a critical issue. Should be implemented proactively.
- **Fix**: Implement CSRF tokens: backend generates a CSRF token on login and returns it in the response (not in HttpOnly cookie, in readable cookie or response body). Frontend sends it as `X-CSRF-Token` header on state-mutating requests. Backend validates it.

#### AUTH-11 — Database commit as side effect inside `get_current_user` dependency
- **Severity**: MEDIUM
- **File**: `backend/api/routes/auth.py:125-148`
- **Description**: `get_current_user` is a read-path dependency injected into almost every endpoint. When it detects that a user's `current_project_id` points to a project they're no longer a member of, it silently resets it to their personal project and commits to the database. Side-effecting DB writes inside a dependency function are unexpected and can cause subtle bugs — e.g., the commit may flush other uncommitted state from the same session.
- **Fix**: Log the stale project membership issue and reset the in-memory user object, but do not commit inside the dependency. Let the endpoint's normal commit cycle handle persistence, or add a separate lightweight endpoint for the user to explicitly switch projects.

#### AUTH-12 — Public invitation token endpoint has no rate limiting
- **Severity**: MEDIUM
- **File**: `backend/api/routes/project_invitations.py:409-436`
- **Description**: `GET /invitations/{token}` is publicly accessible with no authentication and no rate limiting. The response includes project name, project slug, inviter name, role assignment, and expiry. While tokens are cryptographically strong (256 bits of entropy), the absence of rate limiting means an attacker can make unlimited requests to probe tokens or map relationships between projects and emails.
- **Fix**: Add a rate limit decorator (e.g., `@limiter.limit("20/minute")`) to this endpoint. Also consider logging token lookup attempts for anomaly detection.

---

### LOW

#### AUTH-13 — No token blacklist on logout/account deletion
- **Severity**: LOW
- **File**: `backend/api/routes/auth.py:550-563, 566-667`
- **Description**: Logout is stateless (documented in code). After logout or account deletion, access tokens remain valid until their 60-minute expiry. Acknowledged as a known trade-off in the codebase.
- **Fix**: Implement a Redis-backed token blacklist. On logout/deletion, add the token's `jti` (or user_id + iat) to a Redis set with TTL matching the token expiry.

#### AUTH-14 — No rate limiting on token refresh
- **Severity**: LOW
- **File**: `backend/api/routes/auth.py:290`
- **Description**: The `/refresh` endpoint is rate-limited at 10/minute, higher than login (5/minute). An attacker with a compromised refresh token could more aggressively maintain access.
- **Fix**: Reduce to 5/minute, same as login.

#### AUTH-15 — Authorization header parsing fragile
- **Severity**: LOW
- **File**: `backend/api/routes/auth.py:74-81`
- **Description**: If the header is `"Bearer"` with no space, `split(" ", 1)[1]` is not called due to the ternary, resulting in an empty string being passed to `verify_access_token`. It works (JWT decode fails on empty string → 401), but the code path is unclear.
- **Fix**: Use explicit split with length check:
  ```python
  parts = authorization.split(" ", 1)
  if len(parts) != 2 or parts[0].lower() != "bearer":
      raise HTTPException(...)
  token = parts[1]
  ```

#### AUTH-16 — Invitation expiry background job not scheduled
- **Severity**: LOW
- **File**: `backend/services/project_invitations.py:16-48`
- **Description**: `expire_old_invitations()` is defined but no evidence it's registered with any scheduler or background task runner. Runtime checks (`is_expired` property) still work correctly so no security issue, but the DB `status` column stays stale showing PENDING for expired invites.
- **Fix**: Register as a daily background task with the app's task queue/scheduler.

#### AUTH-17 — No idle session timeout on frontend
- **Severity**: LOW
- **Files**: `frontend/app/(dashboard)/layout.tsx`
- **Description**: No client-side idle detection or auto-logout. A user who leaves a browser tab open indefinitely maintains their session until the refresh token expires (7 days).
- **Fix**: Implement an idle timer (e.g., 30-60 minutes) using a `mousemove`/`keydown` event listener that resets a timeout. On timeout, call `forceLogout()`.

#### AUTH-18 — bcrypt rehash on login not implemented
- **Severity**: LOW
- **File**: `backend/api/routes/auth.py` (login flow)
- **Description**: The `password_hasher` has a `needs_rehash()` method available (password.py:43) but it's never called. If bcrypt rounds are ever increased, existing passwords won't be upgraded on login.
- **Fix**: After successful password verification in login, call `needs_rehash()` and if true, re-hash and update `user.password_hash`.

---

## What's Working Well
- bcrypt-12 password hashing (appropriate cost factor)
- JWT `type` field prevents access/refresh token confusion
- `password_changed_at` check correctly invalidates access tokens (just missing from refresh)
- Generic error messages on password reset / email resend (no user enumeration)
- No open redirects in any auth flow
- Invitation tokens use `secrets.token_urlsafe(32)` (256 bits entropy)
- Email match enforcement on invitation acceptance (prevents email-swap attacks)
- Role whitelist validation on invitation creation (`owner/admin/member/viewer`)
- Soft-delete aware membership queries throughout
- Token type separation (access vs refresh vs email_verification vs password_reset)
- Rate limiting on all sensitive endpoints (login, register, reset, verify)
- `WWW-Authenticate: Bearer` header returned on 401 responses (OAuth standard)

---

## Fix Priority Order
1. AUTH-01 — Refresh token not invalidated after password change *(CRITICAL)*
2. AUTH-03 — Timing attack on login *(HIGH)*
3. AUTH-04 — `is_active` check missing from login *(HIGH)*
4. AUTH-05 — Duplicate admin dependency function *(HIGH)*
5. AUTH-06 — Brand voice endpoint missing role check *(HIGH)*
6. AUTH-07 — `validate_project_content_creation` no-op *(HIGH)*
7. AUTH-02 — Tokens in localStorage *(HIGH — larger change, plan separately)*
8. AUTH-08 — Email service errors not caught *(MEDIUM)*
9. AUTH-09 — Weak login password validation *(MEDIUM)*
10. AUTH-11 — DB commit side effect in dependency *(MEDIUM)*
11. AUTH-12 — Rate limit on public invite token endpoint *(MEDIUM)*
12. AUTH-10 — CSRF protection *(MEDIUM — coordinate with AUTH-02 migration)*
13. AUTH-13 through AUTH-18 — Low severity, address when time permits
