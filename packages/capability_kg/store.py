"""Load / save RDF graphs as Turtle."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph

from packages.capability_kg.ontology import DEFAULT_NAMESPACE, loanops_ns


def load_graph(path: str | Path, *, namespace: str = DEFAULT_NAMESPACE) -> Graph:
    """Load Turtle from disk. Empty graph if file missing."""
    graph = Graph()
    ns = loanops_ns(namespace)
    graph.bind("loanops", ns)
    graph.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
    p = Path(path)
    if p.is_file():
        graph.parse(p, format="turtle")
    return graph


def save_graph(graph: Graph, path: str | Path) -> Path:
    """Serialize graph to Turtle, creating parent dirs."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(graph.serialize(format="turtle"), encoding="utf-8")
    return p
