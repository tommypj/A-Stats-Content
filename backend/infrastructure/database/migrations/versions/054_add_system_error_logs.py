"""Add system_error_logs table for centralized error tracking

Revision ID: 054
Revises: 053
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'system_error_logs') THEN
                CREATE TABLE system_error_logs (
                    id UUID PRIMARY KEY,
                    error_type VARCHAR(100) NOT NULL,
                    error_code VARCHAR(50),
                    severity VARCHAR(20) NOT NULL DEFAULT 'error',
                    title VARCHAR(500) NOT NULL,
                    message TEXT,
                    stack_trace TEXT,
                    service VARCHAR(100),
                    endpoint VARCHAR(500),
                    http_method VARCHAR(10),
                    http_status INTEGER,
                    request_id VARCHAR(100),
                    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                    resource_type VARCHAR(50),
                    resource_id UUID,
                    context JSONB,
                    user_agent TEXT,
                    ip_address VARCHAR(45),
                    occurrence_count INTEGER NOT NULL DEFAULT 1,
                    first_seen_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
                    resolved_at TIMESTAMP WITH TIME ZONE,
                    resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
                    resolution_notes TEXT,
                    error_fingerprint VARCHAR(64),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            END IF;
        END $$;
    """)

    # Indexes for common query patterns
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_system_error_logs_error_type') THEN
                CREATE INDEX ix_system_error_logs_error_type ON system_error_logs (error_type);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_system_error_logs_severity') THEN
                CREATE INDEX ix_system_error_logs_severity ON system_error_logs (severity);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_system_error_logs_service') THEN
                CREATE INDEX ix_system_error_logs_service ON system_error_logs (service);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_system_error_logs_created_at') THEN
                CREATE INDEX ix_system_error_logs_created_at ON system_error_logs (created_at);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_system_error_logs_user_id') THEN
                CREATE INDEX ix_system_error_logs_user_id ON system_error_logs (user_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_system_error_logs_is_resolved') THEN
                CREATE INDEX ix_system_error_logs_is_resolved ON system_error_logs (is_resolved, created_at);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_system_error_logs_fingerprint') THEN
                CREATE INDEX ix_system_error_logs_fingerprint ON system_error_logs (error_fingerprint);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_system_error_logs_http_status') THEN
                CREATE INDEX ix_system_error_logs_http_status ON system_error_logs (http_status);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("system_error_logs")
