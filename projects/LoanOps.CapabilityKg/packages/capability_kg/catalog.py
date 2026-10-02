"""Application-facing Capability Catalog (hides RDF/SPARQL)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from packages.capability_kg import sparql as sparql_q
from packages.capability_kg.embed_index import (
    EmbeddingEntry,
    embeddings_path_for_ttl,
    load_index,
    rank,
)
from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.capability_kg.store import load_graph
from rdflib import Graph

EmbedFn = Callable[[str], Awaitable[list[float]]]

_DROP_STATUS = frozenset({"rejected", "deprecated"})


@dataclass(frozen=True)
class CapabilityRecord:
    """Bounded capability view for agents / MCP — not a full graph dump."""

    id: str
    description: str | None
    operation_id: str | None
    read_only: bool | None
    review_status: str | None
    permission: str | None
    uri: str | None = None

    def summary_line(self) -> str:
        bits = [f"- capability: {self.id}"]
        if self.operation_id:
            bits.append(f"  operation_id: {self.operation_id}")
        if self.description:
            bits.append(f"  description: {self.description}")
        if self.read_only is not None:
            bits.append(f"  read_only: {self.read_only}")
        if self.permission:
            bits.append(f"  permission: {self.permission}")
        if self.review_status:
            bits.append(f"  review_status: {self.review_status}")
        return "\n".join(bits)


def _to_record(row: dict[str, str | bool | None]) -> CapabilityRecord:
    read = row.get("read_only")
    read_bool = read if isinstance(read, bool) else None
    return CapabilityRecord(
        id=str(row.get("id") or ""),
        description=str(row["description"]) if row.get("description") is not None else None,
        operation_id=str(row["operation_id"]) if row.get("operation_id") is not None else None,
        read_only=read_bool,
        review_status=str(row["review_status"]) if row.get("review_status") is not None else None,
        permission=str(row["permission"]) if row.get("permission") is not None else None,
        uri=str(row["uri"]) if row.get("uri") is not None else None,
    )


class CapabilityCatalog:
    """Facade over RDFLib graph. Load once; query without exposing triples."""

    def __init__(
        self,
        graph: Graph,
        *,
        namespace: str = DEFAULT_NAMESPACE,
        approved_only: bool = False,
        semantic: bool = False,
        embed_index: dict[str, EmbeddingEntry] | None = None,
        embed_query: EmbedFn | None = None,
    ) -> None:
        self._graph = graph
        self._namespace = namespace
        self._approved_only = approved_only
        self._semantic = semantic
        self._embed_index = embed_index or {}
        self._embed_query = embed_query

    @classmethod
    def from_ttl(
        cls,
        path: str | Path,
        *,
        namespace: str = DEFAULT_NAMESPACE,
        approved_only: bool = False,
        semantic: bool = False,
        embed_query: EmbedFn | None = None,
        embeddings_path: str | Path | None = None,
    ) -> CapabilityCatalog:
        ttl = Path(path)
        index: dict[str, EmbeddingEntry] = {}
        if semantic:
            side = Path(embeddings_path) if embeddings_path else embeddings_path_for_ttl(ttl)
            index = load_index(side)
        return cls(
            load_graph(ttl, namespace=namespace),
            namespace=namespace,
            approved_only=approved_only,
            semantic=semantic,
            embed_index=index,
            embed_query=embed_query,
        )

    def _filter(self, rows: list[CapabilityRecord]) -> list[CapabilityRecord]:
        kept: list[CapabilityRecord] = []
        for r in rows:
            status = (r.review_status or "").lower()
            if status in _DROP_STATUS:
                continue
            kept.append(r)
        if not self._approved_only:
            return kept
        allowed = {"approved", "published"}
        return [r for r in kept if (r.review_status or "").lower() in allowed]

    def _prefer_read_only(self, rows: list[CapabilityRecord]) -> list[CapabilityRecord]:
        """v1: prefer read-only; keep writes only if no read-only hits."""
        reads = [r for r in rows if r.read_only is True]
        return reads if reads else rows

    def _keyword_search(self, query: str, *, limit: int) -> list[CapabilityRecord]:
        rows = [
            _to_record(r)
            for r in sparql_q.search_by_needle(self._graph, query, namespace=self._namespace)
        ]
        return self._prefer_read_only(self._filter(rows))[:limit]

    async def search_capabilities(self, query: str, *, limit: int = 15) -> list[CapabilityRecord]:
        keyword = self._keyword_search(query, limit=max(limit * 3, 15))
        if (
            not self._semantic
            or not self._embed_index
            or self._embed_query is None
            or not query.strip()
        ):
            return keyword[:limit]

        try:
            qvec = await self._embed_query(query)
        except Exception:  # noqa: BLE001
            return keyword[:limit]

        by_id = {r.id: r for r in self.list_capabilities(limit=500)}
        keyword_ids = {r.id for r in keyword}
        ranked = rank(qvec, self._embed_index, top_k=max(limit * 3, 15))

        blended: list[tuple[CapabilityRecord, float]] = []
        for cid, cos in ranked:
            rec = by_id.get(cid) or self.get_capability(cid)
            if rec is None:
                continue
            status = (rec.review_status or "").lower()
            if status in _DROP_STATUS:
                continue
            if self._approved_only and status not in {"approved", "published"}:
                continue
            hit = 1.0 if cid in keyword_ids else 0.0
            score = 0.7 * cos + 0.3 * hit
            blended.append((rec, score))

        blended.sort(key=lambda x: x[1], reverse=True)
        ordered = self._prefer_read_only([r for r, _ in blended])
        if ordered:
            return ordered[:limit]
        return keyword[:limit]

    def get_capability(self, capability_id: str) -> CapabilityRecord | None:
        row = sparql_q.get_by_id(self._graph, capability_id, namespace=self._namespace)
        if row is None:
            return None
        rec = _to_record(row)
        filtered = self._filter([rec])
        return filtered[0] if filtered else None

    def find_capabilities_by_domain(self, domain: str, *, limit: int = 50) -> list[CapabilityRecord]:
        rows = [
            _to_record(r)
            for r in sparql_q.by_domain(self._graph, domain, namespace=self._namespace)
        ]
        return self._filter(rows)[:limit]

    def find_capabilities_by_permission(
        self, permission: str, *, limit: int = 50
    ) -> list[CapabilityRecord]:
        rows = [
            _to_record(r)
            for r in sparql_q.by_permission(self._graph, permission, namespace=self._namespace)
        ]
        return self._filter(rows)[:limit]

    def find_capabilities_by_application(
        self, application: str, *, limit: int = 50
    ) -> list[CapabilityRecord]:
        rows = [
            _to_record(r)
            for r in sparql_q.by_application(self._graph, application, namespace=self._namespace)
        ]
        return self._filter(rows)[:limit]

    async def find_capabilities_for_intent(
        self, intent: str, *, limit: int = 15
    ) -> list[CapabilityRecord]:
        """Natural-language intent → capabilities (semantic when enabled)."""
        return await self.search_capabilities(intent, limit=limit)

    def list_capabilities(self, *, limit: int = 100) -> list[CapabilityRecord]:
        rows = [_to_record(r) for r in sparql_q.list_all(self._graph, namespace=self._namespace)]
        return self._filter(rows)[:limit]
