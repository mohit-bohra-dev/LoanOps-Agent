"""Merge shards into a Graph for CapabilityCatalog / query helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from packages.capability_kg.catalog import CapabilityCatalog
from packages.capability_kg.embed_index import EmbeddingEntry, embeddings_path_for_shards, load_index
from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.capability_kg.store import load_graph
from packages.eakg.pipeline_layout import graph_db_dir
from rdflib import Graph

EmbedFn = Callable[[str], Awaitable[list[float]]]


def merge_shards(
    shard_dir: str | Path,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    include_approved_only_catalog: bool = False,
) -> Graph:
    """Union GraphDb named-graph TTLs (file mode) into one Graph."""
    root = Path(shard_dir)
    flat = Graph()

    def _add(path: Path) -> None:
        if not path.is_file():
            return
        g = load_graph(path, namespace=namespace)
        for triple in g:
            flat.add(triple)

    gdir = graph_db_dir(root)
    if gdir.is_dir():
        for path in sorted(gdir.glob("*.ttl")):
            if ".evidence." in path.name:
                continue
            _add(path)
            _add(gdir / f"{path.stem}.evidence.ttl")

    # Legacy layout (tests / old fixtures)
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
        _add(gdir / "approved.ttl")
        _add(root / "catalog" / "approved.ttl")

    return flat


def _embeddings_from_store(shard_dir: str | Path) -> dict[str, EmbeddingEntry]:
    try:
        from packages.eakg.artifact_store import get_eakg_artifact_store

        arts = get_eakg_artifact_store()
        payload = arts.get_embeddings()
        if not isinstance(payload, dict):
            return {}
        items = payload.get("capabilities")
        if not isinstance(items, list):
            return {}
        out: dict[str, EmbeddingEntry] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            cid = item.get("id")
            vec = item.get("vector")
            if not isinstance(cid, str) or not isinstance(vec, list):
                continue
            floats = [float(v) for v in vec if isinstance(v, (int, float))]
            if len(floats) != len(vec):
                continue
            out[cid] = EmbeddingEntry(
                id=cid,
                text=str(item.get("text") or ""),
                text_hash=str(item.get("text_hash") or ""),
                vector=floats,
            )
        return out
    except Exception:  # noqa: BLE001
        return {}


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
    index: dict[str, EmbeddingEntry] = {}
    if semantic:
        index = _embeddings_from_store(shard_dir)
        if not index:
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
