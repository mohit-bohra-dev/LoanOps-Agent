"""Resumable repository onboarding pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.common.settings import Settings
from packages.eakg.analyzers.registry import select_analyzers
from packages.eakg.detectors import EnterpriseIndex, run_detectors
from packages.eakg.engineering import project_links
from packages.eakg.extractors import detect_technology
from packages.eakg.gitops import access_check, clone_or_fetch
from packages.eakg.graph_build import interface_to_graph, relationships_to_graph
from packages.eakg.locks import RepoLock
from packages.eakg.models import ApiOperationFact, RepoInterface
from packages.eakg.openapi_enrich import enrich_interface
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
) -> dict[str, Any]:
    """Run extract → interface → graph for one repository."""
    cfg = settings or Settings()
    store.ensure_layout()
    report: dict[str, Any] = {"repository_id": record.repository_id, "stages": []}

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
        api = api_adapters[0]
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
        iface_obj = api_result.extra.get("repo_interface")
        details_obj = api_result.extra.get("details")
        if not isinstance(iface_obj, RepoInterface) or not isinstance(details_obj, dict):
            registry.set_status(record.repository_id, index_status="failed")
            report["error"] = "dotnet adapter missing RepoInterface"
            return report
        iface = iface_obj
        details = details_obj

        # openapi hybrid
        iface = await enrich_interface(
            iface,
            store,
            mode=cfg.eakg.openapi_mode,
            token=cfg.eakg.live_spec_token,
        )
        report["stages"].append(
            {
                "extract": {
                    "operations": len(iface.operations),
                    "packages": len(iface.packages),
                }
            }
        )

        ops = details.get("operations")
        assert isinstance(ops, list)
        g, eg = interface_to_graph(iface, ops if ops and isinstance(ops[0], ApiOperationFact) else None)
        store.write_graph(record.repository_id, g)
        store.write_evidence(record.repository_id, eg)
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
                "detector_versions": {"dotnet_roslyn": "2.0.0", "dotnet_static": "1.0.0"},
                "input_hashes": input_hashes,
                "counts": {
                    "operations": len(iface.operations),
                    "packages": len(iface.packages),
                    "topics": len(iface.topics),
                },
            },
        )
        registry.set_status(
            record.repository_id,
            index_status="indexed",
            commit=commit,
            access_status="ok",
        )

        if run_semantic:
            registry.set_status(record.repository_id, index_status="enriching")
            props = await propose_for_repo(iface, store, use_llm=False)
            report["stages"].append({"proposals": len(props)})
            registry.set_status(record.repository_id, index_status="pending_review", commit=commit)

    return report


def rebuild_cross_app(
    registry: RepositoryRegistry,
    store: ShardStore,
    *,
    settings: Settings | None = None,
    force: bool = False,
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

    index = EnterpriseIndex(
        url_key_to_app=url_map,
        connection_key_to_catalog=conn_map,
        catalog_owner_app={
            "loanservicing": "loanservices",
            "fee": "fees",
            "escrow": "escrow",
            "escrowcore": "escrow",
        },
        interfaces=interfaces,
    )

    all_rels = []
    dropped = 0
    for iface in interfaces.values():
        rels, d = run_detectors(iface, index)
        all_rels.extend(rels)
        dropped += d

    # dedupe by relationship_id
    by_id = {r.relationship_id: r for r in all_rels}
    graph = relationships_to_graph(list(by_id.values()))
    store.write_cross_app(graph)

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
