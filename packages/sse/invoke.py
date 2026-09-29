"""Invoke SSE REST APIs with host allow-list."""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import quote, urlencode, urljoin

import httpx
from pydantic import BaseModel

from packages.sse.loader import OpenApiCatalogService, assert_allowed_url
from packages.sse.types import ApiOperation


class InvokeResult(BaseModel):
    ok: bool
    status: int
    status_text: str
    url: str
    data: Any = None
    error_message: str | None = None
    duration_ms: float | None = None
    cache_hit: bool = False


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
) -> InvokeResult:
    base = resolve_base_url(service, operation)
    resolved = substitute_path(path, path_params)
    url = urljoin(base + "/", resolved.lstrip("/"))
    if query:
        url = f"{url}?{urlencode({k: str(v) for k, v in query.items()})}"

    assert_allowed_url(url, service.allowed_origins())

    method_u = method.upper()
    cache_key = f"sse:api:{method_u}:{url}"
    if cache is not None and method_u == "GET":
        hit = await cache.get(cache_key)
        if hit is not None:
            return InvokeResult.model_validate({**hit, "cache_hit": True})

    req_headers = dict(headers or {})
    if service.bearer_token and "Authorization" not in req_headers:
        req_headers["Authorization"] = f"Bearer {service.bearer_token}"

    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(
            method_u,
            url,
            headers=req_headers,
            json=body if body is not None and method_u not in ("GET", "HEAD") else None,
        )
    duration = (time.perf_counter() - started) * 1000
    try:
        data: Any = resp.json()
    except Exception:  # noqa: BLE001
        data = resp.text

    result = InvokeResult(
        ok=resp.is_success,
        status=resp.status_code,
        status_text=resp.reason_phrase,
        url=url,
        data=data,
        error_message=None if resp.is_success else str(data)[:500],
        duration_ms=duration,
    )
    if cache is not None and method_u == "GET" and resp.is_success:
        await cache.set(cache_key, result.model_dump(), ttl=cache_ttl)
    return result
