"""Louvain communities over deterministic doc_links (seeded)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import networkx as nx  # type: ignore[import-untyped]
from networkx.algorithms.community import louvain_partitions  # type: ignore[import-untyped]

LOUVAIN_SEED = 42
SUMMARIES_NAMESPACE = "graphrag_summaries"


def graph_from_doc_links(edges: list[dict[str, str]]) -> nx.Graph:
    """Build undirected graph; nodes inserted in sorted order for determinism."""
    g = nx.Graph()
    nodes: set[str] = set()
    for edge in edges:
        a = edge["from"].replace("\\", "/")
        b = edge["to"].replace("\\", "/")
        nodes.add(a)
        nodes.add(b)
    for n in sorted(nodes):
        g.add_node(n)
    for edge in edges:
        a = edge["from"].replace("\\", "/")
        b = edge["to"].replace("\\", "/")
        if a != b:
            g.add_edge(a, b)
    return g


def louvain_communities(g: nx.Graph, *, seed: int = LOUVAIN_SEED) -> list[frozenset[str]]:
    """Level-0 Louvain partition; communities sorted by min member path."""
    if g.number_of_nodes() == 0:
        return []
    parts = list(louvain_partitions(g, seed=seed))
    level0 = parts[0] if parts else []
    communities = [frozenset(c) for c in level0]
    communities.sort(key=lambda c: min(c) if c else "")
    return communities


def extractive_summary(paths: list[str], corpus_root: Path, *, max_chars: int = 800) -> str:
    """First non-empty lines from each member file, capped."""
    parts: list[str] = []
    budget = max_chars
    for rel in sorted(paths):
        if budget <= 0:
            break
        file_path = corpus_root / rel
        if not file_path.is_file():
            continue
        text = file_path.read_text(encoding="utf-8")
        # Strip front-matter
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                text = text[end + 4 :]
        snippet = " ".join(text.split())[: min(200, budget)]
        if snippet:
            parts.append(f"{rel}: {snippet}")
            budget -= len(snippet)
    return " | ".join(parts) if parts else f"Community: {', '.join(sorted(paths)[:5])}"


def corpus_hash(corpus_root: Path) -> str:
    """Stable hash of sorted relative paths + file bytes under corpus_root."""
    h = hashlib.sha256()
    root = corpus_root.resolve()
    for path in sorted(root.rglob("*.md")):
        if any(part.startswith("_") for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def build_community_records(
    edges: list[dict[str, str]],
    corpus_root: Path,
    *,
    seed: int = LOUVAIN_SEED,
) -> list[dict[str, Any]]:
    """Louvain → extractive community records (paths as member ids for P4)."""
    g = graph_from_doc_links(edges)
    communities = louvain_communities(g, seed=seed)
    records: list[dict[str, Any]] = []
    for i, members in enumerate(communities):
        paths = sorted(members)
        records.append(
            {
                "id": f"c{i:04d}",
                "member_paths": paths,
                # P4: path doubles as retrieval key; chunk ids filled at embed time if known.
                "member_chunk_ids": list(paths),
                "summary": extractive_summary(paths, corpus_root),
            }
        )
    return records


def load_doc_links(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    edges = data.get("edges", [])
    if not isinstance(edges, list):
        raise ValueError(f"doc_links edges must be a list: {path}")
    return edges
