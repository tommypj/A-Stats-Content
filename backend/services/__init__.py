"""
Service layer for business logic.
"""

from functools import lru_cache
from typing import Optional

from adapters.knowledge import ChromaAdapter, EmbeddingService, DocumentProcessor
from adapters.ai.anthropic_adapter import AnthropicContentService
from infrastructure.config.settings import settings
from services.knowledge_service import KnowledgeService


@lru_cache
def get_knowledge_service() -> KnowledgeService:
    """
    Get singleton knowledge service instance.

    Returns:
        Configured KnowledgeService instance
    """
    # Initialize ChromaDB adapter
    chroma = ChromaAdapter(
        collection_prefix=settings.chroma_collection_prefix,
    )

    # Initialize embedding service
    # Note: Requires OPENAI_API_KEY environment variable
    openai_key = getattr(settings, "openai_api_key", None)
    embeddings = EmbeddingService(
        api_key=openai_key,
        model="text-embedding-3-small",
    )

    # Initialize document processor
    processor = DocumentProcessor(
        chunk_size=1000,
        chunk_overlap=200,
    )

    # Initialize Anthropic adapter
    anthropic = AnthropicContentService()

    return KnowledgeService(
        chroma_adapter=chroma,
        embedding_service=embeddings,
        document_processor=processor,
        anthropic_adapter=anthropic,
    )


__all__ = [
    "KnowledgeService",
    "get_knowledge_service",
    "scheduler_service",
    "post_queue",
]
