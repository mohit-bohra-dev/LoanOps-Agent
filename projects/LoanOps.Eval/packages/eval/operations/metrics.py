"""Aggregate MCP/prod TraceRecords into ops metrics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from packages.common.providers.eval_store import TraceRecord
from pydantic import BaseModel, Field


class ToolMetrics(BaseModel):
    tool: str
    count: int = 0
    error_count: int = 0
    is_error_count: int = 0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    error_rate: float = 0.0
    is_error_rate: float = 0.0


class OpsMetrics(BaseModel):
    by_tool: dict[str, ToolMetrics] = Field(default_factory=dict)
    by_client: dict[str, int] = Field(default_factory=dict)
    total: int = 0


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * pct
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def compute_ops_metrics(traces: list[TraceRecord]) -> OpsMetrics:
    by_tool_lat: dict[str, list[float]] = defaultdict(list)
    by_tool_err: dict[str, int] = defaultdict(int)
    by_tool_is_err: dict[str, int] = defaultdict(int)
    by_tool_n: dict[str, int] = defaultdict(int)
    by_client: dict[str, int] = defaultdict(int)

    for tr in traces:
        tool = str(tr.attributes.get("tool") or tr.name or "unknown")
        by_tool_n[tool] += 1
        by_tool_lat[tool].append(float(tr.latency_ms))
        if not tr.success:
            by_tool_err[tool] += 1
        if tr.is_error:
            by_tool_is_err[tool] += 1
        client = str(tr.attributes.get("mcp.client_name") or "unknown")
        by_client[client] += 1

    by_tool: dict[str, ToolMetrics] = {}
    for tool, n in by_tool_n.items():
        lats = sorted(by_tool_lat[tool])
        err = by_tool_err[tool]
        is_err = by_tool_is_err[tool]
        by_tool[tool] = ToolMetrics(
            tool=tool,
            count=n,
            error_count=err,
            is_error_count=is_err,
            p50_latency_ms=_percentile(lats, 0.50),
            p95_latency_ms=_percentile(lats, 0.95),
            error_rate=(err / n) if n else 0.0,
            is_error_rate=(is_err / n) if n else 0.0,
        )
    return OpsMetrics(by_tool=by_tool, by_client=dict(by_client), total=len(traces))


def drift_breaches(
    current: OpsMetrics,
    previous: OpsMetrics,
    *,
    max_delta: float,
) -> list[str]:
    """Flag tools whose error_rate or p95 changed more than max_delta (relative)."""
    breaches: list[str] = []
    for tool, cur in current.by_tool.items():
        prev = previous.by_tool.get(tool)
        if prev is None or prev.count == 0:
            continue
        if prev.error_rate > 0:
            delta = abs(cur.error_rate - prev.error_rate) / max(prev.error_rate, 1e-9)
            if delta > max_delta:
                breaches.append(
                    f"{tool} error_rate drift {delta:.2f} > {max_delta}"
                )
        if prev.p95_latency_ms > 0:
            delta = abs(cur.p95_latency_ms - prev.p95_latency_ms) / prev.p95_latency_ms
            if delta > max_delta:
                breaches.append(
                    f"{tool} p95 drift {delta:.2f} > {max_delta}"
                )
    return breaches


def slo_breaches(
    metrics: OpsMetrics,
    slo: dict[str, Any],
) -> list[str]:
    """Compare metrics to ops_slos.yaml structure."""
    breaches: list[str] = []
    min_n = int(slo.get("min_sample_size", 5))
    default = slo.get("default") or {}
    tools_cfg = slo.get("tools") or {}
    for tool, m in metrics.by_tool.items():
        if m.count < min_n:
            continue
        cfg = tools_cfg.get(tool) or default
        p95_lim = float(cfg.get("p95_latency_ms", default.get("p95_latency_ms", 2000)))
        err_lim = float(cfg.get("error_rate", default.get("error_rate", 0.05)))
        is_err_lim = float(cfg.get("is_error_rate", default.get("is_error_rate", 0.05)))
        if m.p95_latency_ms > p95_lim:
            breaches.append(
                f"{tool} p95 {m.p95_latency_ms:.1f}ms > {p95_lim}ms"
            )
        if m.error_rate > err_lim:
            breaches.append(f"{tool} error_rate {m.error_rate:.3f} > {err_lim}")
        if m.is_error_rate > is_err_lim:
            breaches.append(
                f"{tool} is_error_rate {m.is_error_rate:.3f} > {is_err_lim}"
            )
    return breaches
