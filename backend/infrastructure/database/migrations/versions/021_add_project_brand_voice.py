"""Add brand_voice column to projects table.

The ORM model defined brand_voice but no migration ever created the column,
causing UndefinedColumnError on any query that touches the Project model.

Revision ID: 021
Revises: 020
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("brand_voice", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "brand_voice")
