"""Email journey infrastructure: events table, user activity tracking, notification preferences.

Revision ID: 060
Revises: 059
"""
from alembic import op
import sqlalchemy as sa

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New table: user_email_journey_events
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'user_email_journey_events'
            ) THEN
                CREATE TABLE user_email_journey_events (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    email_key VARCHAR(100) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
                    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
                    sent_at TIMESTAMP WITH TIME ZONE,
                    cancelled_at TIMESTAMP WITH TIME ZONE,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
                CREATE UNIQUE INDEX uix_journey_user_email_key
                    ON user_email_journey_events(user_id, email_key)
                    WHERE status IN ('scheduled', 'sent');
                CREATE INDEX ix_journey_status_scheduled
                    ON user_email_journey_events(status, scheduled_for);
            END IF;
        END $$;
    """)

    # Add last_active_at to users
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'last_active_at'
            ) THEN
                ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP WITH TIME ZONE;
            END IF;
        END $$;
    """)

    # Add new notification preference columns
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'notification_preferences'
                AND column_name = 'email_onboarding'
            ) THEN
                ALTER TABLE notification_preferences
                    ADD COLUMN email_onboarding BOOLEAN NOT NULL DEFAULT TRUE;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'notification_preferences'
                AND column_name = 'email_conversion_tips'
            ) THEN
                ALTER TABLE notification_preferences
                    ADD COLUMN email_conversion_tips BOOLEAN NOT NULL DEFAULT TRUE;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'notification_preferences'
                AND column_name = 'email_reengagement'
            ) THEN
                ALTER TABLE notification_preferences
                    ADD COLUMN email_reengagement BOOLEAN NOT NULL DEFAULT TRUE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("user_email_journey_events")
    op.drop_column("users", "last_active_at")
    op.drop_column("notification_preferences", "email_onboarding")
    op.drop_column("notification_preferences", "email_conversion_tips")
    op.drop_column("notification_preferences", "email_reengagement")
