"""Add blog tables: blog_categories, blog_tags, blog_posts, blog_post_tags.

Revision ID: 043
Revises: 042
Create Date: 2026-03-04
"""

from alembic import op

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$ BEGIN

        -- Blog categories
        CREATE TABLE IF NOT EXISTS blog_categories (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        VARCHAR(200) NOT NULL,
            slug        VARCHAR(200) NOT NULL,
            description TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_blog_categories_name UNIQUE (name),
            CONSTRAINT uq_blog_categories_slug UNIQUE (slug)
        );

        CREATE INDEX IF NOT EXISTS ix_blog_categories_slug ON blog_categories (slug);

        -- Blog tags
        CREATE TABLE IF NOT EXISTS blog_tags (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name       VARCHAR(100) NOT NULL,
            slug       VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_blog_tags_name UNIQUE (name),
            CONSTRAINT uq_blog_tags_slug UNIQUE (slug)
        );

        -- Blog posts
        CREATE TABLE IF NOT EXISTS blog_posts (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug                VARCHAR(300) NOT NULL,
            title               VARCHAR(500) NOT NULL,
            meta_title          VARCHAR(200),
            meta_description    VARCHAR(500),
            excerpt             TEXT,
            content_html        TEXT,
            status              VARCHAR(20) NOT NULL DEFAULT 'draft',
            featured_image_url  VARCHAR(2000),
            featured_image_alt  VARCHAR(500),
            og_image_url        VARCHAR(2000),
            author_id           UUID REFERENCES users(id) ON DELETE SET NULL,
            author_name         VARCHAR(200),
            category_id         UUID REFERENCES blog_categories(id) ON DELETE SET NULL,
            published_at        TIMESTAMPTZ,
            schema_faq          JSONB,
            deleted_at          TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_blog_posts_slug UNIQUE (slug)
        );

        CREATE INDEX IF NOT EXISTS ix_blog_posts_slug ON blog_posts (slug);
        CREATE INDEX IF NOT EXISTS ix_blog_posts_status ON blog_posts (status);
        CREATE INDEX IF NOT EXISTS ix_blog_posts_published_at ON blog_posts (published_at);
        CREATE INDEX IF NOT EXISTS ix_blog_posts_author_id ON blog_posts (author_id);
        CREATE INDEX IF NOT EXISTS ix_blog_posts_category_id ON blog_posts (category_id);
        CREATE INDEX IF NOT EXISTS ix_blog_posts_deleted_at ON blog_posts (deleted_at);
        CREATE INDEX IF NOT EXISTS ix_blog_posts_status_published_at ON blog_posts (status, published_at);

        -- Blog post tags (association table)
        CREATE TABLE IF NOT EXISTS blog_post_tags (
            post_id UUID NOT NULL REFERENCES blog_posts(id) ON DELETE CASCADE,
            tag_id  UUID NOT NULL REFERENCES blog_tags(id) ON DELETE CASCADE,
            PRIMARY KEY (post_id, tag_id)
        );

        END $$;
    """)


def downgrade():
    op.execute("""
        DO $$ BEGIN
            DROP TABLE IF EXISTS blog_post_tags;
            DROP TABLE IF EXISTS blog_posts;
            DROP TABLE IF EXISTS blog_tags;
            DROP TABLE IF EXISTS blog_categories;
        END $$;
    """)
