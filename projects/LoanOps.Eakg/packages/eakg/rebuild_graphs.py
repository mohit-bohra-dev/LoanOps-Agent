"""Rebuild RDF + GraphDB named graphs from stored interface.json (no re-extract)."""

from __future__ import annotations

from typing import Any

from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.common.providers.graph_store import AbstractGraphStore
from packages.eakg.graph_build import interface_to_graph
from packages.eakg.graph_upload import upload_graph
from packages.eakg.store import ShardStore


async def rebuild_graphs_from_interfaces(
    store: ShardStore,
    graph_store: AbstractGraphStore,
    repository_ids: list[str],
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, Any]:
    """Re-materialize graph.ttl / evidence.ttl from interface.json and upload."""
    report: dict[str, Any] = {}
    for rid in repository_ids:
        iface = store.read_interface(rid)
        if iface is None:
            report[rid] = {"status": "missing_interface"}
            continue
        g, eg = interface_to_graph(iface, namespace=namespace)
        store.write_graph(rid, g)
        store.write_evidence(rid, eg)
        iri = await upload_graph(
            graph_store, rid, g, namespace=namespace, evidence=eg
        )
        report[rid] = {
            "status": "ok",
            "named_graph": iri,
            "triples": len(g) + len(eg),
            "proxies": len(iface.proxies),
            "packages": len(iface.packages),
        }
    return report
