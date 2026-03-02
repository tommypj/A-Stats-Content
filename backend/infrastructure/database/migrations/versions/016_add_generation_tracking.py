"""
Add generation tracking and admin alerts tables.

Adds generation_logs for tracking every AI generation attempt (article,
outline, image) including status, duration, cost, and input metadata.
Adds admin_alerts for surfacing notable system events to administrators.

Revision ID: 016
Revises: 015
Create Date: 2026-02-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create generation_logs table
    # ------------------------------------------------------------------
    op.create_table(
        "generation_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("ai_model", sa.String(100), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_metadata", sa.JSON(), nullable=True),
        sa.Column("cost_credits", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Single-column indexes declared on columns via index=True
    op.create_index("ix_generation_logs_user_id", "generation_logs", ["user_id"])
    op.create_index("ix_generation_logs_project_id", "generation_logs", ["project_id"])
    op.create_index("ix_generation_logs_resource_type", "generation_logs", ["resource_type"])
    op.create_index("ix_generation_logs_status", "generation_logs", ["status"])

    # Composite indexes
    op.create_index(
        "ix_generation_logs_user_resource",
        "generation_logs",
        ["user_id", "resource_type"],
    )
    op.create_index(
        "ix_generation_logs_created",
        "generation_logs",
        ["created_at"],
    )
    op.create_index(
        "ix_generation_logs_status_type",
        "generation_logs",
        ["status", "resource_type"],
    )

    # ------------------------------------------------------------------
    # 2. Create admin_alerts table
    # ------------------------------------------------------------------
    op.create_table(
        "admin_alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Single-column indexes
    op.create_index("ix_admin_alerts_alert_type", "admin_alerts", ["alert_type"])

    # Composite indexes
    op.create_index(
        "ix_admin_alerts_unread",
        "admin_alerts",
        ["is_read", "created_at"],
    )
    op.create_index(
        "ix_admin_alerts_type_severity",
        "admin_alerts",
        ["alert_type", "severity"],
    )


def downgrade() -> None:
    # Drop admin_alerts first (no dependents)
    op.drop_index("ix_admin_alerts_type_severity", table_name="admin_alerts")
    op.drop_index("ix_admin_alerts_unread", table_name="admin_alerts")
    op.drop_index("ix_admin_alerts_alert_type", table_name="admin_alerts")
    op.drop_table("admin_alerts")

    # Drop generation_logs
    op.drop_index("ix_generation_logs_status_type", table_name="generation_logs")
    op.drop_index("ix_generation_logs_created", table_name="generation_logs")
    op.drop_index("ix_generation_logs_user_resource", table_name="generation_logs")
    op.drop_index("ix_generation_logs_status", table_name="generation_logs")
    op.drop_index("ix_generation_logs_resource_type", table_name="generation_logs")
    op.drop_index("ix_generation_logs_project_id", table_name="generation_logs")
    op.drop_index("ix_generation_logs_user_id", table_name="generation_logs")
    op.drop_table("generation_logs")
