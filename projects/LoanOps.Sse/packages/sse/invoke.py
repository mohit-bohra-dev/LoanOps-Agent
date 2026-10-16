"""Invoke SSE REST APIs with per-app credentials, origin binding, and outcomes."""

from __future__ import annotations

import re
import time
import uuid
from typing import Any, Literal
from urllib.parse import quote, urlencode, urljoin, urlparse

import httpx
from packages.common.providers.audit_sink import AuditEvent
from packages.common.providers.credential_broker import (
    AbstractCredentialBroker,
    CredentialDenied,
    CredentialError,
    CredentialNotConfigured,
    CredentialUnavailable,
    Principal,
)
from packages.sse.catalog import origin_of
from packages.sse.invoke_outcomes import LastInvokeRing
from packages.sse.loader import OpenApiCatalogService, assert_allowed_url
from packages.sse.types import ApiOperation, AppTarget, BreakerRegistry
from pydantic import BaseModel
from packages.common.providers.audit_sink import AuditSinkProvider


async def _record_invoke_metrics(
    *,
    application_id: str | None,
    outcome: str,
    duration_ms: float | None,
) -> None:
    try:
        from packages.common.providers.factory import get_telemetry_provider

        tel = get_telemetry_provider()
        attrs = {"app": application_id or "", "outcome": outcome}
        if duration_ms is not None:
            await tel.record_metric(
                "sse.invoke.latency_ms",
                float(duration_ms),
                unit="ms",
                attributes=attrs,
            )
        await tel.record_metric(
            "sse.invoke.outcome",
            1.0,
            unit="1",
            attributes=attrs,
        )
    except Exception:  # noqa: BLE001
        return

InvokeOutcome = Literal[
    "ok", "no_access", "unavailable", "not_found", "rejected", "error"
]

_STRIP_HEADERS = frozenset({"authorization", "cookie", "proxy-authorization"})
_INVOKE_TIMEOUT = httpx.Timeout(10.0, connect=3.0)


class InvokeResult(BaseModel):
    ok: bool
    status: int
    status_text: str
    url: str
    data: Any = None
    error_message: str | None = None
    duration_ms: float | None = None
    cache_hit: bool = False
    outcome: InvokeOutcome = "ok"
    application_id: str | None = None
    application: str | None = None
    operation_id: str | None = None
    environment: str | None = None


def substitute_path(template: str, path_params: dict[str, str] | None) -> str:
    path = template
    params = path_params or {}
    for name in re.findall(r"\{([^}]+)\}", template):
        value = params.get(name)
        if value is None or value == "":
            raise ValueError(f"Missing required path parameter: {name}")
        path = path.replace(f"{{{name}}}", quote(str(value), safe=""))
    for name, value in params.items():
        path = path.replace(f":{name}", quote(str(value), safe=""))
    return path


def resolve_base_url(service: OpenApiCatalogService, operation: ApiOperation | None) -> str:
    if operation and operation.server_url:
        return urljoin(operation.source_base_url + "/", operation.server_url).rstrip("/")
    if operation and operation.source_base_url:
        return operation.source_base_url.rstrip("/")
    return service.api_base_url.rstrip("/")


def _path_of_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path.rstrip("/") if parsed.path else ""


def _segments_equal(left: str, right: str) -> bool:
    a = [s for s in left.strip("/").split("/") if s]
    b = [s for s in right.strip("/").split("/") if s]
    if len(a) != len(b):
        return False
    return all(x.lower() == y.lower() for x, y in zip(a, b, strict=True))


def effective_base(target: AppTarget, operation: ApiOperation | None) -> str:
    """Compose registry base_url with same-origin spec server path (RC-005)."""
    base = target.base_url.rstrip("/")
    registry_path = _path_of_url(base)
    spec_path = ""
    if operation and operation.server_url:
        server = operation.server_url.strip()
        if "://" in server:
            try:
                if origin_of(server) == target.origin:
                    spec_path = _path_of_url(server)
                # else: different origin → ignore (build_operations records mismatch)
            except Exception:  # noqa: BLE001
                spec_path = ""
        else:
            spec_path = server.rstrip("/")
            if spec_path and not spec_path.startswith("/"):
                spec_path = "/" + spec_path
    if not spec_path:
        return base
    if registry_path and (
        _segments_equal(registry_path, spec_path)
        or registry_path.lower().endswith(spec_path.lower())
    ):
        return base
    return base + spec_path


