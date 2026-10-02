"""Index schedule entrypoints: sync repo | nightly | audit."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from packages.common.settings import Settings
from packages.eakg.gitops import remote_head
from packages.eakg.onboard import onboard_repository, rebuild_cross_app
from packages.eakg.registry import RepositoryRegistry
from packages.eakg.review import (
    audit_stale_proposals,
    auto_approve_structural,
    publish_approved_catalog,
)
from packages.eakg.semantic import propose_for_repo
from packages.eakg.store import ShardStore
from packages.eakg.taac import ingest_taac_file


async def sync_repo(repository_id: str, *, settings: Settings | None = None) -> dict[str, object]:
    """Per-merge: extract only, no LLM."""
    cfg = settings or Settings()
    registry = RepositoryRegistry(cfg.eakg.registry_path)
    store = ShardStore(cfg.eakg.shard_dir)
    rec = registry.get(repository_id)
    if rec is None:
        raise SystemExit(f"unknown repository: {repository_id}")
    local = Path(cfg.eakg.workspace_dir) / repository_id
    return await onboard_repository(
        registry,
        store,
        rec,
        settings=cfg,
        local_path=local if local.is_dir() else None,
        run_semantic=False,
    )


async def sync_nightly(*, settings: Settings | None = None) -> dict[str, object]:
    cfg = settings or Settings()
    registry = RepositoryRegistry(cfg.eakg.registry_path)
    store = ShardStore(cfg.eakg.shard_dir)
    updated: list[str] = []
    for rec in registry.list():
        head = remote_head(rec.git_url, host=cfg.eakg.gitlab_host, branch=rec.default_branch)
        if head and head == rec.last_indexed_commit:
            continue
        local = Path(cfg.eakg.workspace_dir) / rec.repository_id
        await onboard_repository(
            registry,
            store,
            rec,
            settings=cfg,
            local_path=local if local.is_dir() else None,
            run_semantic=True,
        )
        updated.append(rec.repository_id)
        # proposals
        iface = store.read_interface(rec.repository_id)
        if iface:
            await propose_for_repo(iface, store, use_llm=False)

    # refresh TAAC
    taac = cfg.eakg.taac_config_path or cfg.eakg.taac_fixture_path
    if Path(taac).is_file():
        store.write_enterprise_apps(ingest_taac_file(taac))

    cross = rebuild_cross_app(registry, store, settings=cfg)
    approved = auto_approve_structural(store, confidence_threshold=1.0)
    published = publish_approved_catalog(store)
    return {
        "updated_repos": updated,
        "cross_app": cross,
        "auto_approved_edges": approved,
        "approved_catalog_triples": published,
    }


def sync_audit(*, settings: Settings | None = None) -> dict[str, object]:
    cfg = settings or Settings()
    store = ShardStore(cfg.eakg.shard_dir)
    stale = audit_stale_proposals(store, stale_days=cfg.eakg.review_stale_days)
    # orphan / missing evidence check (lightweight)
    issues: list[str] = []
    cross = store.enterprise_root / "cross_app.ttl"
    if cross.is_file():
        text = cross.read_text(encoding="utf-8")
        if "CrossAppRelationship" in text and "hasEvidence" not in text:
            issues.append("cross_app.ttl relationships missing hasEvidence predicates")
    return {
        "stale_proposals": len(stale),
        "stale_ids": [s.get("proposal_id") for s in stale[:50]],
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m packages.eakg.sync")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_repo = sub.add_parser("repo", help="Per-merge incremental extract (no LLM)")
    p_repo.add_argument("--id", required=True)

    sub.add_parser("nightly", help="Nightly catch-up + cross-app + proposals")
    sub.add_parser("audit", help="Weekly drift / stale review audit")

    args = parser.parse_args(argv)
    if args.cmd == "repo":
        result = asyncio.run(sync_repo(args.id))
    elif args.cmd == "nightly":
        result = asyncio.run(sync_nightly())
    else:
        result = sync_audit()
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
