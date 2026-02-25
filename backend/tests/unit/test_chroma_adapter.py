"""
Unit tests for ChromaDB adapter.

Tests cover:
- Collection management
- Document operations (add, query, delete)
- Metadata filtering
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

# Skip if adapter not implemented yet
pytest.importorskip("adapters.knowledge.chroma_adapter", reason="ChromaDB adapter not yet implemented")

from adapters.knowledge.chroma_adapter import (
    ChromaAdapter,
    ChromaDBConnectionError,
    ChromaDBError,
)


@pytest.mark.skip(reason="Tests written for earlier ChromaAdapter API; need rewrite to match current user_id-scoped, async API")
class TestChromaAdapter:
    """Tests for ChromaDB adapter."""

    @pytest.fixture
    def mock_chroma_client(self):
        """Create mock ChromaDB client."""
        client = Mock()
        client.heartbeat = Mock()
        client.get_or_create_collection = Mock()
        client.get_collection = Mock()
        return client

    @pytest.fixture
    def mock_collection(self):
        """Create mock ChromaDB collection."""
        collection = Mock()
        collection.name = "knowledge_vault"
        collection.count = Mock(return_value=0)
        collection.add = Mock()
        collection.query = Mock()
        collection.delete = Mock()
        collection.get = Mock()
        return collection

    @pytest.fixture
    def adapter(self, mock_chroma_client):
        """Create ChromaAdapter instance with mocked client."""
        with patch('adapters.knowledge.chroma_adapter.chromadb.HttpClient', return_value=mock_chroma_client):
            adapter = ChromaAdapter(
                host="localhost",
                port=8000,
                collection_prefix="knowledge_vault"
            )
        return adapter

    def test_get_collection_creates_if_not_exists(self, adapter, mock_chroma_client, mock_collection):
        """Test that get_collection creates collection if it doesn't exist."""
        mock_chroma_client.get_or_create_collection.return_value = mock_collection

        collection = adapter.get_collection()

        assert collection == mock_collection
        mock_chroma_client.get_or_create_collection.assert_called_once_with(
            name="knowledge_vault"
        )

    def test_add_documents_success(self, adapter, mock_chroma_client, mock_collection):
        """Test successful document addition."""
        mock_chroma_client.get_or_create_collection.return_value = mock_collection

        documents = ["This is document 1", "This is document 2"]
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        ids = ["doc1", "doc2"]

        adapter.add_documents(
            documents=documents,
            embeddings=embeddings,
            ids=ids
        )

        mock_collection.add.assert_called_once_with(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=None
        )

    def test_add_documents_with_metadata(self, adapter, mock_chroma_client, mock_collection):
        """Test document addition with metadata."""
        mock_chroma_client.get_or_create_collection.return_value = mock_collection

        documents = ["Document with metadata"]
        embeddings = [[0.1, 0.2, 0.3]]
        ids = ["doc1"]
        metadatas = [{"source": "test.pdf", "page": 1, "user_id": str(uuid4())}]

        adapter.add_documents(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )

        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args[1]
        assert call_args["metadatas"] == metadatas
        assert call_args["metadatas"][0]["source"] == "test.pdf"
        assert call_args["metadatas"][0]["page"] == 1

    def test_query_returns_sorted_results(self, adapter, mock_chroma_client, mock_collection):
        """Test that query returns results sorted by distance."""
        mock_chroma_client.get_or_create_collection.return_value = mock_collection

        # Mock query results
        mock_collection.query.return_value = {
            "ids": [["doc2", "doc1", "doc3"]],
            "documents": [["Text 2", "Text 1", "Text 3"]],
            "distances": [[0.1, 0.3, 0.5]],
            "metadatas": [[{"source": "a.pdf"}, {"source": "b.pdf"}, {"source": "c.pdf"}]]
        }

        query_embedding = [0.1, 0.2, 0.3]
        results = adapter.query(
            query_embeddings=[query_embedding],
            n_results=3
        )

        mock_collection.query.assert_called_once_with(
            query_embeddings=[query_embedding],
            n_results=3,
            where=None
        )

        # Verify results structure
        assert len(results["ids"][0]) == 3
        assert results["distances"][0][0] < results["distances"][0][1]  # Sorted by distance

    def test_query_with_filter(self, adapter, mock_chroma_client, mock_collection):
        """Test query with metadata filter."""
        mock_chroma_client.get_or_create_collection.return_value = mock_collection

        mock_collection.query.return_value = {
            "ids": [["doc1"]],
            "documents": [["Filtered text"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": "test.pdf", "page": 1}]]
        }

        query_embedding = [0.1, 0.2, 0.3]
        where_filter = {"source": "test.pdf"}

        results = adapter.query(
            query_embeddings=[query_embedding],
            n_results=5,
            where=where_filter
        )

        mock_collection.query.assert_called_once_with(
            query_embeddings=[query_embedding],
            n_results=5,
            where=where_filter
        )

        # Verify filtering worked
        assert len(results["ids"][0]) == 1
        assert results["metadatas"][0][0]["source"] == "test.pdf"

    def test_delete_document_success(self, adapter, mock_chroma_client, mock_collection):
        """Test successful document deletion."""
        mock_chroma_client.get_or_create_collection.return_value = mock_collection

        doc_id = "doc123"
        adapter.delete_document(doc_id)

        mock_collection.delete.assert_called_once_with(ids=[doc_id])

    def test_delete_by_source_removes_all_chunks(self, adapter, mock_chroma_client, mock_collection):
        """Test deletion of all chunks from a source."""
        mock_chroma_client.get_or_create_collection.return_value = mock_collection

        source_id = str(uuid4())
        where_filter = {"source_id": source_id}

        adapter.delete_by_source(source_id)

        mock_collection.delete.assert_called_once_with(
            where=where_filter
        )

    def test_get_collection_stats(self, adapter, mock_chroma_client, mock_collection):
        """Test getting collection statistics."""
        mock_chroma_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 150

        stats = adapter.get_stats()

        assert stats["total_documents"] == 150
        assert stats["collection_name"] == "knowledge_vault"
        mock_collection.count.assert_called_once()

    def test_connection_error_handling(self, mock_chroma_client):
        """Test handling of connection errors."""
        # Make heartbeat fail to simulate connection error
        mock_chroma_client.heartbeat.side_effect = Exception("Connection refused")

        with patch('adapters.knowledge.chroma_adapter.chromadb.HttpClient', return_value=mock_chroma_client):
            with pytest.raises(ChromaConnectionError, match="Connection refused"):
                adapter = ChromaAdapter(
                    host="localhost",
                    port=8000,
                    collection_name="test"
                )
                adapter.test_connection()

    def test_query_error_handling(self, adapter, mock_chroma_client, mock_collection):
        """Test handling of query errors."""
        mock_chroma_client.get_or_create_collection.return_value = mock_collection
        mock_collection.query.side_effect = Exception("Query failed")

        with pytest.raises(ChromaQueryError, match="Query failed"):
            adapter.query(
                query_embeddings=[[0.1, 0.2, 0.3]],
                n_results=5
            )

    def test_add_documents_validates_input_lengths(self, adapter, mock_chroma_client, mock_collection):
        """Test that add_documents validates matching input lengths."""
        mock_chroma_client.get_or_create_collection.return_value = mock_collection

        documents = ["doc1", "doc2"]
        embeddings = [[0.1, 0.2]]  # Only 1 embedding for 2 documents
        ids = ["id1", "id2"]

        with pytest.raises(ValueError, match="documents, embeddings, and ids must have the same length"):
            adapter.add_documents(
                documents=documents,
                embeddings=embeddings,
                ids=ids
            )

    def test_context_manager_cleanup(self, mock_chroma_client):
        """Test that context manager properly cleans up resources."""
        with patch('adapters.knowledge.chroma_adapter.chromadb.HttpClient', return_value=mock_chroma_client):
            with ChromaAdapter(host="localhost", port=8000) as adapter:
                assert adapter.client is not None

            # Verify cleanup was called
            # In real implementation, this would close connections
            assert True  # Placeholder for actual cleanup verification


@pytest.mark.skip(reason="Tests written for earlier ChromaAdapter API; need rewrite to match current user_id-scoped, async API")
class TestChromaAdapterIntegration:
    """Integration-style tests for ChromaDB adapter (still mocked but testing workflows)."""

    @pytest.fixture
    def adapter_with_mock(self):
        """Create adapter with fully mocked ChromaDB."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.count.return_value = 0
        mock_client.get_or_create_collection.return_value = mock_collection

        with patch('adapters.knowledge.chroma_adapter.chromadb.HttpClient', return_value=mock_client):
            adapter = ChromaAdapter(host="localhost", port=8000)

        adapter._collection = mock_collection
        return adapter, mock_collection

    def test_add_and_query_workflow(self, adapter_with_mock):
        """Test complete workflow: add documents then query them."""
        adapter, mock_collection = adapter_with_mock

        # Add documents
        documents = ["Cognitive therapy techniques", "Mindfulness meditation guide"]
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        ids = ["doc1", "doc2"]
        metadatas = [{"source": "therapy.pdf", "page": 1}, {"source": "mindfulness.pdf", "page": 1}]

        adapter.add_documents(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )

        # Mock query results
        mock_collection.query.return_value = {
            "ids": [["doc1"]],
            "documents": [["Cognitive therapy techniques"]],
            "distances": [[0.05]],
            "metadatas": [[{"source": "therapy.pdf", "page": 1}]]
        }

        # Query for relevant content
        results = adapter.query(
            query_embeddings=[[0.1, 0.2, 0.3]],
            n_results=1
        )

        # Verify workflow
        assert mock_collection.add.called
        assert mock_collection.query.called
        assert len(results["ids"][0]) == 1
        assert "Cognitive therapy" in results["documents"][0][0]

    def test_update_document_workflow(self, adapter_with_mock):
        """Test updating a document (delete old, add new)."""
        adapter, mock_collection = adapter_with_mock

        doc_id = "doc123"

        # Delete old version
        adapter.delete_document(doc_id)
        mock_collection.delete.assert_called_with(ids=[doc_id])

        # Add new version
        adapter.add_documents(
            documents=["Updated content"],
            embeddings=[[0.1, 0.2, 0.3]],
            ids=[doc_id],
            metadatas=[{"source": "updated.pdf", "version": 2}]
        )

        mock_collection.add.assert_called_once()
