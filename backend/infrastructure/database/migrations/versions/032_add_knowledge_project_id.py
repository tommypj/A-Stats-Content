"""Add project_id to knowledge_sources table (corrective migration).

KV-07: Migration 006 created knowledge_sources without the project_id column
that the KnowledgeSource model defines. This corrective migration adds it.

Revision ID: 032
Revises: 031
Create Date: 2026-02-27
"""

from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add project_id column only if it doesn't already exist (idempotent)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'knowledge_sources'
                  AND column_name = 'project_id'
            ) THEN
                ALTER TABLE knowledge_sources
                    ADD COLUMN project_id VARCHAR(36)
                    REFERENCES projects(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)
    # Create index only if it doesn't already exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'knowledge_sources'
                  AND indexname = 'ix_knowledge_sources_project_id'
            ) THEN
                CREATE INDEX ix_knowledge_sources_project_id
                    ON knowledge_sources (project_id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_index("ix_knowledge_sources_project_id", table_name="knowledge_sources")
    op.drop_column("knowledge_sources", "project_id")
