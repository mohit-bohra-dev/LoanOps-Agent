"""Deterministic document link graph for one-hop retrieval expand."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


class DocLinkGraph:
    """Undirected adjacency over corpus-relative POSIX paths."""

    def __init__(self, edges: list[dict[str, str]] | None = None) -> None:
        self._adj: dict[str, set[str]] = defaultdict(set)
        for edge in edges or []:
            a = edge["from"].replace("\\", "/")
            b = edge["to"].replace("\\", "/")
            if a == b:
                continue
            self._adj[a].add(b)
            self._adj[b].add(a)

    @classmethod
    def from_json_file(cls, path: Path) -> DocLinkGraph:
        data = json.loads(path.read_text(encoding="utf-8"))
        edges = data.get("edges", [])
        if not isinstance(edges, list):
            raise ValueError(f"doc_links edges must be a list: {path}")
        return cls(edges)

    def neighbors(self, path: str) -> list[str]:
        key = path.replace("\\", "/")
        return sorted(self._adj.get(key, ()))


def build_doc_links(corpus_root: Path) -> dict[str, Any]:
    """Scan markdown under *corpus_root* for deterministic edges."""
    root = corpus_root.resolve()
    paths: list[str] = []
    by_category: dict[str, list[str]] = defaultdict(list)
    by_state: dict[str, list[str]] = defaultdict(list)
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def add_edge(a: str, b: str, kind: str) -> None:
        if a == b:
            return
        lo, hi = (a, b) if a < b else (b, a)
        key = (lo, hi, kind)
        if key in seen:
            return
        seen.add(key)
        edges.append({"from": a, "to": b, "kind": kind})

    for path in sorted(root.rglob("*.md")):
        if any(part.startswith("_") for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        paths.append(rel)
        parts = rel.split("/")
        category = parts[0] if len(parts) > 1 else ""
        if category:
            by_category[category].append(rel)
        if category == "state-specific" and len(parts) > 1:
            stem = parts[-1].removesuffix(".md").replace("-policy", "")
            by_state[stem].append(rel)

        text = path.read_text(encoding="utf-8")
        for match in _MD_LINK_RE.finditer(text):
            target = match.group(2).strip()
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            # Resolve relative to file dir
            raw = target.split("#", 1)[0].strip()
            if not raw.endswith(".md"):
                continue
            resolved = (path.parent / raw).resolve()
            try:
                target_rel = resolved.relative_to(root).as_posix()
            except ValueError:
                continue
            if target_rel in {p.relative_to(root).as_posix() for p in root.rglob("*.md")}:
                add_edge(rel, target_rel, "markdown_link")

    for _cat, members in by_category.items():
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                add_edge(a, b, "category")

    for _st, members in by_state.items():
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                add_edge(a, b, "state")

    # Hardship ↔ disaster / state overlays (lightweight SOP→theme joins)
    hardship = [p for p in paths if p.startswith("hardship/")]
    disaster = [p for p in paths if "disaster" in p]
    for h in hardship:
        for d in disaster:
            add_edge(h, d, "category")

    edges.sort(key=lambda e: (e["kind"], e["from"], e["to"]))
    return {"version": 1, "edges": edges}


def write_doc_links(corpus_root: Path, out_path: Path) -> Path:
    payload = build_doc_links(corpus_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path
