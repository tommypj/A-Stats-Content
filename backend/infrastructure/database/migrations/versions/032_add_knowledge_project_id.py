"""Add project_id to knowledge_sources table (corrective migration).

KV-07: Migration 006 created knowledge_sources without the project_id column
that the KnowledgeSource model defines. This corrective migration adds it.

Revision ID: 032
Revises: 031
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add project_id column (nullable — existing rows have no project association)
    op.add_column(
        "knowledge_sources",
        sa.Column(
            "project_id",
            # DB-01: NOTE — FK should use UUID(as_uuid=False) for consistency with other FK columns
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_knowledge_sources_project_id",
        "knowledge_sources",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_sources_project_id", table_name="knowledge_sources")
    op.drop_column("knowledge_sources", "project_id")
