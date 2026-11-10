"""Docs search — one vector index for SOPs + wiki narratives."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from packages.docs.link_graph import DocLinkGraph
from packages.rag.chunker import MarkdownChunker
from packages.common.providers.embedding import EmbeddingProvider
from packages.common.providers.reranker import RerankerProvider
from packages.common.providers.vector_store import (
    SearchResult,
    VectorDocument,
    VectorStoreProvider,
)

DOCS_NAMESPACE = "docs"
DOCS_TOOL_NAMES = ("search_docs", "index_docs")

# Frozen chunk metadata keys (doc-graphrag P1). Changing the set requires re-index.
FROZEN_META_KEYS = ("corpus", "path", "category", "state", "heading_path")

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal YAML-ish front-matter: ``key: value`` lines only."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    out: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip("\"'")
        if key:
            out[key] = val
    return out


def relative_corpus_path(path: Path, corpus_root: Path) -> str:
    """POSIX path relative to corpus root — stable across machines."""
    try:
        return path.resolve().relative_to(corpus_root.resolve()).as_posix()
    except ValueError:
        return path.name.replace("\\", "/")


def build_chunk_metadata(
    *,
    corpus: str,
    rel_path: str,
    frontmatter: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Frozen metadata schema for indexed chunks."""
    fm = frontmatter or {}
    parts = rel_path.split("/")
    category = fm.get("category") or (parts[0] if len(parts) > 1 else "")
    state = fm.get("state", "")
    if not state and parts and parts[0] == "state-specific" and len(parts) > 1:
        stem = parts[-1].removesuffix(".md")
        state = stem.replace("-policy", "").replace("_", "-")
    meta: dict[str, Any] = {
        "corpus": corpus,
        "path": rel_path.replace("\\", "/"),
        "category": category,
        "state": state,
        "heading_path": fm.get("heading_path", ""),
    }
    if extra:
        for k, v in extra.items():
            if k == "path" and isinstance(v, str):
                meta["path"] = v.replace("\\", "/")
            elif k in FROZEN_META_KEYS and k != "path":
                meta[k] = v
            elif k not in FROZEN_META_KEYS:
                meta[k] = v
    return meta


