"""Layer 1 runner end-to-end."""

from __future__ import annotations

import pytest
from packages.eval.mcp.layer1 import run_layer1


@pytest.mark.asyncio
async def test_run_layer1_passes() -> None:
    report = await run_layer1(enforce_latency=False)
    assert report.protocol_version == "2025-03-26"
    assert report.suites
    failed = [c.id for c in report.cases if not c.passed]
    assert failed == [], f"failed cases: {failed}"
    assert report.thresholds_passed
