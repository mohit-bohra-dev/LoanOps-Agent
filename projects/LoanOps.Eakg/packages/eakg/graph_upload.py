"""Upload RDFLib graphs to the SPARQL named-graph store (ADR-026)."""

from __future__ import annotations

from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.common.providers.graph_store import (
    AbstractGraphStore,
    named_graph_iri,
)
from rdflib import Graph


async def upload_graph(
    store: AbstractGraphStore,
    repository_id: str,
    graph: Graph,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    evidence: Graph | None = None,
) -> str:
    """Replace the named graph for ``repository_id`` (union of graph + evidence)."""
    combined = Graph()
    for triple in graph:
        combined.add(triple)
    if evidence is not None:
        for triple in evidence:
            combined.add(triple)
    turtle = combined.serialize(format="turtle")
    if isinstance(turtle, bytes):
        turtle = turtle.decode("utf-8")
    iri = named_graph_iri(repository_id, namespace=namespace)
    await store.replace_named_graph(iri, turtle)
    return iri
