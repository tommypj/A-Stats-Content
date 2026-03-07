"""Add site_audits, audit_pages, and audit_issues tables.

Revision ID: 048
"""

import sqlalchemy as sa
from alembic import op

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'site_audits'
            ) THEN
                CREATE TABLE site_audits (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                    domain VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    pages_crawled INTEGER NOT NULL DEFAULT 0,
                    pages_discovered INTEGER NOT NULL DEFAULT 0,
                    total_issues INTEGER NOT NULL DEFAULT 0,
                    critical_issues INTEGER NOT NULL DEFAULT 0,
                    warning_issues INTEGER NOT NULL DEFAULT 0,
                    info_issues INTEGER NOT NULL DEFAULT 0,
                    score INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    started_at TIMESTAMPTZ,
                    completed_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'site_audits'
                AND indexname = 'ix_site_audits_user_id'
            ) THEN
                CREATE INDEX ix_site_audits_user_id ON site_audits (user_id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'site_audits'
                AND indexname = 'ix_site_audits_status'
            ) THEN
                CREATE INDEX ix_site_audits_status ON site_audits (status);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'audit_pages'
            ) THEN
                CREATE TABLE audit_pages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    audit_id UUID NOT NULL REFERENCES site_audits(id) ON DELETE CASCADE,
                    url VARCHAR(2048) NOT NULL,
                    status_code INTEGER,
                    response_time_ms INTEGER,
                    content_type VARCHAR(255),
                    word_count INTEGER,
                    title VARCHAR(500),
                    meta_description TEXT,
                    h1_count INTEGER NOT NULL DEFAULT 0,
                    has_canonical BOOLEAN NOT NULL DEFAULT FALSE,
                    has_og_tags BOOLEAN NOT NULL DEFAULT FALSE,
                    has_structured_data BOOLEAN NOT NULL DEFAULT FALSE,
                    has_robots_meta BOOLEAN NOT NULL DEFAULT FALSE,
                    page_size_bytes INTEGER,
                    redirect_chain JSONB,
                    issues JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'audit_pages'
                AND indexname = 'ix_audit_pages_audit_id'
            ) THEN
                CREATE INDEX ix_audit_pages_audit_id ON audit_pages (audit_id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'audit_issues'
            ) THEN
                CREATE TABLE audit_issues (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    audit_id UUID NOT NULL REFERENCES site_audits(id) ON DELETE CASCADE,
                    page_id UUID REFERENCES audit_pages(id) ON DELETE CASCADE,
                    issue_type VARCHAR(100) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    message TEXT NOT NULL,
                    details JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'audit_issues'
                AND indexname = 'ix_audit_issues_audit_id'
            ) THEN
                CREATE INDEX ix_audit_issues_audit_id ON audit_issues (audit_id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'audit_issues'
                AND indexname = 'ix_audit_issues_severity'
            ) THEN
                CREATE INDEX ix_audit_issues_severity ON audit_issues (severity);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("audit_issues")
    op.drop_table("audit_pages")
    op.drop_table("site_audits")
