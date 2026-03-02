"""Add partial indexes for soft-deleted rows performance

DB-H2: Six tables that have deleted_at columns lack partial indexes scoped
to active (non-deleted) rows. This migration adds WHERE deleted_at IS NULL
partial indexes so that the common active-row queries use tight index scans
instead of full-table scans.

NOTE: CREATE INDEX CONCURRENTLY cannot run inside a transaction. Alembic wraps
upgrades in a transaction by default, so we use plain CREATE INDEX here
(which takes a ShareLock — brief, sub-second for typical table sizes).
Each statement is wrapped in an idempotent DO block so re-runs are safe.

Revision ID: 037
Revises: 036
Create Date: 2026-03-02
"""
from alembic import op

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None

# (index_name, table, column, where_clause)
_INDEXES = [
    (
        "ix_users_active_user_id",
        "users",
        "id",
        "WHERE deleted_at IS NULL",
    ),
    (
        "ix_articles_active_project",
        "articles",
        "project_id",
        "WHERE deleted_at IS NULL",
    ),
    (
        "ix_articles_active_user",
        "articles",
        "user_id",
        "WHERE deleted_at IS NULL",
    ),
    (
        "ix_outlines_active_project",
        "outlines",
        "project_id",
        "WHERE deleted_at IS NULL",
    ),
    (
        "ix_knowledge_sources_active_project",
        "knowledge_sources",
        "project_id",
        "WHERE deleted_at IS NULL",
    ),
    (
        "ix_project_invitations_active",
        "project_invitations",
        "project_id",
        "WHERE deleted_at IS NULL",
    ),
]


def upgrade() -> None:
    for index_name, table, column, where in _INDEXES:
        op.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE indexname = '{index_name}'
                ) THEN
                    CREATE INDEX {index_name}
                        ON {table}({column}) {where};
                END IF;
            END $$;
        """)


def downgrade() -> None:
    for index_name, _table, _column, _where in _INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {index_name};")
