"""EAKG unit + pilot validation tests (synthetic fixtures, no live GitLab)."""

from __future__ import annotations

from pathlib import Path

import pytest
from packages.eakg.detectors import EnterpriseIndex, run_detectors
from packages.eakg.extractors import detect_technology
from packages.eakg.extractors.dotnet import extract_repo
from packages.eakg.merge import catalog_from_shards, merge_shards
from packages.eakg.onboard import onboard_repository, rebuild_cross_app
from packages.eakg.query import (
    explain_capability,
    find_providers,
    impact_of_change,
    search_capabilities,
)
from packages.eakg.registry import RepositoryRegistry
from packages.eakg.review import auto_approve_structural, publish_approved_catalog
from packages.eakg.store import ShardStore
from packages.eakg.taac import (
    ingest_taac_file,
    load_service_url_map,
    normalize_topic,
    url_key_to_app_id,
)

FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[5]  # repo root (projects/LoanOps.Eakg/packages/eakg/tests)
TAAC = ROOT / "data" / "eakg" / "fixtures" / "taac-client-config.redacted.json"


def test_url_key_to_app_id() -> None:
    assert url_key_to_app_id("EscrowManagerApiUrl") == "escrow"
    assert url_key_to_app_id("FeesApiUrl") == "fees"
    assert url_key_to_app_id("LoanServicesUrl") == "loanservices"


def test_normalize_topic() -> None:
    assert normalize_topic("svt-dev-FinancialTransactionPosted") == "FinancialTransactionPosted"
    assert (
        normalize_topic("arn:aws:sns:us-west-2:000:svt-dev-FinancialTransactionPosted")
        == "FinancialTransactionPosted"
    )


def test_detect_technology_dotnet() -> None:
    assert detect_technology(FIX / "fees") == "dotnet-aspnetcore"


def test_extract_fees_packages_and_routes() -> None:
    iface, details = extract_repo(
        FIX / "fees",
        repository_id="fees",
        application_id="fees",
        commit_sha="abc",
        api_project_path="src/Fees.WebApi",
    )
    pkgs = {p.package_id for p in details["packages"]}  # type: ignore[index]
    assert "PNMAC.LoanServices.Client" in pkgs
    assert "PNMAC.LoanServices.Domain" in pkgs
    assert any(r.composed_path.startswith("/api/Loans/") for r in details["routes"])  # type: ignore[index]
    assert "LoanServicesUrl" in iface.service_url_keys
    assert "LoanServicesContext" in iface.connection_keys
    assert any("FinancialTransactionPosted" in t.topic_value for t in details["topics"])  # type: ignore[index]


def test_extract_loanservices_proxy_and_ops() -> None:
    iface, details = extract_repo(
        FIX / "loanservices",
        repository_id="loanservices",
        application_id="loanservices",
        commit_sha="def",
        api_project_path="src/LoanServices.WebApi",
        extractor="regex",
    )
    assert any(p.class_name == "EscrowApiProxy" for p in details["proxies"])  # type: ignore[index]
    actions = {o.action for o in details["operations"]}  # type: ignore[index]
    assert "GetLoanSummary" in actions
    assert "GetPaymentSchedules" in actions


def test_extract_loanservices_roslyn_ops() -> None:
    pytest.importorskip("subprocess")
    from packages.eakg.extractors.roslyn import roslyn_tool_available

    if not roslyn_tool_available():
        pytest.skip("dotnet SDK / roslyn tool not available")
    _, details = extract_repo(
        FIX / "loanservices",
        repository_id="loanservices",
        application_id="loanservices",
        commit_sha="def",
        api_project_path="src/LoanServices.WebApi",
        extractor="roslyn",
    )
    assert details.get("extractor") == "dotnet_roslyn"
    actions = {o.action for o in details["operations"]}  # type: ignore[index]
    assert "GetLoanSummary" in actions
    assert "GetPaymentSchedules" in actions
    ops = details["operations"]
    assert isinstance(ops, list) and ops
    assert ops[0].evidence[0].detector_id == "dotnet_roslyn"  # type: ignore[index]


def test_extract_escrow_authorize() -> None:
    _, details = extract_repo(
        FIX / "escrow",
        repository_id="escrow",
        application_id="escrow",
        commit_sha="ghi",
        api_project_path="src/Escrow.Api",
    )
    ops = details["operations"]  # type: ignore[index]
    assert ops
    assert ops[0].authz_source in {"attribute", "class-level"}
    assert ops[0].authz_policy is not None


