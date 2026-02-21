"""
Knowledge Vault API routes for document upload and RAG queries.
"""

import math
import time
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    UploadFile,
    Form,
    File,
)
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.knowledge import (
    SourceUploadResponse,
    KnowledgeSourceResponse,
    KnowledgeSourceListResponse,
    KnowledgeSourceUpdateRequest,
    QueryRequest,
    QueryResponse,
    SourceSnippet,
    KnowledgeStatsResponse,
    ReprocessRequest,
    ReprocessResponse,
)
from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db
from infrastructure.database.models import KnowledgeSource, KnowledgeQuery, User, SourceStatus

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# File upload limits and allowed types
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/html": "html",
}
ALLOWED_EXTENSIONS = {"pdf", "txt", "md", "docx", "html"}


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


@router.post("/upload", response_model=SourceUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # comma-separated
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document to the knowledge vault.

    Accepts PDF, TXT, MD, DOCX, and HTML files up to 10MB.
    Files are queued for background processing and chunking.
    """
    # Validate file type
    file_ext = get_file_extension(file.filename)
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content to check size
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    # TODO: Check user's storage limits (implement in future)
    # For now, we'll allow uploads

    # Parse tags
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

    # Generate title if not provided
    if not title:
        title = file.filename.rsplit(".", 1)[0]  # Remove extension

    # Create KnowledgeSource record
    source_id = str(uuid4())
    source = KnowledgeSource(
        id=source_id,
        user_id=current_user.id,
        title=title,
        filename=file.filename,
        file_type=file_ext,
        file_size=file_size,
        file_url=None,  # TODO: Save to storage and set URL
        status=SourceStatus.PENDING.value,
        description=description,
        tags=tag_list if tag_list else None,
        chunk_count=0,
        char_count=0,
    )

    db.add(source)
    await db.commit()
    await db.refresh(source)

    # TODO: Queue background processing task
    # For now, we'll just return the pending status
    # In the future, this will trigger:
    # 1. Save file to storage (S3 or local)
    # 2. Extract text from file
    # 3. Chunk the text
    # 4. Generate embeddings
    # 5. Store in ChromaDB
    # 6. Update source status to COMPLETED

    return SourceUploadResponse(
        id=source.id,
        title=source.title,
        filename=source.filename,
        file_type=source.file_type,
        file_size=source.file_size,
        status=source.status,
        message="Document uploaded successfully. Processing will begin shortly.",
    )


@router.get("/sources", response_model=KnowledgeSourceListResponse)
async def list_sources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    file_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List user's knowledge sources with pagination and filtering.

    Supports filtering by:
    - status: pending, processing, completed, failed
    - search: search in title, filename, description
    - file_type: pdf, txt, md, docx, html
    """
    query = select(KnowledgeSource).where(KnowledgeSource.user_id == current_user.id)

    # Apply filters
    if status:
        query = query.where(KnowledgeSource.status == status)

    if file_type:
        query = query.where(KnowledgeSource.file_type == file_type)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (KnowledgeSource.title.ilike(search_pattern))
            | (KnowledgeSource.filename.ilike(search_pattern))
            | (KnowledgeSource.description.ilike(search_pattern))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(desc(KnowledgeSource.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    sources = result.scalars().all()

    # Convert tags from JSON to list
    items = []
    for source in sources:
        source_dict = {
            "id": source.id,
            "title": source.title,
            "filename": source.filename,
            "file_type": source.file_type,
            "file_size": source.file_size,
            "file_url": source.file_url,
            "status": source.status,
            "chunk_count": source.chunk_count,
            "char_count": source.char_count,
            "description": source.description,
            "tags": source.tags if source.tags else [],
            "error_message": source.error_message,
            "processing_started_at": source.processing_started_at,
            "processing_completed_at": source.processing_completed_at,
            "created_at": source.created_at,
            "updated_at": source.updated_at,
        }
        items.append(KnowledgeSourceResponse(**source_dict))

    return KnowledgeSourceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/sources/{source_id}", response_model=KnowledgeSourceResponse)
async def get_source(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get details of a specific knowledge source.
    """
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.user_id == current_user.id,
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source not found",
        )

    # Convert to response model
    return KnowledgeSourceResponse(
        id=source.id,
        title=source.title,
        filename=source.filename,
        file_type=source.file_type,
        file_size=source.file_size,
        file_url=source.file_url,
        status=source.status,
        chunk_count=source.chunk_count,
        char_count=source.char_count,
        description=source.description,
        tags=source.tags if source.tags else [],
        error_message=source.error_message,
        processing_started_at=source.processing_started_at,
        processing_completed_at=source.processing_completed_at,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.put("/sources/{source_id}", response_model=KnowledgeSourceResponse)
async def update_source(
    source_id: str,
    request: KnowledgeSourceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update knowledge source metadata (title, description, tags).
    """
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.user_id == current_user.id,
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source not found",
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    await db.commit()
    await db.refresh(source)

    return KnowledgeSourceResponse(
        id=source.id,
        title=source.title,
        filename=source.filename,
        file_type=source.file_type,
        file_size=source.file_size,
        file_url=source.file_url,
        status=source.status,
        chunk_count=source.chunk_count,
        char_count=source.char_count,
        description=source.description,
        tags=source.tags if source.tags else [],
        error_message=source.error_message,
        processing_started_at=source.processing_started_at,
        processing_completed_at=source.processing_completed_at,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a knowledge source and its chunks from ChromaDB.

    This will:
    1. Delete the source record from PostgreSQL
    2. Delete associated chunks from ChromaDB (TODO)
    3. Delete the file from storage (TODO)
    """
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.user_id == current_user.id,
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source not found",
        )

    # TODO: Delete chunks from ChromaDB
    # await chroma_adapter.delete_source_chunks(source_id)

    # TODO: Delete file from storage
    # if source.file_url:
    #     await storage_adapter.delete_file(source.file_url)

    await db.delete(source)
    await db.commit()


@router.post("/query", response_model=QueryResponse)
async def query_knowledge(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Query the knowledge vault using RAG (Retrieval-Augmented Generation).

    Process:
    1. Generate embedding for the query
    2. Search ChromaDB for similar chunks
    3. Build context from retrieved chunks
    4. Call Anthropic API to generate answer
    5. Log query for analytics
    6. Return answer with source citations
    """
    start_time = time.time()

    # TODO: Implement RAG query flow
    # For now, return a placeholder response

    # Validate that user has completed sources
    if request.source_ids:
        # Check that specified sources exist and are completed
        result = await db.execute(
            select(KnowledgeSource).where(
                KnowledgeSource.id.in_(request.source_ids),
                KnowledgeSource.user_id == current_user.id,
            )
        )
        sources = result.scalars().all()

        if len(sources) != len(request.source_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more specified sources not found",
            )

        # Check if any sources are not completed
        incomplete = [s for s in sources if s.status != SourceStatus.COMPLETED.value]
        if incomplete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Some sources are not yet processed: {[s.title for s in incomplete]}",
            )
    else:
        # Query all completed sources
        result = await db.execute(
            select(KnowledgeSource).where(
                KnowledgeSource.user_id == current_user.id,
                KnowledgeSource.status == SourceStatus.COMPLETED.value,
            )
        )
        sources = result.scalars().all()

        if not sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No completed knowledge sources found. Please upload and process documents first.",
            )

    # TODO: Implement actual RAG flow
    # 1. Generate query embedding using Anthropic or OpenAI
    # 2. Search ChromaDB for top-k similar chunks
    # 3. Build context from chunks
    # 4. Create prompt with context and query
    # 5. Call Anthropic API to generate answer
    # 6. Extract source citations

    # Placeholder response
    query_time_ms = int((time.time() - start_time) * 1000)

    # Create placeholder answer
    answer = (
        "RAG query implementation is pending. This endpoint will retrieve relevant "
        "chunks from your knowledge sources and use Anthropic Claude to generate "
        "a comprehensive answer based on your documents."
    )

    # Create placeholder sources
    source_snippets = []
    if request.include_sources:
        for source in sources[:request.max_results]:
            source_snippets.append(
                SourceSnippet(
                    source_id=source.id,
                    source_title=source.title,
                    content="[Placeholder chunk content]",
                    relevance_score=0.95,
                    chunk_index=0,
                )
            )

    # Log the query
    query_log = KnowledgeQuery(
        id=str(uuid4()),
        user_id=current_user.id,
        query_text=request.query,
        response_text=answer,
        sources_used=[
            {
                "source_id": s.source_id,
                "source_title": s.source_title,
                "relevance_score": s.relevance_score,
            }
            for s in source_snippets
        ] if source_snippets else None,
        query_time_ms=query_time_ms,
        chunks_retrieved=len(source_snippets),
        success=True,
    )

    db.add(query_log)
    await db.commit()

    return QueryResponse(
        query=request.query,
        answer=answer,
        sources=source_snippets,
        query_time_ms=query_time_ms,
        chunks_retrieved=len(source_snippets),
    )


@router.get("/stats", response_model=KnowledgeStatsResponse)
async def get_knowledge_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get knowledge vault statistics for the current user.

    Includes:
    - Total sources, chunks, and characters
    - Storage used in MB
    - Query statistics
    - Breakdown by file type
    """
    # Get source statistics
    source_stats = await db.execute(
        select(
            func.count(KnowledgeSource.id).label("total_sources"),
            func.sum(KnowledgeSource.chunk_count).label("total_chunks"),
            func.sum(KnowledgeSource.char_count).label("total_characters"),
            func.sum(KnowledgeSource.file_size).label("total_bytes"),
        ).where(KnowledgeSource.user_id == current_user.id)
    )
    stats = source_stats.first()

    total_sources = stats.total_sources or 0
    total_chunks = stats.total_chunks or 0
    total_characters = stats.total_characters or 0
    total_bytes = stats.total_bytes or 0
    storage_used_mb = round(total_bytes / (1024 * 1024), 2)

    # Get sources by type
    type_stats = await db.execute(
        select(
            KnowledgeSource.file_type,
            func.count(KnowledgeSource.id).label("count"),
        )
        .where(KnowledgeSource.user_id == current_user.id)
        .group_by(KnowledgeSource.file_type)
    )
    sources_by_type = {row.file_type: row.count for row in type_stats}

    # Get query statistics
    total_queries_result = await db.execute(
        select(func.count(KnowledgeQuery.id)).where(
            KnowledgeQuery.user_id == current_user.id
        )
    )
    total_queries = total_queries_result.scalar() or 0

    # Get recent queries (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_queries_result = await db.execute(
        select(func.count(KnowledgeQuery.id)).where(
            and_(
                KnowledgeQuery.user_id == current_user.id,
                KnowledgeQuery.created_at >= thirty_days_ago,
            )
        )
    )
    recent_queries = recent_queries_result.scalar() or 0

    # Get average query time
    avg_time_result = await db.execute(
        select(func.avg(KnowledgeQuery.query_time_ms)).where(
            KnowledgeQuery.user_id == current_user.id
        )
    )
    avg_query_time = avg_time_result.scalar() or 0.0

    return KnowledgeStatsResponse(
        total_sources=total_sources,
        total_chunks=total_chunks,
        total_characters=total_characters,
        total_queries=total_queries,
        storage_used_mb=storage_used_mb,
        sources_by_type=sources_by_type,
        recent_queries=recent_queries,
        avg_query_time_ms=round(avg_query_time, 2),
    )


@router.post("/sources/{source_id}/reprocess", response_model=ReprocessResponse)
async def reprocess_source(
    source_id: str,
    request: ReprocessRequest = ReprocessRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reprocess a knowledge source.

    Useful for:
    - Retrying failed processing
    - Forcing reprocessing with updated algorithms
    """
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.user_id == current_user.id,
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge source not found",
        )

    # Check if reprocessing is needed
    if source.status == SourceStatus.COMPLETED.value and not request.force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source already processed. Use force=true to reprocess.",
        )

    if source.status == SourceStatus.PROCESSING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source is currently being processed. Please wait.",
        )

    # Reset source status
    source.status = SourceStatus.PENDING.value
    source.error_message = None
    source.processing_started_at = None
    source.processing_completed_at = None

    await db.commit()

    # TODO: Queue background processing task
    # For now, just update status

    return ReprocessResponse(
        source_id=source.id,
        status=source.status,
        message="Source queued for reprocessing",
    )
