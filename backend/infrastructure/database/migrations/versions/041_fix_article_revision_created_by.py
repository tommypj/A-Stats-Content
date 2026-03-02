"""Fix ArticleRevision.created_by: add ondelete SET NULL and index

Revision ID: 041
Revises: 040
"""
from alembic import op

revision = '041'
down_revision = '040'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # LOW-06: Drop existing FK (if any), re-add with ON DELETE SET NULL,
    # make column nullable, and add an index for lookup by author.
    op.execute("""
        DO $$
        BEGIN
            -- Drop existing FK constraint if present (any name)
            IF EXISTS (
                SELECT 1
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu
                  ON tc.constraint_name = ccu.constraint_name
                 AND tc.table_schema = ccu.table_schema
                WHERE tc.table_name = 'article_revisions'
                  AND ccu.column_name = 'created_by'
                  AND tc.constraint_type = 'FOREIGN KEY'
            ) THEN
                ALTER TABLE article_revisions
                    DROP CONSTRAINT IF EXISTS article_revisions_created_by_fkey;
            END IF;

            -- Re-add FK with ON DELETE SET NULL
            ALTER TABLE article_revisions
                ADD CONSTRAINT article_revisions_created_by_fkey
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;

            -- Make column nullable so SET NULL can work
            ALTER TABLE article_revisions
                ALTER COLUMN created_by DROP NOT NULL;

            -- Add index for lookups by created_by
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'ix_article_revisions_created_by'
            ) THEN
                CREATE INDEX ix_article_revisions_created_by
                    ON article_revisions(created_by);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_article_revisions_created_by;")
    # Note: downgrade does not restore the NOT NULL constraint or the old FK
    # to avoid data loss if any rows already have NULL in created_by.
