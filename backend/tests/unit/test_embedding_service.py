"""
Unit tests for Embedding Service.

Tests cover:
- Text embedding generation
- Batch processing
- Mock fallback mode
- Error handling
- Dimension consistency
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

# Skip if service not implemented yet
pytest.importorskip("adapters.knowledge.embedding_service", reason="Embedding service not yet implemented")

from adapters.knowledge.embedding_service import (
    EmbeddingService,
    EmbeddingError,
    EmbeddingProvider,
)


class TestEmbeddingService:
    """Tests for EmbeddingService."""

    @pytest.fixture
    def mock_openai_client(self):
        """Create mock OpenAI client."""
        client = AsyncMock()
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3, 0.4, 0.5])
        ]
        client.embeddings.create = AsyncMock(return_value=mock_response)
        return client

    @pytest.fixture
    def service_with_openai(self, mock_openai_client):
        """Create EmbeddingService with mocked OpenAI."""
        with patch('adapters.knowledge.embedding_service.AsyncOpenAI', return_value=mock_openai_client):
            service = EmbeddingService(
                provider=EmbeddingProvider.OPENAI,
                api_key="test-key",
                model="text-embedding-3-small"
            )
        return service

    @pytest.fixture
    def service_with_mock(self):
        """Create EmbeddingService in mock mode (no API key)."""
        service = EmbeddingService(
            provider=EmbeddingProvider.MOCK,
            api_key=None,
            model="mock"
        )
        return service

    @pytest.mark.asyncio
    async def test_embed_text_success(self, service_with_openai, mock_openai_client):
        """Test successful text embedding."""
        text = "This is a test document about cognitive therapy."

        embedding = await service_with_openai.embed_text(text)

        # Verify API was called
        mock_openai_client.embeddings.create.assert_called_once()
        call_args = mock_openai_client.embeddings.create.call_args[1]
        assert call_args['input'] == text
        assert call_args['model'] == "text-embedding-3-small"

        # Verify embedding format
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, (int, float)) for x in embedding)

    @pytest.mark.asyncio
    async def test_embed_texts_batch(self, service_with_openai, mock_openai_client):
        """Test batch embedding of multiple texts."""
        texts = [
            "First document about mindfulness.",
            "Second document about CBT techniques.",
            "Third document about stress management."
        ]

        # Mock batch response
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3]),
            Mock(embedding=[0.4, 0.5, 0.6]),
            Mock(embedding=[0.7, 0.8, 0.9])
        ]
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        embeddings = await service_with_openai.embed_texts(texts)

        # Verify batch API call
        mock_openai_client.embeddings.create.assert_called_once()
        call_args = mock_openai_client.embeddings.create.call_args[1]
        assert call_args['input'] == texts

        # Verify results
        assert len(embeddings) == 3
        assert all(isinstance(emb, list) for emb in embeddings)

    @pytest.mark.asyncio
    async def test_embed_text_mock_fallback(self, service_with_mock):
        """Test mock embedding generation (no API call)."""
        text = "Test document for mock embeddings."

        embedding = await service_with_mock.embed_text(text)

        # Verify mock embedding
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        # Mock embeddings should be deterministic for same input
        embedding2 = await service_with_mock.embed_text(text)
        assert embedding == embedding2

    @pytest.mark.asyncio
    async def test_embed_text_api_error(self, service_with_openai, mock_openai_client):
        """Test handling of API errors."""
        # Simulate API error
        mock_openai_client.embeddings.create.side_effect = Exception("API rate limit exceeded")

        text = "Test document"

        with pytest.raises(EmbeddingError, match="API rate limit exceeded"):
            await service_with_openai.embed_text(text)

    @pytest.mark.asyncio
    async def test_embedding_dimension_consistency(self, service_with_openai, mock_openai_client):
        """Test that all embeddings have consistent dimensions."""
        texts = ["Short.", "Medium length text.", "This is a longer document with more content."]

        # Mock responses with consistent dimensions
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 1536),
            Mock(embedding=[0.2] * 1536),
            Mock(embedding=[0.3] * 1536)
        ]
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        embeddings = await service_with_openai.embed_texts(texts)

        # All embeddings should have same dimension
        dimensions = [len(emb) for emb in embeddings]
        assert len(set(dimensions)) == 1  # All same
        assert dimensions[0] == 1536  # OpenAI text-embedding-3-small dimension

    @pytest.mark.asyncio
    async def test_embed_empty_text(self, service_with_openai):
        """Test handling of empty text."""
        text = ""

        with pytest.raises(ValueError, match="empty"):
            await service_with_openai.embed_text(text)

    @pytest.mark.asyncio
    async def test_embed_whitespace_only(self, service_with_openai):
        """Test handling of whitespace-only text."""
        text = "   \n\n   \t\t   "

        with pytest.raises(ValueError, match="empty"):
            await service_with_openai.embed_text(text)

    @pytest.mark.asyncio
    async def test_embed_texts_batch_size_limit(self, service_with_openai, mock_openai_client):
        """Test that large batches are split appropriately."""
        # Create 100 texts (assuming batch limit is 50)
        texts = [f"Document {i}" for i in range(100)]

        # Mock responses
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3]) for _ in range(50)]
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        embeddings = await service_with_openai.embed_texts(texts, batch_size=50)

        # Should make 2 API calls (100 / 50)
        assert mock_openai_client.embeddings.create.call_count == 2
        assert len(embeddings) == 100

    @pytest.mark.asyncio
    async def test_mock_embedding_deterministic(self, service_with_mock):
        """Test that mock embeddings are deterministic."""
        text = "Consistent test document"

        embedding1 = await service_with_mock.embed_text(text)
        embedding2 = await service_with_mock.embed_text(text)

        # Same input should produce same output
        assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_mock_embedding_different_for_different_text(self, service_with_mock):
        """Test that different texts produce different mock embeddings."""
        text1 = "First document"
        text2 = "Second document"

        embedding1 = await service_with_mock.embed_text(text1)
        embedding2 = await service_with_mock.embed_text(text2)

        # Different texts should produce different embeddings
        assert embedding1 != embedding2


class TestEmbeddingProviders:
    """Tests for different embedding providers."""

    @pytest.mark.asyncio
    async def test_openai_provider_configuration(self):
        """Test OpenAI provider configuration."""
        with patch('adapters.knowledge.embedding_service.AsyncOpenAI') as mock_openai:
            service = EmbeddingService(
                provider=EmbeddingProvider.OPENAI,
                api_key="test-api-key",
                model="text-embedding-3-large"
            )

            # Verify client was initialized with correct key
            mock_openai.assert_called_once_with(api_key="test-api-key")

    @pytest.mark.asyncio
    async def test_anthropic_provider_not_implemented(self):
        """Test that non-implemented providers raise error."""
        with pytest.raises(NotImplementedError, match="Anthropic"):
            service = EmbeddingService(
                provider=EmbeddingProvider.ANTHROPIC,
                api_key="test-key"
            )

    @pytest.mark.asyncio
    async def test_mock_provider_no_api_key_required(self):
        """Test that mock provider doesn't require API key."""
        # Should not raise error
        service = EmbeddingService(
            provider=EmbeddingProvider.MOCK,
            api_key=None
        )

        text = "Test"
        embedding = await service.embed_text(text)
        assert isinstance(embedding, list)


