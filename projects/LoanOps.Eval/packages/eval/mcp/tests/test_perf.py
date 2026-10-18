"""L1d performance — concurrency, percentiles, payload budgets."""

from __future__ import annotations

import asyncio
import time

import pytest
from packages.eval.mcp.harness import (
    AsgiMcpDriver,
    FakeClient,
    FakeMode,
    percentile,
    run_execute,
)
from packages.eval.mcp.layer1 import MAX_TOOL_RESULT_BYTES, MAX_TOOLS_LIST_BYTES


@pytest.mark.asyncio
async def test_concurrent_execute_isolation() -> None:
    async def one(i: int) -> str:
        return await run_execute(
            name="search_docs",
            arguments={"query": f"q-{i}"},
            client=FakeClient(mode=FakeMode.OK),
        )

    results = await asyncio.gather(*[one(i) for i in range(8)])
    assert results == ["ok:search_docs"] * 8


@pytest.mark.asyncio
async def test_latency_percentiles_on_fake_client() -> None:
    latencies: list[float] = []
    for _ in range(20):
        t0 = time.perf_counter()
        await run_execute(
            name="search_docs",
            arguments={"query": "escrow"},
            client=FakeClient(mode=FakeMode.OK),
        )
        latencies.append((time.perf_counter() - t0) * 1000)
    latencies.sort()
    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    assert p50 <= p95
    assert p95 < 4000.0


def test_payload_budgets() -> None:
    driver = AsgiMcpDriver()
    listed = driver.tools_list()
    assert len(listed.raw_text.encode("utf-8")) <= MAX_TOOLS_LIST_BYTES


@pytest.mark.asyncio
async def test_sample_result_payload_budget() -> None:
    text = await run_execute(
        name="search_docs",
        arguments={"query": "escrow"},
        client=FakeClient(mode=FakeMode.OK),
    )
    assert len(text.encode("utf-8")) <= MAX_TOOL_RESULT_BYTES
