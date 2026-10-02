"""Tests for RDF capability KG + catalog + Phase 9 semantic retrieval."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.capability_kg import sparql as sparql_q
from packages.capability_kg.catalog import CapabilityCatalog
from packages.capability_kg.embed_index import (
    build_index,
    cosine,
    embeddings_path_for_ttl,
    load_index,
    save_index,
)
from packages.capability_kg.extract_openapi import (
    build_graph_from_openapi_dict,
    capability_id_for_operation,
)
from packages.capability_kg.store import save_graph

MINI_OPENAPI = {
    "openapi": "3.0.0",
    "info": {"title": "Loan Services API", "version": "1.0"},
    "paths": {
        "/api/Loans/{loan_id}/Summary": {
            "get": {
                "operationId": "getLoanSummary",
                "summary": "Get loan summary",
                "tags": ["loans"],
                "parameters": [
                    {
                        "name": "loan_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/api/Loans/{loan_id}/PaymentSchedules": {
            "get": {
                "operationId": "getPaymentSchedules",
                "summary": "Get payment schedules for loan",
                "tags": ["payments"],
                "parameters": [
                    {
                        "name": "loan_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
    },
}


async def _stub_embed(text: str) -> list[float]:
    """Hand-crafted dims: payment, history/schedule, loan, summary."""
    t = text.lower()
    return [
        1.0 if ("payment" in t or "schedules" in t) else 0.0,
        1.0 if ("history" in t or "schedule" in t) else 0.0,
        1.0 if "loan" in t else 0.0,
        1.0 if "summary" in t else 0.0,
    ]


def test_capability_id_for_operation() -> None:
    assert capability_id_for_operation("getLoanSummary") == "get_loan_summary"
    assert capability_id_for_operation("getPaymentSchedules") == "get_payment_schedules"


def test_cosine_identical() -> None:
    assert cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_build_and_sparql_search(tmp_path: Path) -> None:
    graph = build_graph_from_openapi_dict(
        MINI_OPENAPI,
        source_id="loanservices",
        source_label="LoanServices",
    )
    ttl = save_graph(graph, tmp_path / "capabilities.ttl")
    assert ttl.is_file()
    assert "get_loan_summary" in ttl.read_text(encoding="utf-8")

    rows = sparql_q.search_by_needle(graph, "payment")
    ids = {str(r["id"]) for r in rows}
    assert "get_payment_schedules" in ids

    read_only = sparql_q.list_read_only(graph)
    assert any(r["id"] == "get_loan_summary" for r in read_only)

    by_perm = sparql_q.by_permission(graph, "loan.read")
    assert len(by_perm) >= 2


@pytest.mark.asyncio
async def test_capability_catalog_facade(tmp_path: Path) -> None:
    graph = build_graph_from_openapi_dict(MINI_OPENAPI, source_label="LoanServices")
    path = save_graph(graph, tmp_path / "capabilities.ttl")
    catalog = CapabilityCatalog.from_ttl(path)

    one = catalog.get_capability("get_loan_summary")
    assert one is not None
    assert one.operation_id == "getLoanSummary"
    assert one.read_only is True
    assert one.review_status == "discovered"

    search = await catalog.search_capabilities("summary")
    assert any(c.id == "get_loan_summary" for c in search)

    by_app = catalog.find_capabilities_by_application("LoanServices")
    assert len(by_app) >= 2

    by_domain = catalog.find_capabilities_by_domain("Loan Servicing")
    assert len(by_domain) >= 2

    approved = CapabilityCatalog.from_ttl(path, approved_only=True)
    assert approved.list_capabilities() == []


@pytest.mark.asyncio
async def test_semantic_ranks_payment_history(tmp_path: Path) -> None:
    graph = build_graph_from_openapi_dict(MINI_OPENAPI, source_label="LoanServices")
    ttl = save_graph(graph, tmp_path / "capabilities.ttl")
    base = CapabilityCatalog.from_ttl(ttl)
    entries = await build_index(base.list_capabilities(), _stub_embed)
    side = embeddings_path_for_ttl(ttl)
    save_index(side, entries)
    assert load_index(side)

    # Query has no token "schedules" — keyword alone is weak; semantic should lift payment.
    catalog = CapabilityCatalog.from_ttl(
        ttl,
        semantic=True,
        embed_query=_stub_embed,
        embeddings_path=side,
    )
    hits = await catalog.search_capabilities("payment history", limit=3)
    ids = [h.id for h in hits]
    assert "get_payment_schedules" in ids
    assert ids.index("get_payment_schedules") < 3


@pytest.mark.asyncio
async def test_semantic_off_and_missing_sidecar(tmp_path: Path) -> None:
    graph = build_graph_from_openapi_dict(MINI_OPENAPI, source_label="LoanServices")
    ttl = save_graph(graph, tmp_path / "capabilities.ttl")

    off = CapabilityCatalog.from_ttl(ttl, semantic=False, embed_query=_stub_embed)
    keyword = await off.search_capabilities("summary")
    assert any(c.id == "get_loan_summary" for c in keyword)

    # semantic on but no embeddings.json → keyword fallback, no raise
    missing = CapabilityCatalog.from_ttl(
        ttl,
        semantic=True,
        embed_query=_stub_embed,
        embeddings_path=tmp_path / "nope.json",
    )
    fallback = await missing.search_capabilities("summary")
    assert any(c.id == "get_loan_summary" for c in fallback)


@pytest.mark.asyncio
async def test_search_sse_apis_includes_capabilities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from packages.common import settings as settings_mod
    from packages.common.settings import CapabilityKgConfig, EakgConfig, Settings
    from packages.sse.fixture import FIXTURE_OPENAPI
    from packages.sse.loader import OpenApiCatalogService
    from packages.sse.tools import handle_search_sse_apis

    graph = build_graph_from_openapi_dict(MINI_OPENAPI, source_label="LoanServices")
    shard_root = tmp_path / "eakg"
    save_graph(graph, shard_root / "repos" / "loanservices" / "graph.ttl")

    base = Settings()

    def _settings() -> Settings:
        return Settings(
            capability_kg=CapabilityKgConfig(enabled=True),
            eakg=EakgConfig(shard_dir=str(shard_root)),
            sse=base.sse,
            mcp=base.mcp,
            tools_client=base.tools_client,
        )

    monkeypatch.setattr(settings_mod, "Settings", _settings)

    fixture = tmp_path / "openapi.json"
    fixture.write_text(json.dumps(FIXTURE_OPENAPI), encoding="utf-8")
    svc = OpenApiCatalogService(
        swagger_links=[],
        api_base_url="https://example.invalid",
        fixture_path=str(fixture),
    )
    text = await handle_search_sse_apis(svc, {"query": "loan summary", "limit": 5})
    assert "Capabilities (EAKG):" in text
    assert "get_loan_summary" in text
    assert "OpenAPI operations:" in text
