# Audit Section 7 — Social Media
**Date**: 2026-02-27
**Status**: Complete

---

## Scope
- Social account OAuth connection flow (Twitter, LinkedIn, Facebook, Instagram)
- Scheduled post creation, publishing, retry
- Background scheduler service
- Platform adapters (Twitter, LinkedIn, Facebook, Instagram)
- Social calendar, compose, history, analytics pages

---

## Files Audited
- `backend/api/routes/social.py`
- `backend/services/social_scheduler.py`
- `backend/adapters/social/twitter_adapter.py`
- `backend/adapters/social/linkedin_adapter.py`
- `backend/adapters/social/facebook_adapter.py`
- `backend/adapters/social/instagram_adapter.py`
- `frontend/app/[locale]/(dashboard)/social/callback/page.tsx`
- `frontend/app/[locale]/(dashboard)/social/compose/page.tsx`
- `frontend/components/social/schedule-picker.tsx`
- `frontend/components/social/calendar-view.tsx`
- `frontend/components/social/platform-selector.tsx`

---

## Findings

### CRITICAL

#### SM-01 — OAuth state parameter not validated — CSRF account hijacking
- **Severity**: CRITICAL
- **Files**: `backend/api/routes/social.py:102-125, 243-354` + `frontend/app/[locale]/(dashboard)/social/callback/page.tsx:18-46`
- **Description**: The OAuth flow generates a `state` token on initiation and stores it server-side, but the callback endpoint does not cross-check that the returned state belongs to the currently authenticated user. The frontend callback page also does not read or validate the state parameter from the URL at all. An attacker who intercepts another user's OAuth state (e.g., via network sniffing, phishing, or an open redirect) can complete the OAuth flow on behalf of the victim, connecting the attacker's social account to the victim's app account.
- **Attack scenario**: Attacker crafts `/social/callback?code=ATTACKER_CODE&state=VICTIM_STATE&platform=twitter` and tricks victim into loading it — attacker's Twitter is now connected to victim's profile.
- **Fix**: Backend: in `_verify_oauth_state()`, after loading the state entry, assert `entry["user_id"] == current_user.id`. Return `None` if mismatch — do not consume the token. Frontend: store `state` in `sessionStorage` before the OAuth redirect; on callback, read it and compare before calling the backend exchange endpoint.

#### SM-02 — `verify_account()` accesses wrong attribute — verification always fails
- **Severity**: CRITICAL
- **File**: `backend/api/routes/social.py:533`
- **Description**: `verify_account()` checks `bool(account.access_token)` but the model stores `account.access_token_encrypted`. The attribute `access_token` does not exist on the model — this raises `AttributeError` at runtime. The except clause catches it and marks the account as invalid. Every account verification call will fail, permanently marking all accounts as unverifiable even when they have valid tokens.
- **Fix**: Replace `bool(account.access_token)` with `bool(account.access_token_encrypted)`. Also implement the documented TODO: make an actual API call to the platform to verify the token is still valid (the current code is a placeholder).

---

### HIGH

#### SM-03 — Race condition in scheduled post publishing — double-publishing
- **Severity**: HIGH
- **File**: `backend/services/social_scheduler.py:98-102, 130-131`
- **Description**: The scheduler fetches due posts and publishes them. The check `if target.is_published: continue` is read-then-act, not atomic. If two scheduler instances run simultaneously (e.g., a scheduled job plus a manual retry), both read the post as unpublished, both publish it, and both mark it as published. The result is duplicate posts on the social platform with no way to detect or retract them.
- **Fix**: Use a DB-level optimistic lock: `UPDATE scheduled_posts SET status='publishing' WHERE id=? AND status='scheduled'` returning rowcount. Only proceed if rowcount == 1 (only one instance won the lock). Use `SELECT ... FOR UPDATE` if using PostgreSQL advisory locks.

#### SM-04 — Facebook page tokens stored as plaintext in `account_metadata`
- **Severity**: HIGH
- **File**: `backend/services/social_scheduler.py:244-247`
- **Description**: Facebook page tokens (long-lived OAuth credentials that allow posting to a Page) are stored as plaintext JSON in the `SocialAccount.account_metadata` column. The same column is passed to adapters and logged in some error paths. If DB backups, logs, or error tracking are ever accessed by an unauthorized party, Facebook page tokens are exposed — granting the holder the ability to post, delete content, and modify settings on connected Pages.
- **Fix**: Encrypt page tokens using the same `encrypt_credential()` function used for `access_token`. Store as `page_token_encrypted` in account_metadata or a dedicated column. Decrypt at publish time only.

