"""Add improve_count to articles and social_posts tracking to users/projects

Revision ID: 035
Revises: 034
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent — safe to run even if columns already exist
    op.execute("""
        DO $$
        BEGIN
            -- articles.improve_count: tracks how many AI improvement passes have been used
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'articles' AND column_name = 'improve_count'
            ) THEN
                ALTER TABLE articles ADD COLUMN improve_count INTEGER NOT NULL DEFAULT 0;
            END IF;

            -- users.social_posts_generated_this_month: monthly social post quota counter
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'social_posts_generated_this_month'
            ) THEN
                ALTER TABLE users ADD COLUMN social_posts_generated_this_month INTEGER NOT NULL DEFAULT 0;
            END IF;

            -- projects.social_posts_generated_this_month: project-level monthly social post counter
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'projects' AND column_name = 'social_posts_generated_this_month'
            ) THEN
                ALTER TABLE projects ADD COLUMN social_posts_generated_this_month INTEGER NOT NULL DEFAULT 0;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'articles' AND column_name = 'improve_count'
            ) THEN
                ALTER TABLE articles DROP COLUMN improve_count;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'social_posts_generated_this_month'
            ) THEN
                ALTER TABLE users DROP COLUMN social_posts_generated_this_month;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'projects' AND column_name = 'social_posts_generated_this_month'
            ) THEN
                ALTER TABLE projects DROP COLUMN social_posts_generated_this_month;
            END IF;
        END $$;
    """)
