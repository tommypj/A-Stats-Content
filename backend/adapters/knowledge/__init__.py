"""
Knowledge vault adapters for document processing and RAG.
"""

from .chroma_adapter import (
    ChromaAdapter,
    ChromaDBConnectionError,
    ChromaDBError,
    Document,
    QueryResult,
    get_chroma_adapter,
)
from .document_processor import (
    DocumentProcessor,
    DocumentType,
    ProcessedChunk,
    ProcessedDocument,
    document_processor,
)
from .embedding_service import (
    EmbeddingError,
    EmbeddingService,
    embedding_service,
)

__all__ = [
    # ChromaDB
    "ChromaAdapter",
    "ChromaDBError",
    "ChromaDBConnectionError",
    "Document",
    "QueryResult",
    "get_chroma_adapter",
    # Embeddings
    "EmbeddingService",
    "EmbeddingError",
    "embedding_service",
    # Document Processing
    "DocumentProcessor",
    "DocumentType",
    "ProcessedChunk",
    "ProcessedDocument",
    "document_processor",
]
