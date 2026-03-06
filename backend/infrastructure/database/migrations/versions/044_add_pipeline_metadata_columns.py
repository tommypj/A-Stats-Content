"""Add pipeline metadata columns to articles table.

Adds quality_tier, schemas, and run_metadata columns to support
the 10-step self-correcting content pipeline.

Revision ID: 044
"""

import sqlalchemy as sa
from alembic import op

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'articles' AND column_name = 'quality_tier'
            ) THEN
                ALTER TABLE articles ADD COLUMN quality_tier VARCHAR(10);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'articles' AND column_name = 'schemas'
            ) THEN
                ALTER TABLE articles ADD COLUMN schemas JSONB;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'articles' AND column_name = 'run_metadata'
            ) THEN
                ALTER TABLE articles ADD COLUMN run_metadata JSONB;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_column("articles", "run_metadata")
    op.drop_column("articles", "schemas")
    op.drop_column("articles", "quality_tier")
