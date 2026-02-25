"""
ChromaDB adapter for vector storage and retrieval.

Provides interface for storing and querying document embeddings using ChromaDB HTTP client.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import chromadb

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Document to be stored in vector database."""

    id: str
    content: str
    metadata: Dict[str, Any]  # source_id, title, chunk_index, user_id, etc.


@dataclass
class QueryResult:
    """Result from vector similarity search."""

    document_id: str
    content: str
    metadata: Dict[str, Any]
    score: float  # similarity score (0-1, higher is more similar)


class ChromaDBError(Exception):
    """Base exception for ChromaDB operations."""

    pass


class ChromaDBConnectionError(ChromaDBError):
    """ChromaDB connection error."""

    pass


class ChromaAdapter:
    """
    ChromaDB vector store adapter for RAG.

    Uses HTTP client to connect to ChromaDB service running in Docker.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_prefix: Optional[str] = None,
    ):
        """
        Initialize ChromaDB adapter with HTTP client.

        Args:
            host: ChromaDB server host (defaults to settings.chroma_host)
            port: ChromaDB server port (defaults to settings.chroma_port)
            collection_prefix: Prefix for collection names (defaults to settings.chroma_collection_prefix)
        """
        self.host = host or settings.chroma_host
        self.port = port or settings.chroma_port
        self.collection_prefix = collection_prefix or settings.chroma_collection_prefix

        # Thread pool for blocking operations (ChromaDB client is synchronous)
        self._executor = ThreadPoolExecutor(max_workers=4)

        try:
            self.client = chromadb.HttpClient(host=self.host, port=self.port)
            # Test connection
            self.client.heartbeat()
            logger.info(f"ChromaDB client connected to {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise ChromaDBConnectionError(f"Could not connect to ChromaDB at {self.host}:{self.port}: {e}")

    def get_collection(self, user_id: str) -> chromadb.Collection:
        """
        Get or create user-specific collection.

        Args:
            user_id: User ID to create collection for

        Returns:
            ChromaDB Collection instance
        """
        collection_name = f"{self.collection_prefix}_{user_id}"

        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},  # Use cosine similarity
            )
            logger.debug(f"Retrieved collection: {collection_name}")
            return collection
        except Exception as e:
            logger.error(f"Failed to get collection {collection_name}: {e}")
            raise ChromaDBError(f"Could not get collection: {e}")

    async def add_documents(
        self, user_id: str, documents: List[Document], embeddings: List[List[float]]
    ) -> List[str]:
        """
        Add documents with their embeddings to the collection.

        Args:
            user_id: User ID
            documents: List of documents to add
            embeddings: List of embedding vectors (must match documents length)

        Returns:
            List of document IDs that were added

        Raises:
            ChromaDBError: If adding documents fails
        """
        if len(documents) != len(embeddings):
            raise ValueError("Documents and embeddings lists must have the same length")

        if not documents:
            return []

        try:
            collection = self.get_collection(user_id)

            # Prepare data for ChromaDB
            ids = [doc.id for doc in documents]
            contents = [doc.content for doc in documents]
            metadatas = [doc.metadata for doc in documents]

            # ChromaDB add is synchronous, run in executor
            await self._run_in_executor(
                collection.add, ids=ids, documents=contents, embeddings=embeddings, metadatas=metadatas
            )

            logger.info(f"Added {len(documents)} documents to collection for user {user_id}")
            return ids

        except Exception as e:
            logger.error(f"Failed to add documents to collection: {e}")
            raise ChromaDBError(f"Could not add documents: {e}")

    async def query(
        self,
        user_id: str,
        query_embedding: List[float],
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[QueryResult]:
        """
        Query similar documents using vector similarity.

        Args:
            user_id: User ID
            query_embedding: Query embedding vector
            n_results: Number of results to return
            filter_metadata: Optional metadata filter (e.g., {"source_id": "document_123"})

        Returns:
            List of query results sorted by similarity (most similar first)

        Raises:
            ChromaDBError: If query fails
        """
        try:
            collection = self.get_collection(user_id)

            # Query is synchronous, run in executor
            results = await self._run_in_executor(
                collection.query,
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata,
            )

            # Parse results
            query_results = []
            if results and results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    query_results.append(
                        QueryResult(
                            document_id=doc_id,
                            content=results["documents"][0][i],
                            metadata=results["metadatas"][0][i],
                            score=1.0 - results["distances"][0][i],  # Convert distance to similarity
                        )
                    )

            logger.debug(f"Query returned {len(query_results)} results for user {user_id}")
            return query_results

        except Exception as e:
            logger.error(f"Failed to query collection: {e}")
            raise ChromaDBError(f"Query failed: {e}")

    async def delete_document(self, user_id: str, document_id: str) -> bool:
        """
        Delete a document from the collection.

        Args:
            user_id: User ID
            document_id: Document ID to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            collection = self.get_collection(user_id)

            # Delete is synchronous, run in executor
            await self._run_in_executor(collection.delete, ids=[document_id])

            logger.info(f"Deleted document {document_id} from collection for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    async def delete_by_source(self, user_id: str, source_id: str) -> int:
        """
        Delete all chunks from a source document.

        Args:
            user_id: User ID
            source_id: Source document ID

        Returns:
            Number of documents deleted
        """
        try:
            collection = self.get_collection(user_id)

            # Delete by metadata filter
            await self._run_in_executor(
                collection.delete, where={"source_id": source_id}
            )

            logger.info(f"Deleted all documents with source_id={source_id} for user {user_id}")
            # Note: ChromaDB doesn't return count of deleted items
            return 1  # Return 1 to indicate success

        except Exception as e:
            logger.error(f"Failed to delete documents by source {source_id}: {e}")
            return 0

    async def get_collection_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get stats about user's collection.

        Args:
            user_id: User ID

        Returns:
            Dictionary with collection statistics
        """
        try:
            collection = self.get_collection(user_id)

            # Count is synchronous, run in executor
            count = await self._run_in_executor(collection.count)

            return {
                "collection_name": f"{self.collection_prefix}_{user_id}",
                "document_count": count,
                "user_id": user_id,
            }

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            raise ChromaDBError(f"Could not get collection stats: {e}")

    async def delete_collection(self, user_id: str) -> bool:
        """
        Delete entire user collection.

        Args:
            user_id: User ID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            collection_name = f"{self.collection_prefix}_{user_id}"

            # Delete is synchronous, run in executor
            await self._run_in_executor(self.client.delete_collection, name=collection_name)

            logger.info(f"Deleted collection {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            return False

    async def _run_in_executor(self, func, *args, **kwargs):
        """
        Run a synchronous function in a thread pool executor.

        ChromaDB client is synchronous, so we need to run it in an executor
        to avoid blocking the async event loop.

        Args:
            func: Function to run
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from the function
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)


# Lazy singleton - only instantiated when actually needed
_chroma_adapter: ChromaAdapter | None = None
_chroma_lock = threading.Lock()


def get_chroma_adapter() -> ChromaAdapter:
    """Get or create the ChromaAdapter singleton.

    Uses lazy initialization with a lock to avoid connection errors at
    import time and prevent duplicate instances under concurrent access.
    """
    global _chroma_adapter
    if _chroma_adapter is None:
        with _chroma_lock:
            if _chroma_adapter is None:
                _chroma_adapter = ChromaAdapter()
    return _chroma_adapter


# Keep for backward compatibility but don't instantiate at import
chroma_adapter = None  # Use get_chroma_adapter() instead
