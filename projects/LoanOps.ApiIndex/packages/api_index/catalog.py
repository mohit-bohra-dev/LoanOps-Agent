"""Runtime operation catalog: load/build operations.json + resolver."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from packages.api_index.keyword_index import KeywordIndex
from packages.api_index.paths import operations_path
from packages.api_index.records import (
    AppInputs,
    CapabilityLookupAll,
    Environment,
    OperationSet,
    UnifiedOperation,
    alias_key,
    build_operations_from_openapi,
    empty_operation_set,
)
from packages.api_index.resolver import OperationResolver
from packages.eakg.registry import RepositoryRegistry
from packages.eakg.spec_cache import read_current_spec
from packages.eakg.store import ShardStore


def _facts_from_interface(ops: list[dict[str, Any]]) -> list[SimpleNamespace]:
    facts: list[SimpleNamespace] = []
    for raw in ops:
        facts.append(
            SimpleNamespace(
                http_method=str(raw.get("method") or ""),
                http_path=str(raw.get("path") or ""),
                controller=str(raw.get("controller") or ""),
                action=raw.get("action"),
                operation_key=str(raw.get("key") or ""),
                authz_policy=raw.get("authz_policy"),
                authz_source=raw.get("authz_source"),
                read_only=raw.get("read_only"),
            )
        )
    return facts


def _attach_capabilities(
    ops: list[UnifiedOperation],
    application_id: str,
    capabilities: CapabilityLookupAll | None,
) -> None:
    if capabilities is None:
        return
    caps = [
        c
        for c in capabilities.list_capabilities(limit=100_000)
        if getattr(c, "application_id", None) in (None, application_id)
        and getattr(c, "operation_id", None)
    ]
    for rec in ops:
        if rec.application_id != application_id:
            continue
        keys = {alias_key(rec.eakg_operation_key or "")}
        if ":" in rec.public_id:
            keys.add(alias_key(rec.public_id.split(":", 1)[-1]))
        keys.discard("")
        for cap in caps:
            app = getattr(cap, "application_id", None)
            if app is not None and app != application_id:
                continue
            op_id = str(getattr(cap, "operation_id", "") or "")
            if alias_key(op_id) in keys:
                cid = str(getattr(cap, "id", "") or "")
                if cid and cid not in rec.capability_ids:
                    rec.capability_ids.append(cid)


def build_operations(
    registry: RepositoryRegistry,
    store: ShardStore,
    environment: Environment,
    *,
    capabilities: CapabilityLookupAll | None = None,
) -> OperationSet:
    """Join cached OpenAPI + EAKG interfaces for every active app."""
    result = empty_operation_set(environment)
    result.built_at = datetime.now(UTC)
    for record in registry.list_active(environment):
        app_id = record.application_id
        target = record.environments[environment]
        doc, pointer = read_current_spec(store, record.repository_id, environment)
        if doc is None and target.spec_fixture:
            from packages.eakg.openapi_enrich import load_fixture_spec

            doc = load_fixture_spec(target.spec_fixture)
        spec_hash = str((pointer or {}).get("spec_hash") or "") or None
        iface = store.read_interface(record.repository_id)
        iface_hash = store.interface_hash(record.repository_id)
        result.inputs[app_id] = AppInputs(spec_hash=spec_hash, interface_hash=iface_hash)
        if doc is None:
            result.issues.setdefault(app_id, []).append("spec_missing")
            continue
        eakg_ops = _facts_from_interface(iface.operations) if iface is not None else []
        ops = build_operations_from_openapi(
            application_id=app_id,
            application_label=record.application,
            environment=environment,
            document=doc,
            base_url=target.base_url,
            spec_hash=spec_hash,
            eakg_ops=eakg_ops,
        )
        _attach_capabilities(ops, app_id, capabilities)
        result.operations.extend(ops)
    result.operations.sort(key=lambda r: (r.application_id, r.path, r.method))
    return result


def write_operations(shard_dir: str | Path, op_set: OperationSet) -> Path:
    payload = op_set.model_dump(mode="json")
    from packages.eakg.artifact_store import FileEakgArtifactStore, get_eakg_artifact_store

    arts = get_eakg_artifact_store()
    if arts.backend == "postgres":
        arts.put_operations(op_set.environment, payload)
    else:
        # Honor caller's shard_dir (tmp_path in tests; pipeline_store in ops).
        FileEakgArtifactStore(
            shard_dir, registry_path=Path(shard_dir) / "_registry.yaml"
        ).put_operations(op_set.environment, payload)
    return operations_path(shard_dir, op_set.environment)


def load_operations(shard_dir: str | Path, environment: str) -> OperationSet | None:
    from packages.eakg.artifact_store import FileEakgArtifactStore, get_eakg_artifact_store

    arts = get_eakg_artifact_store()
    if arts.backend == "postgres":
        raw_db = arts.get_operations(environment)
        if isinstance(raw_db, dict):
            return OperationSet.model_validate(raw_db)
    else:
        raw_file = FileEakgArtifactStore(
            shard_dir, registry_path=Path(shard_dir) / "_registry.yaml"
        ).get_operations(environment)
        if isinstance(raw_file, dict):
            return OperationSet.model_validate(raw_file)
    path = operations_path(shard_dir, environment)
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    return OperationSet.model_validate(raw)


def mismatch_report(op_set: OperationSet, capabilities: CapabilityLookupAll | None = None) -> dict[str, Any]:
    openapi_only = [op.public_id for op in op_set.operations if op.join == "openapi_only"]
    eakg_only = [
        {
            "app": op.application_id,
            "eakg_key": op.eakg_operation_key,
            "path": op.path,
        }
        for op in op_set.operations
        if op.join == "eakg_only"
    ]
    ambiguous = [
        {
            "app": op.application_id,
            "eakg_key": op.eakg_operation_key,
            "path": op.path,
            "public_id": op.public_id,
        }
        for op in op_set.operations
        if op.join == "ambiguous"
    ]
    unbound: list[str] = []
    if capabilities is not None:
        bound = {cid for op in op_set.operations for cid in op.capability_ids}
        for cap in capabilities.list_capabilities(limit=100_000):
            cid = str(getattr(cap, "id", "") or "")
            if cid and cid not in bound and getattr(cap, "operation_id", None):
                unbound.append(cid)
    return {
        "environment": op_set.environment,
        "openapi_only": openapi_only,
        "eakg_only": eakg_only,
        "ambiguous": ambiguous,
        "capabilities_unbound": sorted(unbound),
    }


class OperationCatalog:
    """In-memory catalog backed by operations.json (or an in-process build)."""

    def __init__(self, op_set: OperationSet) -> None:
        self.op_set = op_set
        self.ops = list(op_set.operations)
        self.by_public_id = {op.public_id: op for op in self.ops}
        self.keyword_index = KeywordIndex(self.ops)
        self.resolver = OperationResolver(self.ops, keyword_index=self.keyword_index)

    @classmethod
    def load_or_build(
        cls,
        registry: RepositoryRegistry,
        store: ShardStore,
        environment: Environment,
        *,
        capabilities: CapabilityLookupAll | None = None,
        force_build: bool = False,
    ) -> OperationCatalog:
        if not force_build:
            existing = load_operations(store.root, environment)
            if existing is not None:
                return cls(existing)
        built = build_operations(registry, store, environment, capabilities=capabilities)
        write_operations(store.root, built)
        return cls(built)
