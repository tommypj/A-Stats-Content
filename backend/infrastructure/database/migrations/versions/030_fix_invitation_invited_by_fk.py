"""Fix ProjectInvitation.invited_by FK: CASCADE → SET NULL.

PROJ-09: Deleting an inviter was cascading to delete the invitation row,
destroying the audit trail. Changed to SET NULL so the invitation record
is preserved even if the inviter account is removed.

Revision ID: 030
Revises: 029
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing FK and re-add with ON DELETE SET NULL
    op.drop_constraint(
        "project_invitations_invited_by_fkey",
        "project_invitations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "project_invitations_invited_by_fkey",
        "project_invitations",
        "users",
        ["invited_by"],
        ["id"],
        ondelete="SET NULL",
    )
    # Make the column nullable so SET NULL can work
    op.alter_column("project_invitations", "invited_by", nullable=True)


def downgrade() -> None:
    op.alter_column("project_invitations", "invited_by", nullable=False)
    op.drop_constraint(
        "project_invitations_invited_by_fkey",
        "project_invitations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "project_invitations_invited_by_fkey",
        "project_invitations",
        "users",
        ["invited_by"],
        ["id"],
        ondelete="CASCADE",
    )