class DocsService:
    """Index and search written documentation via provider_contracts ABCs."""

    def __init__(
        self,
        embedding: EmbeddingProvider,
        vector_store: VectorStoreProvider,
        *,
        namespace: str = DOCS_NAMESPACE,
        reranker: RerankerProvider | None = None,
        link_graph: DocLinkGraph | None = None,
        candidate_k: int = 20,
    ) -> None:
        self._embedding = embedding
        self._store = vector_store
        self._namespace = namespace
        self._chunker = MarkdownChunker()
        self._reranker = reranker
        self._link_graph = link_graph
        self._candidate_k = candidate_k

    async def ensure_collection(self) -> None:
        dims = await self._embedding.get_dimensions()
        await self._store.create_collection(self._namespace, dims)

    async def index_markdown_text(
        self,
        text: str,
        *,
        rel_path: str,
        corpus: str = "sop",
        extra_metadata: dict[str, Any] | None = None,
    ) -> int:
        """Index markdown body (live Confluence / cache) into the docs namespace."""
        fm = _parse_frontmatter(text)
        meta = build_chunk_metadata(
            corpus=corpus,
            rel_path=rel_path.replace("\\", "/"),
            frontmatter=fm,
            extra=extra_metadata,
        )
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

    async def index_markdown_file(
        self,
        path: Path,
        *,
        corpus: str = "sop",
        corpus_root: Path | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> int:
        text = path.read_text(encoding="utf-8")
        root = corpus_root if corpus_root is not None else path.parent
        rel = relative_corpus_path(path, root)
        return await self.index_markdown_text(
            text,
            rel_path=rel,
            corpus=corpus,
            extra_metadata=extra_metadata,
        )

    async def index_directory(self, root: Path, *, corpus: str = "sop") -> int:
        total = 0
        root = root.resolve()
        for path in sorted(root.rglob("*.md")):
            # Skip underscore dirs under the corpus (e.g. nested drafts).
            # Do not skip when the corpus root itself is named _confluence.
            try:
                rel_parts = path.relative_to(root).parts
            except ValueError:
                continue
            if any(part.startswith("_") for part in rel_parts[:-1]):
                continue
            total += await self.index_markdown_file(
                path, corpus=corpus, corpus_root=root
            )
        return total

    async def _fetch_by_path(
        self, query_vector: list[float], path: str
    ) -> SearchResult | None:
        hits = await self._store.search(
            query_vector,
            namespace=self._namespace,
            top_k=1,
            filter={"path": path},
        )
        return hits[0] if hits else None

    async def search(self, query: str, *, top_k: int = 5) -> str:
        from contextlib import asynccontextmanager
        from collections.abc import AsyncIterator

        @asynccontextmanager
        async def _docs_span(name: str, **attrs: Any) -> AsyncIterator[Any]:
            try:
                from packages.common.providers.factory import get_telemetry_provider

                tel = get_telemetry_provider()
                async with tel.span(name, attributes=dict(attrs), kind="subtool") as ctx:
                    yield ctx
                return
            except Exception:  # noqa: BLE001
                pass
            from packages.common.providers.telemetry import trace_span

            async with trace_span(name, attributes=dict(attrs), kind="subtool") as ctx:
                yield ctx

        async with _docs_span("docs.embed", query_len=len(query)) as emb_span:
            emb = await self._embedding.embed(query)
            emb_span.output = {"dims": len(emb.vector) if emb.vector else 0}

        retrieve_k = self._candidate_k if self._reranker is not None else top_k
        async with _docs_span(
            "docs.vector_search",
            retrieve_k=retrieve_k,
            query=query[:200],
        ) as vs_span:
            hits = await self._store.search(
                emb.vector,
                query_text=query,
                namespace=self._namespace,
                top_k=retrieve_k,
            )
            hit_paths = [
                {
                    "path": str((h.metadata or {}).get("path") or h.id),
                    "score": float(h.score),
                }
                for h in hits[:10]
            ]
            vs_span.attributes["hit_count"] = len(hits)
            vs_span.attributes["hits"] = hit_paths
            vs_span.output = {"hit_count": len(hits), "hits": hit_paths}

        by_path: dict[str, SearchResult] = {}
        for hit in hits:
            p = str((hit.metadata or {}).get("path") or hit.id)
            by_path.setdefault(p, hit)

        if self._link_graph is not None and by_path:
            async with _docs_span("docs.link_expand") as link_span:
                seed_paths = list(by_path.keys())[:3]
                added = 0
                for seed in seed_paths:
                    for neighbor in self._link_graph.neighbors(seed):
                        if neighbor in by_path:
                            continue
                        fetched = await self._fetch_by_path(emb.vector, neighbor)
                        if fetched is not None:
                            by_path[neighbor] = fetched
                            added += 1
                link_span.attributes["seed_count"] = len(seed_paths)
                link_span.attributes["added_neighbors"] = added
                link_span.output = {
                    "seed_count": len(seed_paths),
                    "added_neighbors": added,
                }

        candidates = list(by_path.values())
        if not candidates:
            return "No matching documents."

        if self._reranker is not None and len(candidates) > 1:
            async with _docs_span(
                "docs.rerank",
                candidate_count=len(candidates),
            ) as rr_span:
                docs_text = [c.text or "" for c in candidates]
                ranked = await self._reranker.rerank(query, docs_text)
                ordered: list[SearchResult] = []
                for rr in ranked:
                    if 0 <= rr.index < len(candidates):
                        ordered.append(candidates[rr.index])
                seen_ids = {o.id for o in ordered}
                for c in candidates:
                    if c.id not in seen_ids:
                        ordered.append(c)
                candidates = ordered
                top = [
                    {
                        "path": str((c.metadata or {}).get("path") or c.id),
                        "score": float(c.score),
                    }
                    for c in candidates[:10]
                ]
                rr_span.attributes["hits"] = top
                rr_span.output = {"hits": top}

        lines: list[str] = []
        for hit in candidates[:top_k]:
            path = (hit.metadata or {}).get("path", hit.id)
            corpus = (hit.metadata or {}).get("corpus", "docs")
            snippet = (hit.text or "")[:400]
            lines.append(
                f"- [{corpus}] {path} (score={hit.score:.3f})\n  {snippet}"
            )
        return "\n".join(lines)
