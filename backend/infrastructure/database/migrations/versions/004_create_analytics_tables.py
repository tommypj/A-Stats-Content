"""Create analytics tables

Revision ID: 004
Revises: 003
Create Date: 2026-02-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create analytics tables for Google Search Console integration."""

    # Create gsc_connections table
    op.create_table(
        "gsc_connections",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("site_url", sa.String(500), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_gsc_connection_user"),
    )
    op.create_index("ix_gsc_connections_user_id", "gsc_connections", ["user_id"])
    op.create_index("ix_gsc_connections_site_url", "gsc_connections", ["site_url"])

    # Create keyword_rankings table
    op.create_table(
        "keyword_rankings",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("site_url", sa.String(500), nullable=False),
        sa.Column("keyword", sa.String(500), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ctr", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("position", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "site_url", "keyword", "date", name="uq_keyword_ranking_user_site_keyword_date"),
    )
    op.create_index("ix_keyword_rankings_user_id", "keyword_rankings", ["user_id"])
    op.create_index("ix_keyword_rankings_site_url", "keyword_rankings", ["site_url"])
    op.create_index("ix_keyword_rankings_keyword", "keyword_rankings", ["keyword"])
    op.create_index("ix_keyword_rankings_date", "keyword_rankings", ["date"])
    op.create_index("ix_keyword_rankings_user_date", "keyword_rankings", ["user_id", "date"])
    op.create_index("ix_keyword_rankings_site_date", "keyword_rankings", ["site_url", "date"])
    op.create_index("ix_keyword_rankings_keyword_date", "keyword_rankings", ["keyword", "date"])

    # Create page_performances table
    op.create_table(
        "page_performances",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("site_url", sa.String(500), nullable=False),
        sa.Column("page_url", sa.String(1000), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ctr", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("position", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "site_url", "page_url", "date", name="uq_page_performance_user_site_page_date"),
    )
    op.create_index("ix_page_performances_user_id", "page_performances", ["user_id"])
    op.create_index("ix_page_performances_site_url", "page_performances", ["site_url"])
    op.create_index("ix_page_performances_page_url", "page_performances", ["page_url"])
    op.create_index("ix_page_performances_date", "page_performances", ["date"])
    op.create_index("ix_page_performances_user_date", "page_performances", ["user_id", "date"])
    op.create_index("ix_page_performances_site_date", "page_performances", ["site_url", "date"])
    op.create_index("ix_page_performances_page_date", "page_performances", ["page_url", "date"])

    # Create daily_analytics table
    op.create_table(
        "daily_analytics",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("site_url", sa.String(500), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("total_clicks", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_impressions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("avg_ctr", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("avg_position", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "site_url", "date", name="uq_daily_analytics_user_site_date"),
    )
    op.create_index("ix_daily_analytics_user_id", "daily_analytics", ["user_id"])
    op.create_index("ix_daily_analytics_site_url", "daily_analytics", ["site_url"])
    op.create_index("ix_daily_analytics_date", "daily_analytics", ["date"])
    op.create_index("ix_daily_analytics_user_date", "daily_analytics", ["user_id", "date"])
    op.create_index("ix_daily_analytics_site_date", "daily_analytics", ["site_url", "date"])


def downgrade() -> None:
    """Drop analytics tables."""
    op.drop_table("daily_analytics")
    op.drop_table("page_performances")
    op.drop_table("keyword_rankings")
    op.drop_table("gsc_connections")