@pytest.mark.asyncio
async def test_pilot_onboard_and_cross_app(tmp_path: Path) -> None:
    reg_path = tmp_path / "repositories.yaml"
    shard = tmp_path / "eakg"
    store = ShardStore(shard)
    store.ensure_layout()
    registry = RepositoryRegistry(reg_path)

    for rid, app, path, api in (
        ("fees", "fees", FIX / "fees", "src/Fees.WebApi"),
        ("loanservices", "loanservices", FIX / "loanservices", "src/LoanServices.WebApi"),
        ("escrow", "escrow", FIX / "escrow", "src/Escrow.Api"),
    ):
        registry.register(
            repository_id=rid,
            application=app,
            application_id=app,
            git_url=f"https://example.invalid/{rid}.git",
            api_project_path=api,
        )
        rec = registry.get(rid)
        assert rec is not None
        await onboard_repository(
            registry,
            store,
            rec,
            local_path=path,
            run_semantic=False,
        )

    # TAAC + cross-app
    from packages.common.settings import EakgConfig, Settings

    settings = Settings(
        eakg=EakgConfig(taac_fixture_path=str(TAAC), shard_dir=str(shard)),
    )

    store.write_enterprise_apps(ingest_taac_file(TAAC))
    result = rebuild_cross_app(registry, store, settings=settings, force=True)
    assert result["relationships"] > 0
    assert result["dropped"] == 0

    # Verify specific pilot edges
    ifaces = {rid: store.read_interface(rid) for rid in ("fees", "loanservices", "escrow")}
    assert all(ifaces.values())
    index = EnterpriseIndex(
        url_key_to_app=load_service_url_map(TAAC),
        connection_key_to_catalog={"LoanServicesContext": "LoanServicing"},
        catalog_owner_app={"loanservicing": "loanservices"},
        interfaces={k: v for k, v in ifaces.items() if v is not None},  # type: ignore[misc]
    )
    fees = ifaces["fees"]
    assert fees is not None
    rels, dropped = run_detectors(fees, index)
    assert dropped == 0
    kinds = {(r.kind, r.to_application, r.to_package) for r in rels}
    assert any(k[0] == "consumesSdk" and k[2] == "PNMAC.LoanServices.Client" for k in kinds)
    assert any(k[0] == "sharesDto" and "LoanServices.Domain" in (k[2] or "") for k in kinds)
    assert any(r.kind == "callsOperation" and r.to_application == "loanservices" for r in rels)
    assert any(r.kind == "readsDataStore" and r.to_datastore == "LoanServicing" for r in rels)
    assert any(r.kind == "publishesEvent" or r.to_topic == "FinancialTransactionPosted" for r in rels)

    ls = ifaces["loanservices"]
    assert ls is not None
    ls_rels, _ = run_detectors(ls, index)
    assert any(r.kind == "callsApplication" and r.to_application == "escrow" for r in ls_rels)

    auto_approve_structural(store, confidence_threshold=1.0)
    publish_approved_catalog(store)

    g = merge_shards(shard)
    # seven questions (smoke)
    hits = search_capabilities(g, "payment")
    assert isinstance(hits, list)
    providers = find_providers(g, "GetLoanSummary")
    assert providers
    explained = explain_capability(g, "get_loan_summary") or explain_capability(g, "GetLoanSummary")
    assert explained is not None
    assert explained.get("application") or explained.get("http_path")
    impacts = impact_of_change(g, "loanservices")
    assert any(i.get("from_application") == "fees" for i in impacts)

    catalog = catalog_from_shards(shard)
    assert catalog.list_capabilities(limit=50)


@pytest.mark.asyncio
async def test_shard_semantic_finds_payment_when_keyword_empty(tmp_path: Path) -> None:
    from packages.capability_kg.extract_openapi import build_graph_from_openapi_dict
    from packages.capability_kg.store import save_graph
    from packages.eakg.embed import embed_shards

    mini = {
        "openapi": "3.0.0",
        "info": {"title": "Loan Services API", "version": "1.0"},
        "paths": {
            "/api/Loans/{loan_id}/PaymentSchedules": {
                "get": {
                    "operationId": "getPaymentSchedules",
                    "summary": "Get payment schedules for loan",
                    "tags": ["payments"],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }
    graph = build_graph_from_openapi_dict(mini, source_label="LoanServices")
    shard = tmp_path / "eakg"
    save_graph(graph, shard / "repos" / "loanservices" / "graph.ttl")

    async def stub(text: str) -> list[float]:
        t = text.lower()
        return [
            1.0 if "payment" in t or "schedule" in t else 0.0,
            1.0 if "schedule" in t else 0.0,
        ]

    kw = catalog_from_shards(shard, semantic=False)
    empty = await kw.search_capabilities("when is the next payment due", limit=5)
    assert empty == []

    await embed_shards(shard, stub)
    sem = catalog_from_shards(shard, semantic=True, embed_query=stub)
    hits = await sem.search_capabilities("when is the next payment due", limit=5)
    assert any("payment" in h.id.lower() for h in hits)


def test_registry_seed_file() -> None:
    reg = RepositoryRegistry(ROOT / "data" / "eakg" / "registry" / "repositories.yaml")
    ids = {r.repository_id for r in reg.list()}
    assert ids == {"escrow", "fees", "loanservices"}
    assert reg.get("fees") and reg.get("fees").gitlab_project_id == 15921


def test_repo4_registry_only(tmp_path: Path) -> None:
    """Adding repository #4 is registry data only — no code change."""
    path = tmp_path / "repositories.yaml"
    reg = RepositoryRegistry(path)
    reg.register(
        repository_id="cash",
        application="Cash",
        application_id="cash",
        git_url="https://example.invalid/cash.git",
        api_project_path="src/Cash.WebApi",
    )
    assert reg.get("cash") is not None
    assert len(reg.list()) == 1


def test_relationship_without_evidence_dropped() -> None:
    from packages.eakg.models import CrossAppRelationship

    bad = CrossAppRelationship(
        relationship_id="x",
        kind="callsOperation",
        from_application="a",
        to_application="b",
        confidence=0.5,
        evidence=[],
    )
    assert bad.validate() is False
