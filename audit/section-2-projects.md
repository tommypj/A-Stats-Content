# Audit Section 2 — Project & Team Management
**Date**: 2026-02-27
**Status**: Complete

---

## Scope
- Project CRUD, member roles, ownership transfer
- Invitation lifecycle (send, accept, expire, revoke)
- Project-level usage limits and billing
- Brand voice propagation to AI generation
- Database model integrity, indexes, cascade behaviour
- Frontend project UI and access control

---

## Files Audited
- `backend/api/routes/projects.py`
- `backend/api/routes/project_invitations.py`
- `backend/api/routes/project_billing.py`
- `backend/api/deps_project.py`
- `backend/services/project_usage.py`
- `backend/services/generation_tracker.py`
- `backend/services/bulk_generation.py`
- `backend/core/plans.py`
- `backend/infrastructure/database/models/project.py`
- `backend/infrastructure/database/migrations/010, 015, 021, 023`
- `backend/api/routes/articles.py` (improve_article endpoint)
- `frontend/app/[locale]/(dashboard)/projects/`
- `frontend/components/project/`

---

## Findings

### CRITICAL

#### PROJ-01 — improve_article endpoint has no usage limit check
- **Severity**: CRITICAL
- **File**: `backend/api/routes/articles.py:1034-1107`
- **Description**: The `improve_article` endpoint calls `content_ai_service.improve_content()` with no call to `GenerationTracker.check_limit()` before or after. Users can call this endpoint an unlimited number of times with zero usage impact. Additionally there are no calls to `log_start()` or `log_success()`, so improvements are invisible in GenerationLog — no cost attribution, no audit trail, and no billing accuracy.
- **Attack scenario**: User on free plan (10 articles/month) uses their 10 articles, then calls `/articles/{id}/improve` indefinitely to trigger unlimited AI generations.
- **Fix**: Add usage limit check at the top of `improve_article`, and wrap the generation in `tracker.log_start()` / `tracker.log_success()`.

#### PROJ-02 — Bulk generation passes extra params to generate_outline() (runtime failure)
- **Severity**: CRITICAL
- **File**: `backend/services/bulk_generation.py:162-170`
- **Description**: The bulk generation service calls `content_ai_service.generate_outline()` with `title`, `writing_style`, and `custom_instructions` parameters that the method signature does not accept. Every bulk outline generation job will fail with a TypeError at runtime. This is a pre-existing known bug from memory.md.
- **Fix**: Either add these parameters to `generate_outline()`'s signature and handle them in prompt construction, or remove the extra arguments from the call in `bulk_generation.py`.

#### PROJ-03 — ProjectInvitation model missing soft-delete field
- **Severity**: CRITICAL
- **File**: `backend/infrastructure/database/models/project.py`
- **Description**: `Project` (line 102) and `ProjectMember` (line 183) both have `deleted_at` and `is_active` for soft deletes. `ProjectInvitation` has neither. Invitations can only be "revoked" via status field — there is no way to fully archive or purge invitation records. This breaks GDPR deletion flows and makes the model inconsistent with the rest of the domain.
- **Fix**: Add a migration adding `deleted_at: Optional[datetime]` to `project_invitations`. Add `is_active` property. Update all queries to filter `ProjectInvitation.deleted_at.is_(None)`. Change ORM cascade from `"all, delete-orphan"` to `"all"`.

#### PROJ-04 — Member management endpoints not implemented
- **Severity**: CRITICAL
- **File**: `backend/api/routes/projects.py` (missing), `backend/tests/integration/test_project_members.py`
- **Description**: The following endpoints exist in the test suite with "SKIPPED — not yet implemented" comments but have no corresponding route:
  - `GET /projects/{id}/members` — list members
  - `PUT /projects/{id}/members/{member_id}` — update member role
  - `DELETE /projects/{id}/members/{member_id}` — remove member
  - `POST /projects/{id}/leave` — leave project
  - `POST /projects/{id}/transfer-ownership` — transfer ownership
  Members can only be added via invitations. There is no direct way to remove a member, change their role, or leave a project you're a member of (but not owner of).
- **Fix**: Implement all five endpoints with proper RBAC (admin+ to manage others, owner-only for transfer).

#### PROJ-05 — Duplicate require_project_admin() in project_invitations.py
- **Severity**: HIGH
- **File**: `backend/api/routes/project_invitations.py:42-90`
- **Description**: This file defines its own local `require_project_admin()` dependency instead of importing from `backend/api/deps_project.py`. The two implementations have subtle differences — the local one checks `project.owner_id == current_user.id` as a first step, the one in `deps_project.py` uses a different check order. Two implementations of the same function will diverge over time.
- **Fix**: Remove the local definition and import `require_project_admin` from `deps_project.py`.

