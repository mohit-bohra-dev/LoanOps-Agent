"""Parse OpenAPI/Swagger docs into ApiOperation list."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from packages.sse.types import ApiOperation, ApiParameter

_ALLOWED: set[str] = {"get", "post", "put", "patch", "delete", "head", "options"}


def _slugify(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return s[:80]


def _parse_parameters(raw: list[Any]) -> list[ApiParameter]:
    params: list[ApiParameter] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        location = item.get("in")
        if not isinstance(name, str) or location not in ("path", "query", "header", "cookie"):
            continue
        schema = item.get("schema") if isinstance(item.get("schema"), dict) else {}
        params.append(
            ApiParameter(
                name=name,
                **{"in": location},
                required=bool(item.get("required")) or location == "path",
                description=item.get("description")
                if isinstance(item.get("description"), str)
                else None,
                schema_type=schema.get("type") if isinstance(schema.get("type"), str) else None,
            )
        )
    return params


def _extract_server_url(doc: dict[str, Any], fallback_base: str) -> str | None:
    servers = doc.get("servers")
    if isinstance(servers, list) and servers:
        first = servers[0]
        if isinstance(first, dict) and isinstance(first.get("url"), str) and first["url"].strip():
            return urljoin(fallback_base + "/", first["url"]).rstrip("/")
    host = doc.get("host")
    if isinstance(host, str):
        schemes = doc.get("schemes")
        scheme = schemes[0] if isinstance(schemes, list) and schemes else "https"
        base_path = doc.get("basePath") if isinstance(doc.get("basePath"), str) else ""
        return f"{scheme}://{host}{base_path}".rstrip("/")
    return None


def parse_openapi_document(
    doc: dict[str, Any],
    source_id: str,
    source_label: str,
    fallback_base: str,
) -> list[ApiOperation]:
    paths = doc.get("paths")
    if not isinstance(paths, dict):
        return []
    server_url = _extract_server_url(doc, fallback_base)
    operations: list[ApiOperation] = []
    for path_key, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        shared = (
            _parse_parameters(path_item["parameters"])
            if isinstance(path_item.get("parameters"), list)
            else []
        )
        for method, op_raw in path_item.items():
            if method not in _ALLOWED or not isinstance(op_raw, dict):
                continue
            op_id_raw = op_raw.get("operationId")
            op_id = op_id_raw if isinstance(op_id_raw, str) else None
            stable = op_id or f"{method.upper()}_{_slugify(path_key)}"
            params = list(shared)
            if isinstance(op_raw.get("parameters"), list):
                params.extend(_parse_parameters(op_raw["parameters"]))
            tags = [t for t in op_raw.get("tags", []) if isinstance(t, str)]
            operations.append(
                ApiOperation(
                    id=f"{source_id}:{stable}",
                    source_id=source_id,
                    source_label=source_label,
                    method=method,  # type: ignore[arg-type]
                    path=path_key,
                    operation_id=op_id,
                    summary=op_raw.get("summary")
                    if isinstance(op_raw.get("summary"), str)
                    else None,
                    description=op_raw.get("description")
                    if isinstance(op_raw.get("description"), str)
                    else None,
                    tags=tags,
                    parameters=params,
                    has_request_body=op_raw.get("requestBody") is not None
                    or "consumes" in op_raw,
                    server_url=server_url,
                    source_base_url=fallback_base.rstrip("/"),
                )
            )
    return operations


def find_operation(
    catalog_ops: list[ApiOperation],
    *,
    operation_id: str | None = None,
    method: str | None = None,
    path: str | None = None,
) -> ApiOperation | None:
    by_id = (operation_id or "").strip()
    if by_id:
        for op in catalog_ops:
            if (
                op.id == by_id
                or op.operation_id == by_id
                or op.id.endswith(f":{by_id}")
                or op.id.lower() == by_id.lower()
            ):
                return op
    m = (method or "").strip().lower()
    p = (path or "").strip()
    if m and p:
        for op in catalog_ops:
            if op.method == m and op.path == p:
                return op
    return None


def search_operations(
    catalog_ops: list[ApiOperation],
    query: str,
    limit: int = 20,
) -> list[ApiOperation]:
    tokens = [t for t in re.split(r"[\s,/|]+", query.lower()) if t]
    if not tokens:
        return catalog_ops[:limit]
    scored: list[tuple[ApiOperation, int]] = []
    for op in catalog_ops:
        hay = " ".join(
            [
                op.id,
                op.operation_id or "",
                op.summary or "",
                op.description or "",
                op.path,
                op.method,
                op.source_label,
                *op.tags,
                *[p.name for p in op.parameters],
            ]
        ).lower()
        score = 0
        for token in tokens:
            if token in hay:
                score += 2
            if token in op.path.lower():
                score += 3
            if op.operation_id and token in op.operation_id.lower():
                score += 4
            if op.summary and token in op.summary.lower():
                score += 3
        if score > 0:
            scored.append((op, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [op for op, _ in scored[:limit]]


def summarize_operation(op: ApiOperation) -> str:
    params = ", ".join(
        f"{p.name} ({p.in_}{', required' if p.required else ''}"
        f"{f', {p.schema_type}' if p.schema_type else ''})"
        for p in op.parameters
    )
    lines = [
        f"- id: {op.id}",
        f"  {op.method.upper()} {op.path}",
        f"  summary: {op.summary}" if op.summary else None,
        f"  tags: {', '.join(op.tags)}" if op.tags else None,
        f"  params: {params}" if params else None,
        f"  source: {op.source_label}",
    ]
    return "\n".join(line for line in lines if line)


def origin_of(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"
