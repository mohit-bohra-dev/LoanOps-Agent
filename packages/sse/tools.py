"""SSE MCP tool handlers (search / list / call)."""

from __future__ import annotations

import json
from typing import Any

from packages.sse.catalog import find_operation, search_operations, summarize_operation
from packages.sse.invoke import invoke_sse_api
from packages.sse.loader import OpenApiCatalogService
from packages.sse.types import ApiOperation

SSE_TOOL_NAMES = (
    "search_sse_apis",
    "list_sse_apis",
    "call_sse_api",
)


async def handle_search_sse_apis(
    service: OpenApiCatalogService,
    args: dict[str, Any],
) -> str:
    catalog = await service.load()
    limit = min(int(args.get("limit") or 15), 50)
    query = str(args.get("query") or "")

    kg_block = await _capability_search_block(query, limit=limit)
    hits = search_operations(catalog.operations, query, limit)
    if not hits and not kg_block:
        return "No matching SSE API operations."
    parts: list[str] = []
    if kg_block:
        parts.append(kg_block)
    if hits:
        parts.append("OpenAPI operations:\n" + "\n".join(summarize_operation(op) for op in hits))
    return "\n\n".join(parts)


async def _capability_search_block(query: str, *, limit: int) -> str | None:
    """Optional RDF capability hits. Keyword OpenAPI search remains the fallback."""
    from pathlib import Path

    from packages.common.settings import Settings

    cfg = Settings().capability_kg
    if not cfg.enabled:
        return None
    path = Path(cfg.ttl_path)
    if not path.is_file():
        return None
    from packages.capability_kg.catalog import CapabilityCatalog

    embed_query = None
    if cfg.semantic:

        async def _embed(text: str) -> list[float]:
            from packages.common.providers.factory import get_embedding_provider

            result = await get_embedding_provider().embed(text)
            return list(result.vector)

        embed_query = _embed

    caps = CapabilityCatalog.from_ttl(
        path,
        namespace=cfg.namespace,
        approved_only=cfg.approved_only,
        semantic=cfg.semantic,
        embed_query=embed_query,
    )
    records = await caps.search_capabilities(query, limit=limit)
    if not records:
        records = await caps.find_capabilities_for_intent(query, limit=limit)
    if not records:
        return None
    lines = ["Capabilities (RDF):"]
    lines.extend(r.summary_line() for r in records)
    return "\n".join(lines)


async def handle_list_sse_apis(
    service: OpenApiCatalogService,
    args: dict[str, Any],
) -> str:
    refresh = bool(args.get("refresh"))
    catalog = await service.load(refresh=refresh)
    limit = min(int(args.get("limit") or 50), 200)
    ops = catalog.operations
    label = args.get("source_label")
    if isinstance(label, str) and label.strip():
        ops = [o for o in ops if o.source_label.lower() == label.strip().lower()]
    ops = ops[:limit]
    source_lines = []
    for src in catalog.sources:
        err = f" ERROR={src.error}" if src.error else ""
        source_lines.append(
            f"  - {src.label} ({src.id}): {src.operation_count} ops{err}"
        )
    header = (
        f"Loaded {len(catalog.operations)} operations from "
        f"{len(catalog.sources)} sources at {catalog.loaded_at}\n"
        + "\n".join(source_lines)
        + "\n"
    )
    if not ops:
        return header + "No operations to list."
    return header + "\n".join(summarize_operation(op) for op in ops)


async def handle_call_sse_api(
    service: OpenApiCatalogService,
    args: dict[str, Any],
    *,
    cache: Any | None = None,
) -> str:
    catalog = await service.load()
    op: ApiOperation | None = None
    operation_id = args.get("operation_id")
    method = args.get("method")
    path = args.get("path")
    if operation_id or (method and path):
        op = find_operation(
            catalog.operations,
            operation_id=str(operation_id) if operation_id else None,
            method=str(method) if method else None,
            path=str(path) if path else None,
        )
    if op is None and not (method and path):
        return "Provide operation_id or method+path."
    use_method = op.method if op else str(method)
    use_path = op.path if op else str(path)
    result = await invoke_sse_api(
        service,
        method=use_method,
        path=use_path,
        path_params=args.get("path_params")
        if isinstance(args.get("path_params"), dict)
        else None,
        query=args.get("query") if isinstance(args.get("query"), dict) else None,
        headers=args.get("headers") if isinstance(args.get("headers"), dict) else None,
        body=args.get("body"),
        operation=op,
        cache=cache,
    )
    payload = {
        "ok": result.ok,
        "status": result.status,
        "url": result.url,
        "cache_hit": result.cache_hit,
        "duration_ms": result.duration_ms,
        "data": result.data,
        "error": result.error_message,
    }
    return json.dumps(payload, default=str)[:8000]


async def dispatch_sse_tool(
    service: OpenApiCatalogService,
    name: str,
    args: dict[str, Any],
    *,
    cache: Any | None = None,
) -> str:
    if name == "search_sse_apis":
        return await handle_search_sse_apis(service, args)
    if name == "list_sse_apis":
        return await handle_list_sse_apis(service, args)
    if name == "call_sse_api":
        return await handle_call_sse_api(service, args, cache=cache)
    raise KeyError(f"Unknown SSE tool: {name}")
