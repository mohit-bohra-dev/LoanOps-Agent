"""Sharded Turtle / JSON store for EAKG — file mode mirrors GraphDb + Postgres folders."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from packages.capability_kg.ontology import DEFAULT_NAMESPACE
from packages.capability_kg.store import load_graph, save_graph
from packages.eakg.models import RepoInterface, utc_now_iso
from packages.eakg.pipeline_layout import graph_db_dir, postgres_dir
from rdflib import Graph

# artifact_store typed as Any to avoid import cycles with artifact_store.py


def content_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class ShardStore:
    """File mode: GraphDb/named_graphs + Postgres/…; postgres mode: no product file writes."""

    def __init__(
        self,
        shard_dir: str | Path,
        *,
        namespace: str = DEFAULT_NAMESPACE,
        artifact_store: Any | None = None,
    ) -> None:
        self.root = Path(shard_dir)
        self.namespace = namespace
        self._artifacts = artifact_store
        self._graph_dir = graph_db_dir(self.root)
        self._pg = postgres_dir(self.root)
        # Legacy aliases used by near-miss / cross-app JSON helpers
        self.enterprise_root = self._pg / "enterprise"
        self.repos_root = self._pg / "interface"  # marker paths only
        self.catalog_root = self._graph_dir
        self.proposals_root = self._pg / "proposals"
        self.decisions_path = self._pg / "decisions" / "decisions.jsonl"

    @property
    def _file_mode(self) -> bool:
        if self._artifacts is None:
            return True
        return getattr(self._artifacts, "backend", "file") == "file"

    def repo_dir(self, repository_id: str) -> Path:
        """Marker path (file mode engineering lives under Postgres/engineering)."""
        return self._pg / "engineering" / repository_id

    def ensure_layout(self) -> None:
        if not self._file_mode:
            return
        for p in (
            self._graph_dir,
            self._pg,
            self.enterprise_root,
            self.proposals_root,
            self.decisions_path.parent,
        ):
            p.mkdir(parents=True, exist_ok=True)

    def _graph_path(self, name: str) -> Path:
        return self._graph_dir / name

    def write_graph(self, repository_id: str, graph: Graph) -> Path:
        dest = self._graph_path(f"{repository_id}.ttl")
        if not self._file_mode:
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        return save_graph(graph, dest)

    def write_evidence(self, repository_id: str, graph: Graph) -> Path:
        dest = self._graph_path(f"{repository_id}.evidence.ttl")
        if not self._file_mode:
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        return save_graph(graph, dest)

    def write_interface(self, iface: RepoInterface) -> Path:
        data = iface.to_dict()
        if self._artifacts is not None:
            self._artifacts.put_interface(iface.repository_id, data)
            return self._pg / "interface" / f"{iface.repository_id}.json"
        dest = self._pg / "interface" / f"{iface.repository_id}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return dest

    def read_interface(self, repository_id: str) -> RepoInterface | None:
        if self._artifacts is not None:
            raw = self._artifacts.get_interface(repository_id)
            if raw is None:
                return None
            return RepoInterface.from_dict(raw)
        path = self._pg / "interface" / f"{repository_id}.json"
        if not path.is_file():
            return None
        return RepoInterface.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def interface_hash(self, repository_id: str) -> str | None:
        iface = self.read_interface(repository_id)
        if iface is None:
            return None
        return content_hash(iface.to_dict())

    def write_manifest(self, repository_id: str, manifest: dict[str, Any]) -> Path:
        manifest = {**manifest, "written_at": utc_now_iso()}
        if self._artifacts is not None:
            self._artifacts.put_manifest(repository_id, manifest)
            return self._pg / "manifest" / f"{repository_id}.json"
        dest = self._pg / "manifest" / f"{repository_id}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return dest

    def read_manifest(self, repository_id: str) -> dict[str, Any] | None:
        if self._artifacts is not None:
            return self._artifacts.get_manifest(repository_id)
        path = self._pg / "manifest" / f"{repository_id}.json"
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None

    def write_cross_app(self, graph: Graph) -> Path:
        dest = self._graph_path("cross_app.ttl")
        if not self._file_mode:
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        return save_graph(graph, dest)

    def write_enterprise_apps(self, graph: Graph) -> Path:
        dest = self._graph_path("applications.ttl")
        if not self._file_mode:
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        return save_graph(graph, dest)

    def load_repo_graph(self, repository_id: str) -> Graph:
        return load_graph(self._graph_path(f"{repository_id}.ttl"), namespace=self.namespace)

    def write_approved(self, graph: Graph) -> Path:
        dest = self._graph_path("approved.ttl")
        if not self._file_mode:
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        return save_graph(graph, dest)

    def append_proposal(self, repository_id: str, row: dict[str, Any]) -> Path:
        if self._artifacts is not None:
            self._artifacts.append_proposal(repository_id, row)
            return self.proposals_root / f"{repository_id}.jsonl"
        self.proposals_root.mkdir(parents=True, exist_ok=True)
        path = self.proposals_root / f"{repository_id}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        return path

    def read_proposals(self, repository_id: str) -> list[dict[str, Any]]:
        if self._artifacts is not None:
            return self._artifacts.read_proposals(repository_id)
        path = self.proposals_root / f"{repository_id}.jsonl"
        if not path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def append_decision(self, row: dict[str, Any]) -> Path:
        if self._artifacts is not None:
            self._artifacts.append_decision(row)
            return self.decisions_path
        self.decisions_path.parent.mkdir(parents=True, exist_ok=True)
        with self.decisions_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        return self.decisions_path

    def read_decisions(self) -> list[dict[str, Any]]:
        if self._artifacts is not None:
            return self._artifacts.read_decisions()
        if not self.decisions_path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in self.decisions_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def engineering_dir(self, repository_id: str) -> Path:
        if self._file_mode:
            dest = self._pg / "engineering" / repository_id
            dest.mkdir(parents=True, exist_ok=True)
            return dest
        return Path(tempfile.mkdtemp(prefix=f"eakg-eng-{repository_id}-"))

    def persist_engineering_dir(self, repository_id: str, eng_dir: Path) -> None:
        """Copy JSON engineering artifacts into the artifact store (both backends)."""
        if self._artifacts is None:
            return
        for name in ("graph.json", "links.json"):
            path = eng_dir / name
            if not path.is_file():
                continue
            raw: object = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self._artifacts.put_engineering(repository_id, name, raw)

    def write_engineering_links(self, repository_id: str, payload: dict[str, Any]) -> Path:
        if self._artifacts is not None:
            self._artifacts.put_engineering(repository_id, "links.json", payload)
        dest = self._pg / "engineering" / repository_id / "links.json"
        if self._file_mode:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return dest

    def write_openapi_cache(self, repository_id: str, commit: str, spec: dict[str, Any]) -> Path:
        if self._artifacts is not None:
            pointer = {"spec_hash": commit[:12], "commit": commit}
            self._artifacts.put_openapi(
                repository_id, "cache", pointer=pointer, spec=spec
            )
            return self._pg / "openapi" / repository_id / "cache.json"
        dest = self._pg / "openapi" / repository_id / f"{commit[:12]}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        return dest

    def read_openapi_cache(self, repository_id: str, commit: str) -> dict[str, Any] | None:
        if self._artifacts is not None:
            spec, _pointer = self._artifacts.get_openapi_spec(repository_id, "cache")
            if spec is not None:
                return spec
        path = self._pg / "openapi" / repository_id / f"{commit[:12]}.json"
        if not path.is_file():
            return None
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None
