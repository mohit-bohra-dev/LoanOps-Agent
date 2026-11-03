"""L8 metrics unit tests."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.common.providers.eval_store import TraceRecord
from packages.eval.operations.metrics import compute_ops_metrics, slo_breaches


def test_compute_ops_metrics() -> None:
    traces = [
        TraceRecord(
            trace_id="a",
            name="mcp.tool.call",
            environment="prod",
            latency_ms=100,
            success=True,
            attributes={"tool": "search_docs", "mcp.client_name": "cursor"},
        ),
        TraceRecord(
            trace_id="b",
            name="mcp.tool.call",
            environment="prod",
            latency_ms=200,
            success=False,
            is_error=True,
            attributes={"tool": "search_docs", "mcp.client_name": "cursor"},
        ),
    ]
    m = compute_ops_metrics(traces)
    assert m.total == 2
    assert m.by_tool["search_docs"].error_rate == 0.5
    assert m.by_client["cursor"] == 2


def test_slo_breach_on_high_error() -> None:
    traces = [
        TraceRecord(
            trace_id=str(i),
            name="mcp.tool.call",
            environment="prod",
            latency_ms=100,
            success=False,
            is_error=True,
            attributes={"tool": "search_docs"},
            start_time=datetime.now(timezone.utc),
        )
        for i in range(10)
    ]
    m = compute_ops_metrics(traces)
    breaches = slo_breaches(
        m,
        {
            "min_sample_size": 5,
            "default": {"p95_latency_ms": 2000, "error_rate": 0.05, "is_error_rate": 0.05},
            "tools": {},
        },
    )
    assert any("error_rate" in b for b in breaches)
