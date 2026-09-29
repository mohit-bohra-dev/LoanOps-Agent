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
