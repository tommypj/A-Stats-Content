"""Add white-label agency mode tables.

Agency profiles, client workspaces, report templates, and generated reports
for Phase 5 White-Label Agency Mode.

Revision ID: 028
Revises: 027
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agency_profiles",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, unique=True),
        sa.Column("agency_name", sa.String(255), nullable=False),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("brand_colors", sa.JSON, nullable=True),  # {primary, secondary, accent}
        sa.Column("custom_domain", sa.String(255), nullable=True, unique=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("footer_text", sa.Text, nullable=True),
        sa.Column("max_clients", sa.Integer, nullable=False, server_default="5"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "client_workspaces",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("agency_id", UUID(as_uuid=False), sa.ForeignKey("agency_profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("project_id", UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True, unique=True),
        sa.Column("client_name", sa.String(255), nullable=False),
        sa.Column("client_email", sa.String(255), nullable=True),
        sa.Column("client_logo_url", sa.String(500), nullable=True),
        sa.Column("is_portal_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("portal_access_token", sa.String(255), nullable=True, unique=True, index=True),
        sa.Column("allowed_features", sa.JSON, nullable=True),  # [analytics, content, social]
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_client_workspaces_agency_client", "client_workspaces", ["agency_id", "client_name"])

    op.create_table(
        "report_templates",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("agency_id", UUID(as_uuid=False), sa.ForeignKey("agency_profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("template_config", sa.JSON, nullable=False),  # {sections, branding, metrics_to_include}
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "generated_reports",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("agency_id", UUID(as_uuid=False), sa.ForeignKey("agency_profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("client_workspace_id", UUID(as_uuid=False), sa.ForeignKey("client_workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("report_template_id", UUID(as_uuid=False), sa.ForeignKey("report_templates.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("report_data", sa.JSON, nullable=True),
        sa.Column("pdf_url", sa.String(500), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_generated_reports_agency_generated", "generated_reports", ["agency_id", "generated_at"])
    op.create_index("ix_generated_reports_workspace_generated", "generated_reports", ["client_workspace_id", "generated_at"])


def downgrade() -> None:
    op.drop_index("ix_generated_reports_workspace_generated")
    op.drop_index("ix_generated_reports_agency_generated")
    op.drop_table("generated_reports")
    op.drop_table("report_templates")
    op.drop_index("ix_client_workspaces_agency_client")
    op.drop_table("client_workspaces")
    op.drop_table("agency_profiles")
