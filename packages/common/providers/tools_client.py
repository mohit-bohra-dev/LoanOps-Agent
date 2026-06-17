"""Tools client provider protocol — re-exports from provider_contracts."""

from provider_contracts.tools_client import (
    AbstractToolsClientProvider as ToolsClientProvider,
)
from provider_contracts.tools_client import ToolCall, ToolResult

__all__ = ["ToolsClientProvider", "ToolCall", "ToolResult"]
