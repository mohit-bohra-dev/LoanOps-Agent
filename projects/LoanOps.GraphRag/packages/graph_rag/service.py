"""GraphRagService — wrap DocsService with optional community summary routing."""

from __future__ import annotations

from typing import Literal

from packages.docs.service import DOCS_NAMESPACE, DocsService
from packages.graph_rag.artifact import ArtifactStatus, GraphRagArtifact, load_artifact
from packages.graph_rag.communities import SUMMARIES_NAMESPACE
from packages.graph_rag.route import Route, select_route
from packages.common.providers.embedding import EmbeddingProvider
from packages.common.providers.vector_store import SearchResult, VectorStoreProvider

DocsSearchMode = Literal[
    "flat", "rerank_hop", "graphrag_local", "graphrag_global", "graphrag_degraded"
]


class GraphRagService:
    """Same ``search`` signature as DocsService; route is internal only."""

    def __init__(
        self,
        docs: DocsService,
        embedding: EmbeddingProvider,
        vector_store: VectorStoreProvider,
        artifact: GraphRagArtifact,
        *,
        summary_namespace: str = SUMMARIES_NAMESPACE,
        docs_namespace: str = DOCS_NAMESPACE,
    ) -> None:
        self._docs = docs
        self._embedding = embedding
        self._store = vector_store
        self._artifact = artifact
        self._summary_ns = summary_namespace
        self._docs_ns = docs_namespace
        self._by_id = {
            str(c["id"]): c for c in artifact.communities if isinstance(c.get("id"), str)
        }
        self.artifact_status: ArtifactStatus = artifact.status
        self.last_mode: DocsSearchMode = "graphrag_degraded"

    @classmethod
    def maybe_wrap(
        cls,
        docs: DocsService,
        embedding: EmbeddingProvider,
        vector_store: VectorStoreProvider,
        artifact_dir: str,
        *,
        expected_corpus_hash: str | None = None,
    ) -> DocsService | GraphRagService:
        """Wrap when artifact present and usable; else return DocsService unchanged."""
        from pathlib import Path

        artifact = load_artifact(
            Path(artifact_dir), expected_corpus_hash=expected_corpus_hash
        )
        if artifact.status in ("absent", "corrupt"):
            return docs
        # stale still wraps but search always degrades to docs (FR-012)
        return cls(docs, embedding, vector_store, artifact)

    def health(self) -> dict[str, str]:
        if self.artifact_status != "ok":
            mode: DocsSearchMode = "graphrag_degraded"
        else:
            mode = self.last_mode
        return {
            "docs_search": mode,
            "graphrag_artifact": self.artifact_status,
        }

    async def search(self, query: str, *, top_k: int = 5) -> str:
        if self.artifact_status != "ok":
            self.last_mode = "graphrag_degraded"
            return await self._docs.search(query, top_k=top_k)

        route: Route = select_route(query)
        if route == "local":
            self.last_mode = "graphrag_local"
            return await self._docs.search(query, top_k=top_k)

        self.last_mode = "graphrag_global"
        try:
            return await self._global_search(query, top_k=top_k)
        except Exception:  # noqa: BLE001 — never raise through /chat
            self.last_mode = "graphrag_degraded"
            return await self._docs.search(query, top_k=top_k)

    async def _global_search(self, query: str, *, top_k: int) -> str:
        emb = await self._embedding.embed(query)
        hits = await self._store.search(
            emb.vector,
            query_text=query,
            namespace=self._summary_ns,
            top_k=min(3, max(1, top_k)),
        )
        if not hits:
            self.last_mode = "graphrag_local"
            return await self._docs.search(query, top_k=top_k)

        member_paths: list[str] = []
        summaries: list[str] = []
        seen: set[str] = set()
        for hit in hits:
            meta = hit.metadata or {}
            cid = str(meta.get("community_id") or hit.id)
            rec = self._by_id.get(cid)
            summary = str((rec or {}).get("summary") or hit.text or "")
            if summary:
                summaries.append(summary)
            paths = list((rec or {}).get("member_paths") or meta.get("member_paths") or [])
            for p in paths:
                ps = str(p).replace("\\", "/")
                if ps not in seen:
                    seen.add(ps)
                    member_paths.append(ps)

        citable = await self._fetch_members(emb.vector, member_paths, top_k=top_k)
        if not citable:
            # Fall back to local if members not in vector store
            self.last_mode = "graphrag_local"
            return await self._docs.search(query, top_k=top_k)

        lines: list[str] = []
        for hit in citable:
            path = (hit.metadata or {}).get("path", hit.id)
            corpus = (hit.metadata or {}).get("corpus", "docs")
            snippet = (hit.text or "")[:400]
            lines.append(f"- [{corpus}] {path} (score={hit.score:.3f})\n  {snippet}")

        if summaries:
            lines.append("")
            lines.append("## context (not citable)")
            for s in summaries[:2]:
                lines.append(f"Community summary: {s[:600]}")

        return "\n".join(lines)

    async def _fetch_members(
        self, query_vector: list[float], paths: list[str], *, top_k: int
    ) -> list[SearchResult]:
        out: list[SearchResult] = []
        for path in paths:
            if len(out) >= top_k:
                break
            hits = await self._store.search(
                query_vector,
                namespace=self._docs_ns,
                top_k=1,
                filter={"path": path},
            )
            if hits:
                out.append(hits[0])
        return out


__all__ = ["GraphRagService", "DocsSearchMode"]
