"""Sharded Turtle / JSON store for EAKG (ADR-017)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from rdflib import Graph

from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.capability_kg.store import load_graph, save_graph
from packages.eakg.models import RepoInterface, utc_now_iso


def content_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class ShardStore:
    """One shard per repository under shard_dir/repos/<id>/."""

    def __init__(self, shard_dir: str | Path, *, namespace: str = DEFAULT_NAMESPACE) -> None:
        self.root = Path(shard_dir)
        self.namespace = namespace
        self.repos_root = self.root / "repos"
        self.enterprise_root = self.root / "enterprise"
        self.catalog_root = self.root / "catalog"
        self.proposals_root = self.root / "proposals"
        self.decisions_path = self.root / "decisions" / "decisions.jsonl"

    def repo_dir(self, repository_id: str) -> Path:
        return self.repos_root / repository_id

    def ensure_layout(self) -> None:
        for p in (
            self.repos_root,
            self.enterprise_root,
            self.catalog_root,
            self.proposals_root,
            self.decisions_path.parent,
        ):
            p.mkdir(parents=True, exist_ok=True)

    def write_graph(self, repository_id: str, graph: Graph) -> Path:
        dest = self.repo_dir(repository_id) / "graph.ttl"
        return save_graph(graph, dest)

    def write_evidence(self, repository_id: str, graph: Graph) -> Path:
        dest = self.repo_dir(repository_id) / "evidence.ttl"
        return save_graph(graph, dest)

    def write_interface(self, iface: RepoInterface) -> Path:
        dest = self.repo_dir(iface.repository_id) / "interface.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = iface.to_dict()
        dest.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return dest

    def read_interface(self, repository_id: str) -> RepoInterface | None:
        path = self.repo_dir(repository_id) / "interface.json"
        if not path.is_file():
            return None
        return RepoInterface.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def interface_hash(self, repository_id: str) -> str | None:
        iface = self.read_interface(repository_id)
        if iface is None:
            return None
        return content_hash(iface.to_dict())

    def write_manifest(self, repository_id: str, manifest: dict[str, Any]) -> Path:
        dest = self.repo_dir(repository_id) / "manifest.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        manifest = {**manifest, "written_at": utc_now_iso()}
        dest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return dest

    def read_manifest(self, repository_id: str) -> dict[str, Any] | None:
        path = self.repo_dir(repository_id) / "manifest.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_cross_app(self, graph: Graph) -> Path:
        self.enterprise_root.mkdir(parents=True, exist_ok=True)
        return save_graph(graph, self.enterprise_root / "cross_app.ttl")

    def write_enterprise_apps(self, graph: Graph) -> Path:
        self.enterprise_root.mkdir(parents=True, exist_ok=True)
        return save_graph(graph, self.enterprise_root / "applications.ttl")

    def load_repo_graph(self, repository_id: str) -> Graph:
        return load_graph(self.repo_dir(repository_id) / "graph.ttl", namespace=self.namespace)

    def write_approved(self, graph: Graph) -> Path:
        self.catalog_root.mkdir(parents=True, exist_ok=True)
        return save_graph(graph, self.catalog_root / "approved.ttl")

    def append_proposal(self, repository_id: str, row: dict[str, Any]) -> Path:
        self.proposals_root.mkdir(parents=True, exist_ok=True)
        path = self.proposals_root / f"{repository_id}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        return path

    def read_proposals(self, repository_id: str) -> list[dict[str, Any]]:
        path = self.proposals_root / f"{repository_id}.jsonl"
        if not path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def append_decision(self, row: dict[str, Any]) -> Path:
        self.decisions_path.parent.mkdir(parents=True, exist_ok=True)
        with self.decisions_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        return self.decisions_path

    def read_decisions(self) -> list[dict[str, Any]]:
        if not self.decisions_path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in self.decisions_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def write_openapi_cache(self, repository_id: str, commit: str, spec: dict[str, Any]) -> Path:
        dest = self.repo_dir(repository_id) / "openapi" / f"{commit[:12]}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        return dest

    def read_openapi_cache(self, repository_id: str, commit: str) -> dict[str, Any] | None:
        path = self.repo_dir(repository_id) / "openapi" / f"{commit[:12]}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
