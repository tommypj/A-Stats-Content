"""Add content decay alerts table.

Tracks content performance decline detected from GSC data.

Revision ID: 024
Revises: 023
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_decay_alerts",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("article_id", UUID(as_uuid=False), sa.ForeignKey("articles.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("alert_type", sa.String(50), nullable=False),  # position_drop, traffic_drop, ctr_drop, impressions_drop
        sa.Column("severity", sa.String(20), nullable=False),  # warning, critical
        sa.Column("keyword", sa.String(500), nullable=True),
        sa.Column("page_url", sa.String(1000), nullable=True),
        sa.Column("metric_name", sa.String(50), nullable=False),  # position, clicks, impressions, ctr
        sa.Column("metric_before", sa.Float, nullable=False),
        sa.Column("metric_after", sa.Float, nullable=False),
        sa.Column("period_days", sa.Integer, nullable=False, server_default="7"),
        sa.Column("percentage_change", sa.Float, nullable=False),
        sa.Column("suggested_actions", sa.JSON, nullable=True),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Add indexes for common queries
    op.create_index("ix_content_decay_alerts_user_type", "content_decay_alerts", ["user_id", "alert_type"])
    op.create_index("ix_content_decay_alerts_unread", "content_decay_alerts", ["user_id", "is_read"])
    op.create_index("ix_content_decay_alerts_created", "content_decay_alerts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_content_decay_alerts_created")
    op.drop_index("ix_content_decay_alerts_unread")
    op.drop_index("ix_content_decay_alerts_user_type")
    op.drop_table("content_decay_alerts")
