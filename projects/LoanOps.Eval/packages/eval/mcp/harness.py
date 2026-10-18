"""Drivers and fake tools clients for Layer 1 MCP eval (no Auth suite)."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from packages.common.providers import ToolCall, ToolResult
from packages.common.settings import McpConfig, Settings, SseConfig
from packages.mcp_server.server import create_app, execute_tool
from starlette.testclient import TestClient

FIXTURE_BEARER = "eval-mcp-l1-token"
FIXTURE_AUTH_HEADER = f"Bearer {FIXTURE_BEARER}"

# Streamable HTTP DNS-rebinding allowlist expects host:port (see FastMCP defaults).
ASGI_BASE_URL = "http://127.0.0.1:8001"

EXPECTED_MCP_TOOLS: tuple[str, ...] = (
    "search_sse_apis",
    "list_sse_apis",
    "call_sse_api",
    "search_docs",
    "search_capabilities",
    "explain_capability",
    "find_providers",
    "impact_of_change",
    "describe_application",
    "search_code",
)

# Happy-path args for FakeClient (deterministic; no live backends).
HAPPY_ARGS: dict[str, dict[str, Any]] = {
    "search_sse_apis": {"query": "loan", "limit": 5},
    "list_sse_apis": {"limit": 10},
    "call_sse_api": {"operation_id": "getLoanSummary", "path_params": {"loan_id": "100245"}},
    "search_docs": {"query": "escrow", "top_k": 3},
    "search_capabilities": {"query": "payment", "limit": 5},
    "explain_capability": {"capability_id": "get_loan_summary"},
    "find_providers": {"query": "getLoanSummary"},
    "impact_of_change": {"target": "LoanServices"},
    "describe_application": {"application_id": "loan-services"},
    "search_code": {"application_id": "loan-services", "query": "Controller", "limit": 5},
}


class FakeMode(StrEnum):
    OK = "ok"
    EMPTY = "empty"
    FAIL = "fail"
    RAISE = "raise"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"


@dataclass
class RpcResponse:
    """Normalized JSON-RPC / HTTP outcome from an MCP driver."""

    http_status: int
    body: dict[str, Any] | None
    raw_text: str
    protocol_error: dict[str, Any] | None = None
    result: dict[str, Any] | None = None

    @property
    def is_jsonrpc_error(self) -> bool:
        return self.protocol_error is not None

    @property
    def tool_is_error(self) -> bool | None:
        if self.result is None:
            return None
        if "isError" in self.result:
            return bool(self.result["isError"])
        # FastMCP may omit isError on success
        return False


class _Op:
    def __init__(self, method: str = "get") -> None:
        self.method = method


@dataclass
class FakeClient:
    """In-process stub matching MCP ``execute_tool`` client Protocol."""

    mode: FakeMode = FakeMode.OK
    method: str = "get"
    calls: list[ToolCall] = field(default_factory=list)
    timeout_flag: bool = False  # when True, TIMEOUT mode returns immediately as error

    async def find_sse_operation(
        self,
        *,
        operation_id: str | None = None,
        method: str | None = None,
        path: str | None = None,
    ) -> _Op | None:
        _ = method, path
        if operation_id == "missing" or operation_id == "unknown_op":
            return None
        return _Op(self.method)

    async def call(self, tool: ToolCall) -> ToolResult:
        self.calls.append(tool)
        name = tool.tool_name
        if self.mode == FakeMode.RAISE:
            raise RuntimeError("simulated upstream exception")
        if self.mode == FakeMode.TIMEOUT:
            if not self.timeout_flag:
                await asyncio.sleep(0.01)
            return ToolResult(
                tool_name=name,
                success=False,
                error="timeout: upstream request exceeded deadline",
            )
        if self.mode == FakeMode.RATE_LIMIT:
            return ToolResult(
                tool_name=name,
                success=False,
                error="429 rate limit: too many requests",
            )
        if self.mode == FakeMode.FAIL:
            return ToolResult(tool_name=name, success=False, error="upstream failed")
        if self.mode == FakeMode.EMPTY:
            return ToolResult(
                tool_name=name,
                success=True,
                data={"text": _empty_text(name)},
            )
        return ToolResult(tool_name=name, success=True, data={"text": _ok_text(name)})

    def capability_catalog(self) -> Any | None:
        return None

    def operation_resolver(self) -> Any | None:
        return None


def _ok_text(name: str) -> str:
    return f"ok:{name}"


def _empty_text(name: str) -> str:
    return f"empty:{name}: no matches"


@dataclass
class FixtureCatalogClient:
    """Deterministic fixture-shaped responses for SSE catalog tools (no HF / live HTTP)."""

    calls: list[ToolCall] = field(default_factory=list)
    empty_search: bool = False

    async def find_sse_operation(
        self,
        *,
        operation_id: str | None = None,
        method: str | None = None,
        path: str | None = None,
    ) -> _Op | None:
        _ = method, path
        if operation_id in (None, "", "unknown_op", "missing"):
            return None
        return _Op("get")

    async def call(self, tool: ToolCall) -> ToolResult:
        self.calls.append(tool)
        name = tool.tool_name
        if name == "list_sse_apis":
            text = (
                "empty:list_sse_apis: no operations"
                if self.empty_search
                else (
                    "operations:\n"
                    "- getLoanSummary GET /api/Loans/{loanId}\n"
                    "- getPaymentSchedules GET /api/..."
                )
            )
            return ToolResult(tool_name=name, success=True, data={"text": text})
        if name == "search_sse_apis":
            q = str(tool.parameters.get("query") or "")
            if self.empty_search or q == "__no_match__":
                return ToolResult(
                    tool_name=name,
                    success=True,
                    data={"text": "empty:search_sse_apis: no confident match"},
                )
            return ToolResult(
                tool_name=name,
                success=True,
                data={
                    "text": (
                        "backend: fixture\n"
                        f"query={q}\n"
                        "- getLoanSummary invoke: call_sse_api\n"
                    )
                },
            )
        if name == "call_sse_api":
            op = tool.parameters.get("operation_id")
            if op in (None, "", "unknown_op"):
                return ToolResult(
                    tool_name=name,
                    success=False,
                    error="operation not found",
                )
            return ToolResult(
                tool_name=name,
                success=True,
                data={"text": '{"loanId":"100245","status":"active","fixture":true}'},
            )
        if name == "search_docs":
            q = str(tool.parameters.get("query") or "")
            if self.empty_search or q == "__no_match__":
                return ToolResult(
                    tool_name=name,
                    success=True,
                    data={"text": "empty:search_docs: no matches"},
                )
            return ToolResult(
                tool_name=name,
                success=True,
                data={"text": f"- [sop] escrow/annual-analysis.md (score=0.9) query={q}"},
            )
        # EAKG-shaped stubs
        return ToolResult(tool_name=name, success=True, data={"text": f"fixture:{name}"})

    def capability_catalog(self) -> Any | None:
        return None

    def operation_resolver(self) -> Any | None:
        return None


def eval_settings(*, role: str = "system") -> Settings:
    return Settings(
        mcp=McpConfig(auth_token=FIXTURE_BEARER, role=role, host="127.0.0.1", port=8001),
        sse=SseConfig(use_fixture=True, swagger_links=[]),
    )


def _parse_rpc_body(
    raw: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return None, None, None
    if not isinstance(body, dict):
        return None, None, None
    err = body.get("error")
    result = body.get("result")
    return (
        body,
        err if isinstance(err, dict) else None,
        result if isinstance(result, dict) else None,
    )


class AsgiMcpDriver:
    """In-process Streamable HTTP via TestClient (default).

    Each ``rpc`` builds a fresh ``create_app`` — StreamableHTTPSessionManager
    allows ``.run()`` only once per app instance.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or eval_settings()
        self._headers = {
            "Authorization": FIXTURE_AUTH_HEADER,
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "Host": "127.0.0.1:8001",
        }

    def rpc(
        self,
        payload: dict[str, Any] | bytes | str,
        *,
        headers: dict[str, str] | None = None,
    ) -> RpcResponse:
        hdrs = dict(self._headers)
        if headers:
            hdrs.update(headers)
        app = create_app(self.settings)
        with TestClient(app, base_url=ASGI_BASE_URL) as client:
            if isinstance(payload, (bytes, str)):
                content = payload if isinstance(payload, bytes) else payload.encode("utf-8")
                response = client.post("/mcp", content=content, headers=hdrs)
            else:
                response = client.post("/mcp", json=payload, headers=hdrs)
        body, err, result = _parse_rpc_body(response.text)
        return RpcResponse(
            http_status=response.status_code,
            body=body,
            raw_text=response.text,
            protocol_error=err,
            result=result,
        )

    def initialize(self, protocol_version: str = "2025-03-26") -> RpcResponse:
        return self.rpc(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": protocol_version,
                    "capabilities": {},
                    "clientInfo": {"name": "loanops-eval-l1", "version": "0.1.0"},
                },
            }
        )

    def tools_list(self) -> RpcResponse:
        return self.rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    def tools_call(self, name: str, arguments: dict[str, Any]) -> RpcResponse:
        return self.rpc(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )


