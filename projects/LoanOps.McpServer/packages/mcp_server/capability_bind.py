"""Capability-bound call_sse_api args: resolve capability_id → public_id."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from packages.capability_kg.catalog import CapabilityCatalog, CapabilityRecord
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


def catalog_from_settings(settings: Settings) -> CapabilityCatalog | None:
    """Load CapabilityCatalog from EAKG shards. None if KG disabled or shards missing."""
    if not settings.capability_kg.enabled:
        return None
    shard_dir = Path(settings.eakg.shard_dir)
    if not shard_dir.is_dir():
        return None
    from packages.eakg.merge import catalog_from_shards

    return catalog_from_shards(
        shard_dir,
        namespace=settings.capability_kg.namespace,
        approved_only=settings.capability_kg.approved_only,
        semantic=settings.capability_kg.semantic,
    )
