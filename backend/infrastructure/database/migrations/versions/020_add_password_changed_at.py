"""Add password_changed_at column to users table.

Separates security-event timestamps from the general-purpose updated_at
(which fires on any row modification via onupdate).  Token invalidation
now checks password_changed_at instead of updated_at so that routine
updates (login tracking, usage resets, avatar uploads) no longer
accidentally invalidate active sessions.

Revision ID: 020
Revises: 019
Create Date: 2026-02-24
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
