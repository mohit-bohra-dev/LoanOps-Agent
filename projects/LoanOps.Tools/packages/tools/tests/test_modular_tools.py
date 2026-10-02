"""Modular tools client smoke (fixture SSE, no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from packages.db.client import DbConfig, SqlServerClient
from packages.sse.fixture import FIXTURE_OPENAPI
from packages.sse.loader import OpenApiCatalogService
from packages.tools.modular_tools import ModularToolsClient
from provider_contracts.tools_client import ToolCall


@pytest.mark.asyncio
async def test_modular_search_sse(tmp_path: Path) -> None:
    path = tmp_path / "openapi.json"
    path.write_text(json.dumps(FIXTURE_OPENAPI), encoding="utf-8")
    sse = OpenApiCatalogService(
        api_base_url="https://fixture.local",
        fixture_path=str(path),
    )
    db = SqlServerClient(DbConfig(), fixture_mode=True)
    client = ModularToolsClient(sse=sse, db=db, role="system")
    result = await client.call(
        ToolCall(tool_name="search_sse_apis", parameters={"query": "loan"})
    )
    assert result.success
    assert "text" in result.data
    assert "Loan" in result.data["text"] or "getLoan" in result.data["text"]


@pytest.mark.asyncio
async def test_modular_blocks_wiki_for_system() -> None:
    sse = OpenApiCatalogService(fixture_path=None, swagger_links=[])
    # empty catalog path without fixture still constructs
    sse = OpenApiCatalogService(
        api_base_url="https://fixture.local",
        fixture_path=None,
        swagger_links=[],
    )
    # force empty in-memory by skipping load network — use fixture empty
    from packages.sse.types import OpenApiCatalog

    sse._catalog = OpenApiCatalog(operations=[], loaded_at="now", sources=[])
    db = SqlServerClient(DbConfig(), fixture_mode=True)
    client = ModularToolsClient(sse=sse, db=db, role="system")
    result = await client.call(
        ToolCall(tool_name="wiki_search_gitlab", parameters={"q": "x"})
    )
    assert not result.success
