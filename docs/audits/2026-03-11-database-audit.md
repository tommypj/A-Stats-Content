# Database Model & Migration Audit

**Date:** 2026-03-11
**Scope:** SQLAlchemy models (`backend/infrastructure/database/models/`) vs Alembic migrations (001-060)
**Database:** PostgreSQL via SQLAlchemy async + asyncpg
**Models cataloged:** 35 SQLAlchemy models across 24 files
**Migration chain:** 001 -> 060 (verified unbroken)

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 2     |
| Warning  | 17    |
| Info     | 10    |
| **Total** | **29** |

---

## 1. Model-Migration Consistency

### DB-A01 [Critical] EmailJourneyEvent.user_id missing ForeignKey in model
- **File:** `backend/infrastructure/database/models/email_journey_event.py` line 27
- **Migration:** `backend/infrastructure/database/migrations/versions/060_email_journey.py` line 25
- The model defines `user_id` as a plain `UUID` column with no `ForeignKey("users.id")`. Migration 060 creates it with `REFERENCES users(id) ON DELETE CASCADE`. The ORM cannot enforce the FK, build relationships, or use it for joins. `create_all()` in tests will create the table without the FK.
- **Fix:** Add `ForeignKey("users.id", ondelete="CASCADE")` to the `user_id` mapped_column.

### DB-A02 [Critical] EmailJourneyEvent index names differ between model and migration
- **File:** `backend/infrastructure/database/models/email_journey_event.py` lines 49-57
- **Migration:** `backend/infrastructure/database/migrations/versions/060_email_journey.py` lines 35-39
- Model declares `ix_ueje_user_email_active` and `ix_ueje_status_scheduled`. Migration creates `uix_journey_user_email_key` and `ix_journey_status_scheduled`. Alembic autogenerate will try to drop the migration indexes and create the model ones, causing downtime or errors.
- **Fix:** Align model index names with migration names (migration is authoritative).

### DB-A03 [Warning] RefundBlockedEmail.blocked_by missing ondelete rule
- **File:** `backend/infrastructure/database/models/refund_blocked_email.py` line 26
- **Migration:** `backend/infrastructure/database/migrations/versions/056_add_refund_tracking.py` line 41
- `ForeignKey("users.id")` has no `ondelete` clause (defaults to RESTRICT). If the admin who blocked an email is hard-deleted, the FK will prevent deletion with an integrity error. Inconsistent with the rest of the codebase (admin FKs use `ondelete="SET NULL"`).
- **Fix:** Add `ondelete="SET NULL"` and create a migration to alter the FK constraint.

### DB-A04 [Warning] Migration 059 is not idempotent
- **File:** `backend/infrastructure/database/migrations/versions/059_article_image_prompts_json.py`
- Uses bare `op.add_column` / `op.drop_column` without `IF NOT EXISTS` guards. If interrupted and re-run, it will fail. This is the most recent non-idempotent migration and violates the project convention ("Alembic migrations must be idempotent" per Railway deploy pitfalls).
- **Fix:** Wrap in `DO $$ BEGIN IF NOT EXISTS ... END $$` guards.

### DB-A05 [Warning] Article.schemas and run_metadata use JSON in model, JSONB in migration
- **File:** `backend/infrastructure/database/models/content.py` lines 224-225
- **Migration:** `backend/infrastructure/database/migrations/versions/044_add_pipeline_metadata_columns.py` lines 32, 39
- Model imports `JSON` from `sqlalchemy` but migration 044 creates these columns as `JSONB`. The DB has JSONB (correct), but SQLAlchemy autogenerate will report a type mismatch.
- **Fix:** Change model to use `JSONB` from `sqlalchemy.dialects.postgresql`.

### DB-A06 [Warning] SystemErrorLog.context uses JSON import from postgresql dialect but it resolves to plain JSON
- **File:** `backend/infrastructure/database/models/error_log.py` line 10, 77
- `from sqlalchemy.dialects.postgresql import JSON` -- this actually imports the standard JSON type, not JSONB. If the migration created the column as JSONB, there is a type mismatch.
- **Fix:** Use `JSONB` explicitly if JSONB semantics are desired.

### DB-A07 [Warning] users.current_project_id index name mismatch
- **File:** `backend/infrastructure/database/models/user.py` line 159
- **Migration:** `backend/infrastructure/database/migrations/versions/015_rename_teams_to_projects.py` line 65
- Model defines `Index("ix_users_current_project", "current_project_id")` but migration creates `ix_users_current_project_id`. Autogenerate will flag a spurious diff.
- **Fix:** Rename model index to `ix_users_current_project_id`.

