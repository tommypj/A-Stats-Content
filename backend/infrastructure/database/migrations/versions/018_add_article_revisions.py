"""Add article_revisions table for version history.

Revision ID: 018
Revises: 017
Create Date: 2026-02-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "article_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("content_html", sa.Text, nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("meta_description", sa.Text, nullable=True),
        sa.Column("word_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("revision_type", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Index for fast per-article revision lookups ordered by time
    op.create_index(
        "ix_article_revisions_article_id",
        "article_revisions",
        ["article_id"],
    )
    op.create_index(
        "ix_article_revisions_article_created",
        "article_revisions",
        ["article_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_article_revisions_article_created", table_name="article_revisions")
    op.drop_index("ix_article_revisions_article_id", table_name="article_revisions")
    op.drop_table("article_revisions")
