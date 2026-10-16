"""Louvain determinism + extractive summary + route."""

from __future__ import annotations

from pathlib import Path

from packages.graph_rag.communities import (
    build_community_records,
    graph_from_doc_links,
    louvain_communities,
)
from packages.graph_rag.route import select_route


def test_select_route_global_hints() -> None:
    assert select_route("Compare CA and TX hardship") == "global"
    assert select_route("What is the late fee waiver?") == "local"


def test_louvain_seed_deterministic() -> None:
    edges = [
        {"from": "a/x.md", "to": "a/y.md", "kind": "category"},
        {"from": "a/y.md", "to": "a/z.md", "kind": "category"},
        {"from": "b/1.md", "to": "b/2.md", "kind": "category"},
    ]
    g = graph_from_doc_links(edges)
    a = louvain_communities(g, seed=42)
    b = louvain_communities(g, seed=42)
    assert a == b
    assert len(a) >= 1


def test_build_community_records(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "x.md").write_text("# X\nhello world\n", encoding="utf-8")
    (tmp_path / "a" / "y.md").write_text("# Y\nhello there\n", encoding="utf-8")
    edges = [{"from": "a/x.md", "to": "a/y.md", "kind": "category"}]
    records = build_community_records(edges, tmp_path)
    assert len(records) == 1
    assert records[0]["id"] == "c0000"
    assert set(records[0]["member_paths"]) == {"a/x.md", "a/y.md"}
    assert "hello" in records[0]["summary"].lower()
