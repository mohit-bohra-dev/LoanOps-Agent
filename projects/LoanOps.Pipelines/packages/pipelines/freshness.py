"""Asset hash freshness for pipeline catalog (no Dagster)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from packages.api_index.catalog import build_operations, load_operations
from packages.common.settings import get_settings
from packages.eakg.runtime import eakg_runtime


def asset_key_api_index(environment: str) -> str:
    return f"openapi_to_api_index:{environment}"


def compute_api_index_hashes(environment: str) -> dict[str, dict[str, str | None]]:
    """Current per-app spec_hash / interface_hash from live ops build."""
    from packages.api_index.records import Environment

    if environment not in ("local", "dev", "stage", "prod"):
        raise ValueError(f"unsupported environment: {environment}")
    env: Environment = environment  # type: ignore[assignment]
    cfg = get_settings()
    registry, store, _arts = eakg_runtime(cfg)
    caps = None
    if cfg.capability_kg.enabled and store.root.is_dir():
        from packages.eakg.merge import catalog_from_shards

        caps = catalog_from_shards(
            store.root,
            namespace=cfg.capability_kg.namespace,
            approved_only=cfg.capability_kg.approved_only,
        )
    op_set = build_operations(registry, store, env, capabilities=caps)
    out: dict[str, dict[str, str | None]] = {}
    for app_id, inputs in op_set.inputs.items():
        out[app_id] = {
            "spec_hash": inputs.spec_hash,
            "interface_hash": inputs.interface_hash,
        }
    return out


def hashes_from_operations_file(environment: str) -> dict[str, dict[str, str | None]] | None:
    """Prefer written OperationSet inputs when available (post-refresh)."""
    cfg = get_settings()
    _registry, store, _arts = eakg_runtime(cfg)
    prior = load_operations(store.root, environment)
    if prior is None:
        return None
    return {
        app_id: {"spec_hash": inputs.spec_hash, "interface_hash": inputs.interface_hash}
        for app_id, inputs in prior.inputs.items()
    }


def store_api_index_hashes(
    arts: Any,
    environment: str,
    hashes: dict[str, dict[str, str | None]],
) -> None:
    arts.put_asset_state(
        asset_key_api_index(environment),
        {
            "pipeline_id": "openapi_to_api_index",
            "environment": environment,
            "apps": hashes,
            "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    )


def evaluate_freshness(
    arts: Any,
    pipeline_id: str,
    *,
    environment: str = "dev",
) -> dict[str, Any]:
    """Return freshness status for a catalog card."""
    if pipeline_id != "openapi_to_api_index":
        return {"status": "unknown", "reason": "no_hash_policy"}
    key = asset_key_api_index(environment)
    stored = arts.get_asset_state(key)
    if stored is None:
        return {"status": "stale", "reason": "never_materialized"}
    stored_apps = stored.get("apps") if isinstance(stored.get("apps"), dict) else {}
    try:
        current = compute_api_index_hashes(environment)
    except Exception as exc:  # noqa: BLE001
        return {"status": "unknown", "reason": f"hash_error:{str(exc)[:80]}"}
    for app_id, cur in current.items():
        old = stored_apps.get(app_id) if isinstance(stored_apps.get(app_id), dict) else {}
        if not isinstance(old, dict):
            old = {}
        if old.get("spec_hash") != cur.get("spec_hash") or old.get("interface_hash") != cur.get(
            "interface_hash"
        ):
            return {
                "status": "stale",
                "reason": f"hash_changed:{app_id}",
                "app": app_id,
            }
    if set(stored_apps) - set(current):
        return {"status": "stale", "reason": "app_retired"}
    return {"status": "fresh", "reason": "hashes_match"}
