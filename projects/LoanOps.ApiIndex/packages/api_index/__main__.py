"""CLI entry for api_index report / health / build."""

from __future__ import annotations

import argparse
import json
import sys

from packages.common.settings import Settings
from packages.eakg.merge import catalog_from_shards
from packages.eakg.registry import RepositoryRegistry
from packages.eakg.store import ShardStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m packages.api_index")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_report = sub.add_parser("report", help="Mismatch report (openapi_only / eakg_only / …)")
    p_report.add_argument("--env", default="")
    p_report.add_argument("--json", action="store_true")
    p_report.add_argument("--rebuild", action="store_true")
    p_health = sub.add_parser("health", help="Health snapshot (Phase 5 stub)")
    p_health.add_argument("--env", default="")
    p_health.add_argument("--probe", action="store_true")
    p_build = sub.add_parser("build", help="Build and write operations.json")
    p_build.add_argument("--env", default="")
    args = parser.parse_args(argv)

    cfg = Settings()
    env = args.env or cfg.eakg.environment
    registry = RepositoryRegistry(cfg.eakg.registry_path)
    store = ShardStore(cfg.eakg.shard_dir)
    store.ensure_layout()
    caps = None
    if cfg.capability_kg.enabled and store.root.is_dir():
        caps = catalog_from_shards(
            store.root,
            namespace=cfg.capability_kg.namespace,
            approved_only=cfg.capability_kg.approved_only,
        )

    if args.cmd == "build":
        from packages.api_index.catalog import OperationCatalog

        catalog = OperationCatalog.load_or_build(
            registry, store, env, capabilities=caps, force_build=True
        )
        print(
            json.dumps(
                {
                    "environment": env,
                    "operations": len(catalog.ops),
                    "inputs": list(catalog.op_set.inputs),
                    "issues": catalog.op_set.issues,
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "report":
        from packages.api_index.catalog import OperationCatalog, mismatch_report

        catalog = OperationCatalog.load_or_build(
            registry, store, env, capabilities=caps, force_build=bool(args.rebuild)
        )
        payload = mismatch_report(catalog.op_set, caps)
        print(json.dumps(payload, indent=2))
        gaps = (
            len(payload["eakg_only"])
            + len(payload["ambiguous"])
            + len(payload["capabilities_unbound"])
        )
        return 2 if gaps else 0

    if args.cmd == "health":
        import asyncio

        from packages.api_index.catalog import OperationCatalog
        from packages.api_index.health import AppHealthService
        from packages.common.providers.factory import get_credential_broker

        catalog = OperationCatalog.load_or_build(
            registry, store, env, capabilities=caps, force_build=False
        )
        broker = None
        try:
            broker = get_credential_broker()
        except Exception:  # noqa: BLE001
            broker = None
        service = AppHealthService(
            settings=cfg,
            registry=registry,
            store=store,
            op_set=catalog.op_set,
            credentials=broker,
            capabilities=caps,
        )
        snap = asyncio.run(service.snapshot(environment=env))
        payload = snap.model_dump(mode="json")
        if args.probe:
            payload["probe"] = "not_run"  # network probe reserved for operators
        print(json.dumps(payload, indent=2))
        degraded = int(snap.summary.get("degraded") or 0)
        return 2 if degraded else 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
