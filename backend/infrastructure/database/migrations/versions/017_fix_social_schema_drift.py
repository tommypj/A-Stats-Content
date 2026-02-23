"""Fix social module schema drift between migration 007 and ORM models.

The original 007_create_social_tables migration created columns with different
names and missing fields compared to what the ORM models (social.py) define.
This migration aligns the DB schema with the ORM model definitions.

Changes:
- social_accounts:  rename account_id->platform_user_id,
                    account_name->platform_username,
                    account_username->platform_display_name,
                    token_expiry->token_expires_at;
                    add project_id, account_metadata, last_verified_at,
                    verification_error;
                    drop last_used;
                    update unique constraint.
- scheduled_posts:  allow scheduled_at to be NULL;
                    drop timezone column;
                    add project_id, link_url, published_at,
                    publish_attempted_at, publish_error.
- post_targets:     rename post_id->scheduled_post_id,
                    account_id->social_account_id,
                    error_message->publish_error,
                    posted_at->published_at;
                    add platform_content, platform_metadata, is_published,
                    analytics_data, last_analytics_fetch;
                    drop status column;
                    update unique constraint and foreign key indexes.

Revision ID: 017
Revises: 016
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # social_accounts
    # =========================================================================

    # Rename columns to match ORM model
    op.alter_column("social_accounts", "account_id", new_column_name="platform_user_id")
    op.alter_column("social_accounts", "account_name", new_column_name="platform_username",
                    existing_type=sa.String(255), nullable=True)
    op.alter_column("social_accounts", "account_username", new_column_name="platform_display_name",
                    existing_type=sa.String(255), nullable=True)
    op.alter_column("social_accounts", "token_expiry", new_column_name="token_expires_at",
                    existing_type=sa.DateTime(timezone=True), nullable=True)

    # Drop old unique constraint (references old column name account_id)
    op.drop_constraint("uq_social_account", "social_accounts", type_="unique")

    # Re-create unique constraint using the new column name and matching ORM index
    # ORM defines: Index("ix_social_accounts_platform_user", "platform", "platform_user_id", unique=True)
    op.create_index(
        "ix_social_accounts_platform_user",
        "social_accounts",
        ["platform", "platform_user_id"],
        unique=True,
    )

    # Add missing columns
    op.add_column(
        "social_accounts",
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_social_accounts_project_id", "social_accounts", ["project_id"])

    op.add_column(
        "social_accounts",
        sa.Column("account_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "social_accounts",
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "social_accounts",
        sa.Column("verification_error", sa.Text(), nullable=True),
    )

    # Drop last_used (not in ORM model)
    op.drop_column("social_accounts", "last_used")

    # =========================================================================
    # scheduled_posts
    # =========================================================================

    # Allow scheduled_at to be NULL (ORM model has nullable=True)
    op.alter_column(
        "scheduled_posts",
        "scheduled_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )

    # Drop timezone column (not in ORM model)
    op.drop_column("scheduled_posts", "timezone")

    # Add project_id foreign key column
    op.add_column(
        "scheduled_posts",
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_scheduled_posts_project_id", "scheduled_posts", ["project_id"])

    # Add publishing metadata columns
    op.add_column(
        "scheduled_posts",
        sa.Column("link_url", sa.String(2048), nullable=True),
    )
    op.add_column(
        "scheduled_posts",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "scheduled_posts",
        sa.Column("publish_attempted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "scheduled_posts",
        sa.Column("publish_error", sa.Text(), nullable=True),
    )

    # Add composite indexes from ORM model
    op.create_index(
        "ix_scheduled_posts_user_scheduled",
        "scheduled_posts",
        ["user_id", "scheduled_at"],
    )

    # =========================================================================
    # post_targets
    # =========================================================================

    # Drop old unique constraint referencing old column names
    op.drop_constraint("uq_post_target", "post_targets", type_="unique")

    # Drop old indexes before renaming columns
    op.drop_index("ix_post_targets_post_id", "post_targets")
    op.drop_index("ix_post_targets_account_id", "post_targets")

    # Rename FK columns
    op.alter_column("post_targets", "post_id", new_column_name="scheduled_post_id",
                    existing_type=postgresql.UUID(as_uuid=False), nullable=False)
    op.alter_column("post_targets", "account_id", new_column_name="social_account_id",
                    existing_type=postgresql.UUID(as_uuid=False), nullable=False)

    # Rename other columns
    op.alter_column("post_targets", "error_message", new_column_name="publish_error",
                    existing_type=sa.Text(), nullable=True)
    op.alter_column("post_targets", "posted_at", new_column_name="published_at",
                    existing_type=sa.DateTime(timezone=True), nullable=True)

    # Drop status column (ORM model uses is_published bool instead)
    op.drop_column("post_targets", "status")

    # Add new columns from ORM model
    op.add_column(
        "post_targets",
        sa.Column("platform_content", sa.Text(), nullable=True),
    )
    op.add_column(
        "post_targets",
        sa.Column("platform_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "post_targets",
        sa.Column("is_published", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
    )
    op.add_column(
        "post_targets",
        sa.Column("analytics_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "post_targets",
        sa.Column("last_analytics_fetch", sa.DateTime(timezone=True), nullable=True),
    )

    # Re-create indexes with new column names
    op.create_index(
        "ix_post_targets_post",
        "post_targets",
        ["scheduled_post_id", "social_account_id"],
    )
    op.create_index(
        "ix_post_targets_scheduled_post_id",
        "post_targets",
        ["scheduled_post_id"],
    )
    op.create_index(
        "ix_post_targets_social_account_id",
        "post_targets",
        ["social_account_id"],
    )


def downgrade() -> None:
    # =========================================================================
    # post_targets (reverse)
    # =========================================================================
    op.drop_index("ix_post_targets_post", "post_targets")
    op.drop_index("ix_post_targets_scheduled_post_id", "post_targets")
    op.drop_index("ix_post_targets_social_account_id", "post_targets")

    op.drop_column("post_targets", "last_analytics_fetch")
    op.drop_column("post_targets", "analytics_data")
    op.drop_column("post_targets", "is_published")
    op.drop_column("post_targets", "platform_metadata")
    op.drop_column("post_targets", "platform_content")

    op.add_column(
        "post_targets",
        sa.Column("status", sa.String(50), nullable=False,
                  server_default=sa.text("'pending'")),
    )

    op.alter_column("post_targets", "published_at", new_column_name="posted_at",
                    existing_type=sa.DateTime(timezone=True), nullable=True)
    op.alter_column("post_targets", "publish_error", new_column_name="error_message",
                    existing_type=sa.Text(), nullable=True)
    op.alter_column("post_targets", "social_account_id", new_column_name="account_id",
                    existing_type=postgresql.UUID(as_uuid=False), nullable=False)
    op.alter_column("post_targets", "scheduled_post_id", new_column_name="post_id",
                    existing_type=postgresql.UUID(as_uuid=False), nullable=False)

    op.create_index("ix_post_targets_account_id", "post_targets", ["account_id"])
    op.create_index("ix_post_targets_post_id", "post_targets", ["post_id"])
    op.create_unique_constraint("uq_post_target", "post_targets", ["post_id", "account_id"])

    # =========================================================================
    # scheduled_posts (reverse)
    # =========================================================================
    op.drop_index("ix_scheduled_posts_user_scheduled", "scheduled_posts")
    op.drop_column("scheduled_posts", "publish_error")
    op.drop_column("scheduled_posts", "publish_attempted_at")
    op.drop_column("scheduled_posts", "published_at")
    op.drop_column("scheduled_posts", "link_url")
    op.drop_index("ix_scheduled_posts_project_id", "scheduled_posts")
    op.drop_column("scheduled_posts", "project_id")

    op.add_column(
        "scheduled_posts",
        sa.Column("timezone", sa.String(50), nullable=False,
                  server_default=sa.text("'UTC'")),
    )
    op.alter_column(
        "scheduled_posts",
        "scheduled_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )

    # =========================================================================
    # social_accounts (reverse)
    # =========================================================================
    op.add_column(
        "social_accounts",
        sa.Column("last_used", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_column("social_accounts", "verification_error")
    op.drop_column("social_accounts", "last_verified_at")
    op.drop_column("social_accounts", "account_metadata")
    op.drop_index("ix_social_accounts_project_id", "social_accounts")
    op.drop_column("social_accounts", "project_id")

    op.drop_index("ix_social_accounts_platform_user", "social_accounts")
    op.create_unique_constraint(
        "uq_social_account",
        "social_accounts",
        ["user_id", "platform", "account_id"],
    )

    op.alter_column("social_accounts", "token_expires_at", new_column_name="token_expiry",
                    existing_type=sa.DateTime(timezone=True), nullable=True)
    op.alter_column("social_accounts", "platform_display_name", new_column_name="account_username",
                    existing_type=sa.String(255), nullable=True)
    op.alter_column("social_accounts", "platform_username", new_column_name="account_name",
                    existing_type=sa.String(255), nullable=False)
    op.alter_column("social_accounts", "platform_user_id", new_column_name="account_id",
                    existing_type=sa.String(255), nullable=False)
