"""Placeholder migration to fill gap in revision chain.

Migration 009 was never created in the original history. This placeholder
exists solely to ensure `alembic check` can traverse the full revision chain
without errors. No schema changes are performed.

Revision ID: 009
Revises: 008
Create Date: 2026-02-27
"""

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op placeholder
    pass


def downgrade() -> None:
    # No-op placeholder
    pass
