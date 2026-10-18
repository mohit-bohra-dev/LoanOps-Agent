"""L1b functional — FakeClient + FixtureCatalogClient."""

from __future__ import annotations

from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from packages.eval.mcp.harness import (
    EXPECTED_MCP_TOOLS,
    HAPPY_ARGS,
    FakeClient,
    FakeMode,
    FixtureCatalogClient,
    run_execute,
)
from packages.mcp_server.policy import PolicyError

RESP = Path(__file__).resolve().parents[1] / "snapshots" / "responses"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", list(EXPECTED_MCP_TOOLS))
async def test_empty_result_is_success_not_error(name: str) -> None:
    client = FakeClient(mode=FakeMode.EMPTY)
    text = await run_execute(name=name, arguments=dict(HAPPY_ARGS[name]), client=client)
    assert text.startswith("empty:")


@pytest.mark.asyncio
async def test_fixture_catalog_search_and_list() -> None:
    fx = FixtureCatalogClient()
    hit = await run_execute(
        name="search_sse_apis", arguments={"query": "loan", "limit": 5}, client=fx
    )
    assert "getLoanSummary" in hit
    listed = await run_execute(name="list_sse_apis", arguments={"limit": 10}, client=fx)
    assert "getLoanSummary" in listed


@pytest.mark.asyncio
async def test_fixture_empty_search_snapshot() -> None:
    RESP.mkdir(parents=True, exist_ok=True)
    text = await run_execute(
        name="search_sse_apis",
        arguments={"query": "__no_match__", "limit": 5},
        client=FixtureCatalogClient(empty_search=True),
    )
    assert text.startswith("empty:")
    path = RESP / "search_sse_apis_empty.txt"
    if not path.is_file():
        path.write_text(text, encoding="utf-8")
    assert path.read_text(encoding="utf-8") == text


@pytest.mark.asyncio
async def test_fixture_call_sse_ok_and_unknown() -> None:
    RESP.mkdir(parents=True, exist_ok=True)
    text = await run_execute(
        name="call_sse_api",
        arguments={"operation_id": "getLoanSummary", "path_params": {"loan_id": "100245"}},
        client=FixtureCatalogClient(),
    )
    path = RESP / "call_sse_api_ok.txt"
    if not path.is_file():
        path.write_text(text, encoding="utf-8")
    assert path.read_text(encoding="utf-8") == text
    # Unresolved operation fails closed as PolicyError (GET-only require resolve).
    with pytest.raises((ToolError, PolicyError)):
        await run_execute(
            name="call_sse_api",
            arguments={"operation_id": "unknown_op"},
            client=FixtureCatalogClient(),
        )


@pytest.mark.asyncio
async def test_limit_one() -> None:
    text = await run_execute(
        name="search_sse_apis",
        arguments={"query": "loan", "limit": 1},
        client=FakeClient(mode=FakeMode.OK),
    )
    assert text.startswith("ok:")
