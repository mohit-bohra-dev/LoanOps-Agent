"""Resumable repository onboarding pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.common.settings import Settings
from packages.eakg.detectors import EnterpriseIndex, run_detectors
from packages.eakg.extractors import detect_technology
from packages.eakg.extractors.dotnet import extract_repo
from packages.eakg.gitops import access_check, clone_or_fetch
from packages.eakg.graph_build import interface_to_graph, relationships_to_graph
from packages.eakg.locks import RepoLock
from packages.eakg.models import ApiOperationFact
from packages.eakg.openapi_enrich import enrich_interface
from packages.eakg.registry import RepositoryRecord, RepositoryRegistry
from packages.eakg.semantic import propose_for_repo
from packages.eakg.store import ShardStore, content_hash
from packages.eakg.taac import (
    ingest_taac_file,
    load_connection_catalogs,
    load_service_url_map,
)


EXTRACTORS = {
    "dotnet-aspnetcore": extract_repo,
    "dotnet": extract_repo,
}


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

        # detect technology
        tech = detect_technology(repo_path)
        record.technology = tech
        registry.upsert(record)
        registry.save()
        report["stages"].append({"technology": tech})

        extractor = EXTRACTORS.get(tech)
        if extractor is None:
            registry.set_status(record.repository_id, index_status="failed")
            report["error"] = f"no extractor for technology={tech}"
            return report

        registry.set_status(record.repository_id, index_status="extracting")
        iface, details = extractor(
            repo_path,
            repository_id=record.repository_id,
            application_id=record.application_id,
            commit_sha=commit,
            api_project_path=record.api_project_path,
        )

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

        input_hashes = {
            "interface": content_hash(iface.to_dict()),
        }
        store.write_manifest(
            record.repository_id,
            {
                "commit": commit,
                "technology": tech,
                "detector_versions": {"dotnet_static": "1.0.0"},
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
