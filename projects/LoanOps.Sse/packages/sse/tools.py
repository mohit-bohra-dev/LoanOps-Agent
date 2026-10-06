"""SSE MCP tool handlers (search / list / call)."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from packages.sse.catalog import find_operation, summarize_operation
from packages.sse.invoke import invoke_sse_api
from packages.sse.loader import OpenApiCatalogService
from packages.sse.semantic import EmbedFn, search_operations_with_embeddings
from packages.sse.types import ApiOperation

SSE_TOOL_NAMES = (
    "search_sse_apis",
    "list_sse_apis",
    "call_sse_api",
)

CapabilityBlock = Callable[[str, int], Awaitable[str | None]]


def _live_embed() -> EmbedFn:
    async def _embed(text: str) -> list[float]:
        from packages.common.providers.factory import get_embedding_provider

        result = await get_embedding_provider().embed(text)
        return list(result.vector)

    return _embed


async def handle_search_sse_apis(
    service: OpenApiCatalogService,
    args: dict[str, Any],
    *,
    capability_block: CapabilityBlock | None = None,
    embed: EmbedFn | None = None,
) -> str:
    catalog = await service.load()
    # LAYER2-BP S1: OpenAPI vector search + optional EAKG block
    limit = min(int(args.get("limit") or 15), 50)
    query = str(args.get("query") or "")

    kg_block: str | None = None
    if capability_block is not None:
        kg_block = await capability_block(query, limit)
    embed_fn = embed if embed is not None else _live_embed()
    hits = await search_operations_with_embeddings(
        catalog.operations,
        query,
        cache=service.openapi_embed_cache,
        limit=limit,
        embed=embed_fn,
    )
    if not hits and not kg_block:
        return "No matching SSE API operations."
    parts: list[str] = []
    if kg_block:
        parts.append(kg_block)
    if hits:
        parts.append("OpenAPI operations:\n" + "\n".join(summarize_operation(op) for op in hits))
    return "\n\n".join(parts)


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
    # LAYER2-BP S2: live GET — inspect operation_id / path / path_params
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
    capability_block: CapabilityBlock | None = None,
) -> str:
    if name == "search_sse_apis":
        return await handle_search_sse_apis(
            service, args, capability_block=capability_block
        )
    if name == "list_sse_apis":
        return await handle_list_sse_apis(service, args)
    if name == "call_sse_api":
        return await handle_call_sse_api(service, args, cache=cache)
    raise KeyError(f"Unknown SSE tool: {name}")
