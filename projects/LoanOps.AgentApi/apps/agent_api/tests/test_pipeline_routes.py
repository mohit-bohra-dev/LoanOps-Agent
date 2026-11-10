"""Pipeline control plane route tests (ADR-033)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.asyncio
async def test_catalog_start_and_get_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "pipeline_store"
    reg = tmp_path / "repositories.yaml"
    reg.write_text("repositories: []\n", encoding="utf-8")
    monkeypatch.setenv("EAKG_STORE__BACKEND", "file")
    monkeypatch.setenv("EAKG_STORE__FILE_SHARD_DIR", str(root))
    monkeypatch.setenv("EAKG__REGISTRY_PATH", str(reg))
    monkeypatch.setenv("EAKG__WORKSPACE_DIR", str(tmp_path / "workspace"))
    from packages.common.settings import get_settings

    get_settings.cache_clear()

    from packages.pipelines import catalog as catalog_mod
    from packages.pipelines.catalog import PipelineSpec
    from packages.pipelines.runner import execute_run

    async def _ok(_params: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "operations": 1}

    monkeypatch.setitem(
        catalog_mod.PIPELINES,
        "openapi_to_api_index",
        PipelineSpec(
            pipeline_id="openapi_to_api_index",
            title="OpenAPI → ApiIndex",
            description="test",
            entrypoint=_ok,
            default_params={"environment": "dev"},
        ),
    )
    monkeypatch.setattr(
        "apps.agent_api.pipeline_routes.dispatch_local",
        lambda _run_id: None,
    )

    from apps.agent_api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        cat = await client.get("/pipelines/catalog")
        assert cat.status_code == 200
        assert any(
            p["pipeline_id"] == "openapi_to_api_index" for p in cat.json()["pipelines"]
        )

        missing = await client.post("/pipelines/no_such/runs", json={"environment": "dev"})
        assert missing.status_code == 404

        started = await client.post(
            "/pipelines/openapi_to_api_index/runs",
            json={"environment": "dev", "triggered_by": "tester"},
        )
        assert started.status_code == 202
        run_id = started.json()["run_id"]

        await execute_run(run_id)

        got = await client.get(f"/pipelines/runs/{run_id}")
        assert got.status_code == 200
        body = got.json()
        assert body["status"] == "succeeded"
        assert body["report"]["operations"] == 1
        assert "logs" in body

        listed = await client.get("/pipelines/runs?pipeline_id=openapi_to_api_index")
        assert listed.status_code == 200
        assert any(r["run_id"] == run_id for r in listed.json()["runs"])
