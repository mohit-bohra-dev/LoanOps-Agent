"""Cached CapabilityCatalog over EAKG shards (fingerprint invalidation)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from packages.capability_kg.catalog import CapabilityCatalog
from packages.capability_kg.embed_index import embeddings_path_for_shards, load_index
from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.eakg.merge import merge_shards
from rdflib import Graph

EmbedFn = Callable[[str], Awaitable[list[float]]]

FileStamp = tuple[str, int, int]  # path, mtime_ns, size


def _stamp(path: Path) -> FileStamp | None:
    if not path.is_file():
        return None
    st = path.stat()
    return (str(path.resolve()), st.st_mtime_ns, st.st_size)


def shard_fingerprint(shard_dir: str | Path) -> tuple[FileStamp, ...]:
    """Stable fingerprint of shard files that feed merge_shards / catalog."""
    root = Path(shard_dir)
    paths: list[Path] = []
    repos = root / "repos"
    if repos.is_dir():
        for repo_dir in sorted(repos.iterdir()):
            if not repo_dir.is_dir():
                continue
            paths.append(repo_dir / "graph.ttl")
            paths.append(repo_dir / "evidence.ttl")
    ent = root / "enterprise"
    paths.append(ent / "applications.ttl")
    paths.append(ent / "cross_app.ttl")
    paths.append(ent / "embeddings.json")
    paths.append(root / "catalog" / "approved.ttl")
    stamps: list[FileStamp] = []
    for p in paths:
        s = _stamp(p)
        if s is not None:
            stamps.append(s)
    return tuple(stamps)


def use_semantic(*, semantic_flag: bool, shard_dir: str | Path) -> bool:
    """Unified rule: explicit flag or embeddings sidecar present."""
    return semantic_flag or embeddings_path_for_shards(shard_dir).is_file()


@dataclass
class _Cache:
    fingerprint: tuple[FileStamp, ...]
    approved_only: bool
    semantic: bool
    namespace: str
    graph: Graph
    catalog: CapabilityCatalog


class CapabilityCatalogService:
    """Lazy merge of EAKG shards; rebuilds only when fingerprint changes."""

    def __init__(
        self,
        shard_dir: str | Path,
        *,
        namespace: str = DEFAULT_NAMESPACE,
        approved_only: bool = False,
        semantic: bool = False,
        embed_query: EmbedFn | None = None,
        enabled: bool = True,
    ) -> None:
        self._shard_dir = Path(shard_dir)
        self._namespace = namespace
        self._approved_only = approved_only
        self._semantic_flag = semantic
        self._embed_query = embed_query
        self._enabled = enabled
        self._cache: _Cache | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def shard_dir(self) -> Path:
        return self._shard_dir

    def fingerprint(self) -> tuple[FileStamp, ...]:
        return shard_fingerprint(self._shard_dir)

    def semantic_enabled(self) -> bool:
        return use_semantic(semantic_flag=self._semantic_flag, shard_dir=self._shard_dir)

    def _rebuild(self) -> _Cache:
        fp = self.fingerprint()
        semantic = self.semantic_enabled()
        graph = merge_shards(
            self._shard_dir,
            namespace=self._namespace,
            include_approved_only_catalog=self._approved_only,
        )
        index = {}
        if semantic:
            index = load_index(embeddings_path_for_shards(self._shard_dir))
        catalog = CapabilityCatalog(
            graph,
            namespace=self._namespace,
            approved_only=self._approved_only,
            semantic=semantic,
            embed_index=index,
            embed_query=self._embed_query if semantic else None,
        )
        return _Cache(
            fingerprint=fp,
            approved_only=self._approved_only,
            semantic=semantic,
            namespace=self._namespace,
            graph=graph,
            catalog=catalog,
        )

    def _ensure(self) -> _Cache | None:
        if not self._enabled:
            return None
        if not self._shard_dir.is_dir():
            return None
        fp = self.fingerprint()
        semantic = self.semantic_enabled()
        cached = self._cache
        if (
            cached is not None
            and cached.fingerprint == fp
            and cached.approved_only == self._approved_only
            and cached.semantic == semantic
            and cached.namespace == self._namespace
        ):
            return cached
        self._cache = self._rebuild()
        return self._cache

    def graph(self) -> Graph | None:
        """Merged RDF graph, or None when disabled / missing shards."""
        cache = self._ensure()
        return None if cache is None else cache.graph

    def catalog(self) -> CapabilityCatalog | None:
        """CapabilityCatalog facade, or None when disabled / missing shards."""
        cache = self._ensure()
        return None if cache is None else cache.catalog

    def capability_count(self) -> int:
        cat = self.catalog()
        if cat is None:
            return 0
        return len(cat.list_capabilities(limit=10_000))
