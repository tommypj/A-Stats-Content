"""
Add social_posts JSON column to articles table.

Stores AI-generated social media post content for Twitter, LinkedIn,
Facebook, and Instagram sharing.

Revision ID: 014
Revises: 013
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "articles",
        sa.Column("social_posts", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("articles", "social_posts")
