"""Add notification_preferences table

Revision ID: 055
Revises: 054
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'notification_preferences'
        ) THEN
            CREATE TABLE notification_preferences (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                email_generation_completed BOOLEAN NOT NULL DEFAULT true,
                email_generation_failed BOOLEAN NOT NULL DEFAULT true,
                email_usage_80_percent BOOLEAN NOT NULL DEFAULT true,
                email_usage_limit_reached BOOLEAN NOT NULL DEFAULT true,
                email_content_decay BOOLEAN NOT NULL DEFAULT true,
                email_weekly_digest BOOLEAN NOT NULL DEFAULT true,
                email_billing_alerts BOOLEAN NOT NULL DEFAULT true,
                email_product_updates BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_notification_preferences_user_id UNIQUE (user_id)
            );
            CREATE INDEX ix_notification_preferences_user_id ON notification_preferences(user_id);
        END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("notification_preferences")
