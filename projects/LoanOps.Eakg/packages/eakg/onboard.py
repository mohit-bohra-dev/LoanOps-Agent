"""Resumable repository onboarding pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.common.providers.graph_store import AbstractGraphStore
from packages.common.settings import Settings
from packages.eakg.analyzers.registry import select_analyzers
from packages.eakg.coverage import build_coverage_manifest
from packages.eakg.detectors import EnterpriseIndex, collect_near_misses, run_detectors
from packages.eakg.engineering import project_links
from packages.eakg.extractors import detect_technology
from packages.eakg.gap_ledger import build_ledger
from packages.eakg.gitops import access_check, clone_or_fetch
from packages.eakg.graph_build import interface_to_graph, relationships_to_graph
from packages.eakg.locks import RepoLock
from packages.eakg.merge_api import merge_api_results
from packages.eakg.models import ApiOperationFact
from packages.eakg.openapi_enrich import enrich_interface
from packages.eakg.patterns import load_patterns
from packages.eakg.registry import RepositoryRecord, RepositoryRegistry
from packages.eakg.semantic import propose_for_repo
from packages.eakg.store import ShardStore, content_hash
from packages.eakg.taac import (
    ingest_taac_file,
    load_connection_catalogs,
    load_service_url_map,
)


def _workspace_repo(settings: Settings, repository_id: str) -> Path:
    return Path(settings.eakg.workspace_dir) / repository_id


async def onboard_repository(
    registry: RepositoryRegistry,
    store: ShardStore,
    record: RepositoryRecord,
    *,
    settings: Settings | None = None,
    skip_clone: bool = False,
    local_path: str | Path | None = None,
    run_semantic: bool = False,
    engineering_graph: bool = False,
    graph_store: AbstractGraphStore | None = None,
) -> dict[str, Any]:
    """Run extract → interface → graph for one repository."""
    cfg = settings or Settings()
    store.ensure_layout()
    report: dict[str, Any] = {"repository_id": record.repository_id, "stages": []}

    if not record.git_url.strip():
        from packages.eakg.spec_cache import refresh_spec

        async def _no_token(_application_id: str, _audience: str) -> str:
            return ""

        pointer = await refresh_spec(record, cfg.eakg.environment, store, _no_token)
        index_status = "indexed" if pointer.get("status") == "ok" else "failed"
        registry.set_status(record.repository_id, index_status=index_status)  # type: ignore[arg-type]
        report["stages"].append({"spec": pointer.get("status")})
        return report

    with RepoLock(Path(cfg.eakg.workspace_dir) / ".locks", record.repository_id):
        # access
        if local_path is None and not skip_clone:
            status, detail = access_check(record.git_url, cfg.eakg.gitlab_host)
            registry.set_status(record.repository_id, access_status=status)  # type: ignore[arg-type]
            report["stages"].append({"access": status, "detail": detail})
            if status != "ok":
                registry.set_status(record.repository_id, index_status="failed")
                return report

        registry.set_status(record.repository_id, index_status="cloning")
        if local_path is not None:
            repo_path = Path(local_path)
            commit = "local"
            head = __import__("subprocess").run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=False,
            )
            if head.returncode == 0:
                commit = head.stdout.strip()
        else:
            dest = _workspace_repo(cfg, record.repository_id)
            commit = clone_or_fetch(
                record.git_url,
                dest,
                host=cfg.eakg.gitlab_host,
                branch=record.default_branch,
            )
            repo_path = dest
        report["stages"].append({"clone": "ok", "commit": commit})

        # detect technology (legacy single label) + analyzer inventory
        tech = detect_technology(repo_path)
        record.technology = tech
        registry.upsert(record)
        registry.save()
        adapters, inv, unsupported = select_analyzers(
            repo_path, engineering_graph=engineering_graph
        )
        report["stages"].append(
            {
                "technology": tech,
                "inventory": {"languages": inv.languages, "projects": inv.projects},
                "unsupported": unsupported,
                "adapters": [a.id for a in adapters],
            }
        )

        api_adapters = [a for a in adapters if a.produces_api_surface]
        if not api_adapters:
            registry.set_status(record.repository_id, index_status="failed")
            report["error"] = f"no extractor for technology={tech}"
            return report

        registry.set_status(record.repository_id, index_status="extracting")
        api_results = []
        for api in api_adapters:
            api_result = api.extract(
                repo_path,
                repository_id=record.repository_id,
                application_id=record.application_id,
                commit_sha=commit,
                api_project_path=record.api_project_path,
            )
            if api_result.error and api.fatal:
                registry.set_status(record.repository_id, index_status="failed")
                report["error"] = api_result.error
                return report
            api_results.append(api_result)

        patterns = load_patterns(cfg.eakg.patterns_dir)
        merged = merge_api_results(
            api_results,
            repository_id=record.repository_id,
            application_id=record.application_id,
            commit_sha=commit,
        )
        coverage = build_coverage_manifest(
            repository_id=record.repository_id,
            adapters=api_adapters,
            results=api_results,
            inventory=inv,
            unsupported=unsupported,
            patterns_hash=patterns.patterns_hash,
        )
        report["stages"].append({"coverage": coverage.to_dict()})

        if not merged.facts:
            registry.set_status(record.repository_id, index_status="failed")
            report["error"] = "no API operations extracted"
            if merged.warnings:
                report["stages"].append({"extract_warnings": merged.warnings})
            # Still persist coverage + ledger for investigation
            _write_ledger_artifacts(
                store,
                record.repository_id,
                coverage=coverage,
                conflicts=merged.conflicts,
            )
            return report
        iface = merged.iface
        extractor_meta: object = merged.extractors
        if len(merged.extractors) == 1:
            extractor_meta = merged.extractors[0]
        details = {
            "operations": merged.facts,
            "extractor": extractor_meta,
        }

        # openapi hybrid — spec comes from the cache, not a live fetch inside enrich
        from packages.common.providers.credential_broker import broker_token_source
        from packages.common.providers.factory import get_credential_broker
        from packages.eakg.spec_cache import read_current_spec, refresh_spec

        env = cfg.eakg.environment
        token_source = broker_token_source(get_credential_broker())
        pointer = await refresh_spec(record, env, store, token_source)
        doc, _cached_pointer = read_current_spec(store, record.repository_id, env)
        target = record.environments.get(env)
        fetch_token = ""
        if target is not None:
            fetch_token = await token_source(record.application_id, target.auth_audience)
        iface = await enrich_interface(
            iface,
            store,
            mode=cfg.eakg.openapi_mode,
            base_url=target.base_url if target is not None else "",
            token=fetch_token,
            fixture_path=target.spec_fixture if target is not None else "",
            spec=doc,
        )
        report["stages"].append({"spec": pointer.get("status")})
        extract_stage: dict[str, object] = {
            "operations": len(iface.operations),
            "packages": len(iface.packages),
            "by_language": merged.language_counts,
        }
        if merged.warnings:
            extract_stage["warnings"] = merged.warnings
        report["stages"].append({"extract": extract_stage})

        ops = details.get("operations")
        assert isinstance(ops, list)
        g, eg = interface_to_graph(
            iface, ops if ops and isinstance(ops[0], ApiOperationFact) else None
        )
        # ADR-026: upload named graph to SPARQL store; no graph.ttl / evidence.ttl in repo.
        from packages.common.providers.factory import get_graph_store
        from packages.eakg.graph_upload import upload_graph

        gs = graph_store if graph_store is not None else get_graph_store()
        graph_iri = await upload_graph(
            gs,
            record.repository_id,
            g,
            namespace=cfg.capability_kg.namespace,
            evidence=eg,
        )
        report["stages"].append({"graph_store": {"named_graph": graph_iri}})
        store.write_interface(iface)

        eng_status = "skipped"
        eng_error: str | None = None
        if engineering_graph:
            gf_adapters = [a for a in adapters if a.id == "graphify_ast"]
            if not gf_adapters:
                eng_status = "skipped"
            else:
                eng_dir = store.engineering_dir(record.repository_id)
                gf_result = gf_adapters[0].extract(
                    repo_path,
                    repository_id=record.repository_id,
                    application_id=record.application_id,
                    commit_sha=commit,
                    api_project_path=record.api_project_path,
                    dest=eng_dir,
                )
                if gf_result.error:
                    eng_status = "failed"
                    eng_error = gf_result.error
                else:
                    ops_list = details.get("operations")
                    facts: list[ApiOperationFact] = []
                    if isinstance(ops_list, list):
                        facts = [o for o in ops_list if isinstance(o, ApiOperationFact)]
                    gpath = eng_dir / "graph.json"
                    if gpath.is_file() and facts:
                        payload = project_links(iface, facts, gpath, commit_sha=commit)
                        store.write_engineering_links(record.repository_id, payload)
                    eng_status = "ok"
        report["stages"].append(
            {"engineering_graph": eng_status, **({"error": eng_error} if eng_error else {})}
        )

        input_hashes = {
            "interface": content_hash(iface.to_dict()),
        }
        ledger_items = _write_ledger_artifacts(
            store,
            record.repository_id,
            coverage=coverage,
            conflicts=merged.conflicts,
        )
        store.write_manifest(
            record.repository_id,
            {
                "commit": commit,
                "technology": tech,
                "extractor": details.get("extractor"),
                "adapters": [a.id for a in adapters],
                "unsupported_languages": unsupported,
                "inventory_languages": inv.languages,
                "engineering_graph": eng_status,
                "coverage_status": coverage.status,
                "patterns_hash": patterns.patterns_hash,
                "conflicts": len(merged.conflicts),
                "ledger_items": len(ledger_items),
                "detector_versions": (
                    merged.detector_versions
                    if merged.detector_versions
                    else {"dotnet_roslyn": "2.1.0", "dotnet_static": "1.0.0"}
                ),
                "input_hashes": input_hashes,
                "counts": {
                    "operations": len(iface.operations),
                    "packages": len(iface.packages),
                    "topics": len(iface.topics),
                },
            },
        )
        index_status = "indexed" if coverage.status == "complete" else "indexed"
        registry.set_status(
            record.repository_id,
            index_status=index_status,  # type: ignore[arg-type]
            commit=commit,
            access_status="ok",
        )
        if coverage.status == "incomplete":
            report["coverage_incomplete"] = True

        if run_semantic:
            registry.set_status(record.repository_id, index_status="enriching")
            props = await propose_for_repo(iface, store, use_llm=False)
            report["stages"].append({"proposals": len(props)})
            registry.set_status(record.repository_id, index_status="pending_review", commit=commit)

        if cfg.eakg.investigate_agent and ledger_items:
            from packages.common.providers.factory import get_chat_provider
            from packages.eakg.investigate_agent import InvestigateContext, investigate_ledger

            chat = get_chat_provider()
            inv_results = await investigate_ledger(
                ledger_items,
                chat=chat,
                ctx=InvestigateContext(
                    repo_root=repo_path,
                    store=store,
                    repository_id=record.repository_id,
                    established_op_keys={
                        f"{o.get('method')}:{o.get('path')}" for o in iface.operations
                    },
                ),
                store=store,
                max_rounds=cfg.eakg.investigate_max_rounds,
                commit_sha=commit,
                patterns_hash=patterns.patterns_hash,
            )
            report["stages"].append(
                {
                    "investigate": {
                        "items": len(ledger_items),
                        "runs": len(inv_results),
                        "proposed": sum(1 for r in inv_results if r.closed_as == "proposed"),
                    }
                }
            )

    return report


def _write_ledger_artifacts(
    store: ShardStore,
    repository_id: str,
    *,
    coverage: Any,
    conflicts: list[Any],
    near_misses: list[dict[str, Any]] | None = None,
    openapi_report: dict[str, Any] | None = None,
    unmapped_taac: list[str] | None = None,
) -> list[Any]:
    """Persist coverage.json + gap_ledger.json (+ optional conflicts)."""
    import json

    from packages.eakg.coverage import CoverageManifest

    cov = coverage if isinstance(coverage, CoverageManifest) else coverage
    items = build_ledger(
        coverage=cov,
        conflicts=list(conflicts or []),
        openapi_report=openapi_report,
        near_misses=near_misses,
        unmapped_taac=unmapped_taac,
        repository_id=repository_id,
    )
    dest = store.repo_dir(repository_id) / "gap_ledger.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps([i.to_dict() for i in items], indent=2),
        encoding="utf-8",
    )
    cov_path = store.repo_dir(repository_id) / "coverage.json"
    cov_path.write_text(json.dumps(coverage.to_dict(), indent=2), encoding="utf-8")
    if conflicts:
        cpath = store.repo_dir(repository_id) / "conflicts.json"
        cpath.write_text(
            json.dumps(
                [c.to_dict() if hasattr(c, "to_dict") else c for c in conflicts],
                indent=2,
            ),
            encoding="utf-8",
        )
    return items


async def rebuild_cross_app(
    registry: RepositoryRegistry,
    store: ShardStore,
    *,
    settings: Settings | None = None,
    force: bool = False,
    graph_store: AbstractGraphStore | None = None,
) -> dict[str, Any]:
    cfg = settings or Settings()
    taac_path = cfg.eakg.taac_config_path or cfg.eakg.taac_fixture_path
    url_map: dict[str, str] = {}
    conn_map: dict[str, str] = {}
    if Path(taac_path).is_file():
        ent = ingest_taac_file(taac_path)
        store.write_enterprise_apps(ent)
        url_map = load_service_url_map(taac_path)
        conn_map = load_connection_catalogs(taac_path)

    interfaces: dict[str, Any] = {}
    hashes: dict[str, str] = {}
    for rec in registry.list():
        iface = store.read_interface(rec.repository_id)
        if iface is None:
            continue
        interfaces[rec.repository_id] = iface
        h = store.interface_hash(rec.repository_id)
        if h:
            hashes[rec.repository_id] = h

    # short-circuit if all hashes unchanged vs last cross_app manifest
    cross_manifest = store.enterprise_root / "cross_app.manifest.json"
    if cross_manifest.is_file() and not force:
        import json

        prev = json.loads(cross_manifest.read_text(encoding="utf-8"))
        if prev.get("interface_hashes") == hashes:
            return {"skipped": True, "reason": "interface hashes unchanged"}

    patterns = load_patterns(cfg.eakg.patterns_dir)
    owners = {
        "loanservicing": "loanservices",
        "fee": "fees",
        "escrow": "escrow",
        "escrowcore": "escrow",
    }
    owners.update(patterns.datastore_owners)
    index = EnterpriseIndex(
        url_key_to_app=url_map,
        connection_key_to_catalog=conn_map,
        catalog_owner_app=owners,
        interfaces=interfaces,
        patterns=patterns,
    )

    all_rels = []
    dropped = 0
    all_near: list[dict[str, object]] = []
    for iface in interfaces.values():
        rels, d = run_detectors(iface, index)
        all_rels.extend(rels)
        dropped += d
        all_near.extend(collect_near_misses(iface, index))

    if all_near:
        import json

        near_path = store.enterprise_root / "near_misses.json"
        store.enterprise_root.mkdir(parents=True, exist_ok=True)
        near_path.write_text(json.dumps(all_near, indent=2), encoding="utf-8")
        # Append near-miss ledger under enterprise
        from packages.eakg.gap_ledger import from_detector_near_misses

        near_items = from_detector_near_misses(
            [dict(x) for x in all_near],
            repository_id="cross_app",
        )
        ledger_path = store.enterprise_root / "gap_ledger.json"
        existing: list[dict[str, object]] = []
        if ledger_path.is_file():
            existing = json.loads(ledger_path.read_text(encoding="utf-8"))
        by_id = {str(r.get("item_id")): r for r in existing if isinstance(r, dict)}
        for it in near_items:
            by_id[it.item_id] = it.to_dict()
        ledger_path.write_text(json.dumps(list(by_id.values()), indent=2), encoding="utf-8")

    # dedupe by relationship_id
    by_id = {r.relationship_id: r for r in all_rels}
    graph = relationships_to_graph(list(by_id.values()))
    # ADR-026: cross-app edges live in SPARQL named graph (no enterprise/cross_app.ttl).
    from packages.common.providers.factory import get_graph_store
    from packages.eakg.graph_upload import upload_graph

    gs = graph_store if graph_store is not None else get_graph_store()
    await upload_graph(
        gs,
        "cross_app",
        graph,
        namespace=cfg.capability_kg.namespace,
    )

    import json

    store.enterprise_root.mkdir(parents=True, exist_ok=True)
    cross_manifest.write_text(
        json.dumps({"interface_hashes": hashes, "relationships": len(by_id), "dropped": dropped}, indent=2),
        encoding="utf-8",
    )
    return {"relationships": len(by_id), "dropped": dropped, "skipped": False}


def path_to_detectors(changed: list[str]) -> set[str] | None:
    """Map changed files to detector names; None means run all."""
    if not changed or changed == ["*"]:
        return None
    detectors: set[str] = set()
    for p in changed:
        pl = p.replace("\\", "/").lower()
        if pl.endswith(".csproj"):
            detectors.add("nuget_sdk")
            detectors.add("auth_dependency")
        if "appsettings" in pl or pl.endswith(".json"):
            detectors.add("service_url")
            detectors.add("event_topic")
            detectors.add("data_store")
        if pl.endswith(".cs"):
            detectors.update(
                {
                    "proxy_class",
                    "route_composition",
                    "service_url",
                    "nuget_sdk",
                }
            )
        if "controller" in pl:
            detectors.add("capability_overlap")
    return detectors or None
