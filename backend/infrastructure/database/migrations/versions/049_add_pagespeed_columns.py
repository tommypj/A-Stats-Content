"""Add PageSpeed Insights columns to audit_pages.

Revision ID: 049
"""

from alembic import op

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_pages'
                AND column_name = 'performance_score'
            ) THEN
                ALTER TABLE audit_pages ADD COLUMN performance_score INT;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_pages'
                AND column_name = 'pagespeed_data'
            ) THEN
                ALTER TABLE audit_pages ADD COLUMN pagespeed_data JSONB;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_column("audit_pages", "pagespeed_data")
    op.drop_column("audit_pages", "performance_score")
