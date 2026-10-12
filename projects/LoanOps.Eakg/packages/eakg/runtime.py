"""Construct registry + shard store wired to the configured artifact backend (ADR-027)."""

from __future__ import annotations

from packages.common.settings import Settings, get_settings
from packages.eakg.artifact_store import (
    AbstractEakgArtifactStore,
    get_eakg_artifact_store,
)
from packages.eakg.registry import RepositoryRegistry
from packages.eakg.store import ShardStore


def eakg_runtime(
    settings: Settings | None = None,
) -> tuple[RepositoryRegistry, ShardStore, AbstractEakgArtifactStore]:
    cfg = settings or get_settings()
    arts = get_eakg_artifact_store(cfg)
    registry = RepositoryRegistry(cfg.eakg.registry_path, artifact_store=arts)
    store = ShardStore(
        cfg.eakg.shard_dir,
        namespace=cfg.capability_kg.namespace,
        artifact_store=arts,
    )
    return registry, store, arts
