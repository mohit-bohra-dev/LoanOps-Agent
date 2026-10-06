"""Merge shards into a Graph for CapabilityCatalog / query helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from packages.capability_kg.catalog import CapabilityCatalog
from packages.capability_kg.embed_index import embeddings_path_for_shards, load_index
from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.capability_kg.store import load_graph
from rdflib import Graph

EmbedFn = Callable[[str], Awaitable[list[float]]]


def merge_shards(
    shard_dir: str | Path,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    include_approved_only_catalog: bool = False,
) -> Graph:
    """Union all repo graphs + enterprise + optional approved catalog into one Graph."""
    root = Path(shard_dir)
    flat = Graph()

    def _add(path: Path) -> None:
        if not path.is_file():
            return
        g = load_graph(path, namespace=namespace)
        for triple in g:
            flat.add(triple)

    repos = root / "repos"
    if repos.is_dir():
        for repo_dir in sorted(repos.iterdir()):
            if not repo_dir.is_dir():
                continue
            _add(repo_dir / "graph.ttl")
            _add(repo_dir / "evidence.ttl")

    ent = root / "enterprise"
    _add(ent / "applications.ttl")
    _add(ent / "cross_app.ttl")

    if include_approved_only_catalog:
        _add(root / "catalog" / "approved.ttl")

    return flat


def catalog_from_shards(
    shard_dir: str | Path,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    approved_only: bool = False,
    semantic: bool = False,
    embed_query: EmbedFn | None = None,
    embeddings_path: str | Path | None = None,
) -> CapabilityCatalog:
    """CapabilityCatalog over merged shards (facade unchanged for MCP)."""
    index = {}
    if semantic:
        side = (
            Path(embeddings_path)
            if embeddings_path is not None
            else embeddings_path_for_shards(shard_dir)
        )
        index = load_index(side)
    return CapabilityCatalog(
        merge_shards(shard_dir, namespace=namespace),
        namespace=namespace,
        approved_only=approved_only,
        semantic=semantic,
        embed_index=index,
        embed_query=embed_query,
    )
