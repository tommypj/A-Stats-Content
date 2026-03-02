"""
Add team ownership to content tables.

Revision ID: 011
Revises: 010_create_team_tables
Create Date: 2026-02-20
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010_create_team_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add team_id columns to content tables for multi-tenancy support.

    Tables updated:
    - articles
    - outlines
    - generated_images
    - social_accounts
    - scheduled_posts
    - knowledge_sources
    - gsc_connections

    All team_id columns are nullable to support both personal and team content.
    Cascade delete ensures content is removed when team is deleted.
    """

    # Add team_id to articles
    op.add_column(
        "articles",
        sa.Column(
            "team_id",
            UUID(as_uuid=False),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_articles_team_id",
        "articles",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_articles_team_id", "articles", ["team_id"])

    # Add team_id to outlines
    op.add_column(
        "outlines",
        sa.Column(
            "team_id",
            UUID(as_uuid=False),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_outlines_team_id",
        "outlines",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_outlines_team_id", "outlines", ["team_id"])

    # Add team_id to generated_images
    op.add_column(
        "generated_images",
        sa.Column(
            "team_id",
            UUID(as_uuid=False),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_generated_images_team_id",
        "generated_images",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_generated_images_team_id", "generated_images", ["team_id"])

    # Add team_id to social_accounts
    op.add_column(
        "social_accounts",
        sa.Column(
            "team_id",
            UUID(as_uuid=False),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_social_accounts_team_id",
        "social_accounts",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_social_accounts_team_id", "social_accounts", ["team_id"])

    # Add team_id to scheduled_posts
    op.add_column(
        "scheduled_posts",
        sa.Column(
            "team_id",
            UUID(as_uuid=False),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_scheduled_posts_team_id",
        "scheduled_posts",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_scheduled_posts_team_id", "scheduled_posts", ["team_id"])

    # Add team_id to knowledge_sources
    op.add_column(
        "knowledge_sources",
        sa.Column(
            "team_id",
            UUID(as_uuid=False),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_knowledge_sources_team_id",
        "knowledge_sources",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_knowledge_sources_team_id", "knowledge_sources", ["team_id"])

    # Add team_id to gsc_connections
    op.add_column(
        "gsc_connections",
        sa.Column(
            "team_id",
            UUID(as_uuid=False),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_gsc_connections_team_id",
        "gsc_connections",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_gsc_connections_team_id", "gsc_connections", ["team_id"])


def downgrade() -> None:
    """
    Remove team_id columns from all content tables.
    """

    # Remove from gsc_connections
    op.drop_index("ix_gsc_connections_team_id", "gsc_connections")
    op.drop_constraint("fk_gsc_connections_team_id", "gsc_connections", type_="foreignkey")
    op.drop_column("gsc_connections", "team_id")

    # Remove from knowledge_sources
    op.drop_index("ix_knowledge_sources_team_id", "knowledge_sources")
    op.drop_constraint("fk_knowledge_sources_team_id", "knowledge_sources", type_="foreignkey")
    op.drop_column("knowledge_sources", "team_id")

    # Remove from scheduled_posts
    op.drop_index("ix_scheduled_posts_team_id", "scheduled_posts")
    op.drop_constraint("fk_scheduled_posts_team_id", "scheduled_posts", type_="foreignkey")
    op.drop_column("scheduled_posts", "team_id")

    # Remove from social_accounts
    op.drop_index("ix_social_accounts_team_id", "social_accounts")
    op.drop_constraint("fk_social_accounts_team_id", "social_accounts", type_="foreignkey")
    op.drop_column("social_accounts", "team_id")

    # Remove from generated_images
    op.drop_index("ix_generated_images_team_id", "generated_images")
    op.drop_constraint("fk_generated_images_team_id", "generated_images", type_="foreignkey")
    op.drop_column("generated_images", "team_id")

    # Remove from outlines
    op.drop_index("ix_outlines_team_id", "outlines")
    op.drop_constraint("fk_outlines_team_id", "outlines", type_="foreignkey")
    op.drop_column("outlines", "team_id")

    # Remove from articles
    op.drop_index("ix_articles_team_id", "articles")
    op.drop_constraint("fk_articles_team_id", "articles", type_="foreignkey")
    op.drop_column("articles", "team_id")
