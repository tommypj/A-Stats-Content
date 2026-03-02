"""
Knowledge vault service for RAG operations.
"""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.knowledge import ChromaAdapter, EmbeddingService, DocumentProcessor
from adapters.ai.anthropic_adapter import AnthropicContentService
from infrastructure.database.models.knowledge import (
    KnowledgeSource,
    KnowledgeQuery,
    SourceStatus,
)

logger = logging.getLogger(__name__)


class KnowledgeService:
    """
    Service for knowledge vault operations.

    Handles document processing, embedding generation, and RAG queries.
    """

    def __init__(
        self,
        chroma_adapter: ChromaAdapter,
        embedding_service: EmbeddingService,
        document_processor: DocumentProcessor,
        anthropic_adapter: AnthropicContentService,
    ):
        """
        Initialize knowledge service.

        Args:
            chroma_adapter: ChromaDB adapter for vector storage
            embedding_service: Service for generating embeddings
            document_processor: Processor for chunking documents
            anthropic_adapter: Anthropic AI for answer generation
        """
        self.chroma = chroma_adapter
        self.embeddings = embedding_service
        self.processor = document_processor
        self.ai = anthropic_adapter

    async def process_document(
        self,
        source_id: str,
        user_id: str,
        file_path: str,
        db: AsyncSession,
        project_id: Optional[str] = None,
    ) -> bool:
        """
        Process a document: extract text, chunk, embed, store in ChromaDB.

        Updates KnowledgeSource status throughout the process.

        Args:
            source_id: ID of the KnowledgeSource record
            user_id: User ID (for ChromaDB collection isolation)
            file_path: Path to the uploaded file
            db: Database session
            project_id: Project ID for ChromaDB collection isolation.
                        Falls back to the source record's ``project_id`` field,
                        then to ``"personal"`` for backward compatibility.

        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # 1. Get KnowledgeSource record
            result = await db.execute(
                select(KnowledgeSource).where(KnowledgeSource.id == source_id)
            )
            source = result.scalar_one_or_none()

            if not source:
                logger.error(f"KnowledgeSource {source_id} not found")
                return False

            # Resolve project_id: caller-supplied → source record → "personal" fallback
            resolved_project_id = project_id or getattr(source, "project_id", None) or "personal"

            # 2. Update status to 'processing'
            source.status = SourceStatus.PROCESSING.value
            source.processing_started_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(f"Processing document: {source.title} ({source_id})")

            # 3. Read and process file into chunks
            source_metadata = {
                "source_id": source_id,
                "title": source.title,
                "user_id": user_id,
                "file_type": source.file_type,
            }

            with open(file_path, "rb") as fh:
                processed_doc = await self.processor.process_file(
                    file=fh,
                    filename=Path(file_path).name,
                    source_id=source_id,
                    metadata=source_metadata,
                )

            chunks = processed_doc.chunks

            if not chunks:
                raise ValueError("No chunks extracted from document")

            logger.info(f"Extracted {len(chunks)} chunks from document")

            # 4. Generate embeddings for all chunks
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = await self.embeddings.embed_texts(chunk_texts)

            logger.info(f"Generated {len(embeddings)} embeddings")

            # 5. Store in ChromaDB
            from adapters.knowledge.chroma_adapter import Document as ChromaDocument
            chroma_docs = [
                ChromaDocument(
                    id=f"{source_id}_chunk_{i}",
                    content=chunk.content,
                    metadata=chunk.metadata,
                )
                for i, chunk in enumerate(chunks)
            ]

            await self.chroma.add_documents(
                user_id=user_id,
                documents=chroma_docs,
                embeddings=embeddings,
                project_id=resolved_project_id,
            )

            logger.info(f"Stored {len(chunks)} chunks in ChromaDB")

            # 6. Update KnowledgeSource with statistics
            total_chars = sum(len(chunk.content) for chunk in chunks)
            source.chunk_count = len(chunks)
            source.char_count = total_chars
            source.status = SourceStatus.COMPLETED.value
            source.processing_completed_at = datetime.now(timezone.utc)
            source.error_message = None

            await db.commit()

            logger.info(
                f"Successfully processed document {source_id}: "
                f"{len(chunks)} chunks, {total_chars} chars"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to process document {source_id}: {e}", exc_info=True)

            # Update status to 'failed' with error message
            try:
                result = await db.execute(
                    select(KnowledgeSource).where(KnowledgeSource.id == source_id)
                )
                source = result.scalar_one_or_none()

                if source:
                    source.status = SourceStatus.FAILED.value
                    source.error_message = str(e)[:1000]  # Truncate if too long
                    source.processing_completed_at = datetime.now(timezone.utc)
                    await db.commit()

            except Exception as db_error:
                logger.error(f"Failed to update error status: {db_error}")

            return False

    async def query_knowledge(
        self,
        user_id: str,
        query: str,
        source_ids: Optional[List[str]] = None,
        max_results: int = 5,
        db: Optional[AsyncSession] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        RAG query: embed query, retrieve chunks, generate answer.

        Args:
            user_id: User ID (for ChromaDB collection isolation)
            query: User's question
            source_ids: Optional list of source IDs to filter by
            max_results: Maximum number of chunks to retrieve
            db: Optional database session for logging queries
            project_id: Project ID for ChromaDB collection isolation.
                        Uses ``"personal"`` when omitted.

        Returns:
            Dictionary with:
                - query: Original query text
                - answer: Generated answer
                - sources: List of source chunks used
                - query_time_ms: Time taken to process query
        """
        resolved_project_id = project_id or "personal"
        start_time = time.time()

        try:
            # 1. Generate query embedding
            query_embedding = await self.embeddings.embed_text(query)

            # 2. Search ChromaDB
            filter_metadata = None
            if source_ids:
                # ChromaDB filter format
                if len(source_ids) == 1:
                    filter_metadata = {"source_id": source_ids[0]}
                else:
                    filter_metadata = {"source_id": {"$in": source_ids}}

            results = await self.chroma.query(
                user_id=user_id,
                query_embedding=query_embedding,
                n_results=max_results,
                filter_metadata=filter_metadata,
                project_id=resolved_project_id,
            )

            logger.info(f"Retrieved {len(results)} chunks for query")

            # 3. Build context from results
            if not results:
                # No relevant content found
                return {
                    "query": query,
                    "answer": "I don't have enough information in my knowledge base to answer this question.",
                    "sources": [],
                    "query_time_ms": int((time.time() - start_time) * 1000),
                }

            context_parts = []
            sources = []

            for result in results:
                # Add to context
                source_title = result.metadata.get("title", "Unknown")
                context_parts.append(
                    f"[Source: {source_title}]\n{result.content}"
                )

                # Add to sources list
                sources.append({
                    "source_id": result.metadata.get("source_id"),
                    "source_title": source_title,
                    "content": result.content[:500],  # Truncate for response
                    "relevance_score": result.score,
                })

            context = "\n\n---\n\n".join(context_parts)

            # 4. Generate answer using Anthropic
            prompt = f"""You are a helpful assistant. Answer the question based ONLY on the provided context.

If the context doesn't contain relevant information to answer the question, say "I don't have enough information in my knowledge base to answer this question."

Always cite which source(s) you used in your answer.

Context:
{context}

Question: {query}

Answer:"""

            answer = await self.ai.generate_text(prompt, max_tokens=2048)

            # 5. Calculate query time
            query_time_ms = int((time.time() - start_time) * 1000)

            # 6. Log query (if db provided)
            if db:
                try:
                    query_record = KnowledgeQuery(
                        user_id=user_id,
                        query_text=query,
                        response_text=answer,
                        sources_used=sources,
                        query_time_ms=query_time_ms,
                        chunks_retrieved=len(results),
                        success=True,
                    )
                    db.add(query_record)
                    await db.commit()

                except Exception as e:
                    logger.error(f"Failed to log query: {e}")
                    # Don't fail the query if logging fails
                    await db.rollback()

            return {
                "query": query,
                "answer": answer,
                "sources": sources,
                "query_time_ms": query_time_ms,
            }

        except Exception as e:
            logger.error(f"Failed to process query: {e}", exc_info=True)

            query_time_ms = int((time.time() - start_time) * 1000)

            # Log failed query
            if db:
                try:
                    query_record = KnowledgeQuery(
                        user_id=user_id,
                        query_text=query,
                        response_text=None,
                        sources_used=[],
                        query_time_ms=query_time_ms,
                        chunks_retrieved=0,
                        success=False,
                        error_message=str(e)[:1000],
                    )
                    db.add(query_record)
                    await db.commit()

                except Exception as log_error:
                    logger.error(f"Failed to log error query: {log_error}")
                    await db.rollback()

            # Return error response
            return {
                "query": query,
                "answer": f"An error occurred while processing your query: {str(e)}",
                "sources": [],
                "query_time_ms": query_time_ms,
            }

    async def delete_source(
        self,
        source_id: str,
        user_id: str,
        db: AsyncSession,
        project_id: Optional[str] = None,
    ) -> bool:
        """
        Delete a source from DB and ChromaDB.

        Args:
            source_id: ID of the KnowledgeSource to delete
            user_id: User ID (for verification and ChromaDB)
            db: Database session
            project_id: Project ID for ChromaDB collection isolation.
                        Falls back to the source record's ``project_id`` field,
                        then to ``"personal"`` for backward compatibility.

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            # 1. Get KnowledgeSource record
            result = await db.execute(
                select(KnowledgeSource).where(
                    KnowledgeSource.id == source_id,
                    KnowledgeSource.user_id == user_id,
                )
            )
            source = result.scalar_one_or_none()

            if not source:
                logger.warning(f"KnowledgeSource {source_id} not found for user {user_id}")
                return False

            # Resolve project_id: caller-supplied → source record → "personal" fallback
            resolved_project_id = project_id or getattr(source, "project_id", None) or "personal"

            # 2. Delete chunks from ChromaDB
            await self.chroma.delete_by_source(
                user_id=user_id,
                source_id=source_id,
                project_id=resolved_project_id,
            )

            logger.info(f"Deleted chunks from ChromaDB for source {source_id}")

            # 3. Delete file from storage (if exists)
            if source.file_url:
                try:
                    file_path = Path(source.file_url)
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"Deleted file: {source.file_url}")
                except Exception as e:
                    logger.warning(f"Failed to delete file {source.file_url}: {e}")

            # 4. Delete KnowledgeSource record (CASCADE will delete related queries)
            await db.delete(source)
            await db.commit()

            logger.info(f"Successfully deleted source {source_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete source {source_id}: {e}", exc_info=True)
            await db.rollback()
            return False

    async def get_source_statistics(
        self,
        user_id: str,
        db: AsyncSession,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics about a user's knowledge vault.

        Args:
            user_id: User ID
            db: Database session
            project_id: Project ID for ChromaDB collection isolation.
                        Uses ``"personal"`` when omitted.

        Returns:
            Dictionary with statistics
        """
        try:
            # KV-05: Use SQL aggregates instead of loading all rows into memory
            agg_result = await db.execute(
                select(
                    func.count(KnowledgeSource.id).label("total"),
                    func.count(KnowledgeSource.id)
                    .filter(KnowledgeSource.status == SourceStatus.COMPLETED.value)
                    .label("completed"),
                    func.coalesce(func.sum(KnowledgeSource.chunk_count), 0).label("chunks"),
                    func.coalesce(func.sum(KnowledgeSource.char_count), 0).label("chars"),
                ).where(KnowledgeSource.user_id == user_id)
            )
            row = agg_result.one()
            total_sources = row.total
            completed_sources = row.completed
            total_chunks = row.chunks
            total_chars = row.chars

            # Get ChromaDB stats
            resolved_project_id = project_id or "personal"
            chroma_stats = await self.chroma.get_collection_stats(user_id, resolved_project_id)

            # Get query count via SQL aggregate
            query_result = await db.execute(
                select(func.count(KnowledgeQuery.id)).where(KnowledgeQuery.user_id == user_id)
            )
            total_queries = query_result.scalar() or 0

            return {
                "total_sources": total_sources,
                "completed_sources": completed_sources,
                "total_chunks": total_chunks,
                "total_chars": total_chars,
                "total_queries": total_queries,
                "chroma_stats": chroma_stats,
            }

        except Exception as e:
            logger.error(f"Failed to get statistics for user {user_id}: {e}")
            return {
                "total_sources": 0,
                "completed_sources": 0,
                "total_chunks": 0,
                "total_chars": 0,
                "total_queries": 0,
                "error": str(e),
            }
