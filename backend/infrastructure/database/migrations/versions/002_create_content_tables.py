"""Create content tables (outlines, articles, generated_images)

Revision ID: 002
Revises: 001
Create Date: 2026-02-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create outlines table
    op.create_table(
        "outlines",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("target_audience", sa.String(length=500), nullable=True),
        sa.Column("tone", sa.String(length=50), nullable=False, server_default="professional"),
        sa.Column("sections", postgresql.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("word_count_target", sa.Integer(), nullable=False, server_default="1500"),
        sa.Column("estimated_read_time", sa.Integer(), nullable=True),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column("generation_prompt", sa.Text(), nullable=True),
        sa.Column("generation_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_outlines_user_id", "outlines", ["user_id"])
    op.create_index("ix_outlines_keyword", "outlines", ["keyword"])
    op.create_index("ix_outlines_status", "outlines", ["status"])

    # Create generated_images table (before articles due to FK)
    op.create_table(
        "generated_images",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("article_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("local_path", sa.String(length=500), nullable=True),
        sa.Column("alt_text", sa.String(length=500), nullable=True),
        sa.Column("style", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="completed"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_generated_images_user_id", "generated_images", ["user_id"])
    op.create_index("ix_generated_images_article_id", "generated_images", ["article_id"])

    # Create articles table
    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("outline_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("slug", sa.String(length=500), nullable=True),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("meta_description", sa.String(length=320), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("read_time", sa.Integer(), nullable=True),
        sa.Column("seo_score", sa.Float(), nullable=True),
        sa.Column("seo_analysis", postgresql.JSON(), nullable=True),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column("generation_prompt", sa.Text(), nullable=True),
        sa.Column("generation_error", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_url", sa.String(length=500), nullable=True),
        sa.Column("wordpress_post_id", sa.Integer(), nullable=True),
        sa.Column("featured_image_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outline_id"], ["outlines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["featured_image_id"], ["generated_images.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_articles_user_id", "articles", ["user_id"])
    op.create_index("ix_articles_outline_id", "articles", ["outline_id"])
    op.create_index("ix_articles_keyword", "articles", ["keyword"])
    op.create_index("ix_articles_status", "articles", ["status"])

    # Add article_id FK to generated_images (deferred)
    op.create_foreign_key(
        "fk_generated_images_article_id",
        "generated_images",
        "articles",
        ["article_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_generated_images_article_id", "generated_images", type_="foreignkey")
    op.drop_index("ix_articles_status", table_name="articles")
    op.drop_index("ix_articles_keyword", table_name="articles")
    op.drop_index("ix_articles_outline_id", table_name="articles")
    op.drop_index("ix_articles_user_id", table_name="articles")
    op.drop_table("articles")
    op.drop_index("ix_generated_images_article_id", table_name="generated_images")
    op.drop_index("ix_generated_images_user_id", table_name="generated_images")
    op.drop_table("generated_images")
    op.drop_index("ix_outlines_status", table_name="outlines")
    op.drop_index("ix_outlines_keyword", table_name="outlines")
    op.drop_index("ix_outlines_user_id", table_name="outlines")
    op.drop_table("outlines")
