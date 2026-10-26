"""Filesystem paths for API index artifacts (file-mode pipeline_store mirrors)."""

from __future__ import annotations

from pathlib import Path


def api_index_dir(shard_dir: str | Path, environment: str) -> Path:
    """Manifest / ops sibling dir under Postgres (file mode)."""
    return Path(shard_dir) / "Postgres" / "api_index" / environment


def operations_path(shard_dir: str | Path, environment: str) -> Path:
    return Path(shard_dir) / "Postgres" / "operations" / f"{environment}.json"


def manifest_path(shard_dir: str | Path, environment: str) -> Path:
    return api_index_dir(shard_dir, environment) / "index.manifest.json"


def sidecar_path(shard_dir: str | Path, environment: str) -> Path:
    """Offline pgvector dump aid (file mode only)."""
    return (
        Path(shard_dir)
        / "Pgvector"
        / "api_index"
        / environment
        / "openapi_embeddings.json"
    )
