"""Add keyword research cache table

Revision ID: 034
Revises: 033
Create Date: 2026-02-27
"""

from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent — safe to run even if the table already exists
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'keyword_research_cache'
            ) THEN
                CREATE TABLE keyword_research_cache (
                    id                     UUID        NOT NULL DEFAULT gen_random_uuid(),
                    user_id                UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    seed_keyword_normalized VARCHAR(200) NOT NULL,
                    seed_keyword_original   VARCHAR(200) NOT NULL,
                    result_json            TEXT        NOT NULL,
                    expires_at             TIMESTAMPTZ NOT NULL,
                    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (id)
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'keyword_research_cache'
                  AND indexname = 'ix_keyword_research_cache_user_id'
            ) THEN
                CREATE INDEX ix_keyword_research_cache_user_id
                    ON keyword_research_cache (user_id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'keyword_research_cache'
                  AND indexname = 'ix_keyword_research_cache_expires_at'
            ) THEN
                CREATE INDEX ix_keyword_research_cache_expires_at
                    ON keyword_research_cache (expires_at);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'keyword_research_cache'
                  AND indexname = 'ix_kw_cache_user_keyword'
            ) THEN
                CREATE INDEX ix_kw_cache_user_keyword
                    ON keyword_research_cache (user_id, seed_keyword_normalized);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_index("ix_kw_cache_user_keyword", table_name="keyword_research_cache")
    op.drop_index("ix_keyword_research_cache_expires_at", table_name="keyword_research_cache")
    op.drop_index("ix_keyword_research_cache_user_id", table_name="keyword_research_cache")
    op.drop_table("keyword_research_cache")
