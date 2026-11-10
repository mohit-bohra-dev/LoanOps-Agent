"""Orchestrate spec refresh → build → reindex (spec §5.3 / §9.3 / §9.6)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

import tempfile
from pathlib import Path

from packages.api_index.catalog import build_operations, load_operations, write_operations
from packages.api_index.indexer import IndexManifest, reindex, write_manifest
from packages.api_index.paths import manifest_path, sidecar_path
from packages.api_index.records import Environment, OperationSet
from packages.common.providers.credential_broker import broker_token_source
from packages.common.providers.factory import (
    get_credential_broker,
    get_embedding_provider,
    get_vector_store_provider,
)
from packages.common.settings import Settings, get_settings
from packages.eakg.artifact_store import AbstractEakgArtifactStore
from packages.eakg.pipeline_layout import resolve_file_shard_dir
from packages.eakg.runtime import eakg_runtime
from packages.eakg.spec_cache import refresh_all as refresh_all_specs
from packages.eakg.spec_cache import refresh_spec
from packages.eakg.store import ShardStore


def _env(value: str) -> Environment:
    if value not in ("local", "dev", "stage", "prod"):
        raise ValueError(f"unsupported environment: {value}")
    return value  # type: ignore[return-value]


async def _token_source(cfg: Settings) -> Any:
    """P4: CredentialBroker; missing creds → unauthenticated fetch."""
    _ = cfg
    broker = get_credential_broker()
    return broker_token_source(broker)


def _caps(cfg: Settings, store: ShardStore) -> Any:
    if not cfg.capability_kg.enabled or not store.root.is_dir():
        return None
    from packages.eakg.merge import catalog_from_shards

    return catalog_from_shards(
        store.root,
        namespace=cfg.capability_kg.namespace,
        approved_only=cfg.capability_kg.approved_only,
    )


def _exit_code(failed: int, fatal: bool = False) -> int:
    if fatal:
        return 1
    if failed:
        return 2
    return 0


def _pipeline_root(cfg: Settings) -> Path:
    return Path(resolve_file_shard_dir(cfg.eakg_store.file_shard_dir))


def _manifest_kv_key(environment: str) -> str:
    return f"api_index.manifest.{environment}"


async def _run_reindex(
    cfg: Settings,
    op_set: OperationSet,
    *,
    arts: AbstractEakgArtifactStore | None = None,
    sidecar_only: bool = False,
) -> dict[str, Any]:
    embedder = get_embedding_provider()
    store = None if sidecar_only else get_vector_store_provider()
    root = _pipeline_root(cfg)
    # Product + live pgvector: no repo sidecar/manifest trees — seed from eakg_kv.
    persist_kv = cfg.eakg_store.backend == "postgres" and not sidecar_only and arts is not None
    if persist_kv:
        assert arts is not None
        tmp = Path(tempfile.mkdtemp(prefix="api-index-"))
        mpath = tmp / "index.manifest.json"
        spath = tmp / "openapi_embeddings.json"
        prior = arts.get_kv(_manifest_kv_key(op_set.environment))
        if prior is not None:
            write_manifest(mpath, IndexManifest.model_validate(prior))
    else:
        mpath = manifest_path(root, op_set.environment)
        spath = sidecar_path(root, op_set.environment)
    report = await reindex(
        op_set.environment,
        op_set,
        vector_store=store,
        embedder=embedder,
        manifest_path=mpath,
        namespace_prefix=cfg.api_index.namespace_prefix,
        sidecar_path=spath,
        sidecar_only=sidecar_only,
    )
    if persist_kv and mpath.is_file():
        assert arts is not None
        raw: object = json.loads(mpath.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            arts.put_kv(_manifest_kv_key(op_set.environment), raw)
    return report.model_dump(mode="json")


async def refresh_app(
    *,
    repository_id: str,
    environment: str,
    cfg: Settings | None = None,
    sidecar_only: bool = False,
) -> dict[str, Any]:
    import time

    from packages.api_index.metrics import record_metric

    started = time.perf_counter()
    cfg = cfg or get_settings()
    registry, store, arts = eakg_runtime(cfg)
    store.ensure_layout()
    record = next(
        (r for r in registry.list_active(environment) if r.repository_id == repository_id
         or r.application_id == repository_id),
        None,
    )
    if record is None:
        report: dict[str, Any] = {
            "repository_id": repository_id,
            "environment": environment,
            "status": "failed",
            "error": "unknown_application",
        }
        await record_metric(
            "api_index.refresh.duration_ms",
            (time.perf_counter() - started) * 1000.0,
            unit="ms",
            attributes={"app": repository_id, "status": "failed"},
        )
        return report
    token = await _token_source(cfg)
    try:
        spec_ptr = await refresh_spec(record, environment, store, token)
    except Exception as exc:  # noqa: BLE001
        report = {
            "repository_id": repository_id,
            "environment": environment,
            "status": "failed",
            "error": str(exc)[:300],
        }
        await record_metric(
            "api_index.refresh.duration_ms",
            (time.perf_counter() - started) * 1000.0,
            unit="ms",
            attributes={"app": repository_id, "status": "failed"},
        )
        return report
    caps = _caps(cfg, store)
    # Rebuild full set (splice cost acceptable at current scale); write + reindex.
    op_set = build_operations(registry, store, _env(environment), capabilities=caps)
    write_operations(store.root, op_set)
    try:
        index_report = await _run_reindex(
            cfg, op_set, arts=arts, sidecar_only=sidecar_only
        )
    except Exception as exc:  # noqa: BLE001
        report = {
            "repository_id": repository_id,
            "environment": environment,
            "status": "failed",
            "spec": spec_ptr,
            "error": str(exc)[:300],
        }
        await record_metric(
            "api_index.refresh.duration_ms",
            (time.perf_counter() - started) * 1000.0,
            unit="ms",
            attributes={"app": repository_id, "status": "failed"},
        )
        return report
    report = {
        "repository_id": repository_id,
        "environment": environment,
        "status": "ok",
        "spec": spec_ptr,
        "operations": len(op_set.operations),
        "index": index_report,
    }
    await record_metric(
        "api_index.refresh.duration_ms",
        (time.perf_counter() - started) * 1000.0,
        unit="ms",
        attributes={"app": repository_id, "status": "ok"},
    )
    return report


async def refresh_all(
    *,
    environment: str,
    cfg: Settings | None = None,
    sidecar_only: bool = False,
) -> dict[str, Any]:
    cfg = cfg or get_settings()
    registry, store, arts = eakg_runtime(cfg)
    store.ensure_layout()
    token = await _token_source(cfg)
    spec_report = await refresh_all_specs(registry, environment, store, token)
    caps = _caps(cfg, store)
    op_set = build_operations(registry, store, _env(environment), capabilities=caps)
    write_operations(store.root, op_set)
    failed = sum(1 for v in spec_report.values() if v.get("status") == "failed")
    try:
        index_report = await _run_reindex(
            cfg, op_set, arts=arts, sidecar_only=sidecar_only
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "environment": environment,
            "status": "failed",
            "spec": spec_report,
            "error": str(exc)[:300],
            "failed_apps": failed + 1,
        }
    status = "ok" if failed == 0 else "partial"
    return {
        "environment": environment,
        "status": status,
        "spec": spec_report,
        "operations": len(op_set.operations),
        "index": index_report,
        "failed_apps": failed,
    }


async def refresh_nightly(
    *,
    environment: str,
    cfg: Settings | None = None,
) -> dict[str, Any]:
    """Refresh specs; rebuild/reindex when spec_hash or interface_hash changed."""
    cfg = cfg or get_settings()
    registry, store, arts = eakg_runtime(cfg)
    store.ensure_layout()
    prior = load_operations(store.root, environment)
    token = await _token_source(cfg)
    spec_report = await refresh_all_specs(registry, environment, store, token)
    caps = _caps(cfg, store)
    op_set = build_operations(registry, store, _env(environment), capabilities=caps)
    changed = False
    if prior is None:
        changed = True
    else:
        for app_id, inputs in op_set.inputs.items():
            old = prior.inputs.get(app_id)
            if old is None or old.spec_hash != inputs.spec_hash or old.interface_hash != inputs.interface_hash:
                changed = True
                break
        if set(prior.inputs) - set(op_set.inputs):
            changed = True  # retired apps
    write_operations(store.root, op_set)
    index_report: dict[str, Any] | None = None
    if changed:
        index_report = await _run_reindex(
            cfg, op_set, arts=arts, sidecar_only=False
        )
    failed = sum(1 for v in spec_report.values() if v.get("status") == "failed")
    return {
        "environment": environment,
        "status": "ok" if failed == 0 else "partial",
        "changed": changed,
        "spec": spec_report,
        "operations": len(op_set.operations),
        "index": index_report,
        "failed_apps": failed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m packages.api_index.refresh")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_app = sub.add_parser("app", help="Refresh one application")
    p_app.add_argument("repository_id")
    p_app.add_argument("--env", default="")
    p_app.add_argument("--sidecar-only", action="store_true")

    p_all = sub.add_parser("all", help="Refresh all active applications")
    p_all.add_argument("--env", default="")
    p_all.add_argument("--sidecar-only", action="store_true")

    p_nightly = sub.add_parser("nightly", help="Nightly: specs then incremental reindex")
    p_nightly.add_argument("--env", default="")

    args = parser.parse_args(argv)
    cfg = Settings()
    env = args.env or cfg.eakg.environment

    try:
        if args.cmd == "app":
            report = asyncio.run(
                refresh_app(
                    repository_id=args.repository_id,
                    environment=env,
                    cfg=cfg,
                    sidecar_only=bool(args.sidecar_only),
                )
            )
            print(json.dumps(report, indent=2, default=str))
            if report.get("status") == "failed":
                return 2 if report.get("error") != "fatal" else 1
            return 0
        if args.cmd == "all":
            report = asyncio.run(
                refresh_all(
                    environment=env,
                    cfg=cfg,
                    sidecar_only=bool(args.sidecar_only),
                )
            )
            print(json.dumps(report, indent=2, default=str))
            return _exit_code(int(report.get("failed_apps") or 0), fatal=report.get("status") == "failed")
        if args.cmd == "nightly":
            report = asyncio.run(refresh_nightly(environment=env, cfg=cfg))
            print(json.dumps(report, indent=2, default=str))
            return _exit_code(int(report.get("failed_apps") or 0))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "failed", "error": str(exc)[:300]}, indent=2))
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