### DB-A08 [Warning] Tag UniqueConstraint in model mismatches partial unique index in DB
- **File:** `backend/infrastructure/database/models/tag.py` lines 41-43
- **Migration:** `backend/infrastructure/database/migrations/versions/053_fix_column_types_and_indexes.py` lines 40-53
- Model declares `UniqueConstraint("user_id", "name")` (non-partial). Migration 053 replaces this with a partial unique index `WHERE deleted_at IS NULL`. In tests using `create_all()`, the constraint will differ from production.
- **Fix:** Replace `UniqueConstraint` with `Index("uq_tags_user_name", "user_id", "name", unique=True, postgresql_where=text("deleted_at IS NULL"))`.

### DB-A09 [Info] 28 non-idempotent early migrations (001-029 and 059)
- Migrations 001-029 (except 022, 009) use bare `op.add_column` / `op.create_table`. All migrations from 033 onward use idempotent patterns. Since early migrations are already applied in production, this is low risk.

### DB-A10 [Info] Migration 042 downgrade is irreversible
- **File:** `backend/infrastructure/database/migrations/versions/042_remove_project_billing.py` line 41
- `downgrade()` is `pass`. Documented as intentional. Migration chain is not fully reversible past this point.

---

## 2. Missing Indexes

### DB-A11 [Warning] AuditIssue.page_id missing index
- **File:** `backend/infrastructure/database/models/site_audit.py` line 191
- `page_id` is a FK to `audit_pages.id` but has no `index=True`. This table can grow large (many issues per audit). Queries filtering issues by page will do sequential scans.

### DB-A12 [Warning] BulkJob.template_id missing index
- **File:** `backend/infrastructure/database/models/bulk.py` line 93
- FK to `content_templates.id` with no `index=True`. Joins or filters on template will scan the table.

### DB-A13 [Warning] AdminAlert.user_id and project_id missing indexes
- **File:** `backend/infrastructure/database/models/generation.py` lines 157, 164
- Both FK columns lack `index=True`.

### DB-A14 [Warning] SystemErrorLog.project_id missing index
- **File:** `backend/infrastructure/database/models/error_log.py` line 69
- FK to `projects.id` with no index. Filtering error logs by project will be unindexed.

### DB-A15 [Warning] SystemErrorLog.error_fingerprint missing index
- **File:** `backend/infrastructure/database/models/error_log.py` line 107
- Used in WHERE clause for deduplication in `backend/services/error_logger.py` line 69 (`SystemErrorLog.error_fingerprint == fingerprint`). Every error insertion does a lookup on this column without an index.

### DB-A16 [Warning] SystemErrorLog.resolved_by missing index
- **File:** `backend/infrastructure/database/models/error_log.py` line 100
- FK to `users.id` with no index.

### DB-A17 [Info] ProjectMember.invited_by missing index
- **File:** `backend/infrastructure/database/models/project.py` line 148
- FK to `users.id` without `index=True`. Low query volume on this column.

### DB-A18 [Info] ProjectInvitation.accepted_by_user_id and revoked_by missing indexes
- **File:** `backend/infrastructure/database/models/project.py` lines 244, 252
- Both FK columns lack indexes. Low query volume expected.

### DB-A19 [Info] BlogPostTag, ArticleTag, OutlineTag tag_id lookups unindexed
- **Files:** `blog.py` lines 88-97, `tag.py` lines 57-82
- Composite PKs `(post_id, tag_id)` / `(article_id, tag_id)` support lookups by the first column. "Find all posts/articles with tag X" requires scanning without a separate `tag_id` index.

---

## 3. Data Integrity Issues

### DB-A20 [Warning] RefundBlockedEmail.blocked_by FK defaults to RESTRICT
- **File:** `backend/infrastructure/database/models/refund_blocked_email.py` line 26
- See DB-A03. Both model and migration omit `ondelete`. Hard-deleting an admin will fail with FK violation.

### DB-A21 [Warning] BlogPost.deleted_at has duplicate indexes
- **File:** `backend/infrastructure/database/models/blog.py` lines 171, 198
- `deleted_at` has `index=True` on the column definition AND is included in `Index("ix_blog_posts_deleted_at", "deleted_at")` in `__table_args__`. This creates two indexes on the same column, wasting disk space and write performance.
- **Fix:** Remove either the column-level `index=True` or the table-level index.

### DB-A22 [Info] No unique constraint on KeywordResearchCache (user_id, seed_keyword_normalized)
- **File:** `backend/infrastructure/database/models/keyword_cache.py`
- Composite index exists but is not unique. Race conditions during cache population could create duplicates.

### DB-A23 [Info] ContentDecayAlert.article_id uses SET NULL on article delete
- **File:** `backend/infrastructure/database/models/analytics.py` line 261
- Orphan alerts remain queryable but without article context. Intentional design.

---

## 4. Migration Quality

