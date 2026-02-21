"""
Knowledge Vault API schemas for document upload and RAG queries.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Upload Schemas
# ============================================================================


class SourceUploadResponse(BaseModel):
    """Response after uploading a document to knowledge vault."""

    id: str
    title: str
    filename: str
    file_type: str
    file_size: int
    status: str
    message: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Source Management Schemas
# ============================================================================


class KnowledgeSourceResponse(BaseModel):
    """Knowledge source detail response."""

    id: str
    title: str
    team_id: Optional[str] = None
    filename: str
    file_type: str
    file_size: int
    file_url: Optional[str]
    status: str
    chunk_count: int
    char_count: int
    description: Optional[str]
    tags: List[str] = Field(default_factory=list)
    error_message: Optional[str]
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeSourceListResponse(BaseModel):
    """Paginated list of knowledge sources."""

    items: List[KnowledgeSourceResponse]
    total: int
    page: int
    page_size: int
    pages: int


class KnowledgeSourceUpdateRequest(BaseModel):
    """Request to update knowledge source metadata."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    tags: Optional[List[str]] = None


# ============================================================================
# Query Schemas
# ============================================================================


class QueryRequest(BaseModel):
    """Request to query the knowledge vault using RAG."""

    query: str = Field(..., min_length=1, max_length=1000)
    team_id: Optional[str] = Field(None, description="Query team sources only")
    source_ids: Optional[List[str]] = Field(
        None,
        description="Filter to specific sources (empty = search all)",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of chunks to retrieve",
    )
    include_sources: bool = Field(
        default=True,
        description="Include source snippets in response",
    )


class SourceSnippet(BaseModel):
    """A snippet from a source document with relevance score."""

    source_id: str
    source_title: str
    content: str
    relevance_score: float
    chunk_index: Optional[int] = None


class QueryResponse(BaseModel):
    """Response from a knowledge vault query."""

    query: str
    answer: str
    sources: List[SourceSnippet] = Field(default_factory=list)
    query_time_ms: int
    chunks_retrieved: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Statistics Schemas
# ============================================================================


class KnowledgeStatsResponse(BaseModel):
    """Knowledge vault statistics for user."""

    total_sources: int
    total_chunks: int
    total_characters: int
    total_queries: int
    storage_used_mb: float
    sources_by_type: dict = Field(
        default_factory=dict,
        description="Count of sources by file type",
    )
    recent_queries: int = Field(
        description="Number of queries in last 30 days",
    )
    avg_query_time_ms: float = Field(
        description="Average query response time",
    )


# ============================================================================
# Processing Schemas
# ============================================================================


class ReprocessRequest(BaseModel):
    """Request to reprocess a failed source."""

    force: bool = Field(
        default=False,
        description="Force reprocessing even if not failed",
    )


class ReprocessResponse(BaseModel):
    """Response from reprocessing request."""

    source_id: str
    status: str
    message: str
