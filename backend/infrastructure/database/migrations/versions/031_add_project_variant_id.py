"""Add lemonsqueezy_variant_id to projects table.

BILL-07: ProjectSubscriptionResponse was returning lemonsqueezy_subscription_id
in the variant_id field, breaking the frontend upgrade UI.

Revision ID: 031
Revises: 030
Create Date: 2026-02-27
"""

from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'projects'
                  AND column_name = 'lemonsqueezy_variant_id'
            ) THEN
                ALTER TABLE projects ADD COLUMN lemonsqueezy_variant_id VARCHAR(255);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_column("projects", "lemonsqueezy_variant_id")
