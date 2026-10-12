"""EAKG capability search block for search_sse_apis (SPARQL store, ADR-026)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from packages.common.providers.graph_store import AbstractGraphStore, GraphStoreError
from packages.common.settings import Settings

CapabilityBlock = Callable[[str, int], Awaitable[str | None]]


def make_sparql_capability_search_block(
    store: AbstractGraphStore,
    *,
    namespace: str,
    enabled: bool = True,
) -> CapabilityBlock:
    """Return a capability_block closure bound to the SPARQL graph store."""

    async def eakg_capability_search_block(query: str, limit: int = 15) -> str | None:
        if not enabled:
            return None
        from packages.eakg.query import search_capabilities

        try:
            rows = await search_capabilities(
                store, query, namespace=namespace, limit=limit
            )
        except GraphStoreError:
            return None
        if not rows:
            return None
        lines = ["Capabilities (EAKG):"]
        for row in rows:
            cid = row.get("id") or row.get("operation_id") or ""
            lines.append(f"- capability: {cid}")
            if row.get("operation_id"):
                lines.append(f"  operation_id: {row['operation_id']}")
            if row.get("http_path"):
                lines.append(f"  http_path: {row['http_path']}")
            if row.get("http_method"):
                lines.append(f"  http_method: {row['http_method']}")
            if row.get("application"):
                lines.append(f"  application: {row['application']}")
        return "\n".join(lines)

    return eakg_capability_search_block


def make_eakg_capability_search_block(
    service: object,
) -> CapabilityBlock:
    """Backward-compatible name: ignore shard service; use ``get_graph_store()``."""
    _ = service
    from packages.common.providers.factory import get_graph_store
    from packages.common.settings import get_settings

    settings = get_settings()
    return make_sparql_capability_search_block(
        get_graph_store(),
        namespace=settings.capability_kg.namespace,
        enabled=settings.capability_kg.enabled,
    )


async def eakg_capability_search_block(query: str, limit: int = 15) -> str | None:
    """Default block from settings + graph store."""
    from packages.common.providers.factory import get_graph_store
    from packages.common.settings import get_settings

    settings: Settings = get_settings()
    cfg = settings.capability_kg
    if not cfg.enabled:
        return None
    block = make_sparql_capability_search_block(
        get_graph_store(),
        namespace=cfg.namespace,
        enabled=True,
    )
    return await block(query, limit)