#### SM-05 — LinkedIn and Facebook token refresh raises `SocialAuthError` — posts fail after expiry
- **Severity**: HIGH
- **Files**: `backend/adapters/social/linkedin_adapter.py:229-247`, `backend/adapters/social/facebook_adapter.py:295-314`
- **Description**: Both adapters explicitly raise `SocialAuthError("Token refresh not supported")` in their `refresh_token()` methods. The scheduler calls `adapter.refresh_token()` when it detects an expired token. Since LinkedIn access tokens expire in 60 days and Facebook tokens in ~60-90 days, any user who doesn't manually reconnect their account will have all their scheduled posts fail silently after expiry. The error is caught, the post is marked failed, but the user receives no notification.
- **Fix**: At minimum, when token refresh fails: (1) mark the `SocialAccount.is_active = False`, (2) send an in-app notification or email to the user to reconnect, (3) stop retrying posts for that account. Ideally implement proper token refresh for LinkedIn (via Long-Lived Token API) and Facebook (via token exchange endpoint).

#### SM-06 — `list_connected_accounts` not scoped to current project — IDOR
- **Severity**: HIGH
- **File**: `backend/api/routes/social.py:176, 560`
- **Description**: `list_connected_accounts()` returns accounts for `current_user.id` without filtering by `project_id`. In a multi-project workspace, this means a user who is a member of two projects sees (and can publish to) social accounts connected by any project. A user added as a viewer to Project B can publish to Project A's Twitter account if they know the account ID.
- **Fix**: Add `project_id=current_user.current_project_id` filter to the social accounts query. Add a project membership check when using an account for publishing.

#### SM-07 — No past-date validation in schedule picker — posts silently scheduled in the past
- **Severity**: HIGH
- **File**: `frontend/components/social/schedule-picker.tsx:31-37, 64-71, 177-197`
- **Description**: The date input has a `min` attribute that blocks past dates in the calendar picker UI, but: (1) the "Best Times" preset buttons calculate times that could land in the past if triggered near midnight, (2) drag-and-drop reschedule on the calendar view accepts any date without validation, (3) manual date string input can bypass the UI min constraint. Posts scheduled in the past trigger immediate backend errors or get stuck in a permanently-pending state.
- **Fix**: Add explicit past-date validation in `handleDateTimeChange()`: reject dates earlier than `new Date() + 5 minutes`. Add the same check in the calendar drag-drop `onDrop` handler. Add server-side validation in the POST endpoint.

#### SM-08 — Platform character limits not enforced before form submission
- **Severity**: HIGH
- **File**: `frontend/app/[locale]/(dashboard)/social/compose/page.tsx:281-292`
- **Description**: The compose form displays character counts via `PlatformSelector` but the `handleSubmit()` function does not validate character limits before calling the API. The textarea has no `maxLength` attribute. Users can type and submit content that exceeds Twitter's 280-char limit; the post fails at the platform API level, returning an opaque error rather than a clear frontend validation message.
- **Fix**: In `handleSubmit()`, for each selected account's platform, check `content.length > PLATFORM_LIMITS[platform]` and show a validation error. Use a `const PLATFORM_LIMITS = { twitter: 280, linkedin: 3000, facebook: 63206, instagram: 2200 }` map. Optionally set dynamic `maxLength` on the textarea based on the most restrictive selected platform.

---

### MEDIUM

#### SM-09 — No rate limiting on social account connection or post creation endpoints
- **Severity**: MEDIUM
- **Files**: `backend/api/routes/social.py:187-240` (initiate_connection), `backend/api/routes/social.py:552-670` (create_scheduled_post)
- **Description**: Neither the OAuth initiation endpoint nor the scheduled post creation endpoint has `@limiter.limit()`. An attacker can spam OAuth initiations to exhaust server-side state storage; a user can create thousands of scheduled posts in seconds, bloating the database and task queue.
- **Fix**: Add `@limiter.limit("10/minute")` on OAuth initiation. Add `@limiter.limit("100/day")` on scheduled post creation. Use per-user limits.

