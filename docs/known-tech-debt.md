# Known Technical Debt

## Non-Idempotent Migrations (001-029)

Migrations 001 through 029 use raw `op.create_table()`, `op.add_column()` without
`DO $$ BEGIN IF NOT EXISTS ... END $$` guards. This is acceptable for deployed databases
since Alembic tracks migration state, but could cause issues if:
- A migration partially fails and needs manual re-run
- The `alembic_version` table gets corrupted

All migrations from 030 onward follow the idempotent pattern.

## TimestampMixin `updated_at` is ORM-only

The `TimestampMixin.updated_at` field uses SQLAlchemy's `onupdate=func.now()`, which
only fires during ORM `session.commit()` calls. Raw SQL UPDATE statements will not
update this field. If accuracy matters for background scripts using raw SQL, add a
PostgreSQL trigger.

## `get_db()` Does Not Auto-Commit

The `get_db()` FastAPI dependency yields a session but does not commit. Every route
must explicitly call `await db.commit()`. The `get_db_context()` context manager does
auto-commit. This is intentional but could cause silent data loss if a commit is missed.
