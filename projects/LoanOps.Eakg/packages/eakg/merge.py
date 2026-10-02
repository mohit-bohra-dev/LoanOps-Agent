"""Merge shards into a Graph for CapabilityCatalog / query helpers."""

from __future__ import annotations

from pathlib import Path

from packages.capability_kg.catalog import CapabilityCatalog
from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.capability_kg.store import load_graph
from rdflib import Graph


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
    embed_query: object | None = None,
) -> CapabilityCatalog:
    """CapabilityCatalog over merged shards (facade unchanged for MCP)."""
    return CapabilityCatalog(
        merge_shards(shard_dir, namespace=namespace),
        namespace=namespace,
        approved_only=approved_only,
        semantic=semantic,
        embed_query=embed_query,  # type: ignore[arg-type]
    )
