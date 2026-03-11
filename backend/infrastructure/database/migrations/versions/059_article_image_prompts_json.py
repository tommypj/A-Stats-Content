"""Convert Article.image_prompt (Text) to image_prompts (JSON array)

Revision ID: 059
Revises: 058
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("image_prompts", JSON, nullable=True))
    op.execute("""
        UPDATE articles
        SET image_prompts = json_build_array(image_prompt)
        WHERE image_prompt IS NOT NULL AND image_prompt != ''
    """)
    op.drop_column("articles", "image_prompt")


def downgrade() -> None:
    op.add_column("articles", sa.Column("image_prompt", sa.Text, nullable=True))
    op.execute("""
        UPDATE articles
        SET image_prompt = image_prompts->>0
        WHERE image_prompts IS NOT NULL
    """)
    op.drop_column("articles", "image_prompts")
