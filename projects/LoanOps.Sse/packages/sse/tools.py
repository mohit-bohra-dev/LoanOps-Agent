"""SSE MCP tool handlers (search / list / call)."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from packages.common.providers.audit_sink import AuditEvent
from packages.common.providers.credential_broker import AbstractCredentialBroker, Principal
from packages.sse.invoke_outcomes import LastInvokeRing
from packages.sse.catalog import find_operation, normalize_path, summarize_operation
from packages.sse.invoke import invoke_sse_api
from packages.sse.loader import OpenApiCatalogService
from packages.sse.semantic import EmbedFn, search_operations_with_embeddings
from packages.sse.types import (
    ApiOperation,
    AppTarget,
    BreakerRegistry,
    InvokeTarget,
    OperationRefResolver,
    Rejection,
)
from packages.common.providers.audit_sink import AuditSinkProvider

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


def _application_ids(args: dict[str, Any]) -> list[str] | None:
    raw = args.get("application") or args.get("application_ids")
    if raw is None:
        return None
    if isinstance(raw, str):
        value = raw.strip()
        return [value] if value else None
    if isinstance(raw, list):
        out = [str(x).strip() for x in raw if str(x).strip()]
        return out or None
    return None


def _unified_to_api_op(rec: Any) -> ApiOperation:
    public_id = str(getattr(rec, "public_id", "") or "")
    return ApiOperation(
        id=public_id,
        source_id=str(getattr(rec, "application_id", "") or ""),
        source_label=str(getattr(rec, "application_label", "") or ""),
        method=getattr(rec, "method"),
        path=str(getattr(rec, "path", "") or ""),
        operation_id=public_id.split(":", 1)[-1] if public_id else None,
        summary=getattr(rec, "summary", None),
        description=getattr(rec, "description", None),
        tags=list(getattr(rec, "tags", None) or []),
        parameters=list(getattr(rec, "parameters", None) or []),
        has_request_body=bool(getattr(rec, "has_request_body", False)),
        server_url=getattr(rec, "server_url", None),
        source_base_url=str(getattr(rec, "source_base_url", "") or ""),
    )


def resolve_invoke_target(
    service: OpenApiCatalogService,
    *,
    operation_ref: str | None,
    method: str | None,
    path: str | None,
    application: str | None,
    resolver: OperationRefResolver | None,
    registry_mode: bool,
    catalog_ops: list[ApiOperation] | None = None,
) -> InvokeTarget | Rejection:
    """Step 0 of §6.4 — resolve operation + AppTarget before invoke."""
    app_arg = application.strip() if isinstance(application, str) and application.strip() else None
    op_ref = operation_ref.strip() if isinstance(operation_ref, str) and operation_ref.strip() else None
    method_s = method.strip().upper() if isinstance(method, str) and method.strip() else None
    path_s = path.strip() if isinstance(path, str) and path.strip() else None

    if not registry_mode:
        ops = catalog_ops or []
        op: ApiOperation | None = None
        if op_ref or (method_s and path_s):
            op = find_operation(
                ops,
                operation_id=op_ref,
                method=method_s,
                path=path_s,
                resolver=resolver,
            )
        return InvokeTarget(operation=op, target=None)

    # Registry mode
    if op_ref and resolver is not None:
        result = resolver.resolve(op_ref, application_id=app_arg)
        kind = type(result).__name__
        if kind == "Ambiguous":
            candidates = getattr(result, "candidates", [])
            detail = ", ".join(f"{pid} ({label})" for pid, label in candidates)
            return Rejection(
                reason="ambiguous",
                message=(
                    f"ambiguous operation '{op_ref}': {detail} — "
                    "pass the application-qualified id"
                ),
            )
        if kind == "NotFound":
            suggestions_list = getattr(result, "suggestions", []) or []
            suggestions = ", ".join(suggestions_list) if suggestions_list else "none"
            return Rejection(
                reason="not_found",
                message=f"operation '{op_ref}' not found; suggestions: {suggestions}",
            )
        if kind == "Resolved":
            rec = getattr(result, "record")
            if app_arg and str(rec.application_id) != app_arg and str(rec.application_label) != app_arg:
                target_chk = service.target_for(app_arg)
                if target_chk is None or target_chk.application_id != rec.application_id:
                    return Rejection(
                        reason="operation_not_in_application",
                        message=(
                            f"operation '{op_ref}' belongs to {rec.application_label} "
                            f"({rec.application_id}), not '{app_arg}'"
                        ),
                        application_id=str(rec.application_id),
                    )
            target = service.target_for(str(rec.application_id))
            if target is None:
                return Rejection(
                    reason="unknown_application",
                    message=f"No registry target for application '{rec.application_id}'",
                    application_id=str(rec.application_id),
                )
            return InvokeTarget(operation=_unified_to_api_op(rec), target=target)

    if op_ref and resolver is None:
        ops = catalog_ops or []
        op = find_operation(ops, operation_id=op_ref)
        if op is None:
            return Rejection(reason="not_found", message=f"operation '{op_ref}' not found")
        target = service.target_for(op.source_id)
        if target is None:
            return Rejection(
                reason="unknown_application",
                message=f"No registry target for application '{op.source_id}'",
                application_id=op.source_id,
            )
        if app_arg and target.application_id != app_arg and target.label != app_arg:
            return Rejection(
                reason="operation_not_in_application",
                message=f"operation '{op_ref}' is not in application '{app_arg}'",
                application_id=target.application_id,
            )
        return InvokeTarget(operation=op, target=target)

    if method_s and path_s:
        if not app_arg:
            return Rejection(
                reason="application_required",
                message=(
                    "In registry mode, a raw method and path need `application`. "
                    "Prefer `operation_id` from `search_sse_apis`."
                ),
            )
        target = service.target_for(app_arg)
        if target is None:
            return Rejection(
                reason="unknown_application",
                message=f"Unknown application '{app_arg}'",
                application_id=app_arg,
            )
        ops = catalog_ops or []
        want = normalize_path(path_s)
        matches = [
            o
            for o in ops
            if o.source_id == target.application_id
            and o.method.upper() == method_s
            and normalize_path(o.path) == want
        ]
        if len(matches) == 1:
            return InvokeTarget(operation=matches[0], target=target)
        return Rejection(
            reason="operation_not_in_application",
            message=(
                f"No matching {method_s} {path_s} in {target.label} "
                f"({target.application_id})"
            ),
            application_id=target.application_id,
        )

    return Rejection(
        reason="not_found",
        message="Provide operation_id or method+path.",
    )


_OPENAPI_INVOKE_HINT = (
    "To fetch live data, call call_sse_api with an operation_id and params below:"
)


def _assemble_search_parts(
    *,
    openapi_body: str | None,
    kg_block: str | None,
) -> str:
    """OpenAPI hits first (actionable), EAKG capabilities after (context only)."""
    parts: list[str] = []
    if openapi_body:
        parts.append(f"{_OPENAPI_INVOKE_HINT}\n{openapi_body}")
    if kg_block:
        parts.append(kg_block)
    if not parts:
        return "No matching SSE API operations."
    return "\n\n".join(parts)


async def handle_search_sse_apis(
    service: OpenApiCatalogService,
    args: dict[str, Any],
    *,
    capability_block: CapabilityBlock | None = None,
    embed: EmbedFn | None = None,
    api_search: Any | None = None,
) -> str:
    catalog = await service.load()
    # LAYER2-BP S1: OpenAPI vector search + optional EAKG block
    limit = min(int(args.get("limit") or 15), 50)
    query = str(args.get("query") or "")
    permission = args.get("permission")
    permission_s = str(permission).strip() if isinstance(permission, str) and permission.strip() else None
    application_ids = _application_ids(args)

    # Cap EAKG rows so noisy alphabetical SPARQL hits do not drown OpenAPI ops.
    kg_block: str | None = None
    if capability_block is not None:
        kg_block = await capability_block(query, min(limit, 5))

    if api_search is not None:
        # Duck-typed ApiSearchService — sse must not import api_index (dep direction).
        outcome = await api_search.search(
            query,
            limit=limit,
            application_ids=application_ids,
            permission=permission_s,
        )
        format_fn = getattr(api_search, "format_outcome", None)
        body = (
            format_fn(outcome, query)
            if callable(format_fn)
            else "No matching SSE API operations."
        )
        hits = getattr(outcome, "hits", None) or []
        if not hits and not kg_block:
            return "No matching SSE API operations."
        openapi_body = body if hits else None
        return _assemble_search_parts(openapi_body=openapi_body, kg_block=kg_block)

    embed_fn = embed if embed is not None else _live_embed()
    hits, used_semantic = await search_operations_with_embeddings(
        catalog.operations,
        query,
        cache=service.openapi_embed_cache,
        limit=limit,
        embed=embed_fn,
        hashes=service.openapi_embed_hashes,
    )
    if not hits and not kg_block:
        return "No matching SSE API operations."
    openapi_body: str | None = None
    if hits:
        header = "OpenAPI operations:"
        if not used_semantic:
            header = "(keyword search — embeddings unavailable)\n" + header
        openapi_body = header + "\n" + "\n".join(summarize_operation(op) for op in hits)
    return _assemble_search_parts(openapi_body=openapi_body, kg_block=kg_block)


def _matches_source_filter(op: ApiOperation, needle: str) -> bool:
    """Match source_label arg against application id or label (agents pass either)."""
    n = needle.strip().lower()
    if not n:
        return True
    sid = op.source_id.lower()
    slabel = op.source_label.lower()
    return n == sid or n == slabel or n in sid or n in slabel


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
        ops = [o for o in ops if _matches_source_filter(o, label)]
    ops = ops[:limit]
    source_lines = []
    for src in catalog.sources:
        # Soften per-source fetch failures — other apps may still be healthy.
        # Agents were treating "ERROR=getaddrinfo" as a total catalog failure.
        if src.error:
            note = f" unavailable ({src.error})"
        else:
            note = ""
        source_lines.append(
            f"  - {src.label} ({src.id}): {src.operation_count} ops{note}"
        )
    ok_ops = sum(1 for s in catalog.sources if not s.error)
    header = (
        f"Loaded {len(catalog.operations)} operations from "
        f"{ok_ops}/{len(catalog.sources)} healthy sources at {catalog.loaded_at}\n"
        + "\n".join(source_lines)
        + "\n"
    )
    if not ops:
        return header + "No operations to list."
    return header + "\n".join(summarize_operation(op) for op in ops)


_LOAN_ID_KEYS = frozenset({"loan_id", "loanid", "loannumber", "id"})


def _path_placeholders(path: str) -> set[str]:
    return set(re.findall(r"\{([^}]+)\}", path or ""))


def route_invoke_params(
    use_path: str,
    path_params: dict[str, Any] | None,
    query: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Move non-path keys out of path_params into query; fill lone path placeholder.

    Agents often pass ``path_params: {loanNumber: ...}`` for query-param endpoints
    (e.g. GetEscrowByLoanNumber). Those keys must become query params.
    """
    path_in = dict(path_params) if isinstance(path_params, dict) else {}
    query_out = dict(query) if isinstance(query, dict) else {}
    placeholders = _path_placeholders(use_path)

    path_out: dict[str, Any] = {}
    for key, value in path_in.items():
        if key in placeholders:
            path_out[key] = value
        else:
            # Prefer existing query value if already set
            query_out.setdefault(key, value)

    # Single missing placeholder: map common loan-id aliases case-insensitively
    missing = [p for p in placeholders if p not in path_out or path_out[p] in (None, "")]
    if len(missing) == 1:
        want = missing[0]
        want_l = want.lower()
        candidates: list[tuple[str, Any]] = []
        for src in (path_in, query_out):
            for k, v in src.items():
                if v in (None, ""):
                    continue
                kl = str(k).lower().replace("_", "")
                if (
                    str(k).lower() == want_l
                    or kl == want_l.replace("_", "")
                    or kl in _LOAN_ID_KEYS
                    or str(k).lower() in _LOAN_ID_KEYS
                ):
                    candidates.append((str(k), v))
        if candidates:
            path_out[want] = candidates[0][1]
            # Drop from query if we promoted the same value into the path
            for k, v in list(query_out.items()):
                if v == candidates[0][1] and str(k).lower().replace("_", "") in {
                    want_l.replace("_", ""),
                    "loanid",
                    "loannumber",
                    "id",
                }:
                    # Keep query keys that are intentionally query params on the op;
                    # only remove exact alias duplicates that were solely for the path.
                    if k not in placeholders and str(k) != want:
                        pass  # leave query alone — loanNumber may be both styles

    return (path_out or None, query_out or None)


