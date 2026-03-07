"""Add seo_reports table.

Revision ID: 051
Revises: 050
"""

from alembic import op

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'seo_reports'
            ) THEN
                CREATE TABLE seo_reports (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    report_type VARCHAR(50) NOT NULL DEFAULT 'overview',
                    date_from VARCHAR(10),
                    date_to VARCHAR(10),
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    error_message TEXT,
                    report_data JSONB,
                    deleted_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX ix_seo_reports_user_id ON seo_reports(user_id);
                CREATE INDEX ix_seo_reports_project_id ON seo_reports(project_id);
                CREATE INDEX ix_seo_reports_status ON seo_reports(status);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS seo_reports;")
