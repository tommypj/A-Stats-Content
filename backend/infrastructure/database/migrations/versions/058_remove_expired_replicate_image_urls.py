"""Remove expired Replicate image URLs from blog posts

Blog posts created via the admin panel may reference temporary Replicate
image URLs (replicate.delivery / pbxt.replicate.delivery) that expire after
a short period.  This migration NULLs out featured_image_url and og_image_url
columns that contain those domains, and strips <img> tags with Replicate
src attributes from content_html.

The frontend already gracefully handles NULL image URLs (conditionally
renders images), and OG metadata falls back to /icon.png.

Revision ID: 058
Revises: 057
Create Date: 2026-03-10
"""
from alembic import op

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. NULL out featured_image_url containing replicate.delivery
    op.execute("""
        UPDATE blog_posts
        SET featured_image_url = NULL
        WHERE featured_image_url LIKE '%replicate.delivery%'
          AND deleted_at IS NULL;
    """)

    # 2. NULL out og_image_url containing replicate.delivery
    op.execute("""
        UPDATE blog_posts
        SET og_image_url = NULL
        WHERE og_image_url LIKE '%replicate.delivery%'
          AND deleted_at IS NULL;
    """)

    # 3. Remove <img> tags with replicate.delivery src from content_html.
    #    Uses PostgreSQL regexp_replace to strip <img ... replicate.delivery ... > tags.
    op.execute("""
        UPDATE blog_posts
        SET content_html = regexp_replace(
            content_html,
            '<img[^>]*src="[^"]*replicate\\.delivery[^"]*"[^>]*/?\\s*>',
            '',
            'gi'
        )
        WHERE content_html LIKE '%replicate.delivery%'
          AND deleted_at IS NULL;
    """)


def downgrade() -> None:
    # Data migration — original URLs are expired and unrecoverable.
    # No downgrade possible.
    pass