---

### HIGH

#### PROJ-06 — Two independent usage limit systems with mismatched values
- **Severity**: HIGH
- **Files**: `backend/core/plans.py`, `backend/services/project_usage.py`
- **Description**: User-level limits are defined in `core/plans.py` (PLANS dict). Project-level limits are defined as a separate hardcoded dict `PROJECT_TIER_LIMITS` in `project_usage.py`. The two systems are never synchronized and have different values:
  | Tier | User outlines | Project outlines |
  |------|---|---|
  | free | 10 | 20 |
  | starter | 50 | 100 |
  | professional | 200 | 400 |
  Articles show the same 2x multiplier. If limits are changed in `core/plans.py`, `project_usage.py` is unaffected.
- **Fix**: Consolidate into a single source of truth. Either derive project limits from `core/plans.py` using a multiplier, or define one unified limits structure and import from it in both places.

#### PROJ-07 — Brand voice not loaded in article generation route
- **Severity**: HIGH
- **File**: `backend/api/routes/articles.py:551-553`
- **Description**: The outline generation route explicitly loads `project.brand_voice` and passes it to the AI adapter. The article generation route does not — it uses hardcoded defaults (`writing_style="balanced"`, `voice="second_person"`, `list_usage="balanced"`). Articles generated from outlines that used project brand voice settings will have inconsistent style.
- **Fix**: In the article generation route, load `project.brand_voice` the same way the outline route does, and apply those values as defaults when the request doesn't explicitly specify them. (Pre-existing known bug from memory.md.)

#### PROJ-08 — regenerate_outline does not reload brand_voice
- **Severity**: HIGH
- **File**: `backend/api/routes/outlines.py:532-590`
- **Description**: The `regenerate_outline` endpoint uses the outline's stored `tone` value but does not reload `project.brand_voice` from the database, unlike the original `create_outline` flow. If the project's brand voice was updated after the outline was created, regeneration still uses the old tone.
- **Fix**: Add the same `project.brand_voice` load logic to `regenerate_outline` that exists in `create_outline`. (Pre-existing known bug from memory.md.)

#### PROJ-09 — ProjectInvitation.invited_by uses CASCADE instead of SET NULL
- **Severity**: HIGH
- **File**: `backend/infrastructure/database/models/project.py:234`
- **Description**: `invited_by` FK to `users.id` is configured with `ondelete="CASCADE"`. If the inviting user's account is deleted, all their sent invitations are hard-deleted too. This destroys the audit trail and may confuse recipients who have a pending invitation link. All other user FK columns on this model use `SET NULL` (accepted_by_user_id line 270, revoked_by line 281).
- **Fix**: Change `ondelete="CASCADE"` to `ondelete="SET NULL"` on `invited_by` and add a migration.

#### PROJ-10 — Personal workspace deletion returns 400 instead of 403
- **Severity**: HIGH
- **File**: `backend/api/routes/projects.py:566-570`
- **Description**: Attempting to delete a personal workspace returns `HTTP 400 Bad Request` with a message explaining it can't be deleted. This should be `HTTP 403 Forbidden` — it is an authorization/policy constraint, not a malformed request.
- **Fix**: Change the `HTTPException` status_code from 400 to 403.

#### PROJ-11 — Frontend brand voice page has no role-gating
- **Severity**: HIGH
- **File**: `frontend/app/[locale]/(dashboard)/projects/brand-voice/page.tsx`
- **Description**: The brand voice settings page loads and displays the save button for any authenticated user regardless of their project role. The backend will reject the save for non-admins (once AUTH-06 is fixed), but there is no frontend check to hide the form or show a read-only view for VIEWERs and EDITORs.
- **Fix**: Read `currentProject.my_role` and only show the save button / enable the form if the user is OWNER or ADMIN.

---

### MEDIUM

#### PROJ-12 — TOCTOU race condition on usage limit enforcement
- **Severity**: MEDIUM
- **Files**: `backend/api/routes/articles.py:517-571`, `backend/services/generation_tracker.py`
- **Description**: `check_limit()` is called and returns True (e.g., 9/10 used), then the AI generation runs in a background task. If two concurrent requests both check at 9/10, both get True, both generate, and the counter ends up at 11. The atomic SQL increment prevents counter corruption but doesn't prevent limit overshoot.
- **Fix**: Re-check the limit inside the background task immediately before calling `log_success()`, and abort if already exceeded. Or use a database-level reservation pattern (increment optimistically and rollback if over limit).