class TestEmbeddingServiceUtils:
    """Tests for utility functions in EmbeddingService."""

    @pytest.fixture
    def service(self):
        """Create mock service."""
        return EmbeddingService(provider=EmbeddingProvider.MOCK)

    def test_normalize_embedding(self, service):
        """Test embedding normalization."""
        embedding = [3.0, 4.0]  # Length = 5

        normalized = service.normalize(embedding)

        # Should be unit vector
        length = sum(x**2 for x in normalized) ** 0.5
        assert abs(length - 1.0) < 0.0001

    def test_cosine_similarity(self, service):
        """Test cosine similarity calculation."""
        emb1 = [1.0, 0.0, 0.0]
        emb2 = [1.0, 0.0, 0.0]
        emb3 = [0.0, 1.0, 0.0]

        # Identical vectors
        sim1 = service.cosine_similarity(emb1, emb2)
        assert abs(sim1 - 1.0) < 0.0001

        # Orthogonal vectors
        sim2 = service.cosine_similarity(emb1, emb3)
        assert abs(sim2 - 0.0) < 0.0001

    @pytest.mark.asyncio
    async def test_retry_logic_on_transient_error(self, mock_openai_client):
        """Test that service retries on transient errors."""
        with patch('adapters.knowledge.embedding_service.AsyncOpenAI', return_value=mock_openai_client):
            service = EmbeddingService(
                provider=EmbeddingProvider.OPENAI,
                api_key="test-key",
                max_retries=3
            )

            # Fail twice, then succeed
            mock_response = Mock()
            mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
            mock_openai_client.embeddings.create.side_effect = [
                Exception("Temporary error"),
                Exception("Temporary error"),
                mock_response
            ]

            embedding = await service.embed_text("Test")

            # Should succeed after retries
            assert len(embedding) == 3
            assert mock_openai_client.embeddings.create.call_count == 3
