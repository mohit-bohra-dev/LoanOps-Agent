"""Docs ingest CLI writes via DocsService only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from packages.common.providers.embedding import EmbeddingResult
from packages.common.providers.vector_store import VectorDocument
from packages.docs.ingest import ingest_sops


class _Emb:
    async def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(vector=[0.1, 0.2], dimensions=2, model="test")

    async def get_dimensions(self) -> int:
        return 2


class _Store:
    def __init__(self) -> None:
        self.docs: list[VectorDocument] = []

    async def create_collection(self, namespace: str, vector_size: int) -> None:
        return None

    async def upsert(
        self, documents: list[VectorDocument], *, namespace: str
    ) -> None:
        self.docs.extend(documents)

    async def search(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []


@pytest.mark.asyncio
async def test_ingest_sops_indexes_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "escrow.md").write_text("# Escrow\n\nShortage rules.\n", encoding="utf-8")
    store = _Store()
    monkeypatch.setattr(
        "packages.docs.ingest.get_embedding_provider", lambda: _Emb()
    )
    monkeypatch.setattr(
        "packages.docs.ingest.get_vector_store_provider", lambda: store
    )
    count = await ingest_sops(tmp_path)
    assert count >= 1
    assert store.docs
    assert all((d.metadata or {}).get("corpus") == "sop" for d in store.docs)
