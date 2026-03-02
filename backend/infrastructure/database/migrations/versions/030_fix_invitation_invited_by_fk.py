"""Fix ProjectInvitation.invited_by FK: CASCADE → SET NULL.

PROJ-09: Deleting an inviter was cascading to delete the invitation row,
destroying the audit trail. Changed to SET NULL so the invitation record
is preserved even if the inviter account is removed.

Revision ID: 030
Revises: 029
Create Date: 2026-02-27
"""

from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing FK on invited_by using a DO block so it succeeds regardless
    # of the constraint's actual name in the target database.
    op.execute("""
        DO $$
        DECLARE
            v_constraint_name text;
        BEGIN
            SELECT c.conname INTO v_constraint_name
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
            WHERE t.relname = 'project_invitations'
              AND c.contype = 'f'
              AND a.attname = 'invited_by'
            LIMIT 1;

            IF v_constraint_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE project_invitations DROP CONSTRAINT '
                    || quote_ident(v_constraint_name);
            END IF;
        END $$;
    """)
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
