"""Contract tests for the tools client provider."""

import pytest
from packages.common.providers.testing import MockToolsClientProvider
from packages.common.providers.tools_client import (
    ToolCall,
    ToolResult,
    ToolsClientProvider,
)


@pytest.fixture
def provider() -> MockToolsClientProvider:
    p = MockToolsClientProvider()
    p.register(
        "get_loan",
        ToolResult(tool_name="get_loan", success=True, data={"loan_id": "L001"}),
    )
    return p


class TestToolsClientProviderContract:
    """Every ToolsClientProvider implementation must pass these tests."""

    async def test_isinstance(self, provider: ToolsClientProvider) -> None:
        assert isinstance(provider, ToolsClientProvider)

    async def test_call_known_tool(self, provider: ToolsClientProvider) -> None:
        result = await provider.call(ToolCall(tool_name="get_loan", parameters={"id": "L001"}))
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.tool_name == "get_loan"

    async def test_call_unknown_tool_fails(self, provider: ToolsClientProvider) -> None:
        result = await provider.call(ToolCall(tool_name="nonexistent"))
        assert result.success is False
        assert result.error is not None

    async def test_list_tools(self, provider: ToolsClientProvider) -> None:
        tools = await provider.list_tools()
        assert isinstance(tools, list)
        assert "get_loan" in tools