async def handle_call_sse_api(
    service: OpenApiCatalogService,
    args: dict[str, Any],
    *,
    cache: Any | None = None,
    credentials: AbstractCredentialBroker | None = None,
    breaker: BreakerRegistry | None = None,
    audit: AuditSinkProvider | None = None,
    resolver: OperationRefResolver | None = None,
    principal: Principal | None = None,
    registry_mode: bool | None = None,
    invoke_ring: LastInvokeRing | None = None,
) -> str:
    catalog = await service.load()
    use_registry = service.registry_mode if registry_mode is None else registry_mode
    application = args.get("application")
    application_s = (
        str(application).strip()
        if isinstance(application, str) and str(application).strip()
        else None
    )
    operation_id = args.get("operation_id")
    method = args.get("method")
    path = args.get("path")

    resolved = resolve_invoke_target(
        service,
        operation_ref=str(operation_id) if operation_id else None,
        method=str(method) if method else None,
        path=str(path) if path else None,
        application=application_s,
        resolver=resolver,
        registry_mode=use_registry,
        catalog_ops=catalog.operations,
    )

    if isinstance(resolved, Rejection):
        if audit is not None:
            try:
                await audit.emit(
                    AuditEvent(
                        event_id=str(uuid.uuid4()),
                        event_type="sse.live_read",
                        payload={
                            "application_id": resolved.application_id,
                            "operation_id": str(operation_id) if operation_id else None,
                            "environment": None,
                            "status": 0,
                            "outcome": "rejected",
                            "duration_ms": 0.0,
                            "url_path_template": str(path) if path else None,
                        },
                    )
                )
            except Exception:  # noqa: BLE001
                pass
        payload = {
            "ok": False,
            "status": 0,
            "url": None,
            "cache_hit": False,
            "duration_ms": 0.0,
            "data": None,
            "error": resolved.message,
            "outcome": "rejected",
            "application_id": resolved.application_id,
            "application": None,
            "operation_id": str(operation_id) if operation_id else None,
            "citation": None,
        }
        return json.dumps(payload, default=str)[:8000]

    op = resolved.operation
    target: AppTarget | None = resolved.target
    if op is None and not (method and path):
        return "Provide operation_id or method+path."
    use_method = op.method if op else str(method)
    use_path = op.path if op else str(path)
    public_id = op.id if op else None
    query_arg = args.get("query")
    if not isinstance(query_arg, dict):
        query_arg = args.get("query_params")
    path_params_arg = (
        args.get("path_params") if isinstance(args.get("path_params"), dict) else None
    )
    routed_path, routed_query = route_invoke_params(
        str(use_path),
        path_params_arg if isinstance(path_params_arg, dict) else None,
        query_arg if isinstance(query_arg, dict) else None,
    )
    result = await invoke_sse_api(
        service,
        method=use_method,
        path=use_path,
        path_params=routed_path,
        query=routed_query,
        headers=args.get("headers") if isinstance(args.get("headers"), dict) else None,
        body=args.get("body"),
        operation=op,
        cache=cache,
        target=target,
        credentials=credentials,
        breaker=breaker,
        audit=audit,
        principal=principal,
        registry_mode=use_registry,
        invoke_ring=invoke_ring,
    )
    citation = f"tool:call_sse_api:{public_id}" if public_id else "tool:call_sse_api"
    payload = {
        "ok": result.ok,
        "status": result.status,
        "url": result.url,
        "cache_hit": result.cache_hit,
        "duration_ms": result.duration_ms,
        "data": result.data,
        "error": result.error_message,
        "outcome": result.outcome,
        "application_id": result.application_id,
        "application": result.application,
        "operation_id": result.operation_id or public_id,
        "citation": citation,
    }
    return json.dumps(payload, default=str)[:8000]


async def dispatch_sse_tool(
    service: OpenApiCatalogService,
    name: str,
    args: dict[str, Any],
    *,
    cache: Any | None = None,
    capability_block: CapabilityBlock | None = None,
    api_search: Any | None = None,
    credentials: AbstractCredentialBroker | None = None,
    breaker: BreakerRegistry | None = None,
    audit: AuditSinkProvider | None = None,
    resolver: OperationRefResolver | None = None,
    principal: Principal | None = None,
    registry_mode: bool | None = None,
    invoke_ring: LastInvokeRing | None = None,
) -> str:
    if name == "search_sse_apis":
        return await handle_search_sse_apis(
            service, args, capability_block=capability_block, api_search=api_search
        )
    if name == "list_sse_apis":
        return await handle_list_sse_apis(service, args)
    if name == "call_sse_api":
        return await handle_call_sse_api(
            service,
            args,
            cache=cache,
            credentials=credentials,
            breaker=breaker,
            audit=audit,
            resolver=resolver,
            principal=principal,
            registry_mode=registry_mode,
            invoke_ring=invoke_ring,
        )
    raise KeyError(f"Unknown SSE tool: {name}")
