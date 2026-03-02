"""Remove project-level billing columns.

Projects are now pure organizational folders.
All billing and quota enforcement lives on the user only.

Revision ID: 042
Revises: 041
Create Date: 2026-03-02
"""

from alembic import op

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$ BEGIN
            DROP INDEX IF EXISTS ix_projects_subscription;

            ALTER TABLE projects
                DROP COLUMN IF EXISTS subscription_tier,
                DROP COLUMN IF EXISTS subscription_status,
                DROP COLUMN IF EXISTS subscription_expires,
                DROP COLUMN IF EXISTS lemonsqueezy_customer_id,
                DROP COLUMN IF EXISTS lemonsqueezy_subscription_id,
                DROP COLUMN IF EXISTS lemonsqueezy_variant_id,
                DROP COLUMN IF EXISTS articles_generated_this_month,
                DROP COLUMN IF EXISTS outlines_generated_this_month,
                DROP COLUMN IF EXISTS images_generated_this_month,
                DROP COLUMN IF EXISTS social_posts_generated_this_month,
                DROP COLUMN IF EXISTS usage_reset_date;
        END $$;
    """)


def downgrade():
    pass  # Non-reversible — data already lost
