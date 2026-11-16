"""Runner state transitions against file artifact store + fake catalog entry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from packages.eakg.artifact_store import FileEakgArtifactStore
from packages.pipelines import catalog as catalog_mod
from packages.pipelines.catalog import PipelineSpec
from datetime import UTC, datetime, timedelta

from packages.pipelines.runner import (
    PipelineBusyError,
    create_run,
    execute_run,
    sweep_stale_runs,
)


@pytest.fixture
def file_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FileEakgArtifactStore:
    root = tmp_path / "pipeline_store"
    reg = tmp_path / "repositories.yaml"
    reg.write_text("repositories: []\n", encoding="utf-8")
    store = FileEakgArtifactStore(root, registry_path=reg)
    store.ensure_schema()

    monkeypatch.setenv("EAKG_STORE__BACKEND", "file")
    monkeypatch.setenv("EAKG_STORE__FILE_SHARD_DIR", str(root))
    monkeypatch.setenv("EAKG__REGISTRY_PATH", str(reg))
    monkeypatch.setenv("EAKG__WORKSPACE_DIR", str(tmp_path / "workspace"))
    from packages.common.settings import get_settings

    get_settings.cache_clear()
    return store


async def _ok(_params: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "operations": 3}


async def _partial(_params: dict[str, Any]) -> dict[str, Any]:
    return {"status": "partial", "failed_apps": 1, "operations": 2}


async def _boom(_params: dict[str, Any]) -> dict[str, Any]:
    raise RuntimeError("explode")


@pytest.mark.asyncio
async def test_success_queued_running_succeeded(
    file_store: FileEakgArtifactStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = file_store
    monkeypatch.setitem(
        catalog_mod.PIPELINES,
        "fake_ok",
        PipelineSpec(
            pipeline_id="fake_ok",
            title="Fake OK",
            description="test",
            entrypoint=_ok,
        ),
    )
    run_id = create_run("fake_ok", {"environment": "dev"}, triggered_by="test")
    row = file_store.get_pipeline_run(run_id)
    assert row is not None
    assert row["status"] == "queued"
    done = await execute_run(run_id)
    assert done["status"] == "succeeded"
    assert done["report"]["operations"] == 3
    final = file_store.get_pipeline_run(run_id)
    assert final is not None
    assert final["status"] == "succeeded"


@pytest.mark.asyncio
async def test_partial_status(
    file_store: FileEakgArtifactStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = file_store
    monkeypatch.setitem(
        catalog_mod.PIPELINES,
        "fake_partial",
        PipelineSpec(
            pipeline_id="fake_partial",
            title="Fake Partial",
            description="test",
            entrypoint=_partial,
        ),
    )
    run_id = create_run("fake_partial", {}, triggered_by="test")
    done = await execute_run(run_id)
    assert done["status"] == "partial"


@pytest.mark.asyncio
async def test_exception_failed(
    file_store: FileEakgArtifactStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = file_store
    monkeypatch.setitem(
        catalog_mod.PIPELINES,
        "fake_boom",
        PipelineSpec(
            pipeline_id="fake_boom",
            title="Fake Boom",
            description="test",
            entrypoint=_boom,
        ),
    )
    run_id = create_run("fake_boom", {}, triggered_by="test")
    done = await execute_run(run_id)
    assert done["status"] == "failed"
    assert "explode" in str(done.get("error") or "")


@pytest.mark.asyncio
async def test_busy_conflict(
    file_store: FileEakgArtifactStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = file_store
    monkeypatch.setitem(
        catalog_mod.PIPELINES,
        "fake_busy",
        PipelineSpec(
            pipeline_id="fake_busy",
            title="Fake Busy",
            description="test",
            entrypoint=_ok,
        ),
    )
    create_run("fake_busy", {}, triggered_by="test")
    with pytest.raises(PipelineBusyError):
        create_run("fake_busy", {}, triggered_by="test")


@pytest.mark.asyncio
async def test_stale_running_does_not_block(
    file_store: FileEakgArtifactStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(
        catalog_mod.PIPELINES,
        "fake_stale",
        PipelineSpec(
            pipeline_id="fake_stale",
            title="Fake Stale",
            description="test",
            entrypoint=_ok,
        ),
    )
    old = (datetime.now(UTC) - timedelta(minutes=45)).isoformat().replace("+00:00", "Z")
    file_store.put_pipeline_run(
        "run_old",
        "fake_stale",
        {"status": "running", "started_at": old, "params": {}},
    )
    swept = sweep_stale_runs(file_store, "fake_stale")
    assert "run_old" in swept
    stale_row = file_store.get_pipeline_run("run_old")
    assert stale_row is not None
    assert stale_row["status"] == "failed"
    assert stale_row["error"] == "stale_timeout"
    run_id = create_run("fake_stale", {}, triggered_by="test")
    assert run_id

    # Fresh running still blocks.
    fresh = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    file_store.put_pipeline_run(
        "run_fresh",
        "fake_stale",
        {"status": "running", "started_at": fresh, "params": {}},
    )
    with pytest.raises(PipelineBusyError):
        create_run("fake_stale", {}, triggered_by="test")
