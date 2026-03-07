"""SEO report model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class SEOReport(Base, TimestampMixin):
    """User-generated SEO analytics report."""

    __tablename__ = "seo_reports"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Report metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="overview"
    )  # overview, keywords, pages, content_health

    # Date range for the report
    date_from: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    date_to: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Generation status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )  # pending, generating, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Report data (JSON snapshot of analytics at generation time)
    report_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User", lazy="joined")
    project = relationship("Project", lazy="select")

    def __repr__(self) -> str:
        return f"<SEOReport(id={self.id}, name={self.name[:30]}, status={self.status})>"
