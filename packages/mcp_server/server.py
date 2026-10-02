"""FastMCP Streamable HTTP server. Tools delegate to ModularToolsClient."""

from __future__ import annotations

import contextlib
import json
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Protocol, cast

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from packages.common.providers import AuditEvent, ToolCall, ToolResult
from packages.common.providers.factory import (
    build_modular_tools_client,
    get_audit_sink_provider,
)
from packages.common.scopes import EAKG_TOOL_NAMES, tools_for_role
from packages.common.settings import Settings
from packages.mcp_server.policy import (
    AuthError,
    PolicyError,
    assert_sse_read_only,
    assert_tool_allowed,
    bearer_matches,
    body_present,
)

_READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)

_SECRET_KEYS = frozenset({"authorization", "api_key", "token", "password", "secret"})


@dataclass(frozen=True)
class RequestMeta:
    authorization: str | None
    user: str | None
    tenant: str | None


_request_meta: ContextVar[RequestMeta | None] = ContextVar("mcp_request_meta", default=None)


class _Op(Protocol):
    method: str


class _Tools(Protocol):
    async def find_sse_operation(
        self,
        *,
        operation_id: str | None = None,
        method: str | None = None,
        path: str | None = None,
    ) -> _Op | None: ...

    async def call(self, tool: ToolCall) -> ToolResult: ...


class _Audit(Protocol):
    async def emit(self, event: AuditEvent) -> None: ...


class StaticTokenVerifier(TokenVerifier):
    """Compare the bearer to MCP__AUTH_TOKEN. Empty config rejects every token."""

    def __init__(self, expected: str) -> None:
        self._expected = expected

    async def verify_token(self, token: str) -> AccessToken | None:
        if not bearer_matches(f"Bearer {token}", self._expected):
            return None
        return AccessToken(token="accepted", client_id="mcp", scopes=["mcp"])


