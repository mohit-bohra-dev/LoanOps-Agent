"""Docs search — one vector index for SOPs + wiki narratives."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.rag.chunker import MarkdownChunker
from provider_contracts.embedding import AbstractEmbeddingProvider as EmbeddingProvider
from provider_contracts.vector_store import (
    AbstractVectorStoreProvider as VectorStoreProvider,
)
from provider_contracts.vector_store import VectorDocument

DOCS_NAMESPACE = "docs"
DOCS_TOOL_NAMES = ("search_docs", "index_docs")


class DocsService:
    """Index and search written documentation via provider_contracts ABCs."""

    def __init__(
        self,
        embedding: EmbeddingProvider,
        vector_store: VectorStoreProvider,
        *,
        namespace: str = DOCS_NAMESPACE,
    ) -> None:
        self._embedding = embedding
        self._store = vector_store
        self._namespace = namespace
        self._chunker = MarkdownChunker()

    async def ensure_collection(self) -> None:
        dims = await self._embedding.get_dimensions()
        await self._store.create_collection(self._namespace, dims)

    async def index_markdown_file(
        self,
        path: Path,
        *,
        corpus: str = "sop",
        extra_metadata: dict[str, Any] | None = None,
    ) -> int:
        text = path.read_text(encoding="utf-8")
        meta = {"corpus": corpus, "path": str(path), **(extra_metadata or {})}
        chunks = self._chunker.chunk(text, meta)
        docs: list[VectorDocument] = []
        for chunk in chunks:
            emb = await self._embedding.embed(chunk.content)
            docs.append(
                VectorDocument(
                    id=chunk.chunk_id,
                    embedding=emb.vector,
                    metadata={**chunk.metadata, "corpus": corpus},
                    text=chunk.content,
                )
            )
        if docs:
            await self._store.upsert(docs, namespace=self._namespace)
        return len(docs)

    async def index_directory(self, root: Path, *, corpus: str = "sop") -> int:
        total = 0
        for path in sorted(root.rglob("*.md")):
            if any(part.startswith("_") for part in path.parts):
                continue
            total += await self.index_markdown_file(path, corpus=corpus)
        return total

    async def search(self, query: str, *, top_k: int = 5) -> str:
        emb = await self._embedding.embed(query)
        hits = await self._store.search(
            emb.vector,
            query_text=query,
            namespace=self._namespace,
            top_k=top_k,
        )
        if not hits:
            return "No matching documents."
        lines: list[str] = []
        for hit in hits:
            path = (hit.metadata or {}).get("path", hit.id)
            corpus = (hit.metadata or {}).get("corpus", "docs")
            snippet = (hit.text or "")[:400]
            lines.append(
                f"- [{corpus}] {path} (score={hit.score:.3f})\n  {snippet}"
            )
        return "\n".join(lines)
