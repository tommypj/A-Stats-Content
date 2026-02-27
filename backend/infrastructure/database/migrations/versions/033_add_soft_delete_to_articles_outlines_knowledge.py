"""Add soft delete columns to articles, outlines, and knowledge sources.

Revision ID: 033
Revises: 032
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # All column/index additions are idempotent — safe to run on databases
    # where these columns/indexes already exist from a prior deploy attempt.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='articles' AND column_name='deleted_at') THEN
                ALTER TABLE articles ADD COLUMN deleted_at TIMESTAMPTZ;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='articles' AND indexname='ix_articles_deleted_at') THEN
                CREATE INDEX ix_articles_deleted_at ON articles (deleted_at);
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='outlines' AND column_name='deleted_at') THEN
                ALTER TABLE outlines ADD COLUMN deleted_at TIMESTAMPTZ;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='outlines' AND indexname='ix_outlines_deleted_at') THEN
                CREATE INDEX ix_outlines_deleted_at ON outlines (deleted_at);
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='knowledge_sources' AND column_name='deleted_at') THEN
                ALTER TABLE knowledge_sources ADD COLUMN deleted_at TIMESTAMPTZ;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename='knowledge_sources' AND indexname='ix_knowledge_sources_deleted_at') THEN
                CREATE INDEX ix_knowledge_sources_deleted_at ON knowledge_sources (deleted_at);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_index("ix_knowledge_sources_deleted_at", table_name="knowledge_sources")
    op.drop_column("knowledge_sources", "deleted_at")

    op.drop_index("ix_outlines_deleted_at", table_name="outlines")
    op.drop_column("outlines", "deleted_at")

    op.drop_index("ix_articles_deleted_at", table_name="articles")
    op.drop_column("articles", "deleted_at")
