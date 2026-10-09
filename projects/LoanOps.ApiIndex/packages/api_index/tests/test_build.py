"""build_operations over registry fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.api_index.catalog import build_operations, mismatch_report, write_operations
from packages.eakg.registry import AppEnvironment, RepositoryRecord, RepositoryRegistry
from packages.eakg.spec_cache import refresh_spec
from packages.eakg.store import ShardStore


async def _token(_a: str, _b: str) -> str:
    return ""


@pytest.mark.asyncio
async def test_build_operations_from_local_fixtures(tmp_path: Path) -> None:
    fixture = tmp_path / "fees.openapi.json"
    fixture.write_text(
        '{"openapi":"3.0.3","info":{"title":"Fees","version":"1"},'
        '"paths":{"/api/fees/{id}":{"get":{"operationId":"getFees","summary":"fees"}}}}',
        encoding="utf-8",
    )
    yaml_path = tmp_path / "repositories.yaml"
    yaml_path.write_text("repositories: []\n", encoding="utf-8")
    registry = RepositoryRegistry(yaml_path)
    record = RepositoryRecord(
        repository_id="fees",
        application="Fees",
        application_id="fees",
        git_url="",
        environments={
            "local": AppEnvironment(base_url="http://127.0.0.1:9102", spec_fixture=str(fixture))
        },
    )
    registry.upsert(record)
    registry.save()
    store = ShardStore(tmp_path / "shards")
    store.ensure_layout()
    await refresh_spec(record, "local", store, _token)
    op_set = build_operations(registry, store, "local")
    assert len(op_set.operations) == 1
    assert op_set.operations[0].public_id == "fees:getFees"
    assert op_set.operations[0].join == "openapi_only"
    path = write_operations(store.root, op_set)
    assert path.is_file()
    report = mismatch_report(op_set)
    assert report["openapi_only"] == ["fees:getFees"]
    assert report["eakg_only"] == []
