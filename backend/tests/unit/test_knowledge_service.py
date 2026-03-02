"""
Unit tests for Knowledge Service.

Tests cover:
- Document processing workflow
- Status updates during processing
- Error handling and recovery
- Query operations with filtering
- Source deletion
- Query logging
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

# Skip if service not implemented yet
pytest.importorskip(
    "core.knowledge.knowledge_service", reason="Knowledge service not yet implemented"
)

from core.knowledge.knowledge_service import (
    KnowledgeService,
    KnowledgeServiceError,
    ProcessingStatus,
)


class TestKnowledgeServiceProcessing:
    """Tests for document processing in KnowledgeService."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mocked dependencies."""
        return {
            "chroma_adapter": Mock(),
            "document_processor": Mock(),
            "embedding_service": AsyncMock(),
            "db_session": AsyncMock(),
        }

    @pytest.fixture
    def service(self, mock_dependencies):
        """Create KnowledgeService with mocked dependencies."""
        return KnowledgeService(
            chroma_adapter=mock_dependencies["chroma_adapter"],
            document_processor=mock_dependencies["document_processor"],
            embedding_service=mock_dependencies["embedding_service"],
            db_session=mock_dependencies["db_session"],
        )

    @pytest.mark.asyncio
    async def test_process_document_success(self, service, mock_dependencies):
        """Test successful document processing."""
        user_id = str(uuid4())
        source_id = str(uuid4())
        file_content = b"Test document content."
        filename = "test.pdf"

        # Mock document processor
        mock_dependencies["document_processor"].process_file.return_value = {
            "chunks": [
                {"text": "Chunk 1", "chunk_index": 0},
                {"text": "Chunk 2", "chunk_index": 1},
            ],
            "metadata": {"filename": filename, "total_chunks": 2},
        }

        # Mock embedding service
        mock_dependencies["embedding_service"].embed_texts.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]

        # Mock ChromaDB
        mock_dependencies["chroma_adapter"].add_documents = Mock()

        result = await service.process_document(
            user_id=user_id, source_id=source_id, file_content=file_content, filename=filename
        )

        # Verify document processor was called
        mock_dependencies["document_processor"].process_file.assert_called_once_with(
            filename, file_content
        )

        # Verify embeddings were created
        mock_dependencies["embedding_service"].embed_texts.assert_called_once()

        # Verify chunks were added to ChromaDB
        mock_dependencies["chroma_adapter"].add_documents.assert_called_once()

        # Verify result
        assert result["status"] == ProcessingStatus.COMPLETED
        assert result["chunks_processed"] == 2

    @pytest.mark.asyncio
    async def test_process_document_updates_status(self, service, mock_dependencies):
        """Test that document processing updates status in database."""
        user_id = str(uuid4())
        source_id = str(uuid4())

        # Mock processing
        mock_dependencies["document_processor"].process_file.return_value = {
            "chunks": [{"text": "Chunk 1", "chunk_index": 0}],
            "metadata": {"filename": "test.pdf", "total_chunks": 1},
        }
        mock_dependencies["embedding_service"].embed_texts.return_value = [[0.1, 0.2, 0.3]]

        # Mock database source object
        mock_source = Mock()
        mock_source.status = ProcessingStatus.PENDING
        mock_dependencies["db_session"].get = AsyncMock(return_value=mock_source)

        await service.process_document(
            user_id=user_id, source_id=source_id, file_content=b"content", filename="test.pdf"
        )

        # Verify status was updated to processing
        assert mock_source.status == ProcessingStatus.COMPLETED
        mock_dependencies["db_session"].commit.assert_called()

    @pytest.mark.asyncio
    async def test_process_document_failure_updates_error(self, service, mock_dependencies):
        """Test that processing failures update error status."""
        user_id = str(uuid4())
        source_id = str(uuid4())

        # Mock database source object
        mock_source = Mock()
        mock_source.status = ProcessingStatus.PENDING
        mock_dependencies["db_session"].get = AsyncMock(return_value=mock_source)

        # Make document processor fail
        mock_dependencies["document_processor"].process_file.side_effect = Exception(
            "Processing failed"
        )

        with pytest.raises(KnowledgeServiceError):
            await service.process_document(
                user_id=user_id, source_id=source_id, file_content=b"content", filename="test.pdf"
            )

        # Verify status was updated to failed
        assert mock_source.status == ProcessingStatus.FAILED
        assert "Processing failed" in mock_source.error_message
        mock_dependencies["db_session"].commit.assert_called()


