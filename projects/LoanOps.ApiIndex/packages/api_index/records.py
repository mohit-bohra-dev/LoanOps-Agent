"""Unified operation records, path normalize, and join."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from packages.sse.catalog import _slugify, normalize_path, parse_openapi_document
from packages.sse.types import ApiParameter, HttpMethod

Environment = Literal["local", "dev", "stage", "prod"]
JoinKind = Literal["exact", "suffix", "openapi_only", "eakg_only", "ambiguous"]

_ALIAS_KEY = re.compile(r"[^a-z0-9]")


def uid(application_id: str, method: str, normalized: str) -> str:
    return f"{application_id}|{method.upper()}|{normalized}"


def alias_key(value: str) -> str:
    return _ALIAS_KEY.sub("", value.lower())


def _segs(normalized: str) -> list[str]:
    return [s for s in normalized.split("/") if s]


def _last_literal(normalized: str) -> str:
    segs = _segs(normalized)
    for seg in reversed(segs):
        if seg != "{}":
            return seg
    return ""


class UnifiedOperation(BaseModel):
    uid: str
    public_id: str
    application_id: str
    application_label: str
    environment: Environment
    method: HttpMethod
    path: str
    normalized_path: str
    summary: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    parameters: list[ApiParameter] = Field(default_factory=list)
    has_request_body: bool = False
    read_only: bool
    callable: bool
    permission: str | None = None
    authz_source: str | None = None
    code_unit: str | None = None
    evidence: list[dict[str, str | int]] = Field(default_factory=list)
    eakg_operation_key: str | None = None
    capability_ids: list[str] = Field(default_factory=list)
    join: JoinKind
    spec_hash: str | None = None
    server_url: str | None = None
    source_base_url: str = ""


class AppInputs(BaseModel):
    spec_hash: str | None = None
    interface_hash: str | None = None


class OperationSet(BaseModel):
    environment: str
    built_at: datetime
    inputs: dict[str, AppInputs] = Field(default_factory=dict)
    operations: list[UnifiedOperation] = Field(default_factory=list)
    issues: dict[str, list[str]] = Field(default_factory=dict)


@dataclass(frozen=True)
class Resolved:
    record: UnifiedOperation
    matched_alias: str

    @property
    def public_id(self) -> str:
        return self.record.public_id

    @property
    def read_only(self) -> bool:
        return self.record.read_only


@dataclass(frozen=True)
class Ambiguous:
    ref: str
    candidates: list[tuple[str, str]]


@dataclass(frozen=True)
class NotFound:
    ref: str
    suggestions: list[str]


class CapabilityLookupAll(Protocol):
    def list_capabilities(self, *, limit: int = 100) -> list[Any]: ...


def _public_ids_for_app(
    application_id: str,
    ops: list[Any],
) -> dict[str, str]:
    """Map operation object id → public_id with collision fallbacks."""
    counts: dict[str, int] = {}
    for op in ops:
        key = op.operation_id or f"{op.method.upper()}_{_slugify(op.path)}"
        counts[key] = counts.get(key, 0) + 1
    assigned: dict[str, str] = {}
    used: set[str] = set()
    for op in sorted(ops, key=lambda o: (o.path, o.method, o.id)):
        base = op.operation_id if op.operation_id and counts[op.operation_id] == 1 else (
            f"{op.method.upper()}_{_slugify(op.path)}"
        )
        if op.operation_id and counts.get(op.operation_id, 0) > 1:
            base = f"{op.method.upper()}_{_slugify(op.path)}"
        candidate = f"{application_id}:{base}"
        n = 2
        while candidate in used:
            candidate = f"{application_id}:{base}_{n}"
            n += 1
        used.add(candidate)
        assigned[op.id] = candidate
    return assigned


def build_operations_from_openapi(
    *,
    application_id: str,
    application_label: str,
    environment: Environment,
    document: dict[str, Any],
    base_url: str,
    spec_hash: str | None,
    eakg_ops: list[Any] | None = None,
) -> list[UnifiedOperation]:
    """Join OpenAPI ops with optional EAKG facts for one app."""
    oa_ops = parse_openapi_document(document, application_id, application_label, base_url)
    public_ids = _public_ids_for_app(application_id, oa_ops)
    records: dict[str, UnifiedOperation] = {}
    buckets: dict[tuple[str, str], list[UnifiedOperation]] = {}

    for op in oa_ops:
        np = normalize_path(op.path)
        key = uid(application_id, op.method, np)
        read_only = op.method in {"get", "head"} and not op.has_request_body
        rec = UnifiedOperation(
            uid=key,
            public_id=public_ids[op.id],
            application_id=application_id,
            application_label=application_label,
            environment=environment,
            method=op.method,
            path=op.path,
            normalized_path=np,
            summary=op.summary,
            description=op.description,
            tags=list(op.tags),
            parameters=list(op.parameters),
            has_request_body=op.has_request_body,
            read_only=read_only,
            callable=read_only,
            join="openapi_only",
            spec_hash=spec_hash,
            server_url=op.server_url,
            source_base_url=op.source_base_url,
        )
        records[key] = rec
        buckets.setdefault((op.method.lower(), _last_literal(np)), []).append(rec)

    for fact in eakg_ops or []:
        method = str(getattr(fact, "http_method", getattr(fact, "method", ""))).lower()
        path = str(getattr(fact, "http_path", ""))
        controller = str(getattr(fact, "controller", "") or "")
        if not method or not path:
            continue
        np_e = normalize_path(path, controller=controller or None)
        exact = uid(application_id, method, np_e)
        join: JoinKind
        target: UnifiedOperation | None = None
        if exact in records:
            target = records[exact]
            join = "exact"
        else:
            eakg_segs = _segs(np_e)
            cands = [
                o
                for o in buckets.get((method, _last_literal(np_e)), [])
                if (oa := _segs(o.normalized_path))[-len(eakg_segs) :] == eakg_segs
                and len(oa) > len(eakg_segs)
            ]
            if len(cands) > 1 and controller:
                stem = controller.removesuffix("Controller").lower()
                eakg_len = len(_segs(np_e))
                cands = [
                    o
                    for o in cands
                    if stem in _segs(o.normalized_path)[:-eakg_len]
                ]
            if len(cands) == 1:
                target = cands[0]
                join = "suffix"
            elif cands:
                join = "ambiguous"
                target = None
            else:
                join = "eakg_only"
                target = None

        eakg_key = str(getattr(fact, "operation_key", getattr(fact, "name", "")) or "") or None
        code_unit = None
        action = getattr(fact, "action", None)
        if controller and action:
            code_unit = f"{controller}.{action}"
        permission = getattr(fact, "authz_policy", None)
        authz_source = getattr(fact, "authz_source", None)
        eakg_ro = getattr(fact, "read_only", None)

        if target is None:
            if join in {"eakg_only", "ambiguous"}:
                records[exact] = UnifiedOperation(
                    uid=exact,
                    public_id=f"{application_id}:{eakg_key or _slugify(path)}",
                    application_id=application_id,
                    application_label=application_label,
                    environment=environment,
                    method=method,  # type: ignore[arg-type]
                    path=path,
                    normalized_path=np_e,
                    read_only=False,
                    callable=False,
                    permission=str(permission) if permission else None,
                    authz_source=str(authz_source) if authz_source else None,
                    code_unit=code_unit,
                    eakg_operation_key=eakg_key,
                    join=join,
                    spec_hash=spec_hash,
                )
            continue

        target.join = join
        target.eakg_operation_key = eakg_key
        target.code_unit = code_unit
        if permission:
            target.permission = str(permission)
        if authz_source:
            target.authz_source = str(authz_source)
        if eakg_ro is False:
            target.read_only = False
            target.callable = False
        else:
            target.read_only = target.method in {"get", "head"} and not target.has_request_body
            target.callable = target.read_only and target.join not in {"eakg_only", "ambiguous"}

    for rec in records.values():
        if rec.join == "openapi_only":
            rec.callable = rec.read_only
        elif rec.join in {"exact", "suffix"}:
            rec.callable = rec.read_only
        else:
            rec.callable = False

    return sorted(records.values(), key=lambda r: (r.application_id, r.path, r.method))


def empty_operation_set(environment: Environment) -> OperationSet:
    return OperationSet(environment=environment, built_at=datetime.now(UTC))
