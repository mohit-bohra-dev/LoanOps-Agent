"""MCP fixture eval runner — in-process, no disk reports."""

from __future__ import annotations

import pytest
from packages.common.providers.testing import MockTelemetryProvider
from packages.mcp_server.eval_run import run_mcp_eval


@pytest.mark.asyncio
async def test_run_mcp_eval_all_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    tel = MockTelemetryProvider()
    monkeypatch.setattr(
        "packages.mcp_server.eval_run.get_telemetry_provider",
        lambda: tel,
    )
    metrics = await run_mcp_eval()
    assert metrics["mcp_auth_correctness"] == 1.0
    assert metrics["mcp_policy_correctness"] == 1.0
    assert metrics["mcp_success_rate"] == 1.0
    names = {m["name"] for m in tel.recorded_metrics}
    assert "eval.mcp.mcp_auth_correctness" in names
    assert "eval.mcp.mcp_policy_correctness" in names
    assert "eval.mcp.mcp_success_rate" in names
