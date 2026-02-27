"""Add soft-delete to project_invitations table.

PROJ-03: ProjectInvitation was the only model without a deleted_at column,
inconsistent with all other models and required for GDPR compliance.

Revision ID: 029
Revises: 028
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_invitations",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_invitations", "deleted_at")
