"""Add soft delete columns to articles, outlines, and knowledge sources.

Revision ID: 033
Revises: 032
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_articles_deleted_at", "articles", ["deleted_at"])

    op.add_column("outlines", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_outlines_deleted_at", "outlines", ["deleted_at"])

    op.add_column("knowledge_sources", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_knowledge_sources_deleted_at", "knowledge_sources", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_sources_deleted_at", table_name="knowledge_sources")
    op.drop_column("knowledge_sources", "deleted_at")

    op.drop_index("ix_outlines_deleted_at", table_name="outlines")
    op.drop_column("outlines", "deleted_at")

    op.drop_index("ix_articles_deleted_at", table_name="articles")
    op.drop_column("articles", "deleted_at")
