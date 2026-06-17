"""Contract tests for the embedding provider."""

import pytest

from packages.common.providers.embedding import EmbeddingProvider, EmbeddingResult
from packages.common.providers.testing import MockEmbeddingProvider


@pytest.fixture
def provider() -> EmbeddingProvider:
    return MockEmbeddingProvider()


class TestEmbeddingProviderContract:
    """Every EmbeddingProvider implementation must pass these tests."""

    async def test_isinstance(self, provider: EmbeddingProvider) -> None:
        assert isinstance(provider, EmbeddingProvider)

    async def test_embed_returns_embedding_result(self, provider: EmbeddingProvider) -> None:
        result = await provider.embed("test sentence")
        assert isinstance(result, EmbeddingResult)
        assert isinstance(result.vector, list)
        assert len(result.vector) == result.dimensions
        assert result.model == "mock"

    async def test_embed_batch_returns_list(self, provider: EmbeddingProvider) -> None:
        texts = ["hello", "world"]
        results = await provider.embed_batch(texts)
        assert len(results) == 2
        assert all(isinstance(r, EmbeddingResult) for r in results)

    async def test_embed_deterministic(self, provider: EmbeddingProvider) -> None:
        r1 = await provider.embed("same input")
        r2 = await provider.embed("same input")
        assert r1.vector == r2.vector
