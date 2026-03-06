"""Convert planned_date to TIMESTAMPTZ and add auto_publish column.

Revision ID: 047
"""

import sqlalchemy as sa
from alembic import op

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            -- Convert planned_date from DATE to TIMESTAMP WITH TIME ZONE
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'articles'
                AND column_name = 'planned_date'
                AND data_type = 'date'
            ) THEN
                ALTER TABLE articles
                    ALTER COLUMN planned_date TYPE TIMESTAMP WITH TIME ZONE
                    USING planned_date::TIMESTAMP WITH TIME ZONE;
            END IF;

            -- Add auto_publish column
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'articles'
                AND column_name = 'auto_publish'
            ) THEN
                ALTER TABLE articles ADD COLUMN auto_publish BOOLEAN NOT NULL DEFAULT FALSE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE articles DROP COLUMN IF EXISTS auto_publish;")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'articles'
                AND column_name = 'planned_date'
            ) THEN
                ALTER TABLE articles
                    ALTER COLUMN planned_date TYPE DATE
                    USING planned_date::DATE;
            END IF;
        END $$;
    """)
