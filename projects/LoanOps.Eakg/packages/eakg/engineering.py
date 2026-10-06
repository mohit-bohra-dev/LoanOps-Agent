"""Project EAKG operations onto Graphify AST nodes; one-hop callers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.eakg.join import eakg_operation_local_name, join_key
from packages.eakg.models import ApiOperationFact, RepoInterface


def _posix(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _files_match(evidence_path: str, source_file: str) -> bool:
    a = _posix(evidence_path).lower()
    b = _posix(source_file).lower()
    if not a or not b:
        return False
    return a == b or b.endswith(a) or a.endswith(b)


def _label_matches_action(label: str, action: str, controller: str) -> bool:
    lab = label.strip()
    act = action.strip()
    if not lab or not act:
        return False
    if lab == act:
        return True
    if lab.endswith("()") and lab[:-2] == act:
        return True
    if controller and lab in {f"{controller}.{act}", f"{controller}.{act}()"}:
        return True
    if lab.endswith(f".{act}") or lab.endswith(f".{act}()"):
        return True
    return False


def _load_graphify(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return [], []
    nodes = raw.get("nodes")
    if not isinstance(nodes, list):
        nodes = []
    edges = raw.get("edges")
    if not isinstance(edges, list):
        links = raw.get("links")
        edges = links if isinstance(links, list) else []
    node_dicts = [n for n in nodes if isinstance(n, dict)]
    edge_dicts = [e for e in edges if isinstance(e, dict)]
    return node_dicts, edge_dicts


def project_links(
    iface: RepoInterface,
    operations: list[ApiOperationFact],
    graphify_path: Path,
    *,
    commit_sha: str,
) -> dict[str, Any]:
    """Match Roslyn file+action to Graphify nodes. No match → omit (no Task/List fuzzy)."""
    nodes, _edges = _load_graphify(graphify_path)
    links: list[dict[str, Any]] = []
    for op in operations:
        ev_path = op.evidence[0].file_path if op.evidence else ""
        line = op.evidence[0].line_start if op.evidence else 0
        hit: dict[str, Any] | None = None
        for node in nodes:
            sf = str(node.get("source_file") or "")
            label = str(node.get("label") or "")
            if not _files_match(ev_path, sf):
                continue
            if not _label_matches_action(label, op.action, op.controller):
                continue
            hit = node
            break
        if hit is None:
            continue
        loc = str(hit.get("source_location") or "")
        links.append(
            {
                "eakg_operation": eakg_operation_local_name(
                    iface.application_id, op.action, op.http_method
                ),
                "join_key": join_key(iface.application_id, op.http_method, op.http_path),
                "graphify_node_id": str(hit.get("id") or ""),
                "file": ev_path or str(hit.get("source_file") or ""),
                "symbol": f"{op.controller}.{op.action}" if op.controller else op.action,
                "line": line,
                "source_location": loc,
                "confidence": 0.95,
                "detector_id": "graphify_ast+dotnet_roslyn",
                "commit_sha": commit_sha,
            }
        )
    return {
        "commit": commit_sha,
        "graphify_graph": "engineering/graph.json",
        "links": links,
    }


def explain_operation(
    links_path: Path,
    graphify_path: Path,
    operation_local: str,
) -> dict[str, Any]:
    """Linked file/line plus one-hop Graphify callers (incoming ``calls``)."""
    if not links_path.is_file():
        return {"error": "links.json missing", "operation": operation_local}
    blob = json.loads(links_path.read_text(encoding="utf-8"))
    if not isinstance(blob, dict):
        return {"error": "links.json invalid", "operation": operation_local}
    rows = blob.get("links")
    if not isinstance(rows, list):
        return {"error": "links.json has no links", "operation": operation_local}
    match: dict[str, Any] | None = None
    for row in rows:
        if isinstance(row, dict) and str(row.get("eakg_operation") or "") == operation_local:
            match = row
            break
    if match is None:
        return {"error": "operation not linked", "operation": operation_local, "commit": blob.get("commit")}
    node_id = str(match.get("graphify_node_id") or "")
    callers: list[dict[str, str]] = []
    if graphify_path.is_file() and node_id:
        nodes, edges = _load_graphify(graphify_path)
        by_id = {str(n.get("id") or ""): n for n in nodes}
        for edge in edges:
            rel = str(edge.get("relation") or "")
            if rel and rel != "calls":
                continue
            if str(edge.get("target") or "") != node_id:
                continue
            src_id = str(edge.get("source") or "")
            src = by_id.get(src_id) or {}
            callers.append(
                {
                    "id": src_id,
                    "label": str(src.get("label") or src_id),
                    "file": str(src.get("source_file") or ""),
                    "location": str(src.get("source_location") or ""),
                }
            )
    return {
        "operation": operation_local,
        "commit": blob.get("commit"),
        "file": match.get("file"),
        "symbol": match.get("symbol"),
        "line": match.get("line"),
        "join_key": match.get("join_key"),
        "graphify_node_id": node_id,
        "callers": callers,
    }
