"""Email template overrides table for admin-edited email templates.

Revision ID: 061
Revises: 060
"""
from alembic import op
import sqlalchemy as sa

revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'email_template_overrides'
            ) THEN
                CREATE TABLE email_template_overrides (
                    id UUID PRIMARY KEY,
                    email_key VARCHAR(100) NOT NULL,
                    subject VARCHAR(500),
                    html TEXT,
                    updated_by_admin_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
                CREATE UNIQUE INDEX uix_email_template_overrides_email_key
                    ON email_template_overrides(email_key);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("email_template_overrides")
