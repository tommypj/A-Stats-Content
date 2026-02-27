"""Add keyword research cache table

Revision ID: 034
Revises: 033
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "keyword_research_cache",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seed_keyword_normalized", sa.String(200), nullable=False),
        sa.Column("seed_keyword_original", sa.String(200), nullable=False),
        sa.Column("result_json", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_keyword_research_cache_user_id", "keyword_research_cache", ["user_id"])
    op.create_index("ix_keyword_research_cache_expires_at", "keyword_research_cache", ["expires_at"])
    op.create_index("ix_kw_cache_user_keyword", "keyword_research_cache", ["user_id", "seed_keyword_normalized"])


def downgrade() -> None:
    op.drop_index("ix_kw_cache_user_keyword", table_name="keyword_research_cache")
    op.drop_index("ix_keyword_research_cache_expires_at", table_name="keyword_research_cache")
    op.drop_index("ix_keyword_research_cache_user_id", table_name="keyword_research_cache")
    op.drop_table("keyword_research_cache")
