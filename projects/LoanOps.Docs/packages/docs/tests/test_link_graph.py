"""Doc link graph + one-hop expand (doc-graphrag P3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from packages.docs.link_graph import DocLinkGraph, build_doc_links
from packages.docs.service import DocsService
from provider_contracts.embedding import EmbeddingResult
from provider_contracts.reranker import AbstractRerankerProvider, RerankResult
from provider_contracts.vector_store import VectorDocument
from provider_contracts.vector_store.mock import MockVectorStoreProvider


class _FakeEmbed:
    async def get_dimensions(self) -> int:
        return 3

    async def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(vector=[0.1, 0.2, 0.3], dimensions=3, model="fake")

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        return [await self.embed(t) for t in texts]


class _FakeReranker(AbstractRerankerProvider):
    async def rerank(self, query: str, documents: list[str]) -> list[RerankResult]:
        # Prefer documents that mention "disaster"
        scored = sorted(
            enumerate(documents),
            key=lambda iv: (0 if "disaster" in iv[1].lower() else 1, iv[0]),
        )
        return [RerankResult(index=i, score=float(100 - rank)) for rank, (i, _) in enumerate(scored)]


def test_build_doc_links_category_and_markdown(tmp_path: Path) -> None:
    hardship = tmp_path / "hardship"
    hardship.mkdir()
    (hardship / "forbearance.md").write_text(
        "# Forbearance\n\nSee [disaster](disaster-forbearance.md).\n",
        encoding="utf-8",
    )
    (hardship / "disaster-forbearance.md").write_text(
        "# Disaster\n\nDisaster forbearance.\n",
        encoding="utf-8",
    )
    payload = build_doc_links(tmp_path)
    kinds = {e["kind"] for e in payload["edges"]}
    assert "markdown_link" in kinds
    g = DocLinkGraph(payload["edges"])
    assert "hardship/disaster-forbearance.md" in g.neighbors("hardship/forbearance.md")


@pytest.mark.asyncio
async def test_search_one_hop_and_rerank() -> None:
    store = MockVectorStoreProvider()
    await store.create_collection("docs", 3)
    docs = [
        VectorDocument(
            id="a",
            embedding=[0.9, 0.0, 0.0],
            metadata={"path": "hardship/forbearance.md", "corpus": "sop"},
            text="Standard forbearance pauses payments.",
        ),
        VectorDocument(
            id="b",
            embedding=[0.1, 0.0, 0.0],
            metadata={"path": "hardship/disaster-forbearance.md", "corpus": "sop"},
            text="Disaster forbearance after a declared event.",
        ),
    ]
    await store.upsert(docs, namespace="docs")

    graph = DocLinkGraph(
        [
            {
                "from": "hardship/forbearance.md",
                "to": "hardship/disaster-forbearance.md",
                "kind": "markdown_link",
            }
        ]
    )
    svc = DocsService(
        _FakeEmbed(),
        store,
        reranker=_FakeReranker(),
        link_graph=graph,
        candidate_k=5,
    )
    # Force top hit to be forbearance by making its vector closer — mock scores by cosine.
    text = await svc.search("disaster options", top_k=2)
    assert "hardship/disaster-forbearance.md" in text
    assert "hardship/forbearance.md" in text
