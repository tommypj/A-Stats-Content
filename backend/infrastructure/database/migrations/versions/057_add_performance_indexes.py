"""Add composite indexes for high-traffic query patterns

Revision ID: 057
Revises: 056
Create Date: 2026-03-10
"""
from alembic import op

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # article_revisions: used by _save_revision() on every article edit
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_article_revisions_article_created'
        ) THEN
            CREATE INDEX ix_article_revisions_article_created
            ON article_revisions (article_id, created_at);
        END IF;
        END $$;
    """)

    # keyword_rankings: used by every analytics query
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_keyword_rankings_user_site_date'
        ) THEN
            CREATE INDEX ix_keyword_rankings_user_site_date
            ON keyword_rankings (user_id, site_url, date);
        END IF;
        END $$;
    """)

    # page_performances: same query pattern as keyword_rankings
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_page_performances_user_site_date'
        ) THEN
            CREATE INDEX ix_page_performances_user_site_date
            ON page_performances (user_id, site_url, date);
        END IF;
        END $$;
    """)

    # site_audits: filtered by status in background tasks
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_site_audits_user_status'
        ) THEN
            CREATE INDEX ix_site_audits_user_status
            ON site_audits (user_id, status);
        END IF;
        END $$;
    """)

    # competitor_analyses: filtered by status in background tasks
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_comp_analyses_user_status'
        ) THEN
            CREATE INDEX ix_comp_analyses_user_status
            ON competitor_analyses (user_id, status);
        END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_article_revisions_article_created;")
    op.execute("DROP INDEX IF EXISTS ix_keyword_rankings_user_site_date;")
    op.execute("DROP INDEX IF EXISTS ix_page_performances_user_site_date;")
    op.execute("DROP INDEX IF EXISTS ix_site_audits_user_status;")
    op.execute("DROP INDEX IF EXISTS ix_comp_analyses_user_status;")
