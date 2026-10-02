"""Unit tests for McpToolsClient (no network)."""

from __future__ import annotations

from typing import Any

import pytest
from packages.tools.mcp_tools_client import McpToolsClient, mcp_endpoint_url
from provider_contracts.tools_client import ToolCall


class FakeMcpSession:
    def __init__(
        self,
        *,
        tools: list[str] | None = None,
        responses: dict[str, tuple[bool, str]] | None = None,
    ) -> None:
        self.tools = tools or ["search_sse_apis", "list_sse_apis", "call_sse_api", "search_docs"]
        self.responses = responses or {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_tool_names(self) -> list[str]:
        return list(self.tools)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        self.calls.append((name, arguments))
        if name in self.responses:
            return self.responses[name]
        return True, f"ok:{name}"


def test_mcp_endpoint_url_normalizes_path() -> None:
    assert mcp_endpoint_url(host="127.0.0.1", port=8001, path="/mcp") == "http://127.0.0.1:8001/mcp"
    assert mcp_endpoint_url(host="127.0.0.1", port=8001, path="mcp") == "http://127.0.0.1:8001/mcp"


@pytest.mark.asyncio
async def test_list_tools_filters_by_role() -> None:
    session = FakeMcpSession(tools=["search_sse_apis", "search_docs", "index_docs"])
    client = McpToolsClient(session=session, role="care_rep")
    names = await client.list_tools()
    assert names == ["search_sse_apis", "search_docs"]
    assert "index_docs" not in client.allowed_tools


@pytest.mark.asyncio
async def test_call_success_and_error() -> None:
    session = FakeMcpSession(
        responses={
            "search_sse_apis": (True, "hits"),
            "call_sse_api": (False, "unauthorized"),
        }
    )
    client = McpToolsClient(session=session, role="system")
    ok = await client.call(ToolCall(tool_name="search_sse_apis", parameters={"query": "loan"}))
    assert ok.success is True
    assert ok.data["text"] == "hits"
    bad = await client.call(
        ToolCall(
            tool_name="call_sse_api",
            parameters={"operation_id": "getLoanSummary"},
        )
    )
    assert bad.success is False
    assert bad.error == "unauthorized"
    assert session.calls[0][0] == "search_sse_apis"
    assert session.calls[1][1]["operation_id"] == "getLoanSummary"


@pytest.mark.asyncio
async def test_call_denied_by_scope() -> None:
    session = FakeMcpSession()
    client = McpToolsClient(session=session, role="customer")
    result = await client.call(ToolCall(tool_name="search_docs", parameters={"query": "x"}))
    assert result.success is False
    assert "not allowed" in (result.error or "")
    assert session.calls == []