def _app_label(target: AppTarget | None, operation: ApiOperation | None) -> str:
    if target is not None:
        return target.label
    if operation is not None:
        return operation.source_label
    return "application"


def _app_id(target: AppTarget | None, operation: ApiOperation | None) -> str:
    if target is not None:
        return target.application_id
    if operation is not None and operation.source_id:
        return operation.source_id
    return "-"


def _env(target: AppTarget | None) -> str:
    return target.environment if target is not None else "legacy"


def _public_op_id(operation: ApiOperation | None) -> str | None:
    if operation is None:
        return None
    return operation.id


def _strip_client_auth(headers: dict[str, str] | None) -> dict[str, str]:
    return {
        k: v
        for k, v in (headers or {}).items()
        if k.lower() not in _STRIP_HEADERS
    }


def _msg_no_access_missing(label: str, app_id: str, env: str) -> str:
    return f"{label} ({app_id}) has not granted LoanOps access in {env}."


def _msg_no_access_refused(label: str, app_id: str, env: str) -> str:
    return f"{label} ({app_id}) access was refused or revoked in {env}."


def _msg_no_access_perm(label: str, app_id: str) -> str:
    return f"LoanOps lacks permission to call {label} ({app_id})."


def _msg_cred_error(label: str) -> str:
    return f"Could not obtain credentials for {label}; try again later."


def _msg_unavailable(label: str, app_id: str) -> str:
    return f"{label} ({app_id}) is temporarily unavailable."


async def _emit_live_read(
    audit: AuditSinkProvider | None,
    *,
    application_id: str | None,
    operation_id: str | None,
    environment: str | None,
    status: int,
    outcome: InvokeOutcome,
    duration_ms: float,
    url_path_template: str | None,
) -> None:
    if audit is None:
        return
    try:
        await audit.emit(
            AuditEvent(
                event_id=str(uuid.uuid4()),
                event_type="sse.live_read",
                payload={
                    "application_id": application_id,
                    "operation_id": operation_id,
                    "environment": environment,
                    "status": status,
                    "outcome": outcome,
                    "duration_ms": round(duration_ms, 2),
                    "url_path_template": url_path_template,
                },
            )
        )
    except Exception:  # noqa: BLE001 — audit must not break invoke
        pass


def _result(
    *,
    ok: bool,
    status: int,
    status_text: str,
    url: str,
    outcome: InvokeOutcome,
    error_message: str | None = None,
    data: Any = None,
    duration_ms: float = 0.0,
    cache_hit: bool = False,
    target: AppTarget | None = None,
    operation: ApiOperation | None = None,
) -> InvokeResult:
    return InvokeResult(
        ok=ok,
        status=status,
        status_text=status_text,
        url=url,
        data=data,
        error_message=error_message,
        duration_ms=duration_ms,
        cache_hit=cache_hit,
        outcome=outcome,
        application_id=_app_id(target, operation) if target or operation else None,
        application=_app_label(target, operation) if target or operation else None,
        operation_id=_public_op_id(operation),
        environment=_env(target) if target else ("legacy" if operation else None),
    )


