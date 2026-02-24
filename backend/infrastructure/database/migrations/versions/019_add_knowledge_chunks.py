"""Add knowledge_chunks table for storing document text chunks.

Revision ID: 019
Revises: 018
Create Date: 2026-02-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create knowledge_chunks table for local text-based search."""

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_knowledge_chunks_source_id", "knowledge_chunks", ["source_id"])
    op.create_index(
        "ix_knowledge_chunks_source_index",
        "knowledge_chunks",
        ["source_id", "chunk_index"],
    )


def downgrade() -> None:
    """Drop knowledge_chunks table."""
    op.drop_table("knowledge_chunks")
