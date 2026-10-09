"""P4 invoke: per-app tokens, origin binding, outcomes, audit, rejection (spec §14.1)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

import httpx
import pytest
from packages.common.providers.audit_sink import AuditEvent
from packages.common.providers.credential_broker import MockCredentialBroker
from packages.sse.invoke import effective_base, invoke_sse_api
from packages.sse.loader import OpenApiCatalogService
from packages.sse.tools import handle_call_sse_api, resolve_invoke_target
from packages.sse.types import ApiOperation, AppTarget, Rejection
from packages.api_index.breaker import InMemoryBreaker


class _AuditCapture:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def emit(self, event: AuditEvent) -> None:
        self.events.append(event)

    async def flush(self) -> None:
        return None


def _op(
    *,
    app: str = "fees",
    label: str = "Fees API",
    method: str = "get",
    path: str = "/api/fees/{id}",
    server_url: str | None = None,
    base: str = "https://feesapi.dev.example.invalid",
) -> ApiOperation:
    return ApiOperation(
        id=f"{app}:getFees",
        source_id=app,
        source_label=label,
        method=method,  # type: ignore[arg-type]
        path=path,
        operation_id="getFees",
        server_url=server_url,
        source_base_url=base,
    )


def _target(
    app: str = "fees",
    label: str = "Fees API",
    base: str = "https://feesapi.dev.example.invalid",
) -> AppTarget:
    origin = f"{urlparse(base).scheme}://{urlparse(base).netloc}"
    return AppTarget(
        application_id=app,
        label=label,
        environment="dev",
        base_url=base,
        origin=origin,
        audience="https://fees.aud",
    )


class _PerHostTransport(httpx.AsyncBaseTransport):
    """Assert Authorization header per host; return canned responses."""

    def __init__(
        self,
        tokens_by_host: dict[str, str],
        *,
        status_by_host: dict[str, int] | None = None,
    ) -> None:
        self.tokens_by_host = tokens_by_host
        self.status_by_host = status_by_host or {}
        self.seen: list[tuple[str, str | None]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host or ""
        auth = request.headers.get("Authorization")
        self.seen.append((host, auth))
        expected = self.tokens_by_host.get(host)
        if expected is not None:
            assert auth == f"Bearer {expected}", (
                f"host {host} got {auth!r}, expected Bearer {expected!r}"
            )
        status = self.status_by_host.get(host, 200)
        return httpx.Response(status, json={"ok": status == 200, "host": host})


@pytest.mark.asyncio
async def test_per_app_token_never_crosses_hosts() -> None:
    broker = MockCredentialBroker(
        tokens={"fees": "tok-fees", "escrow": "tok-escrow"}
    )
    transport = _PerHostTransport(
        {
            "feesapi.dev.example.invalid": "tok-fees",
            "escrowapi.dev.example.invalid": "tok-escrow",
        }
    )
    service = OpenApiCatalogService(
        swagger_links=[],
        api_base_url="https://feesapi.dev.example.invalid",
        registry_mode=True,
        app_targets=lambda: {
            "fees": _target("fees", base="https://feesapi.dev.example.invalid"),
            "escrow": _target(
                "escrow",
                label="Escrow Manager",
                base="https://escrowapi.dev.example.invalid",
            ),
        },
    )
    for app, base in (
        ("fees", "https://feesapi.dev.example.invalid"),
        ("escrow", "https://escrowapi.dev.example.invalid"),
    ):
        result = await invoke_sse_api(
            service,
            method="GET",
            path="/api/x",
            operation=_op(app=app, base=base, path="/api/x", label=app),
            target=_target(app, base=base),
            credentials=broker,
            transport=transport,
            registry_mode=True,
        )
        assert result.outcome == "ok"
    hosts = {h for h, _ in transport.seen}
    assert "feesapi.dev.example.invalid" in hosts
    assert "escrowapi.dev.example.invalid" in hosts


@pytest.mark.asyncio
async def test_401_retry_then_no_access() -> None:
    broker = MockCredentialBroker(tokens={"fees": "tok"})
    calls = {"n": 0}

    class Once401(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(401, json={"error": "unauthorized"})

    service = OpenApiCatalogService(registry_mode=True, swagger_links=[])
    result = await invoke_sse_api(
        service,
        method="GET",
        path="/api/x",
        operation=_op(path="/api/x"),
        target=_target(),
        credentials=broker,
        transport=Once401(),
        registry_mode=True,
    )
    assert result.outcome == "no_access"
    assert "Fees API" in (result.error_message or "")
    assert "unauthorized" not in (result.error_message or "").lower()
    assert calls["n"] == 1  # same token after invalidate → no useful retry


@pytest.mark.asyncio
async def test_403_no_access() -> None:
    broker = MockCredentialBroker(tokens={"fees": "tok"})

    class Forbidden(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={})

    result = await invoke_sse_api(
        OpenApiCatalogService(registry_mode=True, swagger_links=[]),
        method="GET",
        path="/api/x",
        operation=_op(path="/api/x"),
        target=_target(),
        credentials=broker,
        transport=Forbidden(),
        registry_mode=True,
    )
    assert result.outcome == "no_access"
    assert "permission" in (result.error_message or "").lower()


@pytest.mark.asyncio
async def test_timeout_unavailable_and_breaker() -> None:
    broker = MockCredentialBroker(tokens={"fees": "tok"})
    breaker = InMemoryBreaker(threshold=5, cooldown_s=30.0)

    class Hang(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("boom")

    service = OpenApiCatalogService(registry_mode=True, swagger_links=[])
    for _ in range(5):
        result = await invoke_sse_api(
            service,
            method="GET",
            path="/api/x",
            operation=_op(path="/api/x"),
            target=_target(),
            credentials=broker,
            breaker=breaker,
            transport=Hang(),
            registry_mode=True,
        )
        assert result.outcome == "unavailable"

    assert breaker.is_open("fees")
    # Sixth call short-circuits (no transport hit)
    class FailIfCalled(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise AssertionError("breaker should prevent I/O")

    short = await invoke_sse_api(
        service,
        method="GET",
        path="/api/x",
        operation=_op(path="/api/x"),
        target=_target(),
        credentials=broker,
        breaker=breaker,
        transport=FailIfCalled(),
        registry_mode=True,
    )
    assert short.outcome == "unavailable"


@pytest.mark.asyncio
async def test_client_authorization_stripped() -> None:
    broker = MockCredentialBroker(tokens={"fees": "tok-fees"})
    seen: list[str | None] = []

    class Capture(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            seen.append(request.headers.get("Authorization"))
            return httpx.Response(200, json={})

    await invoke_sse_api(
        OpenApiCatalogService(registry_mode=True, swagger_links=[]),
        method="GET",
        path="/api/x",
        operation=_op(path="/api/x"),
        target=_target(),
        credentials=broker,
        headers={"Authorization": "Bearer evil", "X-Custom": "1"},
        transport=Capture(),
        registry_mode=True,
    )
    assert seen == ["Bearer tok-fees"]


@pytest.mark.asyncio
async def test_origin_mismatch_raises() -> None:
    """target.origin binding rejects URL on another host."""
    broker = MockCredentialBroker(tokens={"fees": "tok"})
    bad = AppTarget(
        application_id="fees",
        label="Fees",
        environment="dev",
        base_url="https://feesapi.dev.example.invalid",
        origin="https://other.example.invalid",  # intentional mismatch
        audience="aud",
    )
    with pytest.raises(PermissionError):
        await invoke_sse_api(
            OpenApiCatalogService(registry_mode=True, swagger_links=[]),
            method="GET",
            path="/api/x",
            operation=_op(path="/api/x"),
            target=bad,
            credentials=broker,
            registry_mode=True,
        )


@pytest.mark.asyncio
async def test_audit_live_read_emitted() -> None:
    broker = MockCredentialBroker(tokens={"fees": "tok"})
    audit = _AuditCapture()

    class Ok(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"a": 1})

    await invoke_sse_api(
        OpenApiCatalogService(registry_mode=True, swagger_links=[]),
        method="GET",
        path="/api/x",
        operation=_op(path="/api/x"),
        target=_target(),
        credentials=broker,
        audit=audit,  # type: ignore[arg-type]
        transport=Ok(),
        registry_mode=True,
    )
    assert len(audit.events) == 1
    assert audit.events[0].event_type == "sse.live_read"
    payload = audit.events[0].payload
    assert payload["outcome"] == "ok"
    assert payload["application_id"] == "fees"
    assert "token" not in json.dumps(payload).lower()


@pytest.mark.asyncio
async def test_registry_raw_method_path_requires_application() -> None:
    service = OpenApiCatalogService(
        registry_mode=True,
        swagger_links=[],
        app_targets=lambda: {"fees": _target()},
    )
    audit = _AuditCapture()
    text = await handle_call_sse_api(
        service,
        {"method": "GET", "path": "/api/fees/1"},
        audit=audit,  # type: ignore[arg-type]
        registry_mode=True,
        credentials=MockCredentialBroker(tokens={"fees": "tok"}),
    )
    payload = json.loads(text)
    assert payload["outcome"] == "rejected"
    assert "application" in payload["error"].lower()
    assert any(e.payload.get("outcome") == "rejected" for e in audit.events)


def test_resolve_application_required() -> None:
    service = OpenApiCatalogService(registry_mode=True, swagger_links=[])
    result = resolve_invoke_target(
        service,
        operation_ref=None,
        method="GET",
        path="/api/x",
        application=None,
        resolver=None,
        registry_mode=True,
        catalog_ops=[],
    )
    assert isinstance(result, Rejection)
    assert result.reason == "application_required"


def test_effective_base_same_origin_server_path() -> None:
    target = _target(base="https://feesapi.dev.example.invalid")
    op = _op(
        server_url="https://feesapi.dev.example.invalid/fees",
        base="https://feesapi.dev.example.invalid",
    )
    assert effective_base(target, op) == "https://feesapi.dev.example.invalid/fees"


def test_effective_base_ignores_foreign_server() -> None:
    target = _target(base="https://feesapi.dev.example.invalid")
    op = _op(
        server_url="https://other.example.invalid/fees",
        base="https://feesapi.dev.example.invalid",
    )
    assert effective_base(target, op) == "https://feesapi.dev.example.invalid"


@pytest.mark.asyncio
async def test_sc006_named_no_access_message() -> None:
    broker = MockCredentialBroker(tokens={})  # missing fees
    result = await invoke_sse_api(
        OpenApiCatalogService(registry_mode=True, swagger_links=[]),
        method="GET",
        path="/api/loans/1/summary",
        operation=_op(path="/api/loans/1/summary", label="Loan Summary API"),
        target=_target(label="Loan Summary API"),
        credentials=broker,
        registry_mode=True,
    )
    assert result.outcome == "no_access"
    msg = result.error_message or ""
    assert "Loan Summary API" in msg
    assert "fees" in msg
    assert "unauthorized" not in msg.lower()


@pytest.mark.asyncio
async def test_one_app_unavailable_other_ok() -> None:
    broker = MockCredentialBroker(tokens={"fees": "t1", "escrow": "t2"})

    class Mixed(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if "escrow" in (request.url.host or ""):
                raise httpx.ConnectError("down")
            return httpx.Response(200, json={"fees": True})

    service = OpenApiCatalogService(registry_mode=True, swagger_links=[])
    transport = Mixed()
    fees = await invoke_sse_api(
        service,
        method="GET",
        path="/api/x",
        operation=_op(path="/api/x"),
        target=_target(),
        credentials=broker,
        transport=transport,
        registry_mode=True,
    )
    escrow = await invoke_sse_api(
        service,
        method="GET",
        path="/api/y",
        operation=_op(
            app="escrow",
            label="Escrow Manager",
            path="/api/y",
            base="https://escrowapi.dev.example.invalid",
        ),
        target=_target(
            "escrow",
            label="Escrow Manager",
            base="https://escrowapi.dev.example.invalid",
        ),
        credentials=broker,
        transport=transport,
        registry_mode=True,
    )
    assert fees.outcome == "ok"
    assert escrow.outcome == "unavailable"
    assert "Escrow Manager" in (escrow.error_message or "")
