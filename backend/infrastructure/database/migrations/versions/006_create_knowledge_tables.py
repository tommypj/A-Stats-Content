"""Create knowledge vault tables

Revision ID: 006
Revises: 005
Create Date: 2026-02-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create knowledge vault tables for RAG with ChromaDB."""

    # Create knowledge_sources table
    op.create_table(
        "knowledge_sources",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        # Source information
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_url", sa.String(1000), nullable=True),
        # Processing status
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Metadata
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSON(), nullable=True),
        # Processing timestamps
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        # Standard timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Foreign keys
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # Create indexes for knowledge_sources
    op.create_index("ix_knowledge_sources_user_id", "knowledge_sources", ["user_id"])
    op.create_index("ix_knowledge_sources_status", "knowledge_sources", ["status"])
    op.create_index("ix_knowledge_sources_file_type", "knowledge_sources", ["file_type"])
    op.create_index(
        "ix_knowledge_sources_user_status", "knowledge_sources", ["user_id", "status"]
    )
    op.create_index(
        "ix_knowledge_sources_user_created",
        "knowledge_sources",
        ["user_id", "created_at"],
    )

    # Create knowledge_queries table
    op.create_table(
        "knowledge_queries",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        # Query data
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("sources_used", postgresql.JSON(), nullable=True),
        # Performance metrics
        sa.Column("query_time_ms", sa.Integer(), nullable=False),
        sa.Column("chunks_retrieved", sa.Integer(), nullable=False),
        # Success tracking
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Standard timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Foreign keys
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # Create indexes for knowledge_queries
    op.create_index("ix_knowledge_queries_user_id", "knowledge_queries", ["user_id"])
    op.create_index(
        "ix_knowledge_queries_user_created",
        "knowledge_queries",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    """Drop knowledge vault tables."""
    op.drop_table("knowledge_queries")
    op.drop_table("knowledge_sources")