#### SM-10 — `media_urls` in scheduled posts not validated — SSRF vector
- **Severity**: MEDIUM
- **File**: `backend/services/social_scheduler.py:253, 287`
- **Description**: When publishing a scheduled post, `post.media_urls` is passed directly to platform adapters without validation. URLs could point to internal network resources (`http://169.254.169.254/` metadata endpoint on cloud), extremely large files (multi-GB downloads causing DoS), or infinite redirect loops. The scheduler fetches/processes these URLs as the backend process, creating a Server-Side Request Forgery opportunity.
- **Fix**: Validate all media URLs before publishing: enforce `https://` scheme, whitelist domains or block internal IP ranges (RFC 1918 + link-local), enforce per-URL content-length limit via HEAD request before download.

#### SM-11 — Update scheduled post allows arbitrary status transitions
- **Severity**: MEDIUM
- **File**: `backend/api/routes/social.py:833-924`
- **Description**: The update endpoint accepts `request.status` and applies it directly without transition validation. A client can set any post to PUBLISHED status without it actually being published, or set a PUBLISHED post back to DRAFT, corrupting analytics and the post history.
- **Fix**: Implement a state machine: only allow `DRAFT → SCHEDULED` and `SCHEDULED → DRAFT` transitions via the update endpoint. Reject any other status change with 422.

#### SM-12 — LinkedIn post ID parsed from wrong response field — always stored as empty string
- **Severity**: MEDIUM
- **File**: `backend/adapters/social/linkedin_adapter.py:336, 451`
- **Description**: After creating a LinkedIn post, the adapter does `result.get("id", "")`. The actual LinkedIn API response nests the post ID as `result["value"]["id"]`. The stored `platform_post_id` is always an empty string, making post tracking, analytics, and deletion via the API impossible.
- **Fix**: Parse the LinkedIn response correctly: `result.get("value", {}).get("id", "")`. Add a log warning if the result is still empty after parsing.

#### SM-13 — Multi-image Facebook post silently falls back to single image
- **Severity**: MEDIUM
- **File**: `backend/adapters/social/facebook_adapter.py:489-493`
- **Description**: When a user creates a post with multiple images for Facebook, the adapter logs a warning and recursively calls itself with only the first image. The user expects a photo carousel and receives a single-image post with no error or notification. This is a silent feature degradation.
- **Fix**: Either implement Facebook carousel/multi-photo API (FB Graph API `/me/photos` multi-upload flow), or reject multi-image posts with a clear error: "Facebook only supports 1 image per post in the current version." Do not silently degrade.

#### SM-14 — Timezone mismatch in schedule picker — posts sent at wrong time
- **Severity**: MEDIUM
- **File**: `frontend/components/social/schedule-picker.tsx:31-37, 64-71`
- **Description**: The schedule picker allows the user to select a timezone, but the underlying `<input type="date">` and `<input type="time">` elements operate in the browser's local timezone. A user in New York who selects "Tokyo (JST)" and enters "09:00" is scheduling a post for 09:00 Eastern, not 09:00 Tokyo. The selected timezone is sent to the backend but not applied to the datetime conversion before submission.
- **Fix**: Use a timezone-aware datetime picker library (e.g., `react-datepicker` with moment-timezone, or `date-fns-tz`). When building the ISO string for the API, apply the selected timezone offset explicitly: `zonedTimeToUtc(localDateTime, selectedTimezone)`.

