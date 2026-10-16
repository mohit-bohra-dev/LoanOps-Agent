"""GraphRagService fallback + global formatting."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.graph_rag.artifact import GraphRagArtifact, write_artifact
from packages.graph_rag.service import GraphRagService
from packages.common.providers.vector_store import SearchResult


def _docs_mock() -> MagicMock:
    docs = MagicMock()
    docs.search = AsyncMock(return_value="- [sop] local.md (score=0.9)\n  local hit")
    return docs


@pytest.mark.asyncio
async def test_degraded_on_absent_artifact() -> None:
    docs = _docs_mock()
    emb = MagicMock()
    store = MagicMock()
    artifact = GraphRagArtifact(communities=[], manifest={}, status="absent")
    svc = GraphRagService(docs, emb, store, artifact)
    out = await svc.search("compare forbearance options")
    assert "local hit" in out
    assert svc.health()["graphrag_artifact"] == "absent"
    assert svc.health()["docs_search"] == "graphrag_degraded"


@pytest.mark.asyncio
async def test_maybe_wrap_absent_returns_docs(tmp_path: Any) -> None:
    docs = _docs_mock()
    emb = MagicMock()
    store = MagicMock()
    wrapped = GraphRagService.maybe_wrap(docs, emb, store, str(tmp_path / "missing"))
    assert wrapped is docs


@pytest.mark.asyncio
async def test_global_search_citable_plus_summary(tmp_path: Any) -> None:
    write_artifact(
        tmp_path,
        communities=[
            {
                "id": "c0000",
                "member_paths": ["hardship/a.md"],
                "member_chunk_ids": ["hardship/a.md"],
                "summary": "Community about forbearance",
            }
        ],
        corpus_hash="abc",
    )
    artifact = GraphRagArtifact(
        communities=[
            {
                "id": "c0000",
                "member_paths": ["hardship/a.md"],
                "member_chunk_ids": ["hardship/a.md"],
                "summary": "Community about forbearance",
            }
        ],
        manifest={"corpus_hash": "abc"},
        status="ok",
    )
    docs = _docs_mock()
    emb = MagicMock()
    emb.embed = AsyncMock(return_value=MagicMock(vector=[0.1, 0.2]))
    store = MagicMock()

    async def _search(
        _vec: list[float],
        *,
        namespace: str = "",
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
        query_text: str | None = None,
    ) -> list[SearchResult]:
        _ = (top_k, query_text)
        if namespace == "graphrag_summaries":
            return [
                SearchResult(
                    id="c0000",
                    score=0.8,
                    text="Community about forbearance",
                    metadata={"community_id": "c0000", "member_paths": ["hardship/a.md"]},
                )
            ]
        if filter and filter.get("path") == "hardship/a.md":
            return [
                SearchResult(
                    id="chunk1",
                    score=0.7,
                    text="Forbearance may pause payments.",
                    metadata={"path": "hardship/a.md", "corpus": "sop"},
                )
            ]
        return []

    store.search = AsyncMock(side_effect=_search)
    svc = GraphRagService(docs, emb, store, artifact)
    out = await svc.search("compare disaster vs standard forbearance", top_k=3)
    assert "hardship/a.md" in out
    assert "context (not citable)" in out
    assert "Community summary:" in out
    assert svc.last_mode == "graphrag_global"
