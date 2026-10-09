"""Filesystem paths for the API index artifacts."""

from __future__ import annotations

from pathlib import Path


def api_index_dir(shard_dir: str | Path, environment: str) -> Path:
    return Path(shard_dir) / "enterprise" / "api_index" / environment


def operations_path(shard_dir: str | Path, environment: str) -> Path:
    return api_index_dir(shard_dir, environment) / "operations.json"


def manifest_path(shard_dir: str | Path, environment: str) -> Path:
    return api_index_dir(shard_dir, environment) / "index.manifest.json"


def sidecar_path(shard_dir: str | Path, environment: str) -> Path:
    return api_index_dir(shard_dir, environment) / "openapi_embeddings.json"
