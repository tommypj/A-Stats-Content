"""Add token_expires_at to client_workspaces

Revision ID: 040
Revises: 039
"""

from alembic import op

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DB-M3: Add portal token expiry column. NULL means token does not expire (legacy rows).
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'client_workspaces'
                  AND column_name = 'token_expires_at'
            ) THEN
                ALTER TABLE client_workspaces
                    ADD COLUMN token_expires_at TIMESTAMPTZ
                    DEFAULT NULL;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE client_workspaces DROP COLUMN IF EXISTS token_expires_at;")
