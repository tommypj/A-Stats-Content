"""Create social media tables

Revision ID: 007
Revises: 006
Create Date: 2026-02-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create social media tables for scheduling and publishing."""

    # Create social_accounts table
    op.create_table(
        "social_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("account_id", sa.String(255), nullable=False),
        sa.Column("account_name", sa.String(255), nullable=False),
        sa.Column("account_username", sa.String(255), nullable=True),
        sa.Column("profile_image_url", sa.String(1000), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "platform", "account_id", name="uq_social_account"),
    )
    op.create_index("ix_social_accounts_user_id", "social_accounts", ["user_id"])
    op.create_index("ix_social_accounts_platform", "social_accounts", ["platform"])
    op.create_index("ix_social_accounts_user_platform", "social_accounts", ["user_id", "platform"])

    # Create scheduled_posts table
    op.create_table(
        "scheduled_posts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("media_urls", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False, server_default=sa.text("'UTC'")),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("article_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_scheduled_posts_user_id", "scheduled_posts", ["user_id"])
    op.create_index("ix_scheduled_posts_status", "scheduled_posts", ["status"])
    op.create_index("ix_scheduled_posts_article_id", "scheduled_posts", ["article_id"])
    op.create_index("ix_scheduled_posts_scheduled_at", "scheduled_posts", ["scheduled_at"])
    op.create_index("ix_scheduled_posts_user_status", "scheduled_posts", ["user_id", "status"])

    # Create post_targets table
    op.create_table(
        "post_targets",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("post_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("platform_post_id", sa.String(255), nullable=True),
        sa.Column("platform_post_url", sa.String(1000), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["post_id"], ["scheduled_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["social_accounts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("post_id", "account_id", name="uq_post_target"),
    )
    op.create_index("ix_post_targets_post_id", "post_targets", ["post_id"])
    op.create_index("ix_post_targets_account_id", "post_targets", ["account_id"])

    # Create post_analytics table
    op.create_table(
        "post_analytics",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("post_target_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("likes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("comments", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("shares", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["post_target_id"], ["post_targets.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_post_analytics_post_target_id", "post_analytics", ["post_target_id"])
    op.create_index("ix_post_analytics_recorded_at", "post_analytics", ["recorded_at"])


def downgrade() -> None:
    """Drop social media tables."""
    op.drop_table("post_analytics")
    op.drop_table("post_targets")
    op.drop_table("scheduled_posts")
    op.drop_table("social_accounts")
