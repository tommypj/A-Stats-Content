"""
Embedding service for generating text embeddings.

Supports OpenAI embeddings via API or mock embeddings for development.
"""

import hashlib
import logging
from enum import Enum
from typing import List, Optional

import httpx


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    MOCK = "mock"

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Exception raised for embedding errors."""

    pass


class EmbeddingService:
    """
    Service for generating text embeddings.

    Uses OpenAI's embedding API or a simple hash-based mock for development.
    """

    OPENAI_EMBEDDING_URL = "https://api.openai.com/v1/embeddings"

    # Model dimensions
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"
    ):
        """
        Initialize embedding service.

        Args:
            api_key: OpenAI API key (defaults to settings.openai_api_key)
            model: Embedding model to use (defaults to settings.embedding_model)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.embedding_model

        if not self.api_key:
            logger.warning(
                "OpenAI API key not provided. Using mock embeddings for development."
            )

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not self.api_key:
            return await self.embed_text_mock(text)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.OPENAI_EMBEDDING_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"input": text, "model": self.model},
                    timeout=30.0,
                )

                response.raise_for_status()
                data = response.json()

                items = data.get("data") or []
                if not items:
                    raise EmbeddingError("OpenAI API returned no embedding data")
                embedding = items[0].get("embedding")
                if embedding is None:
                    raise EmbeddingError("OpenAI API returned no embedding vector")
                logger.debug(f"Generated embedding for text of length {len(text)}")
                return embedding

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
            raise EmbeddingError(f"Failed to generate embedding: {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batched).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            return []

        if not self.api_key:
            return [await self.embed_text_mock(text) for text in texts]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.OPENAI_EMBEDDING_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"input": texts, "model": self.model},
                    timeout=60.0,
                )

                response.raise_for_status()
                data = response.json()

                embeddings = [item["embedding"] for item in data["data"]]
                logger.info(
                    f"Generated {len(embeddings)} embeddings using model {self.model}"
                )
                return embeddings

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
            raise EmbeddingError(f"Failed to generate embeddings: {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating embeddings: {e}")
            raise EmbeddingError(f"Batch embedding generation failed: {e}")

    async def embed_text_mock(self, text: str) -> List[float]:
        """
        Generate mock embedding for development without API key.

        Uses a deterministic hash-based approach to generate embeddings.
        These are not semantically meaningful but are consistent for the same text.

        Args:
            text: Text to embed

        Returns:
            Mock embedding vector
        """
        dimension = self.MODEL_DIMENSIONS.get(self.model, 1536)

        # Generate deterministic "embedding" from text hash
        text_hash = hashlib.sha256(text.encode()).digest()

        # Expand hash to full dimension by repeating and normalizing
        embedding = []
        for i in range(dimension):
            # Use hash bytes cyclically to generate values
            byte_val = text_hash[i % len(text_hash)]
            # Normalize to [-1, 1] range
            normalized = (byte_val / 255.0) * 2 - 1
            embedding.append(normalized)

        logger.debug(f"Generated mock embedding with dimension {dimension}")
        return embedding

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.

        Returns:
            Embedding dimension
        """
        return self.MODEL_DIMENSIONS.get(self.model, 1536)


# Singleton instance
embedding_service = EmbeddingService()