#### PROJ-13 — Monthly usage reset uses flush() instead of commit()
- **Severity**: MEDIUM
- **File**: `backend/services/project_usage.py:274-312`
- **Description**: `reset_project_usage_if_needed()` calls `await self.db.flush()` (line 309) instead of `await self.db.commit()`. Flush makes changes visible only within the current session. Concurrent requests from different sessions will both see stale data, both reset counters, and both proceed — effectively resetting twice.
- **Fix**: Change `flush()` to `commit()` in the reset method, or implement the reset as an atomic SQL `UPDATE ... WHERE usage_reset_date <= now()` that only affects rows not yet reset.

#### PROJ-14 — User-level limit check fails OPEN; project-level fails CLOSED
- **Severity**: MEDIUM
- **File**: `backend/services/generation_tracker.py:158-212`
- **Description**: When an exception occurs during the limit check:
  - Projects: return `False` (deny generation — fail closed, line 212)
  - Users: return `True` (allow generation — fail open, line 202)
  On a transient DB error, all users on personal workspaces can bypass their monthly limits. The code comment suggests this is intentional ("personal use is more lenient") but it's an undocumented and risky asymmetry.
- **Fix**: Change user-level failure to also fail closed, or add a comment clearly documenting the intentional policy and review the risk.

#### PROJ-15 — improve_article not tracked in GenerationLog
- **Severity**: MEDIUM
- **File**: `backend/api/routes/articles.py:1034-1107`
- **Description**: Even setting aside the limit bypass (PROJ-01), `improve_article` calls `content_ai_service.improve_content()` with no `log_start()` or `log_success()` calls. Improvement operations are invisible in admin analytics and usage reports. Admin cannot see how many AI calls were made.
- **Fix**: Wrap `improve_article` with `tracker.log_start()` and `tracker.log_success()`. (Overlaps with PROJ-01 fix.)

#### PROJ-16 — Bulk job error_summary field never populated
- **Severity**: MEDIUM
- **File**: `backend/services/bulk_generation.py:236-246`
- **Description**: The job schema includes an `error_summary` field. The bulk generation service finalizes jobs with a status of `completed`, `failed`, or `partially_failed` but never populates `error_summary`. Users see a null/empty field even when items failed.
- **Fix**: After processing all items, aggregate failed item error messages into `job.error_summary`.

#### PROJ-17 — brand_voice JSON column has no validation schema
- **Severity**: MEDIUM
- **File**: `backend/infrastructure/database/models/project.py:99`
- **Description**: `brand_voice` is stored as a raw JSON blob. The fields it contains (tone, writing_style, target_audience, custom_instructions, language) are documented only in a comment. Nothing prevents malformed data from being saved. The article/outline generation routes spread this dict directly into AI prompt parameters.
- **Fix**: Define a `BrandVoiceSchema` Pydantic model and validate the incoming dict against it before saving. Also add a migration to set a sensible default `{}` for projects where `brand_voice` is currently NULL.

#### PROJ-18 — current_project_id auto-set on invitation accept
- **Severity**: MEDIUM
- **File**: `backend/api/routes/project_invitations.py:556-557`
- **Description**: When a user accepts an invitation, the server silently sets `user.current_project_id` to the newly joined project if the user had no active project. The user is not informed of this switch. If they were working in a personal workspace, they may not realize their context has changed.
- **Fix**: Only set `current_project_id` if the user has never had a project set (i.e., it is `None`). Display a notification to the user that they have been switched to the new project context.

#### PROJ-19 — N+1 queries in project settings page handlers
- **Severity**: MEDIUM
- **File**: `frontend/app/[locale]/(dashboard)/projects/[projectId]/settings/page.tsx:169-210`
- **Description**: Every member operation (role update, remove member, invite, revoke invitation, resend invitation) calls `loadProjectData()` which reloads the full project, all members, all invitations, and subscription data in one round-trip. For a project with many members this is wasteful. Each individual operation should only update the affected item in local state.
- **Fix**: After each operation, update only the affected slice of state (e.g., replace the modified member in the array) instead of reloading everything.

---

### LOW