async def invoke_sse_api(
    service: OpenApiCatalogService,
    *,
    method: str,
    path: str,
    path_params: dict[str, str] | None = None,
    query: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    body: Any = None,
    operation: ApiOperation | None = None,
    cache: Any | None = None,
    cache_ttl: int = 60,
    target: AppTarget | None = None,
    credentials: AbstractCredentialBroker | None = None,
    breaker: BreakerRegistry | None = None,
    audit: AuditSinkProvider | None = None,
    principal: Principal | None = None,
    registry_mode: bool = False,
    transport: httpx.AsyncBaseTransport | None = None,
    invoke_ring: LastInvokeRing | None = None,
) -> InvokeResult:
    """Live GET/HEAD with per-app token, origin binding, and outcome classification."""
    _ = body  # read-only: never send a request body
    started = time.perf_counter()

    async def _finish(result: InvokeResult) -> InvokeResult:
        if invoke_ring is not None and result.application_id:
            invoke_ring.record(result.application_id, result.outcome)
        await _record_invoke_metrics(
            application_id=result.application_id,
            outcome=result.outcome,
            duration_ms=result.duration_ms,
        )
        return result

    if registry_mode and target is None:
        raise ValueError("registry_mode requires an AppTarget")

    method_u = method.upper()
    if method_u not in ("GET", "HEAD"):
        result = _result(
            ok=False,
            status=0,
            status_text="rejected",
            url="",
            outcome="rejected",
            error_message=f"invoke_sse_api only allows GET/HEAD, got {method_u}",
            target=target,
            operation=operation,
        )
        await _emit_live_read(
            audit,
            application_id=result.application_id,
            operation_id=result.operation_id,
            environment=result.environment,
            status=0,
            outcome="rejected",
            duration_ms=0.0,
            url_path_template=path,
        )
        return await _finish(result)

    if target is not None:
        base = effective_base(target, operation)
    else:
        base = resolve_base_url(service, operation)

    resolved = substitute_path(path, path_params)
    url = urljoin(base + "/", resolved.lstrip("/"))
    if query:
        url = f"{url}?{urlencode({k: str(v) for k, v in query.items()})}"

    app_id = _app_id(target, operation)
    label = _app_label(target, operation)
    env = _env(target)
    op_id = _public_op_id(operation)

    if target is not None:
        try:
            if origin_of(url) != target.origin:
                raise PermissionError(
                    f"Refusing to call {origin_of(url)}: must match app origin "
                    f"{target.origin}."
                )
        except PermissionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PermissionError(f"Invalid invoke URL: {url}") from exc
    else:
        assert_allowed_url(url, service.allowed_origins())

    principal_key = principal.user_id if principal and principal.user_id else "service"
    cache_key = f"sse:api:{env}:{app_id}:{principal_key}:{method_u}:{url}"
    if cache is not None and method_u == "GET":
        hit = await cache.get(cache_key)
        if hit is not None:
            cached = InvokeResult.model_validate({**hit, "cache_hit": True})
            await _emit_live_read(
                audit,
                application_id=cached.application_id,
                operation_id=cached.operation_id,
                environment=cached.environment,
                status=cached.status,
                outcome=cached.outcome,
                duration_ms=cached.duration_ms or 0.0,
                url_path_template=path,
            )
            return await _finish(cached)

    if breaker is not None and breaker.is_open(app_id):
        duration = (time.perf_counter() - started) * 1000
        result = _result(
            ok=False,
            status=0,
            status_text="unavailable",
            url=url,
            outcome="unavailable",
            error_message=_msg_unavailable(label, app_id),
            duration_ms=duration,
            target=target,
            operation=operation,
        )
        await _emit_live_read(
            audit,
            application_id=app_id,
            operation_id=op_id,
            environment=env,
            status=0,
            outcome="unavailable",
            duration_ms=duration,
            url_path_template=path,
        )
        return await _finish(result)

    req_headers = _strip_client_auth(headers)
    token_value: str | None = None
    if credentials is not None and target is not None:
        audience = target.audience
        try:
            access = await credentials.get_token(app_id, audience, principal=principal)
            token_value = access.token.get_secret_value()
        except CredentialNotConfigured:
            duration = (time.perf_counter() - started) * 1000
            result = _result(
                ok=False,
                status=0,
                status_text="no_access",
                url=url,
                outcome="no_access",
                error_message=_msg_no_access_missing(label, app_id, env),
                duration_ms=duration,
                target=target,
                operation=operation,
            )
            await _emit_live_read(
                audit,
                application_id=app_id,
                operation_id=op_id,
                environment=env,
                status=0,
                outcome="no_access",
                duration_ms=duration,
                url_path_template=path,
            )
            return await _finish(result)
        except CredentialDenied:
            duration = (time.perf_counter() - started) * 1000
            result = _result(
                ok=False,
                status=0,
                status_text="no_access",
                url=url,
                outcome="no_access",
                error_message=_msg_no_access_refused(label, app_id, env),
                duration_ms=duration,
                target=target,
                operation=operation,
            )
            await _emit_live_read(
                audit,
                application_id=app_id,
                operation_id=op_id,
                environment=env,
                status=0,
                outcome="no_access",
                duration_ms=duration,
                url_path_template=path,
            )
            return await _finish(result)
        except CredentialUnavailable:
            duration = (time.perf_counter() - started) * 1000
            result = _result(
                ok=False,
                status=0,
                status_text="error",
                url=url,
                outcome="error",
                error_message=_msg_cred_error(label),
                duration_ms=duration,
                target=target,
                operation=operation,
            )
            await _emit_live_read(
                audit,
                application_id=app_id,
                operation_id=op_id,
                environment=env,
                status=0,
                outcome="error",
                duration_ms=duration,
                url_path_template=path,
            )
            return await _finish(result)
    elif service.bearer_token:
        # Legacy swagger_links / fixture: deprecated shared bearer path.
        token_value = service.bearer_token

    if token_value:
        req_headers["Authorization"] = f"Bearer {token_value}"

    async def _do_request(hdrs: dict[str, str]) -> httpx.Response:
        async with httpx.AsyncClient(
            timeout=_INVOKE_TIMEOUT,
            follow_redirects=False,
            transport=transport,
        ) as client:
            return await client.request(method_u, url, headers=hdrs)

    try:
        resp = await _do_request(req_headers)
        if (
            resp.status_code == 401
            and credentials is not None
            and target is not None
            and token_value is not None
        ):
            await credentials.invalidate(app_id, target.audience)
            try:
                access2 = await credentials.get_token(
                    app_id, target.audience, principal=principal
                )
                new_token = access2.token.get_secret_value()
            except CredentialError:
                new_token = token_value
            if new_token != token_value:
                req_headers["Authorization"] = f"Bearer {new_token}"
                resp = await _do_request(req_headers)
    except httpx.TimeoutException:
        duration = (time.perf_counter() - started) * 1000
        if breaker is not None:
            breaker.record_failure(app_id)
        result = _result(
            ok=False,
            status=0,
            status_text="unavailable",
            url=url,
            outcome="unavailable",
            error_message=_msg_unavailable(label, app_id),
            duration_ms=duration,
            target=target,
            operation=operation,
        )
        await _emit_live_read(
            audit,
            application_id=app_id,
            operation_id=op_id,
            environment=env,
            status=0,
            outcome="unavailable",
            duration_ms=duration,
            url_path_template=path,
        )
        return await _finish(result)
    except httpx.HTTPError:
        duration = (time.perf_counter() - started) * 1000
        if breaker is not None:
            breaker.record_failure(app_id)
        result = _result(
            ok=False,
            status=0,
            status_text="unavailable",
            url=url,
            outcome="unavailable",
            error_message=_msg_unavailable(label, app_id),
            duration_ms=duration,
            target=target,
            operation=operation,
        )
        await _emit_live_read(
            audit,
            application_id=app_id,
            operation_id=op_id,
            environment=env,
            status=0,
            outcome="unavailable",
            duration_ms=duration,
            url_path_template=path,
        )
        return await _finish(result)

    duration = (time.perf_counter() - started) * 1000
    try:
        data: Any = resp.json()
    except Exception:  # noqa: BLE001
        data = resp.text

    status = resp.status_code
    if status == 401 or status == 403:
        outcome: InvokeOutcome = "no_access"
        msg = (
            _msg_no_access_refused(label, app_id, env)
            if status == 401
            else _msg_no_access_perm(label, app_id)
        )
        result = _result(
            ok=False,
            status=status,
            status_text=resp.reason_phrase or "no_access",
            url=url,
            outcome=outcome,
            error_message=msg,
            data=data,
            duration_ms=duration,
            target=target,
            operation=operation,
        )
    elif status == 404:
        result = _result(
            ok=False,
            status=status,
            status_text=resp.reason_phrase or "not_found",
            url=url,
            outcome="not_found",
            error_message=f"{label} ({app_id}) returned not found for this operation.",
            data=data,
            duration_ms=duration,
            target=target,
            operation=operation,
        )
    elif status >= 500:
        if breaker is not None:
            breaker.record_failure(app_id)
        result = _result(
            ok=False,
            status=status,
            status_text=resp.reason_phrase or "unavailable",
            url=url,
            outcome="unavailable",
            error_message=_msg_unavailable(label, app_id),
            data=data,
            duration_ms=duration,
            target=target,
            operation=operation,
        )
    elif resp.is_success:
        if breaker is not None:
            breaker.record_success(app_id)
        result = _result(
            ok=True,
            status=status,
            status_text=resp.reason_phrase or "ok",
            url=url,
            outcome="ok",
            data=data,
            duration_ms=duration,
            target=target,
            operation=operation,
        )
        if cache is not None and method_u == "GET":
            await cache.set(cache_key, result.model_dump(), ttl=cache_ttl)
    else:
        result = _result(
            ok=False,
            status=status,
            status_text=resp.reason_phrase or "error",
            url=url,
            outcome="error",
            error_message=str(data)[:500] if data is not None else "request failed",
            data=data,
            duration_ms=duration,
            target=target,
            operation=operation,
        )

    await _emit_live_read(
        audit,
        application_id=app_id,
        operation_id=op_id,
        environment=env,
        status=status,
        outcome=result.outcome,
        duration_ms=duration,
        url_path_template=path,
    )
    return await _finish(result)