@contextmanager
def live_mcp_server(settings: Settings | None = None, *, port: int = 8765) -> Iterator[str]:
    """Start uvicorn on an ephemeral-ish port; yield base MCP URL."""
    import uvicorn

    cfg = settings or eval_settings()
    # Bind the listener port we publish.
    cfg = cfg.model_copy(
        update={"mcp": cfg.mcp.model_copy(update={"port": port, "host": "127.0.0.1"})}
    )
    app = create_app(cfg)
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    # Wait until listening
    deadline = time.time() + 10.0
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("live MCP server failed to start")
    try:
        yield f"http://127.0.0.1:{port}{cfg.mcp.path}"
    finally:
        server.should_exit = True
        thread.join(timeout=5.0)


class LiveMcpDriver:
    """Real Streamable HTTP client against a live uvicorn (integration)."""

    def __init__(self, url: str, *, auth_token: str = FIXTURE_BEARER) -> None:
        self.url = url
        self.auth_token = auth_token

    async def list_tool_names(self) -> list[str]:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        async with streamablehttp_client(self.url, headers=headers, timeout=30.0) as (
            read,
            write,
            _sid,
        ), ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            return [t.name for t in listed.tools]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        from mcp.types import TextContent

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        async with streamablehttp_client(self.url, headers=headers, timeout=30.0) as (
            read,
            write,
            _sid,
        ), ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            parts: list[str] = []
            for block in result.content:
                if isinstance(block, TextContent):
                    parts.append(block.text)
                else:
                    parts.append(str(block))
            text = "\n".join(parts) if parts else ""
            return (not result.isError), text


async def run_execute(
    *,
    name: str,
    arguments: dict[str, Any],
    client: FakeClient | FixtureCatalogClient,
    settings: Settings | None = None,
    audit: Any | None = None,
    telemetry: Any | None = None,
) -> str:
    """Call ``execute_tool`` with fixture bearer (tool-level path)."""
    return await execute_tool(
        name=name,
        arguments=arguments,
        authorization=FIXTURE_AUTH_HEADER,
        user=None,
        tenant=None,
        settings=settings or eval_settings(),
        client=client,
        audit=audit,
        telemetry=telemetry,
    )


def tool_list_snapshot_payload(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize tools/list entries for snapshot compare."""
    out: list[dict[str, Any]] = []
    for t in sorted(tools, key=lambda x: str(x.get("name", ""))):
        ann = t.get("annotations") or {}
        out.append(
            {
                "name": t.get("name"),
                "description": t.get("description"),
                "inputSchema": t.get("inputSchema") or t.get("input_schema"),
                "readOnlyHint": ann.get("readOnlyHint", ann.get("readOnly")),
            }
        )
    return out


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = int(round((p / 100.0) * (len(sorted_vals) - 1)))
    idx = max(0, min(idx, len(sorted_vals) - 1))
    return sorted_vals[idx]
