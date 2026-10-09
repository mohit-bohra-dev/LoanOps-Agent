"""Incremental reindex cases (spec §14.1 P3)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from packages.api_index.indexer import (
    IndexManifest,
    load_manifest,
    namespace_for,
    reindex,
    unified_operation_text,
)
from packages.api_index.records import OperationSet, UnifiedOperation
from packages.common.providers.testing import MockEmbeddingProvider, MockVectorStoreProvider
from packages.sse.semantic import text_hash


def _op(
    *,
    app: str = "fees",
    method: str = "get",
    path: str = "/api/fees/{id}",
    public: str = "fees:getFees",
    summary: str = "fees",
    read_only: bool = True,
    callable_: bool = True,
) -> UnifiedOperation:
    from packages.api_index.records import normalize_path, uid

    norm = normalize_path(path)
    return UnifiedOperation(
        uid=uid(app, method, norm),
        public_id=public,
        application_id=app,
        application_label=app.title(),
        environment="local",
        method=method,  # type: ignore[arg-type]
        path=path,
        normalized_path=norm,
        summary=summary,
        read_only=read_only,
        callable=callable_,
        join="openapi_only",
        source_base_url="http://127.0.0.1:9",
    )


def _op_set(*ops: UnifiedOperation) -> OperationSet:
    return OperationSet(
        environment="local",
        built_at=datetime.now(UTC),
        operations=list(ops),
    )


@pytest.mark.asyncio
async def test_reindex_first_run_embeds_all_second_embeds_zero(tmp_path: Path) -> None:
    vs = MockVectorStoreProvider()
    emb = MockEmbeddingProvider(dimensions=8)
    ops = _op_set(_op(), _op(app="escrow", path="/api/escrow/{id}", public="escrow:getEscrow", summary="escrow"))
    manifest = tmp_path / "index.manifest.json"
    sidecar = tmp_path / "openapi_embeddings.json"
    first = await reindex(
        "local",
        ops,
        vector_store=vs,
        embedder=emb,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    assert first.embedded == 2
    assert first.deleted == 0
    assert first.full_rebuild is True
    assert sidecar.is_file()

    second = await reindex(
        "local",
        ops,
        vector_store=vs,
        embedder=emb,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    assert second.embedded == 0
    assert second.unchanged == 2
    assert second.full_rebuild is False


@pytest.mark.asyncio
async def test_reindex_one_changed_embeds_one(tmp_path: Path) -> None:
    vs = MockVectorStoreProvider()
    emb = MockEmbeddingProvider(dimensions=8)
    op_a = _op()
    op_b = _op(app="escrow", path="/api/escrow/{id}", public="escrow:getEscrow", summary="escrow")
    manifest = tmp_path / "index.manifest.json"
    sidecar = tmp_path / "sidecar.json"
    await reindex(
        "local",
        _op_set(op_a, op_b),
        vector_store=vs,
        embedder=emb,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    changed = _op(summary="fees UPDATED for reindex")
    report = await reindex(
        "local",
        _op_set(changed, op_b),
        vector_store=vs,
        embedder=emb,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    assert report.embedded == 1
    assert report.unchanged == 1


@pytest.mark.asyncio
async def test_reindex_removed_op_deletes(tmp_path: Path) -> None:
    vs = MockVectorStoreProvider()
    emb = MockEmbeddingProvider(dimensions=8)
    op_a = _op()
    op_b = _op(app="escrow", path="/api/escrow/{id}", public="escrow:getEscrow", summary="escrow")
    manifest = tmp_path / "index.manifest.json"
    sidecar = tmp_path / "sidecar.json"
    await reindex(
        "local",
        _op_set(op_a, op_b),
        vector_store=vs,
        embedder=emb,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    report = await reindex(
        "local",
        _op_set(op_a),
        vector_store=vs,
        embedder=emb,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    assert report.deleted == 1
    loaded = load_manifest(manifest)
    assert op_b.uid not in loaded.entries
    assert op_a.uid in loaded.entries


@pytest.mark.asyncio
async def test_reindex_model_change_new_namespace(tmp_path: Path) -> None:
    vs = MockVectorStoreProvider()
    emb8 = MockEmbeddingProvider(dimensions=8)
    emb16 = MockEmbeddingProvider(dimensions=16)
    ops = _op_set(_op())
    manifest = tmp_path / "index.manifest.json"
    sidecar = tmp_path / "sidecar.json"
    first = await reindex(
        "local",
        ops,
        vector_store=vs,
        embedder=emb8,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    second = await reindex(
        "local",
        ops,
        vector_store=vs,
        embedder=emb16,
        manifest_path=manifest,
        namespace_prefix="api_ops",
        sidecar_path=sidecar,
    )
    assert first.namespace != second.namespace
    assert second.full_rebuild is True
    assert second.embedded == 1
    assert second.namespace == namespace_for("api_ops", "local", "mock:16")


def test_unified_operation_text_includes_code_unit() -> None:
    op = _op()
    op.code_unit = "FeesController.Get"
    op.capability_ids = ["GetFees"]
    text = unified_operation_text(op)
    assert "FeesController.Get" in text
    assert "GetFees" in text
    assert text_hash(text)


def test_manifest_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "m.json"
    from packages.api_index.indexer import ManifestEntry, write_manifest

    m = IndexManifest(
        namespace="api_ops_local_deadbeef",
        embed_model_id="mock:8",
        entries={"u1": ManifestEntry(text_hash="abc", public_id="a:b", application_id="a")},
    )
    write_manifest(path, m)
    loaded = load_manifest(path)
    assert loaded.namespace == m.namespace
    assert loaded.entries["u1"].public_id == "a:b"
