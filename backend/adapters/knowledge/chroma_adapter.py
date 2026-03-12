"""
ChromaDB adapter for vector storage and retrieval.

Provides interface for storing and querying document embeddings using ChromaDB HTTP client.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import chromadb

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Document to be stored in vector database."""

    id: str
    content: str
    metadata: dict[str, Any]  # source_id, title, chunk_index, user_id, etc.


@dataclass
class QueryResult:
    """Result from vector similarity search."""

    document_id: str
    content: str
    metadata: dict[str, Any]
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
        host: str | None = None,
        port: int | None = None,
        collection_prefix: str | None = None,
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
            logger.info("ChromaDB client connected to %s:%s", self.host, self.port)
        except Exception as e:
            logger.error("Failed to connect to ChromaDB: %s", e)
            raise ChromaDBConnectionError(
                f"Could not connect to ChromaDB at {self.host}:{self.port}: {e}"
            )

    def _legacy_collection_name(self, user_id: str) -> str:
        """Pre-CHROMA-C1 collection name: single bucket per user, no project scope."""
        return f"{self.collection_prefix}_{user_id}"

    def _try_get_legacy_collection(self, user_id: str) -> "chromadb.Collection | None":
        """
        Return the legacy (pre-CHROMA-C1) collection if it exists and has documents,
        otherwise return None.  Never raises.
        """
        try:
            col = self.client.get_collection(name=self._legacy_collection_name(user_id))
            if col.count() > 0:
                return col
        except Exception:
            pass
        return None

    def get_collection(self, user_id: str, project_id: str = "personal") -> chromadb.Collection:
        """
        Get or create a project-scoped collection.

        Collection names follow the scheme ``{prefix}_{user_id}_{project_id}``.
        Use ``"personal"`` for the personal workspace.

        Args:
            user_id: User ID
            project_id: Project ID (use ``"personal"`` for personal/non-project sources)

        Returns:
            ChromaDB Collection instance
        """
        collection_name = f"{self.collection_prefix}_{user_id}_{project_id}"

        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},  # Use cosine similarity
            )
            logger.debug("Retrieved collection: %s", collection_name)
            return collection
        except Exception as e:
            logger.error("Failed to get collection %s: %s", collection_name, e)
            raise ChromaDBError(f"Could not get collection: {e}")

    async def add_documents(
        self,
        user_id: str,
        documents: list[Document],
        embeddings: list[list[float]],
        project_id: str = "personal",
    ) -> list[str]:
        """
        Add documents with their embeddings to the collection.

        Args:
            user_id: User ID
            documents: List of documents to add
            embeddings: List of embedding vectors (must match documents length)
            project_id: Project ID for collection isolation (default ``"personal"``)

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
            collection = self.get_collection(user_id, project_id)

            # Prepare data for ChromaDB
            ids = [doc.id for doc in documents]
            contents = [doc.content for doc in documents]
            metadatas = [doc.metadata for doc in documents]

            # ChromaDB add is synchronous, run in executor
            await self._run_in_executor(
                collection.add,
                ids=ids,
                documents=contents,
                embeddings=embeddings,
                metadatas=metadatas,
            )

            logger.info(
                "Added %s documents to collection for user %s / project %s",
                len(documents), user_id, project_id,
            )
            return ids

        except Exception as e:
            logger.error("Failed to add documents to collection: %s", e)
            raise ChromaDBError(f"Could not add documents: {e}")

    async def query(
        self,
        user_id: str,
        query_embedding: list[float],
        n_results: int = 5,
        filter_metadata: dict | None = None,
        project_id: str = "personal",
    ) -> list[QueryResult]:
        """
        Query similar documents using vector similarity.

        Args:
            user_id: User ID
            query_embedding: Query embedding vector
            n_results: Number of results to return
            filter_metadata: Optional metadata filter (e.g., {"source_id": "document_123"})
            project_id: Project ID for collection isolation (default ``"personal"``)

        Returns:
            List of query results sorted by similarity (most similar first)

        Raises:
            ChromaDBError: If query fails
        """
        try:
            collection = self.get_collection(user_id, project_id)

            # CHROMA-C1 migration fallback: if the new project-scoped collection
            # is empty, transparently fall back to the legacy per-user collection
            # so existing knowledge bases keep working until sources are re-processed.
            new_count = await self._run_in_executor(collection.count)
            if new_count == 0:
                legacy = await self._run_in_executor(
                    self._try_get_legacy_collection, user_id
                )
                if legacy is not None:
                    logger.warning(
                        "Collection %r_%s_%s is empty — falling back to legacy "
                        "collection %r (%d docs). Re-process knowledge sources to migrate.",
                        self.collection_prefix, user_id, project_id,
                        self._legacy_collection_name(user_id),
                        legacy.count(),
                    )
                    collection = legacy

            # Query is synchronous, run in executor
            results = await self._run_in_executor(
                collection.query,
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata,
            )

            # Parse results
            query_results = []
            if results and results.get("ids") and results["ids"][0]:
                ids = results["ids"][0]
                documents = results.get("documents", [[]])[0] if results.get("documents") else []
                metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
                distances = results.get("distances", [[]])[0] if results.get("distances") else []
                for i, doc_id in enumerate(ids):
                    query_results.append(
                        QueryResult(
                            document_id=doc_id,
                            content=documents[i] if i < len(documents) else "",
                            metadata=metadatas[i] if i < len(metadatas) else {},
                            score=1.0 - distances[i] if i < len(distances) else 0.0,
                        )
                    )

            logger.debug(
                "Query returned %s results for user %s / project %s",
                len(query_results), user_id, project_id,
            )
            return query_results

        except Exception as e:
            logger.error("Failed to query collection: %s", e)
            raise ChromaDBError(f"Query failed: {e}")

    async def delete_document(
        self, user_id: str, document_id: str, project_id: str = "personal"
    ) -> bool:
        """
        Delete a document from the collection.

        Args:
            user_id: User ID
            document_id: Document ID to delete
            project_id: Project ID for collection isolation (default ``"personal"``)

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            collection = self.get_collection(user_id, project_id)

            # Delete is synchronous, run in executor
            await self._run_in_executor(collection.delete, ids=[document_id])

            logger.info(
                "Deleted document %s from collection for user %s / project %s",
                document_id, user_id, project_id,
            )
            return True

        except Exception as e:
            logger.error("Failed to delete document %s: %s", document_id, e)
            return False

    async def delete_by_source(
        self, user_id: str, source_id: str, project_id: str = "personal"
    ) -> int:
        """
        Delete all chunks from a source document.

        Args:
            user_id: User ID
            source_id: Source document ID
            project_id: Project ID for collection isolation (default ``"personal"``)

        Returns:
            Number of documents deleted
        """
        try:
            collection = self.get_collection(user_id, project_id)

            # Delete by metadata filter
            await self._run_in_executor(collection.delete, where={"source_id": source_id})

            logger.info(
                "Deleted all documents with source_id=%s for user %s / project %s",
                source_id, user_id, project_id,
            )
            # Note: ChromaDB doesn't return count of deleted items
            return 1  # Return 1 to indicate success

        except Exception as e:
            logger.error("Failed to delete documents by source %s: %s", source_id, e)
            return 0

    async def get_collection_stats(
        self, user_id: str, project_id: str = "personal"
    ) -> dict[str, Any]:
        """
        Get stats about a user/project collection.

        Args:
            user_id: User ID
            project_id: Project ID for collection isolation (default ``"personal"``)

        Returns:
            Dictionary with collection statistics
        """
        try:
            collection = self.get_collection(user_id, project_id)
            count = await self._run_in_executor(collection.count)

            # If new collection is empty, report legacy count so callers know
            # data exists but needs re-processing.
            legacy_count = 0
            if count == 0:
                legacy = await self._run_in_executor(
                    self._try_get_legacy_collection, user_id
                )
                if legacy is not None:
                    legacy_count = await self._run_in_executor(legacy.count)

            return {
                "collection_name": f"{self.collection_prefix}_{user_id}_{project_id}",
                "document_count": count + legacy_count,
                "user_id": user_id,
                "project_id": project_id,
                # Present so callers can show a migration hint in the UI
                "legacy_docs": legacy_count,
            }

        except Exception as e:
            logger.error("Failed to get collection stats: %s", e)
            raise ChromaDBError(f"Could not get collection stats: {e}")

    async def delete_collection(self, user_id: str, project_id: str = "personal") -> bool:
        """
        Delete an entire project-scoped collection.

        Args:
            user_id: User ID
            project_id: Project ID for collection isolation (default ``"personal"``)

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            collection_name = f"{self.collection_prefix}_{user_id}_{project_id}"

            # Delete is synchronous, run in executor
            await self._run_in_executor(self.client.delete_collection, name=collection_name)

            logger.info("Deleted collection %s", collection_name)
            return True

        except Exception as e:
            logger.error("Failed to delete collection: %s", e)
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

        loop = asyncio.get_running_loop()
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
