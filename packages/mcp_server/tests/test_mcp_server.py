"""MCP policy and unauthenticated Streamable HTTP."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from packages.common.providers import AuditEvent, ToolCall, ToolResult
from packages.common.settings import McpConfig, Settings
from packages.mcp_server.policy import AuthError, PolicyError
from packages.mcp_server.server import create_app, execute_tool


class _Op:
    def __init__(self, method: str) -> None:
        self.method = method


class FakeClient:
    def __init__(self, method: str = "get") -> None:
        self.method = method
        self.calls: list[ToolCall] = []

    async def find_sse_operation(
        self,
        *,
        operation_id: str | None = None,
        method: str | None = None,
        path: str | None = None,
    ) -> _Op | None:
        _ = method, path
        if operation_id == "missing":
            return None
        return _Op(self.method)

    async def call(self, tool: ToolCall) -> ToolResult:
        self.calls.append(tool)
        return ToolResult(tool_name=tool.tool_name, success=True, data={"text": "ok"})


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def emit(self, event: AuditEvent) -> None:
        self.events.append(event)


def _settings(role: str = "system") -> Settings:
    return Settings(mcp=McpConfig(auth_token="secret-token", role=role))


@pytest.mark.asyncio
async def test_missing_and_wrong_bearer_rejected() -> None:
    client = FakeClient()
    audit = FakeAudit()
    settings = _settings()
    with pytest.raises(AuthError):
        await execute_tool(
            name="search_docs",
            arguments={"query": "escrow"},
            authorization=None,
            user=None,
            tenant=None,
            settings=settings,
            client=client,
            audit=audit,
        )
    with pytest.raises(AuthError):
        await execute_tool(
            name="search_docs",
            arguments={"query": "escrow"},
            authorization="Bearer wrong",
            user="rep-1",
            tenant="t1",
            settings=settings,
            client=client,
            audit=audit,
        )
    assert client.calls == []
    assert audit.events[-1].payload["authorization"] == "denied"
    assert "secret-token" not in str(audit.events[-1].payload)


@pytest.mark.asyncio
async def test_care_rep_cannot_call_wiki_tool() -> None:
    client = FakeClient()
    with pytest.raises(PolicyError):
        await execute_tool(
            name="wiki_get_jira_ticket",
            arguments={"key": "SSE-1"},
            authorization="Bearer secret-token",
            user=None,
            tenant=None,
            settings=_settings("care_rep"),
            client=client,
            audit=FakeAudit(),
        )
    assert client.calls == []


@pytest.mark.asyncio
async def test_call_sse_api_rejects_post_and_body() -> None:
    client = FakeClient()
    settings = _settings()
    auth = "Bearer secret-token"
    with pytest.raises(PolicyError):
        await execute_tool(
            name="call_sse_api",
            arguments={"method": "POST", "path": "/api/Loans/1"},
            authorization=auth,
            user=None,
            tenant=None,
            settings=settings,
            client=client,
            audit=None,
        )
    with pytest.raises(PolicyError):
        await execute_tool(
            name="call_sse_api",
            arguments={"operation_id": "getLoanSummary", "body": {"amount": 1}},
            authorization=auth,
            user=None,
            tenant=None,
            settings=settings,
            client=client,
            audit=None,
        )
    assert client.calls == []


@pytest.mark.asyncio
async def test_call_sse_api_get_reaches_client() -> None:
    client = FakeClient(method="get")
    audit = FakeAudit()
    text = await execute_tool(
        name="call_sse_api",
        arguments={"operation_id": "getLoanSummary", "path_params": {"loan_id": "1000002245"}},
        authorization="Bearer secret-token",
        user="rep-1",
        tenant="servicing",
        settings=_settings(),
        client=client,
        audit=audit,
    )
    assert text == "ok"
    assert client.calls[0].tool_name == "call_sse_api"
    payload = audit.events[0].payload
    assert payload["authorization"] == "allowed"
    assert payload["success"] is True
    assert payload["tenant"] == "servicing"
    assert payload["tool_name"] == "call_sse_api"


@pytest.mark.asyncio
async def test_call_sse_api_injects_principal_headers() -> None:
    client = FakeClient(method="get")
    text = await execute_tool(
        name="call_sse_api",
        arguments={"operation_id": "getLoanSummary"},
        authorization="Bearer secret-token",
        user="rep-42",
        tenant="pnmac",
        settings=_settings(),
        client=client,
        audit=None,
    )
    assert text == "ok"
    headers = client.calls[0].parameters.get("headers") or {}
    assert headers["x-loanops-user"] == "rep-42"
    assert headers["x-loanops-tenant"] == "pnmac"


@pytest.mark.asyncio
async def test_customer_role_denied_eakg_tool() -> None:
    client = FakeClient()
    with pytest.raises(PolicyError):
        await execute_tool(
            name="search_capabilities",
            arguments={"query": "payment"},
            authorization="Bearer secret-token",
            user=None,
            tenant=None,
            settings=_settings("customer"),
            client=client,
            audit=FakeAudit(),
        )
    assert client.calls == []


def test_streamable_http_requires_bearer() -> None:
    app = create_app(
        Settings(mcp=McpConfig(auth_token="secret-token", role="system", host="127.0.0.1"))
    )
    with TestClient(app) as client:
        response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert response.status_code == 401
