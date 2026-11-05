"""Unit tests for packages.sse catalog + search."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from packages.sse.catalog import find_operation, parse_openapi_document, search_operations
from packages.sse.fixture import FIXTURE_OPENAPI
from packages.sse.loader import OpenApiCatalogService
from packages.sse.tools import dispatch_sse_tool


def test_parse_fixture_openapi() -> None:
    ops = parse_openapi_document(FIXTURE_OPENAPI, "fixture", "Fixture", "https://fixture.local")
    assert len(ops) == 2
    assert any(op.operation_id == "getLoan" for op in ops)


def test_search_operations_prefers_payment() -> None:
    ops = parse_openapi_document(FIXTURE_OPENAPI, "fixture", "Fixture", "https://fixture.local")
    hits = search_operations(ops, "payment schedule loan", limit=5)
    assert hits
    assert "Payment" in hits[0].path or hits[0].operation_id == "getPaymentSchedules"


def test_find_operation_by_id() -> None:
    ops = parse_openapi_document(FIXTURE_OPENAPI, "fixture", "Fixture", "https://fixture.local")
    op = find_operation(ops, operation_id="fixture:getLoan")
    assert op is not None
    assert op.method == "get"


def test_find_operation_case_insensitive_short_id() -> None:
    ops = parse_openapi_document(FIXTURE_OPENAPI, "fixture", "Fixture", "https://fixture.local")
    op = find_operation(ops, operation_id="GETLOAN")
    assert op is not None
    assert op.operation_id == "getLoan"


def test_source_label_filter_matches_id_or_label() -> None:
    from packages.sse.tools import _matches_source_filter

    ops = parse_openapi_document(
        FIXTURE_OPENAPI, "escrow", "Escrow Manager", "https://escrow.local"
    )
    assert all(_matches_source_filter(o, "escrow") for o in ops)
    assert all(_matches_source_filter(o, "Escrow Manager") for o in ops)
    assert all(_matches_source_filter(o, "manager") for o in ops)
    assert not any(_matches_source_filter(o, "fees") for o in ops)


def test_route_invoke_params_promotes_query_keys() -> None:
    """path_params loanNumber on a query-only path becomes query."""
    from packages.sse.tools import route_invoke_params

    path_out, query_out = route_invoke_params(
        "/api/Escrow/GetEscrowByLoanNumber",
        {"loanNumber": "1000002245"},
        None,
    )
    assert path_out is None
    assert query_out == {"loanNumber": "1000002245"}


def test_route_invoke_params_fills_lone_path_placeholder() -> None:
    from packages.sse.tools import route_invoke_params

    path_out, query_out = route_invoke_params(
        "/api/Loans/{loanId}/Summary",
        {"loan_id": "1000002245"},
        None,
    )
    assert path_out == {"loanId": "1000002245"}
    assert query_out is None or "loan_id" in (query_out or {})


def test_assemble_search_parts_openapi_before_eakg() -> None:
    from packages.sse.tools import _assemble_search_parts

    text = _assemble_search_parts(
        openapi_body="OpenAPI operations:\n- id: escrow:GET_api_escrow_getescrowbyloannumber",
        kg_block="Capabilities (EAKG):\n- capability: AddNotesToElasticSearch",
    )
    openapi_at = text.find("OpenAPI operations:")
    eakg_at = text.find("Capabilities (EAKG):")
    assert openapi_at != -1 and eakg_at != -1
    assert openapi_at < eakg_at
    assert "call call_sse_api" in text


@pytest.mark.asyncio
async def test_catalog_service_fixture(tmp_path: Path) -> None:
    path = tmp_path / "openapi.json"
    path.write_text(json.dumps(FIXTURE_OPENAPI), encoding="utf-8")
    svc = OpenApiCatalogService(
        api_base_url="https://fixture.local",
        fixture_path=str(path),
    )
    catalog = await svc.load()
    assert len(catalog.operations) == 2
    text = await dispatch_sse_tool(svc, "search_sse_apis", {"query": "loan"})
    assert "getLoan" in text or "Loans" in text
