"""
White-Label Agency Mode database models for Phase 5.
"""

from datetime import date as date_type, datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Float,
    Date,
    Index,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class AgencyProfile(Base, TimestampMixin):
    """White-label agency profile defining branding and configuration for an agency user."""

    __tablename__ = "agency_profiles"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Owner — one agency profile per user
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Branding
    agency_name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    brand_colors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    custom_domain: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True
    )

    # Contact and footer
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    footer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Limits and status
    max_clients: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<AgencyProfile("
            f"agency_name={self.agency_name!r}, "
            f"max_clients={self.max_clients}, "
            f"is_active={self.is_active}"
            f")>"
        )


class ClientWorkspace(Base, TimestampMixin):
    """A client-facing workspace scoped to a project, managed by an agency."""

    __tablename__ = "client_workspaces"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Parent agency
    agency_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("agency_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Associated project — one workspace per project
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Client identity
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Portal access
    is_portal_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    portal_access_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Portal token expiry. NULL means token does not expire (legacy).",
    )

    # Feature gating (list of enabled feature keys)
    allowed_features: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_client_workspaces_agency_name", "agency_id", "client_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<ClientWorkspace("
            f"client_name={self.client_name!r}, "
            f"agency_id={self.agency_id!r}, "
            f"is_portal_enabled={self.is_portal_enabled}"
            f")>"
        )


class ReportTemplate(Base, TimestampMixin):
    """A reusable report template owned by an agency."""

    __tablename__ = "report_templates"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Parent agency
    agency_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("agency_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Template definition
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<ReportTemplate("
            f"name={self.name!r}, "
            f"agency_id={self.agency_id!r}"
            f")>"
        )


class GeneratedReport(Base, TimestampMixin):
    """A report generated for a client workspace, optionally from a template."""

    __tablename__ = "generated_reports"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Parent agency
    agency_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("agency_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Target client workspace
    client_workspace_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("client_workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional template reference — row survives template deletion
    report_template_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("report_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Report classification and period
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    period_start: Mapped[date_type] = mapped_column(Date, nullable=False)
    period_end: Mapped[date_type] = mapped_column(Date, nullable=False)

    # Report payload and delivery
    report_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Generation timestamp
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_generated_reports_agency_generated", "agency_id", "generated_at"),
        Index(
            "ix_generated_reports_workspace_generated",
            "client_workspace_id",
            "generated_at",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<GeneratedReport("
            f"report_type={self.report_type!r}, "
            f"period_start={self.period_start}, "
            f"period_end={self.period_end}, "
            f"client_workspace_id={self.client_workspace_id!r}"
            f")>"
        )
