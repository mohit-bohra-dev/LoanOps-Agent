"""CLI: python -m packages.eakg ..."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from packages.common.settings import Settings
from packages.eakg.onboard import onboard_repository, rebuild_cross_app
from packages.eakg.registry_import import import_taac
from packages.eakg.registry_validate import validate_registry
from packages.eakg.review import (
    decide,
    list_pending,
    publish_approved_catalog,
    review_pilot_edges,
)
from packages.eakg.runtime import eakg_runtime
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
    p_on.add_argument(
        "--engineering-graph",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Graphify AST → shard engineering/graph.json (default: EAKG__ENGINEERING_GRAPH; "
            "not fatal if graphify fails)"
        ),
    )

    sub.add_parser("cross-app", help="Rebuild cross-app named graph in SPARQL store")
    sub.add_parser(
        "embed",
        help="Write data/eakg/enterprise/embeddings.json from merged shards",
    )

    p_load = sub.add_parser(
        "graph-load",
        help="Load Turtle files into GraphDB named graphs (one-time cutover)",
    )
    p_load.add_argument(
        "--ids",
        default="escrow,fees,loanservices",
        help="Comma-separated repository ids (default: pilot three)",
    )
    p_load.add_argument(
        "--from-shard-dir",
        default="",
        help="Optional shard root with repos/<id>/graph.ttl (cutover only)",
    )

    p_rebuild = sub.add_parser(
        "rebuild-graphs",
        help="Rebuild graph.ttl + GraphDB from stored interface.json (no re-extract)",
    )
    p_rebuild.add_argument(
        "--ids",
        default="escrow,fees,loanservices",
        help="Comma-separated repository ids (default: pilot three)",
    )

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

    p_q = sub.add_parser("query", help="Smoke-search / find / impact against SPARQL store")
    p_q.add_argument("mode", choices=["search", "find", "explain", "impact"])
    p_q.add_argument("needle")
    p_q.add_argument("--limit", type=int, default=10)
    p_q.add_argument(
        "--semantic",
        action="store_true",
        help="Deprecated: shard embeddings path; use keyword SPARQL search",
    )

    p_code = sub.add_parser(
        "code",
        help="Explain EAKG operation via Graphify one-hop callers (links.json)",
    )
    p_code.add_argument("--id", required=True, help="repository_id")
    p_code.add_argument(
        "--operation",
        required=True,
        help="RDF local name, e.g. op_loanservices_GetLoanSummary_GET",
    )

    p_registry = sub.add_parser("registry", help="Validate or import the application mapping")
    reg_sub = p_registry.add_subparsers(dest="registry_cmd", required=True)
    p_val = reg_sub.add_parser("validate", help="Print registry issues as JSON")
    p_val.add_argument("--env", default="")
    p_imp = reg_sub.add_parser("import-taac", help="Fill blank base URLs from TAAC ServiceUrls")
    p_imp.add_argument("--env", required=True)
    p_imp.add_argument("--path", default="")
    p_imp.add_argument("--dry-run", action="store_true")

    p_refresh = sub.add_parser(
        "spec-refresh",
        help="Refresh cached OpenAPI specs for the active environment",
    )
    p_refresh.add_argument("--env", default="")

    p_art = sub.add_parser("artifacts", help="ADR-027 artifact store (Postgres)")
    art_sub = p_art.add_subparsers(dest="artifacts_cmd", required=True)
    art_sub.add_parser(
        "migrate-from-disk",
        help="Copy registry/interface/openapi/ops from data/eakg into Postgres",
    )
    art_sub.add_parser("status", help="Show backend + registry count")

    p_proc = sub.add_parser("process", help="ADR-028 business process KG pilot")
    proc_sub = p_proc.add_subparsers(dest="process_cmd", required=True)
    p_pe = proc_sub.add_parser("extract", help="Extract + validate fixtures → proposal JSON")
    p_pe.add_argument(
        "--fixtures",
        default="projects/LoanOps.Eakg/packages/eakg/tests/fixtures/process",
    )
    p_pe.add_argument("--maps", default="data/process_kg/maps")
    p_pe.add_argument(
        "--out",
        default="data/process_kg/account-maintenance.proposal.json",
    )
    p_pe.add_argument(
        "--names",
        default="account_maintenance,efta_sensitive,efta_paid_in_advance,fha_non_impound",
    )
    p_pv = proc_sub.add_parser("validate", help="Re-validate last proposal file")
    p_pv.add_argument(
        "--proposal",
        default="data/process_kg/account-maintenance.proposal.json",
    )
    p_pl = proc_sub.add_parser(
        "load",
        help="Load proposal graphs into GraphStore (pending_review)",
    )
    p_pl.add_argument(
        "--proposal",
        default="data/process_kg/account-maintenance.proposal.json",
    )
    p_pl.add_argument(
        "--fixtures",
        default="projects/LoanOps.Eakg/packages/eakg/tests/fixtures/process",
    )
    p_pl.add_argument("--maps", default="data/process_kg/maps")
    p_pl.add_argument(
        "--names",
        default=(
            "account_maintenance,efta_sensitive,"
            "efta_paid_in_advance,fha_non_impound"
        ),
    )
    p_ps = proc_sub.add_parser("show", help="Explain one process from GraphStore")
    p_ps.add_argument("process_id")
    p_pa = proc_sub.add_parser(
        "approve",
        help="Set hasReviewStatus=approved (not run in pilot by default)",
    )
    p_pa.add_argument("process_id")
    p_pa.add_argument("--by", default="", help="Reviewer id")
    p_pf = proc_sub.add_parser("verify-fresh", help="Compare live version/hash to stored")
    p_pf.add_argument("process_id")
    p_pf.add_argument("--version", type=int, required=True)
    p_pf.add_argument("--hash", required=True)
    p_pr = proc_sub.add_parser("revalidate", help="Flag broken capability links")
    p_pr.add_argument(
        "--keys",
        default="",
        help="Comma-separated known operation keys (app|METHOD|path)",
    )
    p_prep = proc_sub.add_parser("report", help="Print extraction/validation report JSON")
    p_prep.add_argument(
        "--proposal",
        default="data/process_kg/account-maintenance.proposal.json",
    )

    p_inv = sub.add_parser(
        "investigate",
        help="ADR-029: LLM investigator over gap ledger (EAKG__INVESTIGATE_AGENT)",
    )
    p_inv.add_argument("--id", default="", help="repository_id (or enterprise/cross_app)")
    p_inv.add_argument("--limit", type=int, default=5)
    p_inv.add_argument(
        "--ledger",
        default="",
        help="Optional path to gap_ledger.json (default: shard or enterprise)",
    )
    p_inv.add_argument(
        "--openapi-report",
        default="",
        help="Optional ApiIndex mismatch report JSON to merge into ledger",
    )
    p_inv.add_argument("--dry-run", action="store_true", help="Build ledger only; no LLM")

    p_pat = sub.add_parser("patterns", help="ADR-029 pattern store / backtest")
    pat_sub = p_pat.add_subparsers(dest="patterns_cmd", required=True)
    pat_sub.add_parser("hash", help="Print patterns_hash for EAKG__PATTERNS_DIR")
    p_bt = pat_sub.add_parser("backtest", help="Backtest a pattern proposal JSON")
    p_bt.add_argument("--proposal", required=True, help="JSON file with pattern payload")
    p_bt.add_argument(
        "--motivating",
        default="",
        help="Optional JSON list of ledger items",
    )

    args = parser.parse_args(argv)
    cfg = Settings()
    registry, store, arts = eakg_runtime(cfg)
    store.ensure_layout()

    if args.cmd == "artifacts":
        if args.artifacts_cmd == "migrate-from-disk":
            from packages.eakg.migrate_artifacts import migrate_from_disk

            print(json.dumps(migrate_from_disk(cfg), indent=2))
            return 0
        print(
            json.dumps(
                {
                    "backend": arts.backend,
                    "registry_count": len(arts.load_registry()),
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "process":
        from pathlib import Path

        from packages.eakg.process_graph import (
            explain_process,
            extract_bundle,
            load_processes,
            report_extraction,
            revalidate_links,
            set_review_status,
            verify_fresh,
            write_proposal,
        )

        if args.process_cmd == "extract":
            names = [x.strip() for x in args.names.split(",") if x.strip()]
            drafts, validations = extract_bundle(
                Path(args.fixtures), Path(args.maps), names
            )
            write_proposal(Path(args.out), drafts, validations)
            print(json.dumps(report_extraction(drafts, validations), indent=2))
            return 0

        if args.process_cmd in {"validate", "report"}:
            proposal_path = Path(args.proposal)
            payload = json.loads(proposal_path.read_text(encoding="utf-8"))
            print(json.dumps(payload.get("report") or payload, indent=2))
            return 0

        if args.process_cmd == "load":
            from packages.common.providers.factory import get_graph_store

            names = [x.strip() for x in args.names.split(",") if x.strip()]
            drafts, validations = extract_bundle(
                Path(args.fixtures), Path(args.maps), names
            )
            write_proposal(Path(args.proposal), drafts, validations)
            gs = get_graph_store()
            result = asyncio.run(
                load_processes(
                    gs,
                    drafts,
                    validations,
                    namespace=cfg.capability_kg.namespace,
                )
            )
            print(json.dumps(result, indent=2))
            return 0

        if args.process_cmd == "show":
            from packages.common.providers.factory import get_graph_store

            gs = get_graph_store()
            print(
                json.dumps(
                    asyncio.run(
                        explain_process(
                            gs,
                            args.process_id,
                            namespace=cfg.capability_kg.namespace,
                        )
                    ),
                    indent=2,
                )
            )
            return 0

        if args.process_cmd == "approve":
            from packages.common.providers.factory import get_graph_store

            gs = get_graph_store()
            print(
                json.dumps(
                    asyncio.run(
                        set_review_status(
                            gs,
                            args.process_id,
                            "approved",
                            reviewer=args.by,
                            namespace=cfg.capability_kg.namespace,
                        )
                    ),
                    indent=2,
                )
            )
            return 0

        if args.process_cmd == "verify-fresh":
            from packages.common.providers.factory import get_graph_store

            gs = get_graph_store()
            print(
                json.dumps(
                    asyncio.run(
                        verify_fresh(
                            gs,
                            args.process_id,
                            live_version=args.version,
                            live_hash=args.hash,
                            namespace=cfg.capability_kg.namespace,
                        )
                    ),
                    indent=2,
                )
            )
            return 0

        if args.process_cmd == "revalidate":
            from packages.common.providers.factory import get_graph_store

            keys = {x.strip() for x in args.keys.split(",") if x.strip()}
            gs = get_graph_store()
            print(
                json.dumps(
                    asyncio.run(
                        revalidate_links(
                            gs,
                            known_operation_keys=keys,
                            namespace=cfg.capability_kg.namespace,
                        )
                    ),
                    indent=2,
                )
            )
            return 0

        return 1

    if args.cmd == "registry":
        if args.registry_cmd == "validate":
            issues = validate_registry(registry)
            payload = {
                app: [issue.__dict__ for issue in rows]
                for app, rows in issues.items()
                if rows and (not args.env or any(i.environment in (None, args.env) for i in rows))
            }
            print(json.dumps(payload, indent=2))
            blocking = any(i.severity == "blocking" for rows in issues.values() for i in rows)
            return 2 if blocking else 0
        taac_path = args.path or cfg.eakg.taac_fixture_path
        taac_report = import_taac(registry, taac_path, args.env, dry_run=args.dry_run)
        print(json.dumps(taac_report.to_dict(), indent=2))
        return 0

    if args.cmd == "spec-refresh":
        from packages.eakg.spec_cache import refresh_all

        env = args.env or cfg.eakg.environment

        async def _no_token(_application_id: str, _audience: str) -> str:
            return ""

        refresh_report = asyncio.run(refresh_all(registry, env, store, _no_token))
        failed = any(row.get("status") != "ok" for row in refresh_report.values())
        print(json.dumps(refresh_report, indent=2))
        return 2 if failed else 0

    if args.cmd == "register":
        registered = registry.register(
            repository_id=args.id,
            application=args.application,
            git_url=args.git_url,
            application_id=args.application_id or args.id,
            gitlab_project_id=args.gitlab_project_id,
            team=args.team,
            api_project_path=args.api_project_path,
        )
        print(json.dumps(registered.to_dict(), indent=2))
        return 0

    if args.cmd == "onboard":
        onboard_rec = registry.get(args.id)
        if onboard_rec is None:
            print(f"unknown repository: {args.id}", file=sys.stderr)
            return 1
        eng = (
            cfg.eakg.engineering_graph
            if args.engineering_graph is None
            else bool(args.engineering_graph)
        )
        result = asyncio.run(
            onboard_repository(
                registry,
                store,
                onboard_rec,
                settings=cfg,
                local_path=args.local_path or None,
                run_semantic=bool(args.semantic),
                engineering_graph=eng,
            )
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.cmd == "rebuild-graphs":
        from packages.common.providers.factory import get_graph_store
        from packages.eakg.rebuild_graphs import rebuild_graphs_from_interfaces

        ids = [x.strip() for x in args.ids.split(",") if x.strip()]
        rebuild_report = asyncio.run(
            rebuild_graphs_from_interfaces(
                store,
                get_graph_store(),
                ids,
                namespace=cfg.capability_kg.namespace,
            )
        )
        print(json.dumps(rebuild_report, indent=2))
        failed = any(
            isinstance(v, dict) and v.get("status") != "ok"
            for v in rebuild_report.values()
        )
        return 2 if failed else 0

    if args.cmd == "code":
        from packages.eakg.engineering import explain_operation

        eng = store.engineering_dir(args.id)
        print(
            json.dumps(
                explain_operation(
                    eng / "links.json",
                    eng / "graph.json",
                    args.operation,
                ),
                indent=2,
                default=str,
            )
        )
        return 0

    if args.cmd == "cross-app":
        print(
            json.dumps(
                asyncio.run(rebuild_cross_app(registry, store, settings=cfg)),
                indent=2,
            )
        )
        return 0

    if args.cmd == "graph-load":
        from pathlib import Path

        from packages.common.providers.factory import get_graph_store
        from packages.eakg.graph_upload import upload_graph
        from rdflib import Graph

        shard = Path(args.from_shard_dir or cfg.eakg.shard_dir)
        gs = get_graph_store()
        ns = cfg.capability_kg.namespace
        report: dict[str, object] = {}

        async def _load() -> dict[str, object]:
            out: dict[str, object] = {}
            for rid in [x.strip() for x in args.ids.split(",") if x.strip()]:
                gpath = shard / "repos" / rid / "graph.ttl"
                epath = shard / "repos" / rid / "evidence.ttl"
                if not gpath.is_file():
                    out[rid] = {"status": "missing", "path": str(gpath)}
                    continue
                g = Graph()
                g.parse(gpath, format="turtle")
                eg = Graph()
                if epath.is_file():
                    eg.parse(epath, format="turtle")
                iri = await upload_graph(gs, rid, g, namespace=ns, evidence=eg or None)
                out[rid] = {
                    "status": "ok",
                    "named_graph": iri,
                    "triples": len(g) + len(eg),
                }
            return out

        report = asyncio.run(_load())
        print(json.dumps(report, indent=2))
        failed = any(
            isinstance(v, dict) and v.get("status") != "ok" for v in report.values()
        )
        return 2 if failed else 0

    if args.cmd == "ingest-taac":
        path = args.path or cfg.eakg.taac_config_path or cfg.eakg.taac_fixture_path
        g = ingest_taac_file(path)
        dest = store.write_enterprise_apps(g)

        async def _upload_apps() -> str:
            from packages.common.providers.factory import get_graph_store
            from packages.eakg.graph_upload import upload_graph

            return await upload_graph(
                get_graph_store(),
                "applications",
                g,
                namespace=cfg.capability_kg.namespace,
            )

        iri = asyncio.run(_upload_apps())
        print(
            json.dumps(
                {
                    "wrote": str(dest),
                    "triples": len(g),
                    "named_graph": iri,
                    "path": path,
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "embed":

        async def _embed_cli() -> dict[str, object]:
            from packages.common.providers.factory import get_embedding_provider
            from packages.eakg.embed import embed_from_settings

            async def _embed(text: str) -> list[float]:
                result = await get_embedding_provider().embed(text)
                return list(result.vector)

            dest = await embed_from_settings(_embed)
            from packages.eakg.artifact_store import get_eakg_artifact_store

            arts = get_eakg_artifact_store(cfg)
            payload = arts.get_embeddings() or {}
            caps = payload.get("capabilities") if isinstance(payload, dict) else None
            n = len(caps) if isinstance(caps, list) else 0
            return {"wrote": str(dest), "capabilities": n, "backend": arts.backend}

        print(json.dumps(asyncio.run(_embed_cli()), indent=2))
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
        from packages.common.providers.factory import get_graph_store
        from packages.eakg.query import (
            explain_capability,
            find_providers,
            impact_of_change,
            search_capabilities,
        )

        ns = cfg.capability_kg.namespace
        gs = get_graph_store()

        async def _q() -> object:
            if args.mode == "search":
                return await search_capabilities(
                    gs, args.needle, namespace=ns, limit=args.limit
                )
            if args.mode == "find":
                return await find_providers(gs, args.needle, namespace=ns)
            if args.mode == "explain":
                return await explain_capability(gs, args.needle, namespace=ns)
            return await impact_of_change(gs, args.needle, namespace=ns)

        print(json.dumps(asyncio.run(_q()), indent=2, default=str))
        return 0

    if args.cmd == "investigate":
        from pathlib import Path

        from packages.eakg.gap_ledger import LedgerItem, from_openapi_join_report
        from packages.eakg.investigate_agent import (
            InvestigateContext,
            investigate_ledger,
        )
        from packages.eakg.patterns import load_patterns

        rid = args.id or "enterprise"
        ledger_path = Path(args.ledger) if args.ledger else None
        if ledger_path is None:
            candidate = store.repo_dir(rid) / "gap_ledger.json"
            if not candidate.is_file():
                candidate = store.enterprise_root / "gap_ledger.json"
            ledger_path = candidate
        items: list[LedgerItem] = []
        if ledger_path.is_file():
            raw_items = json.loads(ledger_path.read_text(encoding="utf-8"))
            items = [LedgerItem.from_dict(x) for x in raw_items if isinstance(x, dict)]
        if args.openapi_report:
            report = json.loads(Path(args.openapi_report).read_text(encoding="utf-8"))
            items.extend(from_openapi_join_report(report, repository_id=rid))
        if args.dry_run or not cfg.eakg.investigate_agent:
            print(
                json.dumps(
                    {
                        "dry_run": True,
                        "investigate_agent": cfg.eakg.investigate_agent,
                        "items": len(items),
                        "ledger": [i.to_dict() for i in items[: args.limit]],
                    },
                    indent=2,
                )
            )
            return 0
        from packages.common.providers.factory import get_chat_provider

        patterns = load_patterns(cfg.eakg.patterns_dir)
        chat = get_chat_provider()
        results = asyncio.run(
            investigate_ledger(
                items,
                chat=chat,
                ctx=InvestigateContext(store=store, repository_id=rid),
                store=store,
                max_rounds=cfg.eakg.investigate_max_rounds,
                patterns_hash=patterns.patterns_hash,
                limit=args.limit,
            )
        )
        print(
            json.dumps(
                {
                    "runs": len(results),
                    "results": [r.to_dict() for r in results],
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "patterns":
        from pathlib import Path

        from packages.eakg.gap_ledger import LedgerItem
        from packages.eakg.pattern_backtest import backtest_from_dirs
        from packages.eakg.patterns import load_patterns

        if args.patterns_cmd == "hash":
            ps = load_patterns(cfg.eakg.patterns_dir)
            print(json.dumps({"patterns_dir": cfg.eakg.patterns_dir, "hash": ps.patterns_hash}))
            return 0
        if args.patterns_cmd == "backtest":
            proposal = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
            payload = proposal.get("payload") or proposal.get("candidate") or proposal
            motivating: list[LedgerItem] = []
            if args.motivating:
                raw_m = json.loads(Path(args.motivating).read_text(encoding="utf-8"))
                motivating = [
                    LedgerItem.from_dict(x) for x in raw_m if isinstance(x, dict)
                ]
            ifaces = []
            for rec in registry.list():
                iface = store.read_interface(rec.repository_id)
                if iface is not None:
                    ifaces.append(iface)
            report = backtest_from_dirs(
                patterns_dir=cfg.eakg.patterns_dir,
                proposal_payload=payload if isinstance(payload, dict) else {},
                motivating_items=motivating,
                interfaces=ifaces,
            )
            print(json.dumps(report.to_dict(), indent=2))
            return 0 if report.passed else 2

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
