"""Reset user usage counters and fix usage_reset_date.

One-time data fix: the usage_reset_date was initialized without resetting
counters, leaving users permanently blocked at their limit. This resets
all counters to zero and sets usage_reset_date to the first of next month
for all users who currently have a usage_reset_date set.

Revision ID: 022
Revises: 021
Create Date: 2026-02-24
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE users
        SET articles_generated_this_month = 0,
            outlines_generated_this_month = 0,
            images_generated_this_month = 0,
            usage_reset_date = date_trunc('month', now() AT TIME ZONE 'UTC') + interval '1 month'
        WHERE usage_reset_date IS NOT NULL
    """)


def downgrade() -> None:
    # Data-only migration; cannot meaningfully reverse counter resets
    pass
