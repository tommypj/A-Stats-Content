"""Add refund_count to users and refund_blocked_emails table

Revision ID: 056
Revises: 055
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add refund_count to users
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'refund_count'
        ) THEN
            ALTER TABLE users ADD COLUMN refund_count INTEGER NOT NULL DEFAULT 0;
        END IF;
        END $$;
    """)

    # Create refund_blocked_emails table
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'refund_blocked_emails'
        ) THEN
            CREATE TABLE refund_blocked_emails (
                id UUID PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                reason VARCHAR(500),
                blocked_by UUID REFERENCES users(id),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_refund_blocked_email UNIQUE (email)
            );
            CREATE INDEX idx_refund_blocked_email ON refund_blocked_emails (LOWER(email));
        END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS refund_blocked_emails;")
    op.execute("""
        DO $$ BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'refund_count'
        ) THEN
            ALTER TABLE users DROP COLUMN refund_count;
        END IF;
        END $$;
    """)
