"""Add content-to-revenue attribution tables.

Conversion goals, content conversions tracking, and revenue reports
for Phase 4 Content-to-Revenue Attribution.

Revision ID: 027
Revises: 026
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversion_goals",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("goal_type", sa.String(50), nullable=False),  # page_visit, form_submit, purchase, custom
        sa.Column("goal_config", sa.JSON, nullable=True),  # target_url_pattern, event_name, revenue_value
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "content_conversions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("article_id", UUID(as_uuid=False), sa.ForeignKey("articles.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("goal_id", UUID(as_uuid=False), sa.ForeignKey("conversion_goals.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("page_url", sa.String(1000), nullable=True),
        sa.Column("keyword", sa.String(500), nullable=True),
        sa.Column("date", sa.Date, nullable=False, index=True),
        sa.Column("visits", sa.Integer, nullable=False, server_default="0"),
        sa.Column("conversions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("conversion_rate", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("revenue", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("attribution_model", sa.String(50), nullable=False, server_default="last_touch"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_content_conversions_user_date", "content_conversions", ["user_id", "date"])
    op.create_index("ix_content_conversions_article_date", "content_conversions", ["article_id", "date"])
    op.create_index("ix_content_conversions_goal_date", "content_conversions", ["goal_id", "date"])

    op.create_table(
        "revenue_reports",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("report_type", sa.String(50), nullable=False),  # weekly, monthly
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("total_organic_visits", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_conversions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_revenue", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("top_articles", sa.JSON, nullable=True),
        sa.Column("top_keywords", sa.JSON, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_revenue_reports_user_type", "revenue_reports", ["user_id", "report_type"])
    op.create_index("ix_revenue_reports_period", "revenue_reports", ["period_start", "period_end"])


def downgrade() -> None:
    op.drop_index("ix_revenue_reports_period")
    op.drop_index("ix_revenue_reports_user_type")
    op.drop_table("revenue_reports")
    op.drop_index("ix_content_conversions_goal_date")
    op.drop_index("ix_content_conversions_article_date")
    op.drop_index("ix_content_conversions_user_date")
    op.drop_table("content_conversions")
    op.drop_table("conversion_goals")
