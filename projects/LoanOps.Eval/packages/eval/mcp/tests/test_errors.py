"""L1b error handling — fail / raise / timeout / rate-limit → clear failure."""

from __future__ import annotations

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from packages.common.providers.testing import MockTelemetryProvider
from packages.eval.mcp.harness import FIXTURE_AUTH_HEADER, FakeClient, FakeMode, eval_settings
from packages.eval.mcp.layer1 import FakeAudit
from packages.mcp_server.server import execute_tool


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "expect_substr"),
    [
        (FakeMode.FAIL, "upstream failed"),
        (FakeMode.TIMEOUT, "timeout"),
        (FakeMode.RATE_LIMIT, "429"),
    ],
)
async def test_upstream_modes_raise_tool_error(
    mode: FakeMode, expect_substr: str
) -> None:
    client = FakeClient(mode=mode, timeout_flag=True)
    audit = FakeAudit()
    tel = MockTelemetryProvider()
    with pytest.raises(ToolError) as ei:
        await execute_tool(
            name="search_docs",
            arguments={"query": "escrow"},
            authorization=FIXTURE_AUTH_HEADER,
            user=None,
            tenant=None,
            settings=eval_settings(),
            client=client,
            audit=audit,
            telemetry=tel,
        )
    assert expect_substr in str(ei.value).lower() or expect_substr in str(ei.value)
    assert audit.events
    assert audit.events[-1].payload.get("success") is False
    outcomes = [m for m in tel.recorded_metrics if m["name"] == "mcp.tool.outcome"]
    assert outcomes
    assert outcomes[-1]["attributes"]["outcome"] == "error"


@pytest.mark.asyncio
async def test_client_raise_does_not_silent_succeed() -> None:
    client = FakeClient(mode=FakeMode.RAISE)
    audit = FakeAudit()
    tel = MockTelemetryProvider()
    with pytest.raises(RuntimeError, match="simulated"):
        await execute_tool(
            name="search_docs",
            arguments={"query": "escrow"},
            authorization=FIXTURE_AUTH_HEADER,
            user=None,
            tenant=None,
            settings=eval_settings(),
            client=client,
            audit=audit,
            telemetry=tel,
        )
    assert audit.events
    assert audit.events[-1].payload.get("success") is False