class TestKnowledgeServiceQuery:
    """Tests for query operations in KnowledgeService."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mocked dependencies."""
        return {
            "chroma_adapter": Mock(),
            "embedding_service": AsyncMock(),
            "llm_service": AsyncMock(),
            "db_session": AsyncMock(),
        }

    @pytest.fixture
    def service(self, mock_dependencies):
        """Create KnowledgeService with mocked dependencies."""
        return KnowledgeService(
            chroma_adapter=mock_dependencies["chroma_adapter"],
            embedding_service=mock_dependencies["embedding_service"],
            llm_service=mock_dependencies["llm_service"],
            db_session=mock_dependencies["db_session"],
        )

    @pytest.mark.asyncio
    async def test_query_knowledge_success(self, service, mock_dependencies):
        """Test successful knowledge base query."""
        user_id = str(uuid4())
        query = "What is cognitive behavioral therapy?"

        # Mock query embedding
        mock_dependencies["embedding_service"].embed_text.return_value = [0.1, 0.2, 0.3]

        # Mock ChromaDB query results
        mock_dependencies["chroma_adapter"].query.return_value = {
            "ids": [["chunk1", "chunk2"]],
            "documents": [
                ["CBT is a form of psychotherapy.", "It focuses on changing thought patterns."]
            ],
            "distances": [[0.1, 0.2]],
            "metadatas": [
                [{"source": "therapy.pdf", "page": 1}, {"source": "therapy.pdf", "page": 2}]
            ],
        }

        # Mock LLM response
        mock_dependencies[
            "llm_service"
        ].generate_answer.return_value = "Cognitive Behavioral Therapy (CBT) is a form of psychotherapy that focuses on changing thought patterns."

        result = await service.query_knowledge(user_id=user_id, query=query, n_results=5)

        # Verify embeddings were created
        mock_dependencies["embedding_service"].embed_text.assert_called_once_with(query)

        # Verify ChromaDB was queried
        mock_dependencies["chroma_adapter"].query.assert_called_once()

        # Verify LLM generated answer
        mock_dependencies["llm_service"].generate_answer.assert_called_once()

        # Verify result structure
        assert "answer" in result
        assert "sources" in result
        assert len(result["sources"]) == 2

    @pytest.mark.asyncio
    async def test_query_knowledge_with_source_filter(self, service, mock_dependencies):
        """Test querying with source filter."""
        user_id = str(uuid4())
        source_ids = [str(uuid4()), str(uuid4())]
        query = "What is mindfulness?"

        mock_dependencies["embedding_service"].embed_text.return_value = [0.1, 0.2, 0.3]
        mock_dependencies["chroma_adapter"].query.return_value = {
            "ids": [["chunk1"]],
            "documents": [["Mindfulness content"]],
            "distances": [[0.1]],
            "metadatas": [[{"source_id": source_ids[0]}]],
        }
        mock_dependencies["llm_service"].generate_answer.return_value = "Mindfulness is awareness."

        await service.query_knowledge(user_id=user_id, query=query, source_ids=source_ids)

        # Verify filter was applied
        call_args = mock_dependencies["chroma_adapter"].query.call_args[1]
        assert "where" in call_args
        # Filter should restrict to specified sources

    @pytest.mark.asyncio
    async def test_query_knowledge_no_results(self, service, mock_dependencies):
        """Test query with no relevant results."""
        user_id = str(uuid4())
        query = "Unrelated query with no matches"

        mock_dependencies["embedding_service"].embed_text.return_value = [0.1, 0.2, 0.3]

        # Mock empty results
        mock_dependencies["chroma_adapter"].query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "distances": [[]],
            "metadatas": [[]],
        }

        result = await service.query_knowledge(user_id=user_id, query=query)

        # Should return "no information found" response
        assert "answer" in result
        assert (
            "no information" in result["answer"].lower() or "not found" in result["answer"].lower()
        )
        assert len(result["sources"]) == 0

    @pytest.mark.asyncio
    async def test_query_knowledge_logs_query(self, service, mock_dependencies):
        """Test that queries are logged to database."""
        user_id = str(uuid4())
        query = "Test query"

        mock_dependencies["embedding_service"].embed_text.return_value = [0.1, 0.2, 0.3]
        mock_dependencies["chroma_adapter"].query.return_value = {
            "ids": [["chunk1"]],
            "documents": [["Content"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": "test.pdf"}]],
        }
        mock_dependencies["llm_service"].generate_answer.return_value = "Answer"

        await service.query_knowledge(user_id=user_id, query=query)

        # Verify query was logged
        mock_dependencies["db_session"].add.assert_called()
        # Should have added a QueryLog entry


class TestKnowledgeServiceDeletion:
    """Tests for deletion operations in KnowledgeService."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mocked dependencies."""
        return {
            "chroma_adapter": Mock(),
            "storage_adapter": AsyncMock(),
            "db_session": AsyncMock(),
        }

    @pytest.fixture
    def service(self, mock_dependencies):
        """Create KnowledgeService with mocked dependencies."""
        return KnowledgeService(
            chroma_adapter=mock_dependencies["chroma_adapter"],
            storage_adapter=mock_dependencies["storage_adapter"],
            db_session=mock_dependencies["db_session"],
        )

    @pytest.mark.asyncio
    async def test_delete_source_removes_from_chroma(self, service, mock_dependencies):
        """Test that deleting source removes chunks from ChromaDB."""
        user_id = str(uuid4())
        source_id = str(uuid4())

        # Mock database source
        mock_source = Mock()
        mock_source.id = source_id
        mock_source.user_id = user_id
        mock_source.file_path = "uploads/test.pdf"
        mock_dependencies["db_session"].get = AsyncMock(return_value=mock_source)

        await service.delete_source(user_id=user_id, source_id=source_id)

        # Verify ChromaDB deletion
        mock_dependencies["chroma_adapter"].delete_by_source.assert_called_once_with(source_id)

    @pytest.mark.asyncio
    async def test_delete_source_removes_from_storage(self, service, mock_dependencies):
        """Test that deleting source removes file from storage."""
        user_id = str(uuid4())
        source_id = str(uuid4())

        # Mock database source
        mock_source = Mock()
        mock_source.id = source_id
        mock_source.user_id = user_id
        mock_source.file_path = "uploads/test.pdf"
        mock_dependencies["db_session"].get = AsyncMock(return_value=mock_source)

        await service.delete_source(user_id=user_id, source_id=source_id)

        # Verify file deletion
        mock_dependencies["storage_adapter"].delete_file.assert_called_once_with("uploads/test.pdf")

    @pytest.mark.asyncio
    async def test_delete_source_unauthorized(self, service, mock_dependencies):
        """Test that users cannot delete sources they don't own."""
        user_id = str(uuid4())
        other_user_id = str(uuid4())
        source_id = str(uuid4())

        # Mock source owned by different user
        mock_source = Mock()
        mock_source.id = source_id
        mock_source.user_id = other_user_id
        mock_dependencies["db_session"].get = AsyncMock(return_value=mock_source)

        with pytest.raises(PermissionError, match="not authorized"):
            await service.delete_source(user_id=user_id, source_id=source_id)

    @pytest.mark.asyncio
    async def test_delete_source_not_found(self, service, mock_dependencies):
        """Test deleting non-existent source."""
        user_id = str(uuid4())
        source_id = str(uuid4())

        # Mock no source found
        mock_dependencies["db_session"].get = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await service.delete_source(user_id=user_id, source_id=source_id)


class TestKnowledgeServiceStats:
    """Tests for statistics and analytics in KnowledgeService."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mocked dependencies."""
        return {
            "chroma_adapter": Mock(),
            "db_session": AsyncMock(),
        }

    @pytest.fixture
    def service(self, mock_dependencies):
        """Create KnowledgeService with mocked dependencies."""
        return KnowledgeService(
            chroma_adapter=mock_dependencies["chroma_adapter"],
            db_session=mock_dependencies["db_session"],
        )

    @pytest.mark.asyncio
    async def test_get_user_stats(self, service, mock_dependencies):
        """Test getting user knowledge base statistics."""
        user_id = str(uuid4())

        # Mock database query for sources
        mock_sources = [
            Mock(status=ProcessingStatus.COMPLETED),
            Mock(status=ProcessingStatus.COMPLETED),
            Mock(status=ProcessingStatus.PENDING),
        ]
        mock_dependencies["db_session"].execute = AsyncMock()
        mock_dependencies[
            "db_session"
        ].execute.return_value.scalars.return_value.all.return_value = mock_sources

        # Mock ChromaDB stats
        mock_dependencies["chroma_adapter"].get_stats.return_value = {"total_documents": 150}

        stats = await service.get_user_stats(user_id=user_id)

        # Verify stats
        assert stats["total_sources"] == 3
        assert stats["completed_sources"] == 2
        assert stats["pending_sources"] == 1
        assert stats["total_chunks"] == 150

    @pytest.mark.asyncio
    async def test_get_source_detail(self, service, mock_dependencies):
        """Test getting detailed source information."""
        user_id = str(uuid4())
        source_id = str(uuid4())

        # Mock source
        mock_source = Mock()
        mock_source.id = source_id
        mock_source.filename = "therapy_guide.pdf"
        mock_source.status = ProcessingStatus.COMPLETED
        mock_source.chunks_count = 25
        mock_source.created_at = datetime.now(UTC)
        mock_dependencies["db_session"].get = AsyncMock(return_value=mock_source)

        detail = await service.get_source_detail(user_id=user_id, source_id=source_id)

        assert detail["id"] == source_id
        assert detail["filename"] == "therapy_guide.pdf"
        assert detail["status"] == ProcessingStatus.COMPLETED
        assert detail["chunks_count"] == 25
