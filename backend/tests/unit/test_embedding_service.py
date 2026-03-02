"""
Unit tests for Embedding Service.

Tests cover:
- Text embedding generation via httpx (OpenAI API)
- Batch processing
- Mock fallback mode (no API key)
- Error handling
- Dimension consistency
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip if service not implemented yet
pytest.importorskip(
    "adapters.knowledge.embedding_service", reason="Embedding service not yet implemented"
)

from adapters.knowledge.embedding_service import (
    EmbeddingError,
    EmbeddingProvider,
    EmbeddingService,
)


def _make_openai_response(embeddings: list[list[float]]):
    """Build a mock httpx response matching OpenAI embedding API shape."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "data": [{"embedding": emb} for emb in embeddings],
        "model": "text-embedding-3-small",
        "usage": {"prompt_tokens": 10, "total_tokens": 10},
    }
    return mock_response


class TestEmbeddingService:
    """Tests for EmbeddingService with mocked httpx calls."""

    @pytest.mark.asyncio
    async def test_embed_text_success(self):
        """Test successful text embedding via OpenAI API."""
        embedding_vec = [0.1] * 1536
        mock_response = _make_openai_response([embedding_vec])

        with patch("adapters.knowledge.embedding_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_client

            service = EmbeddingService(api_key="test-key", model="text-embedding-3-small")
            result = await service.embed_text("Test document")

        assert isinstance(result, list)
        assert len(result) == 1536
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_texts_batch(self):
        """Test batch embedding of multiple texts."""
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        mock_response = _make_openai_response(embeddings)

        with patch("adapters.knowledge.embedding_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_client

            service = EmbeddingService(api_key="test-key")
            results = await service.embed_texts(["text1", "text2", "text3"])

        assert len(results) == 3
        assert all(isinstance(emb, list) for emb in results)
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_text_mock_fallback(self):
        """Test mock embedding generation (no API key)."""
        with patch("adapters.knowledge.embedding_service.settings") as mock_settings:
            mock_settings.openai_api_key = None
            mock_settings.embedding_model = "text-embedding-3-small"
            service = EmbeddingService(api_key=None)

        embedding = await service.embed_text("Test document for mock embeddings.")

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        # Mock embeddings should be deterministic for same input
        embedding2 = await service.embed_text("Test document for mock embeddings.")
        assert embedding == embedding2

    @pytest.mark.asyncio
    async def test_embed_text_api_error(self):
        """Test handling of API errors raises EmbeddingError."""
        import httpx

        mock_request = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Rate limit exceeded"

        with patch("adapters.knowledge.embedding_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "rate limit", request=mock_request, response=mock_resp
                )
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_client

            service = EmbeddingService(api_key="test-key")
            with pytest.raises(EmbeddingError):
                await service.embed_text("Test document")

    @pytest.mark.asyncio
    async def test_embedding_dimension_consistency(self):
        """Test that all embeddings have consistent dimensions."""
        embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]
        mock_response = _make_openai_response(embeddings)

        with patch("adapters.knowledge.embedding_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_client

            service = EmbeddingService(api_key="test-key")
            results = await service.embed_texts(["short", "medium text", "longer text here"])

        dimensions = [len(emb) for emb in results]
        assert len(set(dimensions)) == 1
        assert dimensions[0] == 1536

    @pytest.mark.asyncio
    async def test_embed_texts_empty_list(self):
        """Test batch embed with empty list returns empty list."""
        service = EmbeddingService(api_key="test-key")
        result = await service.embed_texts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_mock_embedding_deterministic(self):
        """Test that mock embeddings are deterministic."""
        with patch("adapters.knowledge.embedding_service.settings") as mock_settings:
            mock_settings.openai_api_key = None
            mock_settings.embedding_model = "text-embedding-3-small"
            service = EmbeddingService(api_key=None)

        embedding1 = await service.embed_text("Consistent test document")
        embedding2 = await service.embed_text("Consistent test document")
        assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_mock_embedding_different_for_different_text(self):
        """Test that different texts produce different mock embeddings."""
        with patch("adapters.knowledge.embedding_service.settings") as mock_settings:
            mock_settings.openai_api_key = None
            mock_settings.embedding_model = "text-embedding-3-small"
            service = EmbeddingService(api_key=None)

        embedding1 = await service.embed_text("First document")
        embedding2 = await service.embed_text("Second document")
        assert embedding1 != embedding2


class TestEmbeddingProviders:
    """Tests for embedding provider enum and service modes."""

    def test_provider_enum_values(self):
        """Test EmbeddingProvider enum has expected values."""
        assert EmbeddingProvider.OPENAI.value == "openai"
        assert EmbeddingProvider.MOCK.value == "mock"

    def test_service_uses_mock_without_api_key(self):
        """Test that service defaults to mock mode when no API key is provided."""
        with patch("adapters.knowledge.embedding_service.settings") as mock_settings:
            mock_settings.openai_api_key = None
            mock_settings.embedding_model = "text-embedding-3-small"
            service = EmbeddingService(api_key=None)

        assert not service.api_key

    def test_service_uses_openai_with_api_key(self):
        """Test that service uses OpenAI when API key is provided."""
        service = EmbeddingService(api_key="test-key")
        assert service.api_key == "test-key"

    def test_get_embedding_dimension(self):
        """Test get_embedding_dimension returns correct dimensions."""
        service = EmbeddingService(api_key="test-key", model="text-embedding-3-small")
        assert service.get_embedding_dimension() == 1536

        service2 = EmbeddingService(api_key="test-key", model="text-embedding-3-large")
        assert service2.get_embedding_dimension() == 3072
