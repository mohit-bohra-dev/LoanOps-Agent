"""Asset-state freshness helpers."""

from __future__ import annotations

from pathlib import Path

from packages.eakg.artifact_store import FileEakgArtifactStore
from packages.pipelines.freshness import (
    asset_key_api_index,
    evaluate_freshness,
    store_api_index_hashes,
)


def test_evaluate_freshness_never_materialized(tmp_path: Path) -> None:
    reg = tmp_path / "repositories.yaml"
    reg.write_text("repositories: []\n", encoding="utf-8")
    store = FileEakgArtifactStore(tmp_path / "pipeline_store", registry_path=reg)
    store.ensure_schema()
    result = evaluate_freshness(store, "openapi_to_api_index", environment="dev")
    assert result["status"] == "stale"
    assert result["reason"] == "never_materialized"


def test_store_and_key(tmp_path: Path) -> None:
    reg = tmp_path / "repositories.yaml"
    reg.write_text("repositories: []\n", encoding="utf-8")
    store = FileEakgArtifactStore(tmp_path / "pipeline_store", registry_path=reg)
    store.ensure_schema()
    store_api_index_hashes(
        store,
        "dev",
        {"fees": {"spec_hash": "aaa", "interface_hash": "bbb"}},
    )
    got = store.get_asset_state(asset_key_api_index("dev"))
    assert got is not None
    assert got["apps"]["fees"]["spec_hash"] == "aaa"
    other = evaluate_freshness(store, "eakg_sync_nightly", environment="dev")
    assert other["status"] == "unknown"
