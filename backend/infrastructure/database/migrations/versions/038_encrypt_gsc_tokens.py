"""Rename GSC token columns to encrypted naming convention

DB-H1: gsc_connections.access_token and gsc_connections.refresh_token are
plain-text column names that do not signal their encrypted-at-rest nature.
This migration renames them to access_token_encrypted / refresh_token_encrypted
to match the SocialAccount convention and make it clear the values are Fernet-
encrypted (via core.security.encryption.encrypt_credential).

The application layer (analytics.py) and ORM model (analytics.py GSCConnection)
have already been updated to use the new column names before this migration runs.

Revision ID: 038
Revises: 037
Create Date: 2026-03-02
"""

from alembic import op

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'gsc_connections'
                  AND column_name = 'access_token'
            ) THEN
                ALTER TABLE gsc_connections
                    RENAME COLUMN access_token TO access_token_encrypted;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'gsc_connections'
                  AND column_name = 'refresh_token'
            ) THEN
                ALTER TABLE gsc_connections
                    RENAME COLUMN refresh_token TO refresh_token_encrypted;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'gsc_connections'
                  AND column_name = 'access_token_encrypted'
            ) THEN
                ALTER TABLE gsc_connections
                    RENAME COLUMN access_token_encrypted TO access_token;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'gsc_connections'
                  AND column_name = 'refresh_token_encrypted'
            ) THEN
                ALTER TABLE gsc_connections
                    RENAME COLUMN refresh_token_encrypted TO refresh_token;
            END IF;
        END $$;
    """)
