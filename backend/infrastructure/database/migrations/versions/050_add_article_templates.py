"""Add article_templates table.

Revision ID: 050
Revises: 049
"""

from alembic import op

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'article_templates'
            ) THEN
                CREATE TABLE article_templates (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    target_audience VARCHAR(500),
                    tone VARCHAR(50),
                    word_count_target INTEGER NOT NULL DEFAULT 1500,
                    writing_style VARCHAR(100),
                    voice VARCHAR(100),
                    custom_instructions TEXT,
                    sections JSONB,
                    deleted_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX ix_article_templates_user_id ON article_templates(user_id);
                CREATE INDEX ix_article_templates_project_id ON article_templates(project_id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS article_templates;")
