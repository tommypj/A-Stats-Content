"""Add wordpress_credentials to users

Revision ID: 003
Revises: 002
Create Date: 2026-02-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add wordpress_credentials JSON column to users table."""
    op.add_column(
        "users",
        sa.Column("wordpress_credentials", postgresql.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Remove wordpress_credentials column from users table."""
    op.drop_column("users", "wordpress_credentials")
