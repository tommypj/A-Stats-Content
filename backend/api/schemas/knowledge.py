"""
Knowledge Vault API schemas for document upload and RAG queries.
"""

from datetime import datetime

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
    project_id: str | None = None
    filename: str
    file_type: str
    file_size: int
    file_url: str | None
    status: str
    chunk_count: int
    char_count: int
    description: str | None
    tags: list[str] = Field(default_factory=list)
    error_message: str | None
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeSourceListResponse(BaseModel):
    """Paginated list of knowledge sources."""

    items: list[KnowledgeSourceResponse]
    total: int
    page: int
    page_size: int
    pages: int


class KnowledgeSourceUpdateRequest(BaseModel):
    """Request to update knowledge source metadata."""

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    tags: list[str] | None = None


# ============================================================================
# Query Schemas
# ============================================================================


class QueryRequest(BaseModel):
    """Request to query the knowledge vault using RAG."""

    query: str = Field(..., min_length=1, max_length=1000)
    project_id: str | None = Field(None, description="Query project sources only")
    source_ids: list[str] | None = Field(
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
    chunk_index: int | None = None


class QueryResponse(BaseModel):
    """Response from a knowledge vault query."""

    query: str
    answer: str
    sources: list[SourceSnippet] = Field(default_factory=list)
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
