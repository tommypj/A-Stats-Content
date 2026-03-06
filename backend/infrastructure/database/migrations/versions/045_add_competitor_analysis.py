"""Add competitor_analyses and competitor_articles tables.

Revision ID: 045
"""

import sqlalchemy as sa
from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'competitor_analyses'
            ) THEN
                CREATE TABLE competitor_analyses (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                    domain VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    total_urls INTEGER NOT NULL DEFAULT 0,
                    scraped_urls INTEGER NOT NULL DEFAULT 0,
                    total_keywords INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    completed_at TIMESTAMPTZ,
                    expires_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'competitor_analyses'
                AND indexname = 'ix_comp_analysis_user_id'
            ) THEN
                CREATE INDEX ix_comp_analysis_user_id ON competitor_analyses (user_id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'competitor_analyses'
                AND indexname = 'ix_comp_analysis_project_id'
            ) THEN
                CREATE INDEX ix_comp_analysis_project_id ON competitor_analyses (project_id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'competitor_analyses'
                AND indexname = 'ix_comp_analysis_user_domain'
            ) THEN
                CREATE INDEX ix_comp_analysis_user_domain ON competitor_analyses (user_id, domain);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'competitor_analyses'
                AND indexname = 'ix_comp_analysis_expires'
            ) THEN
                CREATE INDEX ix_comp_analysis_expires ON competitor_analyses (expires_at);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'competitor_articles'
            ) THEN
                CREATE TABLE competitor_articles (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    analysis_id UUID NOT NULL REFERENCES competitor_analyses(id) ON DELETE CASCADE,
                    url VARCHAR(2048) NOT NULL,
                    title VARCHAR(500),
                    meta_description TEXT,
                    headings JSONB,
                    url_slug VARCHAR(500),
                    word_count INTEGER,
                    extracted_keyword VARCHAR(255),
                    keyword_confidence FLOAT,
                    scraped_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'competitor_articles'
                AND indexname = 'ix_comp_articles_analysis'
            ) THEN
                CREATE INDEX ix_comp_articles_analysis ON competitor_articles (analysis_id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'competitor_articles'
                AND indexname = 'ix_comp_articles_keyword'
            ) THEN
                CREATE INDEX ix_comp_articles_keyword ON competitor_articles (extracted_keyword);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("competitor_articles")
    op.drop_table("competitor_analyses")
