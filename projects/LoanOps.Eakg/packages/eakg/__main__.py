"""CLI: python -m packages.eakg ..."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from packages.common.settings import Settings
from packages.eakg.onboard import onboard_repository, rebuild_cross_app
from packages.eakg.registry import RepositoryRegistry
from packages.eakg.review import (
    decide,
    list_pending,
    publish_approved_catalog,
    review_pilot_edges,
)
from packages.eakg.store import ShardStore
from packages.eakg.sync import main as sync_main
from packages.eakg.taac import ingest_taac_file


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "sync":
        return sync_main(argv[1:])

    parser = argparse.ArgumentParser(prog="python -m packages.eakg")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_reg = sub.add_parser("register", help="Add a repository to the registry")
    p_reg.add_argument("--id", required=True)
    p_reg.add_argument("--application", required=True)
    p_reg.add_argument("--git-url", required=True)
    p_reg.add_argument("--application-id", default="")
    p_reg.add_argument("--gitlab-project-id", type=int, default=None)
    p_reg.add_argument("--api-project-path", default="")
    p_reg.add_argument("--team", default="")

    p_on = sub.add_parser("onboard", help="Clone/extract one registered repository")
    p_on.add_argument("--id", required=True)
    p_on.add_argument("--local-path", default="")
    p_on.add_argument("--semantic", action="store_true")

    sub.add_parser("cross-app", help="Rebuild cross_app.ttl from interfaces")

    p_taac = sub.add_parser("ingest-taac", help="Ingest TAAC fixture/config")
    p_taac.add_argument("--path", default="")

    p_rev = sub.add_parser("review", help="List or decide proposals")
    p_rev.add_argument("--repo", default="")
    p_rev.add_argument("--status", default="pending_review")
    p_rev.add_argument("--approve", default="")
    p_rev.add_argument("--reject", default="")
    p_rev.add_argument(
        "--pilot",
        action="store_true",
        help="Approve high-value pilot edges; reject noisy callsOperation; republish",
    )

    sub.add_parser("publish", help="Write catalog/approved.ttl")

    p_q = sub.add_parser("query", help="Smoke-search / find / impact against merged shards")
    p_q.add_argument("mode", choices=["search", "find", "explain", "impact"])
    p_q.add_argument("needle")
    p_q.add_argument("--limit", type=int, default=10)

    args = parser.parse_args(argv)
    cfg = Settings()
    registry = RepositoryRegistry(cfg.eakg.registry_path)
    store = ShardStore(cfg.eakg.shard_dir)
    store.ensure_layout()

    if args.cmd == "register":
        rec = registry.register(
            repository_id=args.id,
            application=args.application,
            git_url=args.git_url,
            application_id=args.application_id or args.id,
            gitlab_project_id=args.gitlab_project_id,
            team=args.team,
            api_project_path=args.api_project_path,
        )
        print(json.dumps(rec.to_dict(), indent=2))
        return 0

    if args.cmd == "onboard":
        rec = registry.get(args.id)
        if rec is None:
            print(f"unknown repository: {args.id}", file=sys.stderr)
            return 1
        result = asyncio.run(
            onboard_repository(
                registry,
                store,
                rec,
                settings=cfg,
                local_path=args.local_path or None,
                run_semantic=bool(args.semantic),
            )
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.cmd == "cross-app":
        print(json.dumps(rebuild_cross_app(registry, store, settings=cfg), indent=2))
        return 0

    if args.cmd == "ingest-taac":
        path = args.path or cfg.eakg.taac_config_path or cfg.eakg.taac_fixture_path
        g = ingest_taac_file(path)
        dest = store.write_enterprise_apps(g)
        print(json.dumps({"wrote": str(dest), "triples": len(g)}))
        return 0

    if args.cmd == "review":
        if args.pilot:
            stats = review_pilot_edges(store)
            n = publish_approved_catalog(store)
            print(json.dumps({**stats, "approved_triples": n}, indent=2))
            return 0
        if args.approve:
            print(json.dumps(decide(store, proposal_id=args.approve, decision="approved")))
            return 0
        if args.reject:
            print(json.dumps(decide(store, proposal_id=args.reject, decision="rejected")))
            return 0
        rows = list_pending(store, args.repo or None)
        print(json.dumps(rows[:50], indent=2))
        return 0

    if args.cmd == "publish":
        n = publish_approved_catalog(store)
        print(json.dumps({"approved_triples": n}))
        return 0

    if args.cmd == "query":
        from packages.eakg.merge import merge_shards
        from packages.eakg.query import (
            explain_capability,
            find_providers,
            impact_of_change,
            search_capabilities,
        )

        g = merge_shards(store.root, namespace=cfg.capability_kg.namespace)
        ns = cfg.capability_kg.namespace
        if args.mode == "search":
            rows = search_capabilities(g, args.needle, namespace=ns, limit=args.limit)
        elif args.mode == "find":
            rows = find_providers(g, args.needle, namespace=ns)
        elif args.mode == "explain":
            rows = explain_capability(g, args.needle, namespace=ns)
        else:
            rows = impact_of_change(g, args.needle, namespace=ns)
        print(json.dumps(rows, indent=2, default=str))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
