"""Build an SSE catalog from cached registry specs (no network)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.common.settings import Settings
from packages.eakg.openapi_enrich import load_fixture_spec
from packages.eakg.registry import RepositoryRegistry
from packages.eakg.spec_cache import read_current_spec
from packages.eakg.store import ShardStore
from packages.sse.loader import resolve_catalog_source


def registry_has_usable_spec(cfg: Settings) -> bool:
    registry = RepositoryRegistry(cfg.eakg.registry_path)
    store = ShardStore(cfg.eakg.shard_dir)
    env = cfg.eakg.environment
    for record in registry.list_active(env):
        doc, _pointer = read_current_spec(store, record.repository_id, env)
        if doc is not None:
            return True
        fixture = record.environments[env].spec_fixture
        if fixture and Path(fixture).is_file():
            return True
    return False


def catalog_mode(cfg: Settings) -> str:
    return resolve_catalog_source(
        cfg.sse.catalog_source,
        has_swagger_links=bool(cfg.sse.swagger_links or cfg.sse.swagger_urls),
        registry_has_spec=registry_has_usable_spec(cfg),
        use_fixture=cfg.sse.use_fixture,
    )


def catalog_fingerprint(cfg: Settings) -> tuple[tuple[str, int, int], ...]:
    """(path, mtime_ns, size) for the registry file and each cached spec pointer."""
    parts: list[tuple[str, int, int]] = []
    registry_path = Path(cfg.eakg.registry_path)
    if registry_path.is_file():
        stat = registry_path.stat()
        parts.append((str(registry_path), stat.st_mtime_ns, stat.st_size))
    store = ShardStore(cfg.eakg.shard_dir)
    env = cfg.eakg.environment
    registry = RepositoryRegistry(cfg.eakg.registry_path)
    for record in registry.list_active(env):
        path = store.repo_dir(record.repository_id) / "openapi" / env / "current.json"
        if path.is_file():
            stat = path.stat()
            parts.append((str(path), stat.st_mtime_ns, stat.st_size))
    from packages.api_index.paths import operations_path

    ops_path = operations_path(cfg.eakg.shard_dir, env)
    if ops_path.is_file():
        stat = ops_path.stat()
        parts.append((str(ops_path), stat.st_mtime_ns, stat.st_size))
    return tuple(parts)


def build_registry_specs(cfg: Settings) -> list[dict[str, Any]]:
    registry = RepositoryRegistry(cfg.eakg.registry_path)
    store = ShardStore(cfg.eakg.shard_dir)
    env = cfg.eakg.environment
    specs: list[dict[str, Any]] = []
    for record in registry.list_active(env):
        target = record.environments[env]
        doc, pointer = read_current_spec(store, record.repository_id, env)
        error = None if doc is not None else (pointer or {}).get("last_error")
        if doc is None and target.spec_fixture:
            doc = load_fixture_spec(target.spec_fixture)
            error = None if doc is not None else f"fixture missing: {target.spec_fixture}"
        specs.append(
            {
                "source_id": record.application_id,
                "label": record.application,
                "base_url": target.base_url,
                "document": doc,
                "error": error,
            }
        )
    return specs
