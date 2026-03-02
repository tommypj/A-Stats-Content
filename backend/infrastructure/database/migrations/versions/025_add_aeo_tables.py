"""Add AEO (Answer Engine Optimization) scoring tables.

Tracks AI-readability scores and citations for articles.

Revision ID: 025
Revises: 024
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aeo_scores",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "article_id",
            UUID(as_uuid=False),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=False),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("aeo_score", sa.Integer, nullable=False),  # 0-100
        sa.Column(
            "score_breakdown", sa.JSON, nullable=True
        ),  # {structure_score, faq_score, entity_score, conciseness_score, schema_score, citation_readiness}
        sa.Column("suggestions", sa.JSON, nullable=True),  # array of improvement suggestions
        sa.Column("previous_score", sa.Integer, nullable=True),
        sa.Column(
            "scored_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_aeo_scores_article_scored", "aeo_scores", ["article_id", "scored_at"])
    op.create_index("ix_aeo_scores_user_score", "aeo_scores", ["user_id", "aeo_score"])

    op.create_table(
        "aeo_citations",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "article_id",
            UUID(as_uuid=False),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=False),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "source", sa.String(50), nullable=False
        ),  # chatgpt, perplexity, gemini, bing_copilot
        sa.Column("query", sa.String(1000), nullable=True),
        sa.Column("citation_url", sa.String(2000), nullable=True),
        sa.Column("citation_snippet", sa.Text, nullable=True),
        sa.Column(
            "detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_aeo_citations_article_source", "aeo_citations", ["article_id", "source"])


def downgrade() -> None:
    op.drop_index("ix_aeo_citations_article_source")
    op.drop_table("aeo_citations")
    op.drop_index("ix_aeo_scores_user_score")
    op.drop_index("ix_aeo_scores_article_scored")
    op.drop_table("aeo_scores")
