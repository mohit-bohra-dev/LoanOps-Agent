"""Tools client that calls the LoanOps Streamable HTTP MCP server (ADR-013)."""

from __future__ import annotations

from typing import Any, Protocol

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, TextContent
from packages.common.scopes import tools_for_role
from provider_contracts.tools_client import ToolCall, ToolResult
from provider_contracts.tools_client._base import AbstractToolsClientProvider


class McpSessionHooks(Protocol):
    """Injectable MCP session ops for unit tests (no network)."""

    async def list_tool_names(self) -> list[str]: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> tuple[bool, str]: ...


def mcp_endpoint_url(*, host: str, port: int, path: str) -> str:
    """Build the Streamable HTTP MCP URL from listener settings."""
    normalized = path if path.startswith("/") else f"/{path}"
    return f"http://{host}:{port}{normalized}"


def _text_from_result(result: CallToolResult) -> str:
    parts: list[str] = []
    for block in result.content:
        if isinstance(block, TextContent):
            parts.append(block.text)
        elif hasattr(block, "text"):
            parts.append(str(block.text))
        else:
            parts.append(str(block))
    return "\n".join(parts) if parts else ""


class StreamableHttpMcpSession:
    """One initialize + call/list per operation (server is stateless_http)."""

    def __init__(
        self,
        *,
        url: str,
        auth_token: str,
        timeout: float = 30.0,
        user: str | None = None,
        tenant: str | None = None,
    ) -> None:
        self._url = url
        self._auth_token = auth_token
        self._timeout = timeout
        self._user = user
        self._tenant = tenant

    def _headers(self) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._auth_token}"}
        if self._user:
            headers["x-loanops-user"] = self._user
        if self._tenant:
            headers["x-loanops-tenant"] = self._tenant
        return headers

    async def list_tool_names(self) -> list[str]:
        async with streamablehttp_client(
            self._url,
            headers=self._headers(),
            timeout=self._timeout,
        ) as (read, write, _session_id), ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            return [t.name for t in listed.tools]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        async with streamablehttp_client(
            self._url,
            headers=self._headers(),
            timeout=self._timeout,
        ) as (read, write, _session_id), ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            text = _text_from_result(result)
            if result.isError:
                return False, text or "tool failed"
            return True, text


class McpToolsClient(AbstractToolsClientProvider):
    """Agent-side tools client. Server still runs ModularToolsClient."""

    def __init__(
        self,
        *,
        session: McpSessionHooks,
        role: str = "system",
    ) -> None:
        self._session = session
        self._allowed = tools_for_role(role)

    @property
    def allowed_tools(self) -> frozenset[str]:
        return self._allowed

    def _ok(self, name: str, text: str) -> ToolResult:
        return ToolResult(tool_name=name, success=True, data={"text": text})

    def _err(self, name: str, error: str) -> ToolResult:
        return ToolResult(tool_name=name, success=False, error=error)

    async def list_tools(self) -> list[str]:
        names = await self._session.list_tool_names()
        return [n for n in names if n in self._allowed]

    async def call(self, tool: ToolCall) -> ToolResult:
        name = tool.tool_name
        if name not in self._allowed:
            return self._err(name, f"Tool '{name}' not allowed for current scope")
        try:
            ok, text = await self._session.call_tool(name, dict(tool.parameters))
            if ok:
                return self._ok(name, text)
            return self._err(name, text or "tool failed")
        except Exception as exc:  # noqa: BLE001
            return self._err(name, str(exc))
