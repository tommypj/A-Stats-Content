"""
Add image_prompt column to articles table.

Pre-generated image prompts based on article content for zero-latency
auto-fill in the image generation UI.

Revision ID: 013
Revises: 012
Create Date: 2026-02-21
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "articles",
        sa.Column("image_prompt", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("articles", "image_prompt")
