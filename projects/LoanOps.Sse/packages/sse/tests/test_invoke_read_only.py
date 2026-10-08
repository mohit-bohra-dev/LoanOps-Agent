"""invoke_sse_api is GET/HEAD-only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from packages.sse.fixture import FIXTURE_OPENAPI
from packages.sse.invoke import invoke_sse_api
from packages.sse.loader import OpenApiCatalogService


@pytest.mark.asyncio
async def test_invoke_rejects_post(tmp_path: Path) -> None:
    path = tmp_path / "openapi.json"
    path.write_text(json.dumps(FIXTURE_OPENAPI), encoding="utf-8")
    service = OpenApiCatalogService(
        api_base_url="https://fixture.local",
        fixture_path=str(path),
    )
    result = await invoke_sse_api(
        service,
        method="POST",
        path="/api/Loans/1000002245",
        body={"x": 1},
    )
    assert not result.ok
    assert result.error_message is not None
    assert "GET/HEAD" in result.error_message
