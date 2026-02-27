"""
Knowledge Vault API routes for document upload and RAG queries.
"""

import logging
import math
import os
from pathlib import Path
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
    Query,
    UploadFile,
    Form,
    File,
)
from api.middleware.rate_limit import limiter
from sqlalchemy import select, func, and_, desc, delete
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
from api.utils import escape_like
from infrastructure.database.connection import get_db
from infrastructure.database.models import KnowledgeSource, KnowledgeChunk, KnowledgeQuery, User, SourceStatus
from services import knowledge_processor as kp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# File upload limits and allowed types
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {"pdf", "txt", "md", "docx", "html", "csv", "json"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/csv",
    "text/html",
    "application/json",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",  # fallback for unknown MIME types
}


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _build_ownership_filter(current_user: User):
    """Return the appropriate SQLAlchemy filter for ownership."""
    if current_user.current_project_id:
        return KnowledgeSource.project_id == current_user.current_project_id
    return and_(
        KnowledgeSource.user_id == current_user.id,
        KnowledgeSource.project_id.is_(None),
    )


async def _process_document(
    db: AsyncSession,
    source: KnowledgeSource,
    file_content: bytes,
) -> None:
    """
    Extract text from *file_content*, split into chunks, persist chunks,
    and update the source record with the final status.

    This runs synchronously in the request handler — it is fast enough for
    files up to 10 MB without a background worker.
    """
    now = datetime.now(timezone.utc)
    source.status = SourceStatus.PROCESSING.value
    source.processing_started_at = now
    source.error_message = None
    await db.commit()

    try:
        # 1. Extract text
        text, fully_extracted = kp.extract_text(file_content, source.file_type)

        if not text.strip():
            if not fully_extracted:
                source.status = SourceStatus.FAILED.value
                source.error_message = (
                    "Could not extract text from this file. "
                    "The required library may not be installed."
                )
            else:
                source.status = SourceStatus.FAILED.value
                source.error_message = "The file appears to be empty or contains no extractable text."
            await db.commit()
            return

        # 2. Split into chunks
        chunks = kp.split_into_chunks(text)
        if not chunks:
            source.status = SourceStatus.FAILED.value
            source.error_message = "No text chunks could be created from this document."
            await db.commit()
            return

        # 3. Delete any existing chunks for this source (reprocess scenario)
        await db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source.id)
        )

        # 4. Persist new chunks
        chunk_objects = []
        for idx, chunk_text in enumerate(chunks):
            chunk_objects.append(
                KnowledgeChunk(
                    id=str(uuid4()),
                    source_id=source.id,
                    chunk_index=idx,
                    content=chunk_text,
                    char_count=len(chunk_text),
                    created_at=now,
                )
            )
        db.add_all(chunk_objects)

        # 5. Update source metadata
        source.chunk_count = len(chunks)
        source.char_count = len(text)
        source.status = SourceStatus.COMPLETED.value
        source.processing_completed_at = datetime.now(timezone.utc)

        await db.commit()
        logger.info(
            "Processed knowledge source %s: %d chunks, %d chars",
            source.id,
            source.chunk_count,
            source.char_count,
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to process knowledge source %s", source.id)
        source.status = SourceStatus.FAILED.value
        source.error_message = f"Processing error: {str(exc)}"
        await db.commit()


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=SourceUploadResponse)
@limiter.limit("20/minute")  # KV-02: rate limit upload/query to prevent DoS
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # comma-separated
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document to the knowledge vault.

    Accepts PDF, TXT, MD, DOCX, HTML, CSV and JSON files up to 10 MB.
    Text is extracted and chunked synchronously; the source is marked
    COMPLETED (or FAILED) before the response is returned.
    """
    # Validate extension
    file_ext = get_file_extension(file.filename or "")
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Validate MIME type
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {file.content_type}",
        )

    # Read and validate size
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024:.0f} MB",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    # Parse tags
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

    # Default title from filename
    if not title:
        raw_name = file.filename or "untitled"
        title = raw_name.rsplit(".", 1)[0] if "." in raw_name else raw_name

    # Persist file to disk
    source_id = str(uuid4())
    file_path = kp.get_file_path(source_id, file.filename or f"file.{file_ext}")
    try:
        with open(file_path, "wb") as fh:
            fh.write(file_content)
    except OSError as exc:
        logger.error("Failed to save uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file to storage",
        ) from exc

    # Create DB record
    source = KnowledgeSource(
        id=source_id,
        user_id=current_user.id,
        project_id=current_user.current_project_id if current_user.current_project_id else None,
        title=title,
        filename=file.filename,
        file_type=file_ext,
        file_size=file_size,
        file_url=str(file_path),
        status=SourceStatus.PENDING.value,
        description=description,
        tags=tag_list if tag_list else None,
        chunk_count=0,
        char_count=0,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    # Process the document immediately
    await _process_document(db, source, file_content)
    await db.refresh(source)

    return SourceUploadResponse(
        id=source.id,
        title=source.title,
        filename=source.filename,
        file_type=source.file_type,
        file_size=source.file_size,
        status=source.status,
        message=(
            "Document processed successfully."
            if source.status == SourceStatus.COMPLETED.value
            else f"Document uploaded but processing failed: {source.error_message}"
        ),
    )


# ---------------------------------------------------------------------------
# List sources
# ---------------------------------------------------------------------------

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
    """
    query = select(KnowledgeSource).where(_build_ownership_filter(current_user))

    if status:
        query = query.where(KnowledgeSource.status == status)
    if file_type:
        query = query.where(KnowledgeSource.file_type == file_type)
    if search:
        search_pattern = f"%{escape_like(search)}%"
        query = query.where(
            (KnowledgeSource.title.ilike(search_pattern))
            | (KnowledgeSource.filename.ilike(search_pattern))
            | (KnowledgeSource.description.ilike(search_pattern))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(desc(KnowledgeSource.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    sources = result.scalars().all()

    items = [
        KnowledgeSourceResponse(
            id=s.id,
            title=s.title,
            filename=s.filename,
            file_type=s.file_type,
            file_size=s.file_size,
            file_url=s.file_url,
            status=s.status,
            chunk_count=s.chunk_count,
            char_count=s.char_count,
            description=s.description,
            tags=s.tags if s.tags else [],
            error_message=s.error_message,
            processing_started_at=s.processing_started_at,
            processing_completed_at=s.processing_completed_at,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sources
    ]

    return KnowledgeSourceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


# ---------------------------------------------------------------------------
# Get single source
# ---------------------------------------------------------------------------

@router.get("/sources/{source_id}", response_model=KnowledgeSourceResponse)
async def get_source(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific knowledge source."""
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            _build_ownership_filter(current_user),
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge source not found")

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


# ---------------------------------------------------------------------------
# Update source metadata
# ---------------------------------------------------------------------------

@router.put("/sources/{source_id}", response_model=KnowledgeSourceResponse)
async def update_source(
    source_id: str,
    request: KnowledgeSourceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update knowledge source metadata (title, description, tags)."""
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            _build_ownership_filter(current_user),
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge source not found")

    for field, value in request.model_dump(exclude_unset=True).items():
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


# ---------------------------------------------------------------------------
# Delete source
# ---------------------------------------------------------------------------

@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a knowledge source, its on-disk file, and all associated chunks.
    """
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            _build_ownership_filter(current_user),
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge source not found")

    # Delete chunks (cascade handles this, but be explicit)
    await db.execute(
        delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id)
    )

    # Delete on-disk file — KV-04: validate path resolves within storage dir before deletion.
    if source.file_url:
        from pathlib import Path
        try:
            resolved = Path(source.file_url).resolve()
            if resolved.is_relative_to(kp.KNOWLEDGE_STORAGE_DIR.resolve()):
                kp.delete_file(source.file_url)
            else:
                logger.warning("Skipping file deletion: path %s is outside storage dir", source.file_url)
        except Exception as path_err:
            logger.warning("Invalid file path for deletion %s: %s", source.file_url, path_err)

    await db.delete(source)
    await db.commit()


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse)
@limiter.limit("30/minute")  # KV-02: rate limit knowledge queries
async def query_knowledge(
    http_request: Request,
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Query the knowledge vault using keyword-based search.

    Splits the query into words, scores every stored chunk, and returns
    the top matching passages together with a synthesised answer text.
    """
    start_time = time.time()

    ownership_filter = _build_ownership_filter(current_user)

    # Determine which sources to search
    if request.source_ids:
        src_result = await db.execute(
            select(KnowledgeSource).where(
                KnowledgeSource.id.in_(request.source_ids),
                ownership_filter,
            )
        )
        sources = src_result.scalars().all()

        if len(sources) != len(request.source_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied or source not found",
            )

        incomplete = [s for s in sources if s.status != SourceStatus.COMPLETED.value]
        if incomplete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Some sources are not yet processed: {[s.title for s in incomplete]}",
            )
    else:
        src_result = await db.execute(
            select(KnowledgeSource).where(
                ownership_filter,
                KnowledgeSource.status == SourceStatus.COMPLETED.value,
            )
        )
        sources = src_result.scalars().all()

        if not sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No completed knowledge sources found. Please upload and process documents first.",
            )

    # KV-06: Limit chunk loading to prevent O(N) memory exhaustion.
    # We cap at 500 chunks; for large vaults this may miss some relevant results,
    # but prevents the query from becoming unbounded.
    source_ids = [s.id for s in sources]
    source_title_map = {s.id: s.title for s in sources}

    chunks_result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.source_id.in_(source_ids))
        .limit(500)
    )
    all_chunks = chunks_result.scalars().all()

    if not all_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Knowledge sources have no indexed chunks. Try reprocessing them.",
        )

    # Build search tuples: (chunk_id, source_id, source_title, chunk_index, content)
    chunk_tuples = [
        (c.id, c.source_id, source_title_map[c.source_id], c.chunk_index, c.content)
        for c in all_chunks
    ]

    # Run keyword search
    top_chunks = kp.search_chunks(chunk_tuples, request.query, top_k=request.max_results)
    answer = kp.build_answer(request.query, top_chunks)

    # Build source snippets
    source_snippets = []
    if request.include_sources:
        for chunk in top_chunks:
            # Normalise score to [0, 1] range for the response
            normalised_score = min(chunk["score"] / 10.0, 1.0)
            source_snippets.append(
                SourceSnippet(
                    source_id=chunk["source_id"],
                    source_title=chunk["source_title"],
                    content=chunk["content"][:600],
                    relevance_score=round(normalised_score, 4),
                    chunk_index=chunk["chunk_index"],
                )
            )

    query_time_ms = int((time.time() - start_time) * 1000)

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


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=KnowledgeStatsResponse)
async def get_knowledge_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge vault statistics for the current user/project."""
    ownership_filter = _build_ownership_filter(current_user)

    source_stats = await db.execute(
        select(
            func.count(KnowledgeSource.id).label("total_sources"),
            func.sum(KnowledgeSource.chunk_count).label("total_chunks"),
            func.sum(KnowledgeSource.char_count).label("total_characters"),
            func.sum(KnowledgeSource.file_size).label("total_bytes"),
        ).where(ownership_filter)
    )
    stats = source_stats.first()

    total_sources = stats.total_sources or 0
    total_chunks = stats.total_chunks or 0
    total_characters = stats.total_characters or 0
    total_bytes = stats.total_bytes or 0
    storage_used_mb = round(total_bytes / (1024 * 1024), 2)

    type_stats = await db.execute(
        select(
            KnowledgeSource.file_type,
            func.count(KnowledgeSource.id).label("count"),
        )
        .where(ownership_filter)
        .group_by(KnowledgeSource.file_type)
    )
    sources_by_type = {row.file_type: row.count for row in type_stats}

    # KV-03: KnowledgeQuery lacks project_id — query counts span all user projects.
    # TODO: Add project_id to KnowledgeQuery model + migration, then filter here.
    total_queries_result = await db.execute(
        select(func.count(KnowledgeQuery.id)).where(
            KnowledgeQuery.user_id == current_user.id
        )
    )
    total_queries = total_queries_result.scalar() or 0

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_queries_result = await db.execute(
        select(func.count(KnowledgeQuery.id)).where(
            and_(
                KnowledgeQuery.user_id == current_user.id,
                KnowledgeQuery.created_at >= thirty_days_ago,
            )
        )
    )
    recent_queries = recent_queries_result.scalar() or 0

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


# ---------------------------------------------------------------------------
# Reprocess
# ---------------------------------------------------------------------------

@router.post("/sources/{source_id}/reprocess", response_model=ReprocessResponse)
async def reprocess_source(
    source_id: str,
    request: ReprocessRequest = ReprocessRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-extract text and re-chunk a knowledge source.

    Use *force=true* to reprocess sources that are already in COMPLETED status.
    """
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            _build_ownership_filter(current_user),
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge source not found")

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

    # File must still exist on disk
    if not source.file_url or not os.path.exists(source.file_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Original file is no longer available on disk. Please re-upload the document.",
        )

    # Validate file path is within expected storage directory
    from services.knowledge_processor import KNOWLEDGE_STORAGE_DIR
    resolved = Path(source.file_url).resolve()
    if not resolved.is_relative_to(KNOWLEDGE_STORAGE_DIR.resolve()):
        logger.error("File path outside storage directory: %s", source.file_url)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid file path",
        )

    # Read the stored file and reprocess
    with open(source.file_url, "rb") as fh:
        file_content = fh.read()

    await _process_document(db, source, file_content)
    await db.refresh(source)

    return ReprocessResponse(
        source_id=source.id,
        status=source.status,
        message=(
            "Source reprocessed successfully."
            if source.status == SourceStatus.COMPLETED.value
            else f"Reprocessing failed: {source.error_message}"
        ),
    )