#### PROJ-20 — Missing composite index on ProjectInvitation(project_id, email, status)
- **Severity**: LOW
- **File**: `backend/infrastructure/database/models/project.py`
- **Description**: The most common query on invitations — "is there a pending invite for this email in this project?" — filters on `(project_id, email, status)`. Currently only individual column indexes exist. A composite index would significantly improve performance on projects with many invitations.
- **Fix**: Add a migration adding `Index("ix_project_invitations_project_email_status", "project_id", "email", "status")`.

#### PROJ-21 — Inconsistent naming: logo_url vs avatar_url
- **Severity**: LOW
- **File**: `backend/api/routes/projects.py:522-523`
- **Description**: The update endpoint references `data.logo_url` but the DB column is `avatar_url`. It works because the schema maps it, but the inconsistency makes the code confusing.
- **Fix**: Standardize to `avatar_url` in both the schema and the route.

#### PROJ-22 — Viewers can see all member email addresses
- **Severity**: LOW
- **File**: `frontend/components/project/project-members-list.tsx:114-117`
- **Description**: The member list component renders email addresses for all members regardless of the viewer's role. Depending on the app's privacy model, VIEWERs may not need to see the email addresses of other members.
- **Fix**: Verify the intended design. If emails should be private, either filter them from the backend response for non-admin roles, or only display them in the UI for ADMIN+ users.

#### PROJ-23 — No pagination on project member list
- **Severity**: LOW
- **File**: `frontend/components/project/project-members-list.tsx`
- **Description**: Member list renders all members in one go. For enterprise projects with many members this will degrade UI performance.
- **Fix**: Add server-side pagination or virtual scrolling for the member list.

#### PROJ-24 — lemonsqueezy_customer_id nullable unique constraint
- **Severity**: LOW
- **File**: `backend/infrastructure/database/models/project.py:75-76`
- **Description**: `lemonsqueezy_customer_id` is both `unique=True` and `nullable=True`. PostgreSQL treats multiple NULLs as distinct (so multiple NULL rows are allowed), but this is not guaranteed across all DB engines. Should be explicitly tested.
- **Fix**: Verify behaviour is correct in PostgreSQL. Add a comment documenting the intentional NULL handling.

---

## What's Working Well
- Project creation: correct ownership assignment, member creation, slug generation
- Project deletion: type-to-confirm UI, soft delete, cascade to members
- Ownership transfer UI: strong two-step confirmation
- Invitation tokens: cryptographically secure (`secrets.token_urlsafe(32)`)
- RBAC on invitation endpoints: all require ADMIN+
- Soft-delete on Project and ProjectMember: consistent and correct
- Cascade FK on ProjectMember(project_id): hard-delete on project cascades correctly
- Usage counter increments: atomic SQL-level updates prevent counter corruption
- Plan limits: unlimited tiers correctly use `-1` sentinel value

---

## Fix Priority Order
1. PROJ-01 — improve_article has no usage limit check *(CRITICAL)*
2. PROJ-02 — Bulk generation extra params crash *(CRITICAL — pre-existing known bug)*
3. PROJ-04 — Member management endpoints not implemented *(CRITICAL)*
4. PROJ-03 — ProjectInvitation missing soft-delete *(CRITICAL)*
5. PROJ-05 — Duplicate require_project_admin *(HIGH)*
6. PROJ-06 — Two independent limit systems mismatched *(HIGH)*
7. PROJ-07 — Brand voice not loaded in article generation *(HIGH — pre-existing known bug)*
8. PROJ-08 — regenerate_outline doesn't reload brand_voice *(HIGH — pre-existing known bug)*
9. PROJ-09 — ProjectInvitation.invited_by CASCADE → SET NULL *(HIGH)*
10. PROJ-10 — Personal workspace delete returns 400 not 403 *(HIGH)*
11. PROJ-11 — Brand voice page no role-gating in frontend *(HIGH)*
12. PROJ-12 — TOCTOU race on usage limit *(MEDIUM)*
13. PROJ-13 — Monthly reset flush() vs commit() *(MEDIUM)*
14. PROJ-14 — Asymmetric fail-open/fail-closed *(MEDIUM)*
15. PROJ-15 — improve_article not tracked in GenerationLog *(MEDIUM)*
16. PROJ-16 — Bulk job error_summary never populated *(MEDIUM)*
17. PROJ-17 — brand_voice JSON no validation schema *(MEDIUM)*
18. PROJ-18 — current_project_id auto-set on invite accept *(MEDIUM)*
19. PROJ-19 — N+1 queries in settings page *(MEDIUM)*
20. PROJ-20 through PROJ-24 — Low severity items *(LOW)*
