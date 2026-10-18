"""Live uvicorn + MCP SDK client (integration marker)."""

from __future__ import annotations

import asyncio

import pytest
from packages.eval.mcp.harness import EXPECTED_MCP_TOOLS, LiveMcpDriver, live_mcp_server


@pytest.mark.integration
def test_live_tools_list_via_sdk_client() -> None:
    with live_mcp_server(port=8765) as url:
        names = asyncio.run(LiveMcpDriver(url).list_tool_names())
    assert set(names) == set(EXPECTED_MCP_TOOLS)
