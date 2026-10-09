"""Incremental embed + upsert into the vector store (spec §3.4)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, Field

from packages.api_index.keyword_index import unified_to_api_operation
from packages.api_index.records import OperationSet, UnifiedOperation
from packages.common.providers.embedding import EmbeddingProvider
from packages.common.providers.vector_store import VectorDocument, VectorStoreProvider
from packages.sse.semantic import (
    OpenApiEmbeddingEntry,
    operation_text,
    save_openapi_index,
    text_hash,
)

_BATCH_SIZE = 64
_BATCH_CONCURRENCY = 4


class ManifestEntry(BaseModel):
    text_hash: str
    public_id: str
    application_id: str


class IndexManifest(BaseModel):
    namespace: str = ""
    embed_model_id: str = ""
    entries: dict[str, ManifestEntry] = Field(default_factory=dict)


class IndexReport(BaseModel):
    environment: str
    namespace: str = ""
    embed_model_id: str = ""
    embedded: int = 0
    deleted: int = 0
    unchanged: int = 0
    failed_apps: dict[str, str] = Field(default_factory=dict)
    full_rebuild: bool = False
    duration_ms: float = 0.0


def point_id(environment: str, uid: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"loanops:{environment}:{uid}"))


def model_fingerprint(model_id: str) -> str:
    return hashlib.sha256(model_id.encode("utf-8")).hexdigest()[:8]


def namespace_for(prefix: str, environment: str, model_id: str) -> str:
    return f"{prefix}_{environment}_{model_fingerprint(model_id)}"


def unified_operation_text(op: UnifiedOperation) -> str:
    """operation_text extended with code_unit and capability ids (§3.4)."""
    base = operation_text(unified_to_api_operation(op))
    extras: list[str] = []
    if op.code_unit:
        extras.append(op.code_unit)
    extras.extend(cid for cid in op.capability_ids if cid)
    if not extras:
        return base
    return base.rstrip(".") + ". " + ". ".join(extras) + "."


def _meta(op: UnifiedOperation, *, text_hash_value: str, embed_model_id: str) -> dict[str, Any]:
    return {
        "application_id": op.application_id,
        "application_label": op.application_label,
        "environment": op.environment,
        "method": op.method,
        "path": op.path,
        "normalized_path": op.normalized_path,
        "public_id": op.public_id,
        "uid": op.uid,
        "read_only": op.read_only,
        "permission": op.permission,
        "capability_ids": list(op.capability_ids),
        "text_hash": text_hash_value,
        "embed_model_id": embed_model_id,
        "spec_hash": op.spec_hash,
    }


def load_manifest(path: Path) -> IndexManifest:
    if not path.is_file():
        return IndexManifest()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return IndexManifest()
    return IndexManifest.model_validate(raw)


def write_manifest(path: Path, manifest: IndexManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def _chunks(items: list[UnifiedOperation], size: int) -> list[list[UnifiedOperation]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def reindex(
    environment: str,
    ops: OperationSet,
    *,
    vector_store: VectorStoreProvider | None,
    embedder: EmbeddingProvider,
    manifest_path: Path,
    namespace_prefix: str,
    sidecar_path: Path,
    sidecar_only: bool = False,
) -> IndexReport:
    """Incremental reindex: text_hash diff, batch embed, upsert/delete, sidecar."""
    started = time.perf_counter()
    if sidecar_only:
        vector_store = None
    probe = await embedder.embed("probe")
    model_id = f"{probe.model}:{probe.dimensions}"
    dims = int(probe.dimensions)
    ns = namespace_for(namespace_prefix, environment, model_id)
    manifest = load_manifest(manifest_path)
    callable_ops = [op for op in ops.operations if op.callable]
    by_uid = {op.uid: op for op in callable_ops}
    texts = {op.uid: unified_operation_text(op) for op in callable_ops}
    hashes = {uid: text_hash(text) for uid, text in texts.items()}

    full_rebuild = manifest.namespace != ns or not manifest.namespace
    stale_ns = manifest.namespace if full_rebuild and manifest.namespace and manifest.namespace != ns else ""
    if full_rebuild:
        todo = list(callable_ops)
    else:
        todo = [
            op
            for op in callable_ops
            if manifest.entries.get(op.uid) is None
            or manifest.entries[op.uid].text_hash != hashes[op.uid]
        ]

    embedded = 0
    failed_apps: dict[str, str] = {}
    sidecar_entries: dict[str, OpenApiEmbeddingEntry] = {}

    # Preserve existing sidecar vectors for unchanged ops when present.
    if sidecar_path.is_file():
        from packages.sse.semantic import load_openapi_index

        existing = load_openapi_index(sidecar_path)
        for op in callable_ops:
            if op.uid in {t.uid for t in todo}:
                continue
            entry = existing.get(op.public_id)
            if entry is not None and entry.text_hash == hashes[op.uid]:
                sidecar_entries[op.public_id] = entry

    if vector_store is not None:
        await vector_store.ensure_namespace(ns, vector_size=dims)

    sem = asyncio.Semaphore(_BATCH_CONCURRENCY)

    async def _embed_batch(batch: list[UnifiedOperation]) -> None:
        nonlocal embedded
        batch_texts = [texts[op.uid] for op in batch]
        async with sem:
            try:
                results = await embedder.embed_batch(batch_texts)
            except Exception as exc:  # noqa: BLE001 — isolate per batch / app
                for op in batch:
                    failed_apps.setdefault(op.application_id, str(exc)[:300])
                return
        docs: list[VectorDocument] = []
        for op, result in zip(batch, results, strict=True):
            th = hashes[op.uid]
            vec = list(result.vector)
            sidecar_entries[op.public_id] = OpenApiEmbeddingEntry(
                id=op.public_id,
                text=texts[op.uid],
                text_hash=th,
                vector=vec,
            )
            if vector_store is not None:
                docs.append(
                    VectorDocument(
                        id=point_id(environment, op.uid),
                        embedding=vec,
                        metadata=_meta(op, text_hash_value=th, embed_model_id=model_id),
                        text=texts[op.uid],
                    )
                )
            embedded += 1
        if docs and vector_store is not None:
            try:
                await vector_store.upsert(docs, namespace=ns)
            except Exception as exc:  # noqa: BLE001
                for op in batch:
                    failed_apps.setdefault(op.application_id, str(exc)[:300])

    await asyncio.gather(*(_embed_batch(batch) for batch in _chunks(todo, _BATCH_SIZE)))

    removed_uids = set(manifest.entries) - set(by_uid)
    deleted = 0
    if removed_uids and vector_store is not None:
        try:
            await vector_store.delete(
                [point_id(environment, uid) for uid in removed_uids],
                namespace=ns,
            )
            deleted = len(removed_uids)
        except Exception as exc:  # noqa: BLE001
            failed_apps.setdefault("_delete", str(exc)[:300])

    new_entries: dict[str, ManifestEntry] = {}
    for op in callable_ops:
        if op.application_id in failed_apps and op.uid in {t.uid for t in todo}:
            # keep prior entry if present so a later retry can catch up
            prior = manifest.entries.get(op.uid)
            if prior is not None and prior.text_hash == hashes[op.uid]:
                new_entries[op.uid] = prior
            continue
        new_entries[op.uid] = ManifestEntry(
            text_hash=hashes[op.uid],
            public_id=op.public_id,
            application_id=op.application_id,
        )

    new_manifest = IndexManifest(
        namespace=ns,
        embed_model_id=model_id,
        entries=new_entries,
    )
    write_manifest(manifest_path, new_manifest)

    if stale_ns and vector_store is not None and manifest.entries:
        try:
            await vector_store.delete(
                [point_id(environment, uid) for uid in manifest.entries],
                namespace=stale_ns,
            )
        except Exception as exc:  # noqa: BLE001 — stale cleanup best-effort
            failed_apps.setdefault("_stale_ns", str(exc)[:300])

    # Fill sidecar for any callable ops still missing (sidecar-only path embeds above).
    for op in callable_ops:
        if op.public_id in sidecar_entries:
            continue
        # Unchanged ops without prior sidecar vector: leave absent (search falls back).

    save_openapi_index(sidecar_path, sidecar_entries)

    unchanged = len(callable_ops) - len(todo)
    report = IndexReport(
        environment=environment,
        namespace=ns,
        embed_model_id=model_id,
        embedded=embedded,
        deleted=deleted,
        unchanged=max(0, unchanged),
        failed_apps=failed_apps,
        full_rebuild=full_rebuild,
        duration_ms=(time.perf_counter() - started) * 1000.0,
    )
    try:
        from packages.api_index.metrics import record_metric

        await record_metric(
            "api_index.reindex.embedded",
            float(embedded),
            unit="1",
            attributes={"environment": environment},
        )
    except Exception:  # noqa: BLE001
        pass
    return report
