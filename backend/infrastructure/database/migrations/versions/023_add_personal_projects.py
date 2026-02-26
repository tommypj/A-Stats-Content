"""Add personal projects for all users.

- Adds is_personal boolean column to projects table.
- Creates a "Personal Workspace" project for every existing non-deleted user.
- Creates ProjectMember (owner) rows for each personal project.
- Sets current_project_id for users who have it NULL.
- Migrates orphaned content (project_id IS NULL) to the personal project.

Revision ID: 023
Revises: 022
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add is_personal column
    op.add_column(
        "projects",
        sa.Column("is_personal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # 2. Create personal projects for all existing non-deleted users
    op.execute("""
        INSERT INTO projects (id, name, slug, owner_id, is_personal,
                              subscription_tier, subscription_status, subscription_expires,
                              articles_generated_this_month, outlines_generated_this_month,
                              images_generated_this_month, usage_reset_date,
                              max_members, created_at, updated_at)
        SELECT
            gen_random_uuid()::text,
            'Personal Workspace',
            'personal-' || LEFT(u.id::text, 8),
            u.id,
            true,
            COALESCE(u.subscription_tier, 'free'),
            COALESCE(u.subscription_status, 'active'),
            u.subscription_expires,
            COALESCE(u.articles_generated_this_month, 0),
            COALESCE(u.outlines_generated_this_month, 0),
            COALESCE(u.images_generated_this_month, 0),
            u.usage_reset_date,
            1,
            NOW(),
            NOW()
        FROM users u
        WHERE u.deleted_at IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM projects p
              WHERE p.owner_id = u.id AND p.is_personal = true
          )
    """)

    # 3. Create ProjectMember (owner) rows for each personal project
    op.execute("""
        INSERT INTO project_members (id, project_id, user_id, role, joined_at, created_at, updated_at)
        SELECT
            gen_random_uuid()::text,
            p.id,
            p.owner_id,
            'owner',
            NOW(),
            NOW(),
            NOW()
        FROM projects p
        WHERE p.is_personal = true
          AND NOT EXISTS (
              SELECT 1 FROM project_members pm
              WHERE pm.project_id = p.id AND pm.user_id = p.owner_id
          )
    """)

    # 4. Set current_project_id for users who have it NULL
    op.execute("""
        UPDATE users u
        SET current_project_id = p.id
        FROM projects p
        WHERE p.owner_id = u.id
          AND p.is_personal = true
          AND p.deleted_at IS NULL
          AND u.current_project_id IS NULL
    """)

    # 5. Migrate orphaned content to personal projects
    # Articles
    op.execute("""
        UPDATE articles a
        SET project_id = p.id
        FROM projects p
        WHERE p.owner_id = a.user_id
          AND p.is_personal = true
          AND p.deleted_at IS NULL
          AND a.project_id IS NULL
    """)

    # Outlines
    op.execute("""
        UPDATE outlines o
        SET project_id = p.id
        FROM projects p
        WHERE p.owner_id = o.user_id
          AND p.is_personal = true
          AND p.deleted_at IS NULL
          AND o.project_id IS NULL
    """)

    # Generated images
    op.execute("""
        UPDATE generated_images gi
        SET project_id = p.id
        FROM projects p
        WHERE p.owner_id = gi.user_id
          AND p.is_personal = true
          AND p.deleted_at IS NULL
          AND gi.project_id IS NULL
    """)

    # Knowledge sources
    op.execute("""
        UPDATE knowledge_sources ks
        SET project_id = p.id
        FROM projects p
        WHERE p.owner_id = ks.user_id
          AND p.is_personal = true
          AND p.deleted_at IS NULL
          AND ks.project_id IS NULL
    """)

    # Social accounts
    op.execute("""
        UPDATE social_accounts sa
        SET project_id = p.id
        FROM projects p
        WHERE p.owner_id = sa.user_id
          AND p.is_personal = true
          AND p.deleted_at IS NULL
          AND sa.project_id IS NULL
    """)

    # Scheduled posts
    op.execute("""
        UPDATE scheduled_posts sp
        SET project_id = p.id
        FROM projects p
        WHERE p.owner_id = sp.user_id
          AND p.is_personal = true
          AND p.deleted_at IS NULL
          AND sp.project_id IS NULL
    """)

    # Generation logs
    op.execute("""
        UPDATE generation_logs gl
        SET project_id = p.id
        FROM projects p
        WHERE p.owner_id = gl.user_id
          AND p.is_personal = true
          AND p.deleted_at IS NULL
          AND gl.project_id IS NULL
    """)

    # GSC connections
    op.execute("""
        UPDATE gsc_connections gc
        SET project_id = p.id
        FROM projects p
        WHERE p.owner_id = gc.user_id
          AND p.is_personal = true
          AND p.deleted_at IS NULL
          AND gc.project_id IS NULL
    """)


def downgrade() -> None:
    # Remove is_personal column (personal projects remain but lose their flag)
    op.drop_column("projects", "is_personal")
