"""Unit tests for factory MCP tools client construction."""

from __future__ import annotations

import pytest

from packages.common.providers.base import ProviderConfigError
from packages.common.providers.factory import build_mcp_tools_client
from packages.common.settings import McpConfig, Settings, ToolsClientConfig


def test_build_mcp_tools_client_requires_auth_token() -> None:
    cfg = Settings(
        tools_client=ToolsClientConfig(provider="mcp"),
        mcp=McpConfig(auth_token=""),
    )
    with pytest.raises(ProviderConfigError, match="MCP__AUTH_TOKEN"):
        build_mcp_tools_client(cfg, role="system")


def test_build_mcp_tools_client_ok() -> None:
    cfg = Settings(
        tools_client=ToolsClientConfig(provider="mcp"),
        mcp=McpConfig(auth_token="secret", host="127.0.0.1", port=8001, path="/mcp"),
    )
    client = build_mcp_tools_client(cfg, role="care_rep")
    assert "search_sse_apis" in client.allowed_tools  # type: ignore[attr-defined]
    assert "index_docs" not in client.allowed_tools  # type: ignore[attr-defined]
