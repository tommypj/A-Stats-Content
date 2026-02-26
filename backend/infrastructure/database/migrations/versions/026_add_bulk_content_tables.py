"""Add bulk content generation tables.

Content templates, bulk jobs, and bulk job items for programmatic SEO workflows.

Revision ID: 026
Revises: 025
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_templates",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("template_config", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "bulk_jobs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("job_type", sa.String(50), nullable=False),  # outline_generation, article_generation, wordpress_publish
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),  # pending, processing, completed, partially_failed, failed, cancelled
        sa.Column("total_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("input_data", sa.JSON, nullable=True),
        sa.Column("template_id", UUID(as_uuid=False), sa.ForeignKey("content_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bulk_jobs_user_status", "bulk_jobs", ["user_id", "status"])

    op.create_table(
        "bulk_job_items",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("bulk_job_id", UUID(as_uuid=False), sa.ForeignKey("bulk_jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("keyword", sa.String(500), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),  # pending, processing, completed, failed, cancelled
        sa.Column("resource_type", sa.String(50), nullable=True),  # outline, article
        sa.Column("resource_id", UUID(as_uuid=False), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bulk_job_items_job_status", "bulk_job_items", ["bulk_job_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_bulk_job_items_job_status")
    op.drop_table("bulk_job_items")
    op.drop_index("ix_bulk_jobs_user_status")
    op.drop_table("bulk_jobs")
    op.drop_table("content_templates")
