"""
Knowledge Vault database models: KnowledgeSource and KnowledgeQuery.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class SourceStatus(str, Enum):
    """Knowledge source processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class KnowledgeSource(Base, TimestampMixin):
    """
    Knowledge source model - tracks uploaded documents for RAG.

    Represents a document/file uploaded to the knowledge vault.
    Files are processed into chunks and stored in ChromaDB for vector search.
    """

    __tablename__ = "knowledge_sources"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Owner
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Project ownership (optional - for multi-tenancy)
    project_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Source information
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # pdf, txt, md, docx, html
    file_size: Mapped[int] = mapped_column(nullable=False)  # bytes
    file_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )  # Storage URL (e.g., S3, local path)

    # Processing status
    status: Mapped[str] = mapped_column(
        String(50),
        default=SourceStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    chunk_count: Mapped[int] = mapped_column(default=0, nullable=False)
    char_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    """
    Structure:
    ["tag1", "tag2", "tag3"]
    """

    # Processing details
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Indexes
    __table_args__ = (
        Index("ix_knowledge_sources_user_status", "user_id", "status"),
        Index("ix_knowledge_sources_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeSource(id={self.id}, title={self.title[:30]}, status={self.status})>"

    @property
    def is_processed(self) -> bool:
        """Check if source is successfully processed."""
        return self.status == SourceStatus.COMPLETED.value

    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return round(self.file_size / (1024 * 1024), 2)


class KnowledgeQuery(Base, TimestampMixin):
    """
    Knowledge query model - tracks user queries for analytics.

    Logs all queries made to the knowledge vault for usage tracking,
    performance monitoring, and to improve the RAG system.
    """

    __tablename__ = "knowledge_queries"

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Owner
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Query data
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sources_used: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    """
    Structure:
    [
        {
            "source_id": "uuid",
            "source_title": "Document Title",
            "relevance_score": 0.95
        },
        ...
    ]
    """

    # Performance metrics
    query_time_ms: Mapped[int] = mapped_column(nullable=False)
    chunks_retrieved: Mapped[int] = mapped_column(nullable=False)

    # Optional: Track if query was successful
    success: Mapped[bool] = mapped_column(default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Indexes
    __table_args__ = (
        Index("ix_knowledge_queries_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeQuery(id={self.id}, query={self.query_text[:30]}, chunks={self.chunks_retrieved})>"

    @property
    def query_time_seconds(self) -> float:
        """Get query time in seconds."""
        return round(self.query_time_ms / 1000, 2)
