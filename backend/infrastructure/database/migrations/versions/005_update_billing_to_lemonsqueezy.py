"""Update billing fields from Stripe to LemonSqueezy

Revision ID: 005
Revises: 004
Create Date: 2026-02-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Migrate from Stripe to LemonSqueezy billing fields."""

    # 1. Drop the old stripe index
    op.drop_index("ix_users_stripe", table_name="users")

    # 2. Drop the unique constraint on stripe_customer_id
    op.drop_constraint("users_stripe_customer_id_key", "users", type_="unique")

    # 3. Rename stripe columns to lemonsqueezy
    op.alter_column("users", "stripe_customer_id", new_column_name="lemonsqueezy_customer_id")
    op.alter_column(
        "users", "stripe_subscription_id", new_column_name="lemonsqueezy_subscription_id"
    )

    # 4. Add new LemonSqueezy-specific columns
    op.add_column("users", sa.Column("lemonsqueezy_variant_id", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column("subscription_status", sa.String(50), server_default="active", nullable=False),
    )

    # 5. Add unique constraint on lemonsqueezy_customer_id
    op.create_unique_constraint(
        "users_lemonsqueezy_customer_id_key", "users", ["lemonsqueezy_customer_id"]
    )

    # 6. Create new index for lemonsqueezy_customer_id
    op.create_index("ix_users_lemonsqueezy", "users", ["lemonsqueezy_customer_id"])


def downgrade() -> None:
    """Revert LemonSqueezy billing changes back to Stripe."""

    # Reverse the operations in opposite order

    # 1. Drop the lemonsqueezy index
    op.drop_index("ix_users_lemonsqueezy", table_name="users")

    # 2. Drop the unique constraint on lemonsqueezy_customer_id
    op.drop_constraint("users_lemonsqueezy_customer_id_key", "users", type_="unique")

    # 3. Remove new columns
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "lemonsqueezy_variant_id")

    # 4. Rename lemonsqueezy columns back to stripe
    op.alter_column(
        "users", "lemonsqueezy_subscription_id", new_column_name="stripe_subscription_id"
    )
    op.alter_column("users", "lemonsqueezy_customer_id", new_column_name="stripe_customer_id")

    # 5. Re-create the unique constraint on stripe_customer_id
    op.create_unique_constraint("users_stripe_customer_id_key", "users", ["stripe_customer_id"])

    # 6. Re-create the old stripe index
    op.create_index("ix_users_stripe", "users", ["stripe_customer_id"])
