"""Load / validate GraphRAG artifact (P4 communities + P5 graph)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

ArtifactStatus = Literal["absent", "ok", "stale", "corrupt"]


@dataclass(frozen=True)
class GraphRagArtifact:
    communities: list[dict[str, Any]]
    manifest: dict[str, Any]
    status: ArtifactStatus
    graph: dict[str, Any] | None = None


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_artifact(
    artifact_dir: Path,
    *,
    expected_corpus_hash: str | None = None,
) -> GraphRagArtifact:
    """Load communities + manifest (+ optional graph) from Postgres or file mirror."""
    from packages.common.settings import get_settings

    if get_settings().eakg_store.backend == "postgres":
        from packages.eakg.artifact_store import get_eakg_artifact_store

        arts = get_eakg_artifact_store()
        communities_raw = arts.get_graphrag("communities")
        manifest = arts.get_graphrag("manifest")
        if isinstance(communities_raw, list) and isinstance(manifest, dict):
            communities: list[dict[str, Any]] = []
            for row in communities_raw:
                if not isinstance(row, dict) or "id" not in row or "summary" not in row:
                    return GraphRagArtifact(
                        communities=[], manifest={}, status="corrupt"
                    )
                communities.append(row)
            graph_raw = arts.get_graphrag("graph")
            graph = graph_raw if isinstance(graph_raw, dict) else None
            if expected_corpus_hash is not None:
                got = str(manifest.get("corpus_hash") or "")
                if got != expected_corpus_hash:
                    return GraphRagArtifact(
                        communities=communities,
                        manifest=manifest,
                        status="stale",
                        graph=graph,
                    )
            return GraphRagArtifact(
                communities=communities, manifest=manifest, status="ok", graph=graph
            )
        return GraphRagArtifact(communities=[], manifest={}, status="absent")

    communities_path = artifact_dir / "communities.json"
    manifest_path = artifact_dir / "manifest.json"
    if not communities_path.is_file() or not manifest_path.is_file():
        return GraphRagArtifact(communities=[], manifest={}, status="absent")
    try:
        communities_raw = _read_json(communities_path)
        manifest = _read_json(manifest_path)
        if not isinstance(communities_raw, list) or not isinstance(manifest, dict):
            return GraphRagArtifact(communities=[], manifest={}, status="corrupt")
        communities: list[dict[str, Any]] = []
        for row in communities_raw:
            if not isinstance(row, dict) or "id" not in row or "summary" not in row:
                return GraphRagArtifact(communities=[], manifest={}, status="corrupt")
            communities.append(row)
        graph: dict[str, Any] | None = None
        graph_path = artifact_dir / "graph.json"
        if graph_path.is_file():
            graw = _read_json(graph_path)
            graph = graw if isinstance(graw, dict) else None
        if expected_corpus_hash is not None:
            got = str(manifest.get("corpus_hash") or "")
            if got != expected_corpus_hash:
                return GraphRagArtifact(
                    communities=communities,
                    manifest=manifest,
                    status="stale",
                    graph=graph,
                )
        return GraphRagArtifact(
            communities=communities, manifest=manifest, status="ok", graph=graph
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return GraphRagArtifact(communities=[], manifest={}, status="corrupt")


def write_artifact(
    artifact_dir: Path,
    *,
    communities: list[dict[str, Any]],
    corpus_hash: str,
    doc_links_version: int = 1,
    graph: dict[str, Any] | None = None,
    model_id: str | None = None,
    prompt_version: str | None = None,
    schema_version: str | None = None,
    phase: str = "p4",
    summary_kind: str = "extractive",
    gap_ledger: list[dict[str, Any]] | None = None,
) -> None:
    manifest: dict[str, Any] = {
        "version": 1,
        "corpus_hash": corpus_hash,
        "doc_links_version": doc_links_version,
        "summary_kind": summary_kind,
        "louvain_seed": 42,
        "phase": phase,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if model_id is not None:
        manifest["model_id"] = model_id
    if prompt_version is not None:
        manifest["prompt_version"] = prompt_version
    if schema_version is not None:
        manifest["schema_version"] = schema_version

    from packages.common.settings import get_settings

    # Product postgres: persist via EAKG artifact store (caller/eakg owns DSN).
    # File mode: write under artifact_dir (default Postgres/graphrag mirror).
    cfg = get_settings()
    if cfg.eakg_store.backend == "postgres":
        from packages.eakg.artifact_store import get_eakg_artifact_store

        arts = get_eakg_artifact_store(cfg)
        arts.put_graphrag("communities", communities)
        arts.put_graphrag("manifest", manifest)
        if graph is not None:
            arts.put_graphrag("graph", graph)
        if gap_ledger is not None:
            arts.put_graphrag("gap_ledger", gap_ledger)
        return

    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "communities.json").write_text(
        json.dumps(communities, indent=2) + "\n", encoding="utf-8"
    )
    if graph is not None:
        (artifact_dir / "graph.json").write_text(
            json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if gap_ledger is not None:
        (artifact_dir / "gap_ledger.json").write_text(
            json.dumps(gap_ledger, indent=2) + "\n", encoding="utf-8"
        )
    (artifact_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def refuse_confluence_repo_write(*, sop_source: str, write_repo_artifact: bool) -> None:
    """Exit contract: non-local SOP source must not write repo artifacts."""
    if write_repo_artifact and sop_source != "local":
        raise SystemExit(
            f"refuse: DATA__SOP_SOURCE={sop_source!r} cannot write repo GraphRAG artifact "
            "(use local data/sops only; Confluence writes disallowed)"
        )
