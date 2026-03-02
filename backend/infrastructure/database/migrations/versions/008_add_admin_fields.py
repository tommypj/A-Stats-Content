"""Add admin fields to users and create admin_audit_logs table

Revision ID: 008
Revises: 007
Create Date: 2026-02-20

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add admin functionality to users and create audit logs table."""

    # Add suspension fields to users table
    op.add_column(
        "users", sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column("users", sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("suspended_reason", sa.Text(), nullable=True))

    # Create index on role column for admin queries
    op.create_index("ix_users_role", "users", ["role"])

    # Create admin_audit_logs table
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
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
    )

    # Add foreign keys
    op.create_foreign_key(
        "fk_admin_audit_logs_admin_user_id",
        "admin_audit_logs",
        "users",
        ["admin_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_admin_audit_logs_target_user_id",
        "admin_audit_logs",
        "users",
        ["target_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create indexes on admin_audit_logs
    op.create_index("ix_admin_audit_logs_admin_user_id", "admin_audit_logs", ["admin_user_id"])
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"])
    op.create_index("ix_admin_audit_admin_action", "admin_audit_logs", ["admin_user_id", "action"])
    op.create_index("ix_admin_audit_target", "admin_audit_logs", ["target_type", "target_id"])
    op.create_index("ix_admin_audit_target_user", "admin_audit_logs", ["target_user_id"])
    op.create_index("ix_admin_audit_created", "admin_audit_logs", ["created_at"])


def downgrade() -> None:
    """Remove admin functionality."""

    # Drop admin_audit_logs table and its indexes
    op.drop_index("ix_admin_audit_created", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_target_user", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_target", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_admin_action", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_action", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_admin_user_id", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")

    # Remove index from users table
    op.drop_index("ix_users_role", table_name="users")

    # Remove suspension fields from users table
    op.drop_column("users", "suspended_reason")
    op.drop_column("users", "suspended_at")
    op.drop_column("users", "is_suspended")