class CaptureHeadersMiddleware:
    """Stash user/tenant headers for the tool handler. Does not log them."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        token = _request_meta.set(
            RequestMeta(
                authorization=headers.get("authorization"),
                user=headers.get("x-loanops-user"),
                tenant=headers.get("x-loanops-tenant"),
            )
        )
        try:
            await self.app(scope, receive, send)
        finally:
            _request_meta.reset(token)


def sanitize_args(args: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in args.items():
        if key.lower() in _SECRET_KEYS:
            clean[key] = "[redacted]"
        elif isinstance(value, str):
            clean[key] = value[:500]
        elif isinstance(value, dict):
            clean[key] = sanitize_args(value)
        else:
            clean[key] = value
    return clean


def _meta() -> RequestMeta:
    current = _request_meta.get()
    if current is None:
        return RequestMeta(authorization=None, user=None, tenant=None)
    return current


async def _execute_eakg_tool(
    name: str,
    arguments: dict[str, Any],
    settings: Settings,
) -> str:
    """Run EAKG query tools. When approved_only, read catalog/approved.ttl only."""
    from pathlib import Path

    from packages.capability_kg.store import load_graph
    from packages.eakg.merge import merge_shards
    from packages.eakg.query import (
        explain_capability,
        find_providers,
        impact_of_change,
        search_capabilities,
    )

    ns = settings.capability_kg.namespace
    if settings.capability_kg.approved_only:
        approved = Path(settings.eakg.shard_dir) / "catalog" / "approved.ttl"
        if not approved.is_file():
            return json.dumps([])
        graph = load_graph(approved, namespace=ns)
    else:
        graph = merge_shards(settings.eakg.shard_dir, namespace=ns)

    if name == "search_capabilities":
        rows = search_capabilities(
            graph,
            str(arguments.get("query") or ""),
            namespace=ns,
            limit=int(arguments.get("limit") or 15),
        )
        return json.dumps(rows, indent=2)
    if name == "explain_capability":
        row = explain_capability(
            graph,
            str(arguments.get("capability_id") or ""),
            namespace=ns,
        )
        return json.dumps(row or {"error": "not found"}, indent=2)
    if name == "find_providers":
        rows = find_providers(graph, str(arguments.get("query") or ""), namespace=ns)
        return json.dumps(rows, indent=2)
    if name == "impact_of_change":
        rows = impact_of_change(graph, str(arguments.get("target") or ""), namespace=ns)
        if settings.capability_kg.approved_only:
            rows = [r for r in rows if r.get("review_status") == "approved"]
        return json.dumps(rows, indent=2)
    raise PolicyError(f"Unknown EAKG tool: {name}")


async def execute_tool(
    *,
    name: str,
    arguments: dict[str, Any],
    authorization: str | None,
    user: str | None,
    tenant: str | None,
    settings: Settings,
    client: _Tools,
    audit: _Audit | None,
) -> str:
    """Auth, scope, GET-only, then the existing tools client. Raises AuthError or PolicyError."""
    started = time.perf_counter()
    error: str | None = None
    success = False
    summary = ""
    decision = "denied"
    call_args = dict(arguments)
    try:
        if not bearer_matches(authorization, settings.mcp.auth_token):
            raise AuthError("unauthorized")
        allowed = tools_for_role(settings.mcp.role)
        assert_tool_allowed(name, allowed)

        if name in EAKG_TOOL_NAMES:
            decision = "allowed"
            full = await _execute_eakg_tool(name, call_args, settings)
            success = True
            summary = full[:500]
            return full

        if name == "call_sse_api":
            method_arg = call_args.get("method")
            method_text = str(method_arg) if method_arg is not None else None
            if body_present(call_args.get("body")):
                raise PolicyError("call_sse_api body is not allowed")
            if method_text is not None and method_text.strip().upper() != "GET":
                raise PolicyError("call_sse_api method must be GET")
            op_id = call_args.get("operation_id")
            path = call_args.get("path")
            operation = await client.find_sse_operation(
                operation_id=str(op_id) if op_id else None,
                method=method_text,
                path=str(path) if path else None,
            )
            resolved = operation.method if operation is not None else None
            assert_sse_read_only(method_arg=method_text, body=None, resolved_method=resolved)
            # Principal → enterprise request headers (service bearer still SSE__API_KEY).
            headers_raw = call_args.get("headers")
            headers: dict[str, Any] = dict(headers_raw) if isinstance(headers_raw, dict) else {}
            eff_user = user or (settings.mcp.principal_user or None)
            eff_tenant = tenant or (settings.mcp.principal_tenant or None)
            if eff_user:
                headers.setdefault("x-loanops-user", eff_user)
            if eff_tenant:
                headers.setdefault("x-loanops-tenant", eff_tenant)
            if headers:
                call_args["headers"] = headers

        decision = "allowed"
        result = await client.call(ToolCall(tool_name=name, parameters=call_args))
        success = result.success
        if result.success:
            data = result.data or {}
            text = data.get("text")
            full = str(text if text is not None else data)
            summary = full[:500]
            return full
        error = result.error or "tool failed"
        summary = error[:500]
        raise ToolError(error)
    except (AuthError, PolicyError) as exc:
        error = str(exc)
        summary = error
        raise
    finally:
        if audit is not None:
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            with contextlib.suppress(Exception):
                await audit.emit(
                    AuditEvent(
                        event_id=str(uuid.uuid4()),
                        event_type="mcp.tool.call",
                        user_id=user or (settings.mcp.principal_user or None),
                        payload={
                            "tool_name": name,
                            "role": settings.mcp.role,
                            "tenant": tenant or (settings.mcp.principal_tenant or None),
                            "arguments": sanitize_args(call_args),
                            "authorization": decision,
                            "success": success,
                            "latency_ms": elapsed,
                            "error": error,
                            "result_summary": summary[:500],
                        },
                    )
                )


def create_app(cfg: Settings | None = None) -> Starlette:
    """Streamable HTTP app. /health is public. /mcp requires MCP__AUTH_TOKEN."""
    settings = cfg if cfg is not None else Settings()
    host = settings.mcp.host
    port = settings.mcp.port
    path = settings.mcp.path
    base = f"http://{host}:{port}"
    mcp = FastMCP(
        "LoanOps",
        instructions="Loan servicing read tools. call_sse_api is GET-only.",
        host=host,
        port=port,
        streamable_http_path=path,
        stateless_http=True,
        json_response=True,
        token_verifier=StaticTokenVerifier(settings.mcp.auth_token),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(f"{base}/"),
            resource_server_url=AnyHttpUrl(f"{base}{path}"),
        ),
    )
    client_box: dict[str, _Tools] = {}

    def client() -> _Tools:
        if "client" not in client_box:
            client_box["client"] = cast(
                _Tools, build_modular_tools_client(settings, role=settings.mcp.role)
            )
        return client_box["client"]

    async def _run(name: str, arguments: dict[str, Any]) -> str:
        meta = _meta()
        try:
            return await execute_tool(
                name=name,
                arguments=arguments,
                authorization=meta.authorization,
                user=meta.user,
                tenant=meta.tenant,
                settings=settings,
                client=client(),
                audit=get_audit_sink_provider(),
            )
        except (AuthError, PolicyError) as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        name="search_sse_apis",
        description=("Search SSE OpenAPI catalogs by keywords. Prefer this before call_sse_api."),
        annotations=_READ_ONLY,
    )
    async def search_sse_apis(query: str, limit: int = 15) -> str:
        return await _run("search_sse_apis", {"query": query, "limit": limit})

    @mcp.tool(
        name="list_sse_apis",
        description="List discovered SSE REST operations. Optional source_label filters one app.",
        annotations=_READ_ONLY,
    )
    async def list_sse_apis(
        source_label: str | None = None,
        limit: int = 50,
        refresh: bool = False,
    ) -> str:
        args: dict[str, Any] = {"limit": limit, "refresh": refresh}
        if source_label is not None:
            args["source_label"] = source_label
        return await _run("list_sse_apis", args)

    @mcp.tool(
        name="call_sse_api",
        description=(
            "Invoke a GET SSE REST operation by operation_id or method+path. "
            "Non-GET methods and bodies are rejected."
        ),
        annotations=_READ_ONLY,
    )
    async def call_sse_api(
        operation_id: str | None = None,
        method: str | None = None,
        path: str | None = None,
        path_params: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> str:
        args = {
            "operation_id": operation_id,
            "method": method,
            "path": path,
            "path_params": path_params,
            "query": query,
            "body": body,
        }
        return await _run("call_sse_api", {k: v for k, v in args.items() if v is not None})

    @mcp.tool(
        name="search_docs",
        description=(
            "Search indexed documentation (SOPs / wiki narratives). Not for live loan numbers."
        ),
        annotations=_READ_ONLY,
    )
    async def search_docs(query: str, top_k: int = 5) -> str:
        return await _run("search_docs", {"query": query, "top_k": top_k})

    @mcp.tool(
        name="search_capabilities",
        description=(
            "Search the enterprise capability knowledge graph by keyword. "
            "Returns capabilities with provenance when available."
        ),
        annotations=_READ_ONLY,
    )
    async def search_capabilities_tool(query: str, limit: int = 15) -> str:
        return await _run("search_capabilities", {"query": query, "limit": limit})

    @mcp.tool(
        name="explain_capability",
        description=(
            "Explain one capability: application, API operation, code unit, "
            "permission/authzSource, and evidence."
        ),
        annotations=_READ_ONLY,
    )
    async def explain_capability_tool(capability_id: str) -> str:
        return await _run("explain_capability", {"capability_id": capability_id})

    @mcp.tool(
        name="find_providers",
        description="Which application/API provides a capability or operation name.",
        annotations=_READ_ONLY,
    )
    async def find_providers_tool(query: str) -> str:
        return await _run("find_providers", {"query": query})

    @mcp.tool(
        name="impact_of_change",
        description=(
            "Which applications depend on an API/application via callsOperation/"
            "consumesSdk (evidence included)."
        ),
        annotations=_READ_ONLY,
    )
    async def impact_of_change_tool(target: str) -> str:
        return await _run("impact_of_change", {"target": target})

    @mcp.custom_route("/health", methods=["GET"])  # type: ignore[untyped-decorator]
    async def health(_request: Request) -> Response:
        try:
            client()
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                {"status": "not_ready", "detail": type(exc).__name__}, status_code=503
            )
        return JSONResponse({"status": "ok"})

    app = mcp.streamable_http_app()
    app.add_middleware(CaptureHeadersMiddleware)
    return app
