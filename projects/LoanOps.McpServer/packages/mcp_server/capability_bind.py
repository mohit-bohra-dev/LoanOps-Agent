"""Capability-bound call_sse_api args: resolve capability_id → public_id."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from packages.capability_kg.catalog import CapabilityRecord
from packages.common.providers.graph_store import AbstractGraphStore
from packages.common.settings import Settings
from packages.mcp_server.policy import PolicyError


class CapabilityLookup(Protocol):
    """Minimal catalog surface used by bind helpers (real catalog or test stub)."""

    def get_capability(self, capability_id: str) -> CapabilityRecord | None: ...


class OperationResolveLookup(Protocol):
    def resolve(
        self,
        ref: str,
        *,
        application_id: str | None = None,
    ) -> Any: ...


@dataclass(frozen=True)
class CapabilityBinding:
    """Resolved capability → SSE operation binding."""

    capability_id: str
    operation_id: str
    read_only: bool | None
    permission: str | None
    application_id: str | None = None


def resolve_binding(
    catalog: CapabilityLookup,
    *,
    capability_id: str,
    resolver: OperationResolveLookup | None = None,
) -> CapabilityBinding | None:
    """Map capability_id → binding. None when missing or no operation_id."""
    cid = capability_id.strip()
    if not cid:
        return None
    record = catalog.get_capability(cid)
    if record is None or not record.operation_id:
        return None

    operation_id = record.operation_id
    read_only = record.read_only
    application_id = record.application_id

    if resolver is not None:
        result = resolver.resolve(record.operation_id, application_id=record.application_id)
        kind = type(result).__name__
        if kind == "Ambiguous":
            detail = ", ".join(f"{pid} ({label})" for pid, label in result.candidates)
            raise PolicyError(
                f"capability '{cid}' is ambiguous across applications: {detail}"
            )
        if kind == "NotFound":
            return None
        if kind == "Resolved":
            operation_id = result.public_id
            read_only = result.read_only
            application_id = result.record.application_id
            if not result.read_only:
                raise PolicyError(
                    f"capability '{cid}' maps to a data-changing operation; "
                    "not callable in this version"
                )

    return CapabilityBinding(
        capability_id=record.id or cid,
        operation_id=operation_id,
        read_only=read_only,
        permission=record.permission,
        application_id=application_id,
    )


def assert_call_matches_binding(
    *,
    binding: CapabilityBinding,
    operation_id: str | None,
    method: str | None,
    path: str | None,
) -> None:
    """Reject client-supplied operation_id/method that disagree with binding.

    CapabilityRecord has no path today — ``path`` is accepted but not enforced.
    """
    _ = path  # no path on CapabilityRecord; ignore client path for bind checks
    if operation_id is not None and str(operation_id).strip():
        client = str(operation_id).strip()
        bound = binding.operation_id
        # Allow legacy short ids when the bound value is application-qualified.
        short = bound.split(":", 1)[-1]
        if client != bound and client != short and client.lower() != bound.lower():
            raise PolicyError(
                f"operation_id '{operation_id}' does not match capability "
                f"'{binding.capability_id}' bound to '{binding.operation_id}'"
            )
    if method is not None and str(method).strip():
        if str(method).strip().upper() != "GET":
            raise PolicyError("call_sse_api method must be GET when capability-bound")


def apply_capability_bind(
    call_args: dict[str, Any],
    catalog: CapabilityLookup,
    *,
    require_bind: bool,
    resolver: OperationResolveLookup | None = None,
) -> dict[str, Any]:
    """Rewrite call_sse_api args using capability_id when present.

    - capability_id → resolve, assert client fields, set operation_id from binding
    - require_bind True without capability_id → PolicyError
    - require_bind False + operation_id only → passthrough (legacy)
    """
    raw_cid = call_args.get("capability_id")
    capability_id = str(raw_cid).strip() if raw_cid is not None else ""

    if not capability_id:
        if require_bind:
            raise PolicyError("call_sse_api requires capability_id when capability bind is required")
        return dict(call_args)

    binding = resolve_binding(catalog, capability_id=capability_id, resolver=resolver)
    if binding is None:
        raise PolicyError(f"Unknown or unbound capability_id: {capability_id}")

    client_op = call_args.get("operation_id")
    client_method = call_args.get("method")
    client_path = call_args.get("path")
    assert_call_matches_binding(
        binding=binding,
        operation_id=str(client_op) if client_op is not None else None,
        method=str(client_method) if client_method is not None else None,
        path=str(client_path) if client_path is not None else None,
    )

    out = dict(call_args)
    out["capability_id"] = binding.capability_id
    out["operation_id"] = binding.operation_id
    if binding.application_id:
        out["application"] = binding.application_id
    if binding.read_only:
        out["method"] = "GET"
    return out


class GraphStoreCapabilityLookup:
    """CapabilityLookup backed by SPARQL explain (ADR-026). Warm before sync get."""

    def __init__(
        self,
        store: AbstractGraphStore,
        *,
        namespace: str,
    ) -> None:
        self._store = store
        self._namespace = namespace
        self._by_id: dict[str, CapabilityRecord] = {}

    async def warm(self) -> None:
        from packages.eakg.query import list_operation_records

        rows = await list_operation_records(
            self._store, namespace=self._namespace, limit=10_000
        )
        self._by_id = {}
        for row in rows:
            rec = _record_from_explain(row)
            if rec.id:
                self._by_id[rec.id.lower()] = rec
            if rec.operation_id:
                self._by_id[rec.operation_id.lower()] = rec

    async def resolve_one(self, capability_id: str) -> CapabilityRecord | None:
        from packages.eakg.query import explain_capability

        row = await explain_capability(
            self._store, capability_id, namespace=self._namespace
        )
        if row is None:
            return None
        return _record_from_explain(row)

    def get_capability(self, capability_id: str) -> CapabilityRecord | None:
        key = capability_id.strip().lower()
        if key in self._by_id:
            return self._by_id[key]
        return None


def _record_from_explain(row: dict[str, Any]) -> CapabilityRecord:
    method = str(row.get("http_method") or "")
    read_only = method.upper() == "GET" if method else None
    app = row.get("application")
    return CapabilityRecord(
        id=str(row.get("id") or row.get("operation_id") or ""),
        description=None,
        operation_id=str(row["operation_id"]) if row.get("operation_id") else None,
        read_only=read_only,
        review_status=None,
        permission=str(row["permission"]) if row.get("permission") else None,
        uri=str(row["uri"]) if row.get("uri") else None,
        http_path=str(row["http_path"]) if row.get("http_path") else None,
        application_id=str(app) if app else None,
    )


async def apply_capability_bind_async(
    call_args: dict[str, Any],
    store: AbstractGraphStore,
    *,
    require_bind: bool,
    namespace: str,
    resolver: OperationResolveLookup | None = None,
) -> tuple[dict[str, Any], str | None]:
    """Async bind using SPARQL explain (no shard merge).

    Returns ``(rewritten_args, permission)``.
    """
    raw_cid = call_args.get("capability_id")
    capability_id = str(raw_cid).strip() if raw_cid is not None else ""

    if not capability_id:
        if require_bind:
            raise PolicyError("call_sse_api requires capability_id when capability bind is required")
        return dict(call_args), None

    lookup = GraphStoreCapabilityLookup(store, namespace=namespace)
    record = await lookup.resolve_one(capability_id)
    if record is None or not record.operation_id:
        raise PolicyError(f"Unknown or unbound capability_id: {capability_id}")
    bound = record
    op_key = str(bound.operation_id)
    id_key = bound.id.lower()

    class _One:
        def get_capability(self, cid: str) -> CapabilityRecord | None:
            key = cid.strip().lower()
            if key in {id_key, op_key.lower()}:
                return bound
            return None

    out = apply_capability_bind(
        call_args,
        _One(),
        require_bind=require_bind,
        resolver=resolver,
    )
    return out, bound.permission


def catalog_from_settings(settings: Settings) -> GraphStoreCapabilityLookup | None:
    """SPARQL-backed lookup. Caller must ``await lookup.warm()`` for sync get_capability."""
    if not settings.capability_kg.enabled:
        return None
    from packages.common.providers.factory import get_graph_store

    return GraphStoreCapabilityLookup(
        get_graph_store(),
        namespace=settings.capability_kg.namespace,
    )
