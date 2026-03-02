"""Create users table

Revision ID: 001
Revises:
Create Date: 2026-02-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("email_verification_token", sa.String(length=255), nullable=True),
        sa.Column("email_verification_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_reset_token", sa.String(length=255), nullable=True),
        sa.Column("password_reset_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subscription_tier", sa.String(length=50), nullable=False, server_default="free"),
        sa.Column("subscription_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("timezone", sa.String(length=50), nullable=False, server_default="UTC"),
        sa.Column(
            "articles_generated_this_month", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "outlines_generated_this_month", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("images_generated_this_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage_reset_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("stripe_customer_id"),
    )

    # Create indexes
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_email_status", "users", ["email", "status"])
    op.create_index("ix_users_subscription", "users", ["subscription_tier", "subscription_expires"])
    op.create_index("ix_users_stripe", "users", ["stripe_customer_id"])


def downgrade() -> None:
    op.drop_index("ix_users_stripe", table_name="users")
    op.drop_index("ix_users_subscription", table_name="users")
    op.drop_index("ix_users_email_status", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