#### SM-15 — Missing React Error Boundaries on all social media pages
- **Severity**: MEDIUM
- **File**: All `frontend/app/[locale]/(dashboard)/social/**/*.tsx` pages
- **Description**: No Error Boundary wraps social pages. A runtime JavaScript error (e.g., SM-02's AttributeError propagating, or a null crash in a post component) blanks the entire page with no recovery UI.
- **Fix**: Create a `<SocialErrorBoundary>` component and wrap page content. Show a friendly error with a "Reload" button.

#### SM-16 — No pagination on `list_connected_accounts`
- **Severity**: MEDIUM
- **File**: `backend/api/routes/social.py:168-184`
- **Description**: The connected accounts list returns all accounts without pagination. An agency user connected to 50+ social accounts gets an unbounded response. Additionally, there is no eager loading of related data visible in the query, suggesting potential N+1 loading of account metadata.
- **Fix**: Add standard `page`/`page_size` pagination. Add eager loading for account metadata via `selectinload()`.

#### SM-17 — Calendar drag-drop reschedule accepts past dates without validation
- **Severity**: MEDIUM
- **File**: `frontend/components/social/calendar-view.tsx:119-126`
- **Description**: Calendar drag-drop calls `onReschedule(draggedPost, currentDay)` with no check that `currentDay` is in the future. A user can drag a pending post to a past day; the backend rejects the request but the UI may show the post in the wrong position until refresh.
- **Fix**: In the `onDrop` handler, check `if (currentDay < startOfToday()) { toast.error("Cannot schedule posts in the past"); return; }`.

---

### LOW

#### SM-18 — No timeout on scheduled post publishing — scheduler hangs on slow adapter
- **Severity**: LOW
- **File**: `backend/services/social_scheduler.py:253`
- **Description**: The publish call has no `asyncio.wait_for()` timeout. If a platform adapter hangs (e.g., Twitter API unresponsive during a rate limit storm), the scheduler task blocks indefinitely, preventing all subsequent posts from being published.
- **Fix**: Wrap each publish call: `await asyncio.wait_for(publish_to_platform(post, adapter), timeout=300.0)`. On `asyncio.TimeoutError`, mark post as failed with error "Publishing timed out".

#### SM-19 — No file size or MIME type validation on frontend media upload
- **Severity**: LOW
- **File**: `frontend/app/[locale]/(dashboard)/social/compose/page.tsx:325-339`
- **Description**: The file input accepts `image/*,video/*` but the upload handler only checks file count (max 4). No file size limit is enforced — a user could attach 4× 500MB videos. No explicit MIME type check is performed beyond the browser's `accept` attribute (which is trivially bypassed).
- **Fix**: In `handleMediaUpload`, validate each file: `if (file.size > 50 * 1024 * 1024) { setError("File too large (max 50MB)"); return; }`. Check `file.type` against an allowlist of safe MIME types.

#### SM-20 — Best posting time algorithm uses `published_at` instead of `scheduled_at`
- **Severity**: LOW
- **File**: `backend/api/routes/social.py:1330-1380`
- **Description**: The algorithm that recommends best posting times aggregates historical posts by `published_at` (when the scheduler actually ran, which includes queue lag) instead of `scheduled_at` (when the user intended to post). Recommendations are skewed by scheduler processing delays.
- **Fix**: Group and aggregate by `scheduled_at` (the user's intended time) for computing recommendation buckets. Use `published_at` only for performance analysis.

---

## What's Working Well
- OAuth state token uses `secrets.token_urlsafe(32)` (256 bits entropy) — strong token generation
- Access tokens encrypted at rest via `encrypt_credential()` / Fernet
- Per-platform adapter pattern is clean and extensible (Twitter, LinkedIn, Facebook, Instagram)
- Twitter adapter correctly implements token refresh
- Scheduled post publishing has a retry mechanism (max_retries field on ScheduledPost)
- Platform-specific character limit display in `PlatformSelector` component
- Draft auto-save for compose form using localStorage
- Calendar view shows posts by day with color-coded status
- `_verify_oauth_state()` uses atomic Redis `getdel` to prevent state replay
- Post history page correctly paginates

---

## Fix Priority Order
1. SM-01 — OAuth state CSRF validation missing (CRITICAL)
2. SM-02 — verify_account() wrong attribute crash (CRITICAL)
3. SM-03 — Race condition, double-publishing (HIGH)
4. SM-04 — Facebook page tokens plaintext (HIGH)
5. SM-05 — LinkedIn/Facebook token refresh not implemented (HIGH)
6. SM-06 — Connected accounts not scoped to project — IDOR (HIGH)
7. SM-07 — No past-date validation in schedule picker (HIGH)
8. SM-08 — Character limits not enforced on submit (HIGH)
9. SM-09 — No rate limiting on OAuth or post creation (MEDIUM)
10. SM-10 — media_urls not validated — SSRF (MEDIUM)
11. SM-11 — Arbitrary status transitions in update endpoint (MEDIUM)
12. SM-12 — LinkedIn post ID parsed from wrong field (MEDIUM)
13. SM-13 — Multi-image Facebook silently degrades (MEDIUM)
14. SM-14 — Timezone mismatch in schedule picker (MEDIUM)
15. SM-15 — No Error Boundaries on social pages (MEDIUM)
16. SM-16 — No pagination on list_connected_accounts (MEDIUM)
17. SM-17 — Calendar drag-drop no past-date validation (MEDIUM)
18. SM-18 through SM-20 — Low severity items (LOW)
