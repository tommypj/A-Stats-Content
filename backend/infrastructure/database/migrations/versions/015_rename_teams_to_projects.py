"""
Rename teams to projects throughout the database.

Renames tables (teams->projects, team_members->project_members,
team_invitations->project_invitations), all related FK columns, composite
indexes, and migrates wordpress_credentials from users to projects.
Also removes the unique constraint on gsc_connections.user_id so one user
can hold multiple GSC connections (one per project).

Revision ID: 015
Revises: 014
Create Date: 2026-02-22
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

# revision identifiers, used by Alembic.
revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Rename all team-related objects to project-related objects."""

    # ------------------------------------------------------------------
    # 1. Rename the three core tables
    # ------------------------------------------------------------------
    op.rename_table("teams", "projects")
    op.rename_table("team_members", "project_members")
    op.rename_table("team_invitations", "project_invitations")

    # ------------------------------------------------------------------
    # 2. Rename FK columns on content / user tables
    #    (these still point at the now-renamed "projects" table)
    # ------------------------------------------------------------------

    # users.current_team_id -> current_project_id
    # Drop the old FK constraint first, then rename, then recreate.
    op.drop_constraint("fk_users_current_team_id", "users", type_="foreignkey")
    op.drop_index("ix_users_current_team_id", table_name="users")
    op.alter_column(
        "users",
        "current_team_id",
        new_column_name="current_project_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_users_current_project_id",
        "users",
        "projects",
        ["current_project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_current_project_id", "users", ["current_project_id"])

    # articles.team_id -> project_id
    op.drop_constraint("fk_articles_team_id", "articles", type_="foreignkey")
    op.drop_index("ix_articles_team_id", table_name="articles")
    op.alter_column(
        "articles",
        "team_id",
        new_column_name="project_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_articles_project_id",
        "articles",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_articles_project_id", "articles", ["project_id"])

    # outlines.team_id -> project_id
    op.drop_constraint("fk_outlines_team_id", "outlines", type_="foreignkey")
    op.drop_index("ix_outlines_team_id", table_name="outlines")
    op.alter_column(
        "outlines",
        "team_id",
        new_column_name="project_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_outlines_project_id",
        "outlines",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_outlines_project_id", "outlines", ["project_id"])

    # generated_images.team_id -> project_id
    op.drop_constraint("fk_generated_images_team_id", "generated_images", type_="foreignkey")
    op.drop_index("ix_generated_images_team_id", table_name="generated_images")
    op.alter_column(
        "generated_images",
        "team_id",
        new_column_name="project_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_generated_images_project_id",
        "generated_images",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_generated_images_project_id", "generated_images", ["project_id"])

    # gsc_connections.team_id -> project_id
    op.drop_constraint("fk_gsc_connections_team_id", "gsc_connections", type_="foreignkey")
    op.drop_index("ix_gsc_connections_team_id", table_name="gsc_connections")
    op.alter_column(
        "gsc_connections",
        "team_id",
        new_column_name="project_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_gsc_connections_project_id",
        "gsc_connections",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_gsc_connections_project_id", "gsc_connections", ["project_id"])

    # social_accounts.team_id -> project_id
    op.drop_constraint("fk_social_accounts_team_id", "social_accounts", type_="foreignkey")
    op.drop_index("ix_social_accounts_team_id", table_name="social_accounts")
    op.alter_column(
        "social_accounts",
        "team_id",
        new_column_name="project_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_social_accounts_project_id",
        "social_accounts",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_social_accounts_project_id", "social_accounts", ["project_id"])

    # scheduled_posts.team_id -> project_id
    op.drop_constraint("fk_scheduled_posts_team_id", "scheduled_posts", type_="foreignkey")
    op.drop_index("ix_scheduled_posts_team_id", table_name="scheduled_posts")
    op.alter_column(
        "scheduled_posts",
        "team_id",
        new_column_name="project_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_scheduled_posts_project_id",
        "scheduled_posts",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_scheduled_posts_project_id", "scheduled_posts", ["project_id"])

    # knowledge_sources.team_id -> project_id
    op.drop_constraint("fk_knowledge_sources_team_id", "knowledge_sources", type_="foreignkey")
    op.drop_index("ix_knowledge_sources_team_id", table_name="knowledge_sources")
    op.alter_column(
        "knowledge_sources",
        "team_id",
        new_column_name="project_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_knowledge_sources_project_id",
        "knowledge_sources",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_knowledge_sources_project_id", "knowledge_sources", ["project_id"])

    # ------------------------------------------------------------------
    # 3. Rename columns inside the newly-renamed junction tables
    #    (project_members.team_id -> project_id,
    #     project_invitations.team_id -> project_id)
    # ------------------------------------------------------------------

    # project_members (formerly team_members) — drop old FK, rename, recreate
    op.drop_constraint("team_members_team_id_fkey", "project_members", type_="foreignkey")
    op.drop_index("ix_team_members_team_id", table_name="project_members")
    op.alter_column(
        "project_members",
        "team_id",
        new_column_name="project_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=False,
    )
    op.create_foreign_key(
        "project_members_project_id_fkey",
        "project_members",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])

    # project_invitations (formerly team_invitations) — drop old FK, rename, recreate
    op.drop_constraint("team_invitations_team_id_fkey", "project_invitations", type_="foreignkey")
    op.drop_index("ix_team_invitations_team_id", table_name="project_invitations")
    op.alter_column(
        "project_invitations",
        "team_id",
        new_column_name="project_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=False,
    )
    op.create_foreign_key(
        "project_invitations_project_id_fkey",
        "project_invitations",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_project_invitations_project_id", "project_invitations", ["project_id"])

    # ------------------------------------------------------------------
    # 4. Rename composite / multi-column indexes via raw SQL
    # ------------------------------------------------------------------
    op.execute("ALTER INDEX ix_teams_subscription RENAME TO ix_projects_subscription")
    op.execute("ALTER INDEX ix_team_members_team_user RENAME TO ix_project_members_project_user")
    op.execute("ALTER INDEX ix_team_invitations_status RENAME TO ix_project_invitations_status")
    op.execute(
        "ALTER INDEX ix_team_invitations_expires_at RENAME TO ix_project_invitations_expires_at"
    )
    # Rename the functional index on users.current_team (created in migration 010 as
    # ix_users_current_team_id; the model declares it as ix_users_current_team — we
    # already dropped/recreated it above as ix_users_current_project_id, so here we
    # only rename the model-level index that may exist under the shorter name).
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_users_current_team') "
        "THEN ALTER INDEX ix_users_current_team RENAME TO ix_users_current_project; "
        "END IF; END $$"
    )

    # ------------------------------------------------------------------
    # 5. Add wordpress_credentials column to projects table
    # ------------------------------------------------------------------
    op.add_column(
        "projects",
        sa.Column("wordpress_credentials", JSON(), nullable=True),
    )

    # ------------------------------------------------------------------
    # 6. Migrate WP credentials from users -> projects
    # ------------------------------------------------------------------
    op.execute(
        """
        UPDATE projects
        SET    wordpress_credentials = u.wordpress_credentials
        FROM   users u
        WHERE  u.current_project_id = projects.id
          AND  u.wordpress_credentials IS NOT NULL
        """
    )

    # ------------------------------------------------------------------
    # 7. Populate gsc_connections.project_id from users.current_project_id
    # ------------------------------------------------------------------
    op.execute(
        """
        UPDATE gsc_connections
        SET    project_id = u.current_project_id
        FROM   users u
        WHERE  u.id = gsc_connections.user_id
          AND  u.current_project_id IS NOT NULL
          AND  gsc_connections.project_id IS NULL
        """
    )

    # ------------------------------------------------------------------
    # 8. Drop wordpress_credentials from users
    # ------------------------------------------------------------------
    op.drop_column("users", "wordpress_credentials")

    # ------------------------------------------------------------------
    # 9. Drop the unique constraint on gsc_connections.user_id so that
    #    one user can have multiple GSC connections (one per project).
    # ------------------------------------------------------------------
    op.drop_constraint("uq_gsc_connection_user", "gsc_connections", type_="unique")


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Reverse all team->project renames and data migrations."""

    # ------------------------------------------------------------------
    # 9 (reverse). Restore the unique constraint on gsc_connections.user_id
    # ------------------------------------------------------------------
    op.create_unique_constraint("uq_gsc_connection_user", "gsc_connections", ["user_id"])

    # ------------------------------------------------------------------
    # 8 (reverse). Re-add wordpress_credentials to users
    # ------------------------------------------------------------------
    op.add_column(
        "users",
        sa.Column("wordpress_credentials", JSON(), nullable=True),
    )

    # ------------------------------------------------------------------
    # 7 (reverse). No rollback needed for the gsc project_id population
    #              (project_id column is reverted with the column rename below).
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 6 (reverse). Migrate WP credentials back from projects -> users
    #              (best-effort: restore to the project owner)
    # ------------------------------------------------------------------
    op.execute(
        """
        UPDATE users
        SET    wordpress_credentials = p.wordpress_credentials
        FROM   projects p
        WHERE  users.current_project_id = p.id
          AND  p.wordpress_credentials IS NOT NULL
        """
    )

    # ------------------------------------------------------------------
    # 5 (reverse). Drop wordpress_credentials from projects
    # ------------------------------------------------------------------
    op.drop_column("projects", "wordpress_credentials")

    # ------------------------------------------------------------------
    # 4 (reverse). Rename composite indexes back via raw SQL
    # ------------------------------------------------------------------
    op.execute("ALTER INDEX ix_projects_subscription RENAME TO ix_teams_subscription")
    op.execute("ALTER INDEX ix_project_members_project_user RENAME TO ix_team_members_team_user")
    op.execute("ALTER INDEX ix_project_invitations_status RENAME TO ix_team_invitations_status")
    op.execute(
        "ALTER INDEX ix_project_invitations_expires_at RENAME TO ix_team_invitations_expires_at"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_users_current_project') "
        "THEN ALTER INDEX ix_users_current_project RENAME TO ix_users_current_team; "
        "END IF; END $$"
    )

    # ------------------------------------------------------------------
    # 1 (reverse). Rename tables back FIRST so that FK constraints
    #              referencing "teams" can find the table.
    # ------------------------------------------------------------------
    op.rename_table("project_invitations", "team_invitations")
    op.rename_table("project_members", "team_members")
    op.rename_table("projects", "teams")

    # ------------------------------------------------------------------
    # 3 (reverse). Rename columns back inside junction tables
    #              (tables are already renamed back above)
    # ------------------------------------------------------------------

    # team_invitations.project_id -> team_id
    op.drop_constraint(
        "project_invitations_project_id_fkey", "team_invitations", type_="foreignkey"
    )
    op.drop_index("ix_project_invitations_project_id", table_name="team_invitations")
    op.alter_column(
        "team_invitations",
        "project_id",
        new_column_name="team_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=False,
    )
    op.create_foreign_key(
        "team_invitations_team_id_fkey",
        "team_invitations",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_team_invitations_team_id", "team_invitations", ["team_id"])

    # team_members.project_id -> team_id
    op.drop_constraint("project_members_project_id_fkey", "team_members", type_="foreignkey")
    op.drop_index("ix_project_members_project_id", table_name="team_members")
    op.alter_column(
        "team_members",
        "project_id",
        new_column_name="team_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=False,
    )
    op.create_foreign_key(
        "team_members_team_id_fkey",
        "team_members",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"])

    # ------------------------------------------------------------------
    # 2 (reverse). Rename FK columns back on content / user tables
    # ------------------------------------------------------------------

    # knowledge_sources.project_id -> team_id
    op.drop_constraint("fk_knowledge_sources_project_id", "knowledge_sources", type_="foreignkey")
    op.drop_index("ix_knowledge_sources_project_id", table_name="knowledge_sources")
    op.alter_column(
        "knowledge_sources",
        "project_id",
        new_column_name="team_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_knowledge_sources_team_id",
        "knowledge_sources",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_knowledge_sources_team_id", "knowledge_sources", ["team_id"])

    # scheduled_posts.project_id -> team_id
    op.drop_constraint("fk_scheduled_posts_project_id", "scheduled_posts", type_="foreignkey")
    op.drop_index("ix_scheduled_posts_project_id", table_name="scheduled_posts")
    op.alter_column(
        "scheduled_posts",
        "project_id",
        new_column_name="team_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_scheduled_posts_team_id",
        "scheduled_posts",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_scheduled_posts_team_id", "scheduled_posts", ["team_id"])

    # social_accounts.project_id -> team_id
    op.drop_constraint("fk_social_accounts_project_id", "social_accounts", type_="foreignkey")
    op.drop_index("ix_social_accounts_project_id", table_name="social_accounts")
    op.alter_column(
        "social_accounts",
        "project_id",
        new_column_name="team_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_social_accounts_team_id",
        "social_accounts",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_social_accounts_team_id", "social_accounts", ["team_id"])

    # gsc_connections.project_id -> team_id
    op.drop_constraint("fk_gsc_connections_project_id", "gsc_connections", type_="foreignkey")
    op.drop_index("ix_gsc_connections_project_id", table_name="gsc_connections")
    op.alter_column(
        "gsc_connections",
        "project_id",
        new_column_name="team_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_gsc_connections_team_id",
        "gsc_connections",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_gsc_connections_team_id", "gsc_connections", ["team_id"])

    # generated_images.project_id -> team_id
    op.drop_constraint("fk_generated_images_project_id", "generated_images", type_="foreignkey")
    op.drop_index("ix_generated_images_project_id", table_name="generated_images")
    op.alter_column(
        "generated_images",
        "project_id",
        new_column_name="team_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_generated_images_team_id",
        "generated_images",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_generated_images_team_id", "generated_images", ["team_id"])

    # outlines.project_id -> team_id
    op.drop_constraint("fk_outlines_project_id", "outlines", type_="foreignkey")
    op.drop_index("ix_outlines_project_id", table_name="outlines")
    op.alter_column(
        "outlines",
        "project_id",
        new_column_name="team_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_outlines_team_id",
        "outlines",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_outlines_team_id", "outlines", ["team_id"])

    # articles.project_id -> team_id
    op.drop_constraint("fk_articles_project_id", "articles", type_="foreignkey")
    op.drop_index("ix_articles_project_id", table_name="articles")
    op.alter_column(
        "articles",
        "project_id",
        new_column_name="team_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_articles_team_id",
        "articles",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_articles_team_id", "articles", ["team_id"])

    # users.current_project_id -> current_team_id
    op.drop_constraint("fk_users_current_project_id", "users", type_="foreignkey")
    op.drop_index("ix_users_current_project_id", table_name="users")
    op.alter_column(
        "users",
        "current_project_id",
        new_column_name="current_team_id",
        existing_type=UUID(as_uuid=False),
        existing_nullable=True,
    )
    op.create_foreign_key(
        "fk_users_current_team_id",
        "users",
        "teams",
        ["current_team_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_current_team_id", "users", ["current_team_id"])
