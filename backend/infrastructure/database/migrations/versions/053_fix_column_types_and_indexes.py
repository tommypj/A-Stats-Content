"""Fix column types and add missing indexes

Revision ID: 053
Revises: 052
Create Date: 2026-03-07
"""
from alembic import op

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # DB-R03: Widen password_hash from VARCHAR(255) to TEXT
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'password_hash'
                AND data_type = 'character varying'
            ) THEN
                ALTER TABLE users ALTER COLUMN password_hash TYPE TEXT;
            END IF;
        END $$;
    """)

    # DB-R07: Add missing index on site_audits.project_id
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_site_audits_project_id ON site_audits(project_id);
    """)

    # DB-R09: Add missing standalone index on users.status
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_status ON users(status);
    """)

    # DB-R20: Fix tag unique constraint to exclude soft-deleted
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_tags_user_name'
            ) THEN
                ALTER TABLE tags DROP CONSTRAINT uq_tags_user_name;
            END IF;
        END $$;
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_tags_user_name
        ON tags(user_id, name) WHERE deleted_at IS NULL;
    """)

    # DB-R21: Add index on article_templates.deleted_at
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_article_templates_deleted_at
        ON article_templates(deleted_at) WHERE deleted_at IS NULL;
    """)

    # DB-R22: Add index on seo_reports.deleted_at
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_seo_reports_deleted_at
        ON seo_reports(deleted_at) WHERE deleted_at IS NULL;
    """)

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_seo_reports_deleted_at;")
    op.execute("DROP INDEX IF EXISTS ix_article_templates_deleted_at;")
    op.execute("DROP INDEX IF EXISTS uq_tags_user_name;")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_tags_user_name'
            ) THEN
                ALTER TABLE tags ADD CONSTRAINT uq_tags_user_name UNIQUE (user_id, name);
            END IF;
        END $$;
    """)
    op.execute("DROP INDEX IF EXISTS ix_users_status;")
    op.execute("DROP INDEX IF EXISTS ix_site_audits_project_id;")
