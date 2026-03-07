"""Add tags, article_tags, outline_tags tables.

Revision ID: 052
Revises: 051
"""

from alembic import op

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            -- Tags table
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'tags'
            ) THEN
                CREATE TABLE tags (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                    name VARCHAR(100) NOT NULL,
                    color VARCHAR(7) NOT NULL DEFAULT '#6366f1',
                    deleted_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_tags_user_name UNIQUE (user_id, name)
                );
                CREATE INDEX ix_tags_user_id ON tags(user_id);
                CREATE INDEX ix_tags_project_id ON tags(project_id);
            END IF;

            -- Article-tag association
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'article_tags'
            ) THEN
                CREATE TABLE article_tags (
                    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (article_id, tag_id)
                );
            END IF;

            -- Outline-tag association
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'outline_tags'
            ) THEN
                CREATE TABLE outline_tags (
                    outline_id UUID NOT NULL REFERENCES outlines(id) ON DELETE CASCADE,
                    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (outline_id, tag_id)
                );
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS outline_tags;")
    op.execute("DROP TABLE IF EXISTS article_tags;")
    op.execute("DROP TABLE IF EXISTS tags;")
