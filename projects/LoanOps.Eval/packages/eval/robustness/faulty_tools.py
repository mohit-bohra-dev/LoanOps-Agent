"""Test-only tools client wrapper that injects degraded downstream faults."""

from __future__ import annotations

from typing import Literal

from packages.common.providers.tools_client import ToolCall, ToolResult, ToolsClientProvider

FaultKind = Literal["tool_timeout", "tool_error", "empty_result"]


class FaultyToolsClient:
    """Wraps a ToolsClientProvider and forces a fault on every call."""

    def __init__(self, inner: ToolsClientProvider, fault: FaultKind) -> None:
        self._inner = inner
        self._fault: FaultKind = fault

    async def list_tools(self) -> list[str]:
        return await self._inner.list_tools()

    async def call(self, tool: ToolCall) -> ToolResult:
        if self._fault == "tool_timeout":
            return ToolResult(
                tool_name=tool.tool_name,
                success=False,
                data={},
                error="tool_timeout: simulated downstream timeout",
            )
        if self._fault == "tool_error":
            return ToolResult(
                tool_name=tool.tool_name,
                success=False,
                data={},
                error="tool_error: simulated downstream failure",
            )
        # empty_result
        return ToolResult(
            tool_name=tool.tool_name,
            success=True,
            data={"text": ""},
            error=None,
        )
