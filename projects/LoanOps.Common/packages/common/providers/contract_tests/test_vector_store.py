"""Contract tests for the vector store provider."""

import pytest
from packages.common.providers.testing import MockVectorStoreProvider
from packages.common.providers.vector_store import (
    SearchResult,
    VectorDocument,
    VectorStoreProvider,
)


@pytest.fixture
def provider() -> VectorStoreProvider:
    return MockVectorStoreProvider()


class TestVectorStoreProviderContract:
    """Every VectorStoreProvider implementation must pass these tests."""

    async def test_isinstance(self, provider: VectorStoreProvider) -> None:
        assert isinstance(provider, VectorStoreProvider)

    async def test_upsert_and_search(self, provider: VectorStoreProvider) -> None:
        docs = [
            VectorDocument(id="1", embedding=[1.0, 0.0, 0.0], text="hello"),
            VectorDocument(id="2", embedding=[0.0, 1.0, 0.0], text="world"),
        ]
        await provider.upsert(docs)
        results = await provider.search([1.0, 0.0, 0.0], top_k=2)
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        # The closest match to [1,0,0] should be doc "1"
        assert results[0].id == "1"

    async def test_delete(self, provider: VectorStoreProvider) -> None:
        docs = [VectorDocument(id="del-1", embedding=[1.0, 0.0], text="to delete")]
        await provider.upsert(docs)
        await provider.delete(["del-1"])
        results = await provider.search([1.0, 0.0], top_k=5)
        ids = [r.id for r in results]
        assert "del-1" not in ids

    async def test_namespace_isolation(self, provider: VectorStoreProvider) -> None:
        doc_a = [VectorDocument(id="a1", embedding=[1.0], text="ns-a")]
        doc_b = [VectorDocument(id="b1", embedding=[1.0], text="ns-b")]
        await provider.upsert(doc_a, namespace="ns-a")
        await provider.upsert(doc_b, namespace="ns-b")
        results_a = await provider.search([1.0], namespace="ns-a", top_k=5)
        assert len(results_a) == 1
        assert results_a[0].id == "a1"
