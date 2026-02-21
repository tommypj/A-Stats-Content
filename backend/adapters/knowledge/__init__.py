"""
Knowledge vault adapters for document processing and RAG.
"""

from .chroma_adapter import (
    ChromaAdapter,
    ChromaDBError,
    ChromaDBConnectionError,
    Document,
    QueryResult,
    get_chroma_adapter,
)
from .embedding_service import (
    EmbeddingService,
    EmbeddingError,
    embedding_service,
)
from .document_processor import (
    DocumentProcessor,
    DocumentType,
    ProcessedChunk,
    ProcessedDocument,
    document_processor,
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
