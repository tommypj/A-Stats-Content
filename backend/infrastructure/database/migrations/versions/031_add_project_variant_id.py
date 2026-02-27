"""Add lemonsqueezy_variant_id to projects table.

BILL-07: ProjectSubscriptionResponse was returning lemonsqueezy_subscription_id
in the variant_id field, breaking the frontend upgrade UI.

Revision ID: 031
Revises: 030
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("lemonsqueezy_variant_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "lemonsqueezy_variant_id")
