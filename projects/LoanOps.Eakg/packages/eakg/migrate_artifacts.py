"""One-time / operator migrate: disk shards → Postgres artifact store (ADR-027)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from packages.common.settings import Settings
from packages.eakg.artifact_store import (
    FileEakgArtifactStore,
    PostgresEakgArtifactStore,
    get_eakg_artifact_store,
    resolve_eakg_store_dsn,
)


def migrate_from_disk(settings: Settings | None = None) -> dict[str, Any]:
    """Copy registry, interfaces, openapi, manifests, operations from files into Postgres."""
    cfg = settings or Settings()
    src = FileEakgArtifactStore(cfg.eakg.shard_dir, registry_path=cfg.eakg.registry_path)
    dest = PostgresEakgArtifactStore(resolve_eakg_store_dsn(cfg))
    dest.ensure_schema()

    report: dict[str, Any] = {
        "registry": 0,
        "interfaces": [],
        "manifests": [],
        "openapi": [],
        "operations": [],
    }

    repos = src.load_registry()
    if not repos and Path(cfg.eakg.registry_path).is_file():
        raw = yaml.safe_load(Path(cfg.eakg.registry_path).read_text(encoding="utf-8")) or {}
        repos = list(raw.get("repositories") or [])
    dest.save_registry([r for r in repos if isinstance(r, dict)])
    report["registry"] = len(repos)

    root = Path(cfg.eakg.shard_dir)
    repos_root = root / "repos"
    if repos_root.is_dir():
        for repo_dir in sorted(repos_root.iterdir()):
            if not repo_dir.is_dir():
                continue
            rid = repo_dir.name
            iface = src.get_interface(rid)
            if iface is not None:
                dest.put_interface(rid, iface)
                report["interfaces"].append(rid)
            man = src.get_manifest(rid)
            if man is not None:
                dest.put_manifest(rid, man)
                report["manifests"].append(rid)
            openapi_root = repo_dir / "openapi"
            if openapi_root.is_dir():
                for env_dir in sorted(openapi_root.iterdir()):
                    if not env_dir.is_dir():
                        continue
                    env = env_dir.name
                    spec, pointer = src.get_openapi_spec(rid, env)
                    if pointer is None:
                        continue
                    dest.put_openapi(rid, env, pointer=pointer, spec=spec)
                    report["openapi"].append(f"{rid}/{env}")

    api_index = root / "enterprise" / "api_index"
    if api_index.is_dir():
        for env_dir in sorted(api_index.iterdir()):
            ops_path = env_dir / "operations.json"
            if not ops_path.is_file():
                continue
            raw = json.loads(ops_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                dest.put_operations(env_dir.name, raw)
                report["operations"].append(env_dir.name)

    # Verify round-trip count
    loaded = dest.load_registry()
    report["verify_registry"] = len(loaded)
    report["backend"] = get_eakg_artifact_store(cfg).backend
    return report
