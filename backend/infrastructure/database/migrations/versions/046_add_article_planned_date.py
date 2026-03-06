"""Add planned_date column to articles for content calendar scheduling.

Revision ID: 046
"""

import sqlalchemy as sa
from alembic import op

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'articles'
                AND column_name = 'planned_date'
            ) THEN
                ALTER TABLE articles ADD COLUMN planned_date DATE;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'articles'
                AND indexname = 'ix_articles_planned_date'
            ) THEN
                CREATE INDEX ix_articles_planned_date ON articles(planned_date);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_articles_planned_date;")
    op.execute("ALTER TABLE articles DROP COLUMN IF EXISTS planned_date;")
