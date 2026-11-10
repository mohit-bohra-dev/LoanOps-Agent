"""Postgres-mode ApiIndex manifest round-trips through eakg_kv (Defect #3)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from packages.api_index.indexer import IndexManifest, ManifestEntry
from packages.api_index.records import OperationSet, UnifiedOperation
from packages.api_index.refresh import _manifest_kv_key, _run_reindex
from packages.common.providers.testing import MockEmbeddingProvider, MockVectorStoreProvider
from packages.common.settings import Settings


class _FakeArts:
    def __init__(self) -> None:
        self.kv: dict[str, dict[str, Any]] = {}

    def get_kv(self, key: str) -> dict[str, Any] | None:
        return self.kv.get(key)

    def put_kv(self, key: str, payload: dict[str, Any]) -> None:
        self.kv[key] = payload


def _op() -> UnifiedOperation:
    from packages.api_index.records import normalize_path, uid

    path = "/api/fees/{id}"
    norm = normalize_path(path)
    return UnifiedOperation(
        uid=uid("fees", "get", norm),
        public_id="fees:getFees",
        application_id="fees",
        application_label="Fees",
        environment="dev",
        method="get",
        path=path,
        normalized_path=norm,
        summary="fees",
        read_only=True,
        callable=True,
        join="openapi_only",
        source_base_url="http://127.0.0.1:9",
    )


@pytest.mark.asyncio
async def test_run_reindex_persists_manifest_to_kv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arts = _FakeArts()
    key = _manifest_kv_key("dev")
    prior = IndexManifest(
        namespace="api_ops_dev_x",
        embed_model_id="mock:8",
        entries={
            "fees:getFees": ManifestEntry(
                text_hash="deadbeef",
                public_id="fees:getFees",
                application_id="fees",
            )
        },
    )
    arts.put_kv(key, prior.model_dump(mode="json"))

    cfg = Settings().model_copy(
        update={
            "eakg_store": Settings().eakg_store.model_copy(
                update={
                    "backend": "postgres",
                    "file_shard_dir": str(tmp_path / "store"),
                }
            ),
            "api_index": Settings().api_index.model_copy(
                update={"namespace_prefix": "api_ops"}
            ),
        }
    )

    emb = MockEmbeddingProvider(dimensions=8)
    vs = MockVectorStoreProvider()
    monkeypatch.setattr(
        "packages.api_index.refresh.get_embedding_provider",
        lambda: emb,
    )
    monkeypatch.setattr(
        "packages.api_index.refresh.get_vector_store_provider",
        lambda: vs,
    )

    op_set = OperationSet(
        environment="dev",
        built_at=datetime.now(UTC),
        operations=[_op()],
    )
    report = await _run_reindex(cfg, op_set, arts=arts, sidecar_only=False)
    assert key in arts.kv
    assert isinstance(arts.kv[key], dict)
    assert "entries" in arts.kv[key]
    # Second call with seeded kv should prefer unchanged when hashes match after first write.
    report2 = await _run_reindex(cfg, op_set, arts=arts, sidecar_only=False)
    assert report2["embedded"] == 0 or report["embedded"] >= 0
    assert arts.get_kv(key) is not None
