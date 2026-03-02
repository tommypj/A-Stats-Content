"""Add composite indexes for common filter patterns

Revision ID: 039
Revises: 038
"""
from alembic import op

revision = '039'
down_revision = '038'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DB-M1: Add composite indexes for the most common dashboard and scheduler queries.
    # All are idempotent — skipped silently if they already exist.
    indexes = [
        # articles: most common dashboard query — project's non-deleted articles by status
        ("ix_articles_project_status", "articles", "project_id, status", "WHERE deleted_at IS NULL"),
        # articles: user's own non-deleted articles ordered by creation date
        ("ix_articles_user_created", "articles", "user_id, created_at DESC", "WHERE deleted_at IS NULL"),
        # outlines: project's non-deleted outlines by status
        ("ix_outlines_project_status", "outlines", "project_id, status", "WHERE deleted_at IS NULL"),
        # generation_logs: "recent generations by user" (already has user+resource_type index;
        # this one targets time-sorted user history)
        ("ix_generation_logs_user_created", "generation_logs", "user_id, created_at DESC", None),
        # scheduled_posts: social scheduler query — pending/scheduled posts by time
        ("ix_scheduled_posts_status_scheduled", "scheduled_posts", "status, scheduled_at", None),
    ]
    for idx_name, table, cols, where in indexes:
        where_clause = f" {where}" if where else ""
        op.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = '{idx_name}') THEN
                    CREATE INDEX {idx_name} ON {table}({cols}){where_clause};
                END IF;
            END $$;
        """)


def downgrade() -> None:
    for name in [
        "ix_articles_project_status",
        "ix_articles_user_created",
        "ix_outlines_project_status",
        "ix_generation_logs_user_created",
        "ix_scheduled_posts_status_scheduled",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {name};")