### DB-A24 [Warning] Migration 059 data migration risk
- **File:** `backend/infrastructure/database/migrations/versions/059_article_image_prompts_json.py`
- Adds `image_prompts` column, migrates data from `image_prompt`, then drops `image_prompt`. No `IF NOT EXISTS` guards. If interrupted between add and drop, re-running will fail. The data migration SQL (`UPDATE ... SET image_prompts = json_build_array(image_prompt)`) is not wrapped in guards either.

### DB-A25 [Warning] Migration 042 irreversible downgrade
- **File:** `backend/infrastructure/database/migrations/versions/042_remove_project_billing.py`
- Drops 11 columns from `projects` with `pass` downgrade. Any rollback past this point loses billing data permanently. Documented but limits recovery options.

### DB-A26 [Info] Migration chain is intact
- All 61 migrations form a valid linear chain. Every `down_revision` correctly points to its predecessor. Migration 010 uses non-standard ID `010_create_team_tables` but 011 references it correctly.

### DB-A27 [Info] Migration 009 is a no-op placeholder
- **File:** `backend/infrastructure/database/migrations/versions/009_placeholder.py`
- Exists solely to fill a gap in the revision chain. Documented and harmless.

---

## 5. Model __init__.py Exports

### DB-A28 [Info] All models properly exported
- Every model class is imported in `__init__.py` and listed in `__all__`. No missing exports.

### DB-A29 [Info] PostTargetStatus enum and UUIDMixin not exported
- `PostTargetStatus` (`social.py` line 46) is defined but not in `__init__.py` imports or `__all__`. May be needed by API schemas.
- `UUIDMixin` (`base.py` line 36) is defined but unused by any model and not exported. Dead code.

---

## 6. Additional Findings

### DB-A30 [Warning] EmailJourneyEvent.metadata uses legacy Column() syntax
- **File:** `backend/infrastructure/database/models/email_journey_event.py` line 43
- Uses `Column("metadata", JSONB, nullable=True)` (SQLAlchemy 1.x style) instead of `mapped_column`. Inconsistent with every other model. The `metadata_` Python name vs `metadata` DB column mapping may cause confusion.

### DB-A31 [Warning] Potential N+1 via lazy="select" relationships in async context
- **File:** `backend/infrastructure/database/models/project.py` line 85 (Project.owner), lines 165-166 (ProjectMember.user, .inviter)
- In async SQLAlchemy, accessing `lazy="select"` relationships triggers implicit IO. If accessed in a loop, this causes N+1 queries.
- **Fix:** Change to `lazy="raise"` and use explicit `selectinload()` / `joinedload()` in routes.

---

## Migration Chain Verification

```
001 -> 002 -> 003 -> 004 -> 005 -> 006 -> 007 -> 008 -> 009 ->
010_create_team_tables -> 011 -> 012 -> 013 -> 014 -> 015 -> 016 -> 017 ->
018 -> 019 -> 020 -> 021 -> 022 -> 023 -> 024 -> 025 -> 026 -> 027 ->
028 -> 029 -> 030 -> 031 -> 032 -> 033 -> 034 -> 035 -> 036 -> 037 ->
038 -> 039 -> 040 -> 041 -> 042 -> 043 -> 044 -> 045 -> 046 -> 047 ->
048 -> 049 -> 050 -> 051 -> 052 -> 053 -> 054 -> 055 -> 056 -> 057 ->
058 -> 059 -> 060
```

No breaks, forks, or gaps detected.

---

## Priority Action Items

1. **[Critical]** Add `ForeignKey("users.id", ondelete="CASCADE")` to `EmailJourneyEvent.user_id` (DB-A01)
2. **[Critical]** Align `EmailJourneyEvent` index names between model and migration 060 (DB-A02)
3. **[Warning]** Add `ondelete="SET NULL"` to `RefundBlockedEmail.blocked_by` + migration (DB-A03)
4. **[Warning]** Make migration 059 idempotent with `IF NOT EXISTS` guards (DB-A04)
5. **[Warning]** Add index on `SystemErrorLog.error_fingerprint` -- queried on every error insertion (DB-A15)
6. **[Warning]** Add index on `AuditIssue.page_id` -- FK without index, high-cardinality table (DB-A11)
7. **[Warning]** Fix Tag `UniqueConstraint` to partial unique index in model (DB-A08)
8. **[Warning]** Change `JSON` to `JSONB` for `Article.schemas` and `Article.run_metadata` in model (DB-A05)
9. **[Warning]** Remove duplicate `deleted_at` index on `BlogPost` (DB-A21)
10. **[Warning]** Add missing indexes on `AdminAlert.user_id/project_id`, `SystemErrorLog.project_id/resolved_by`, `BulkJob.template_id` (DB-A12-A16)
