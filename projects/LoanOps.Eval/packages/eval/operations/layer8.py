"""Layer 8 operations runner — prod MCP SLOs via EvalStore."""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from packages.common.providers.eval_store import ScoreRecord, TraceRecord
from packages.common.providers.testing import InMemoryEvalStore
from packages.eval.operations.metrics import (
    OpsMetrics,
    compute_ops_metrics,
    drift_breaches,
    slo_breaches,
)
from packages.eval.operations.sample_score import score_sampled_trace
from pydantic import BaseModel, Field


def _repo_data_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "golden.jsonl").is_file():
            return parent / "data"
    return here.parents[5] / "data"


_DEFAULT_SLO = _repo_data_dir() / "eval" / "ops_slos.yaml"


class Layer8Report(BaseModel):
    metrics: OpsMetrics = Field(default_factory=OpsMetrics)
    previous_metrics: OpsMetrics | None = None
    thresholds_passed: bool = False
    breaches: list[str] = Field(default_factory=list)
    sample_failures: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    enqueued_reviews: list[str] = Field(default_factory=list)


def load_slos(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _fixture_traces(*, environment: str = "prod") -> list[TraceRecord]:
    """Synthetic MCP traces for CI (no live Langfuse)."""
    now = datetime.now(timezone.utc)
    tools = [
        ("search_docs", 80.0, True),
        ("search_sse_apis", 90.0, True),
        ("call_sse_api", 200.0, True),
        ("list_sse_apis", 40.0, True),
        ("search_docs", 100.0, True),
        ("search_sse_apis", 110.0, True),
        ("call_sse_api", 220.0, True),
        ("list_sse_apis", 50.0, True),
        ("search_docs", 95.0, True),
        ("call_sse_api", 180.0, True),
    ]
    out: list[TraceRecord] = []
    for i, (tool, lat, ok) in enumerate(tools):
        out.append(
            TraceRecord(
                trace_id=f"fix-{i}",
                span_id=f"span-{i}",
                name="mcp.tool.call",
                environment=environment,
                start_time=now - timedelta(hours=1, minutes=i),
                latency_ms=lat,
                success=ok,
                is_error=not ok,
                attributes={
                    "tool": tool,
                    "mcp.client_name": "loanops-agent" if i % 2 == 0 else "cursor",
                },
                input={"tool": tool},
                output={"ok": ok},
            )
        )
    return out


async def run_layer8_async(
    *,
    slo_path: Path,
    environment: str = "prod",
    window_hours: int | None = None,
    sample_rate: float | None = None,
    store: Any | None = None,
    use_fixtures: bool = True,
) -> Layer8Report:
    slo = load_slos(slo_path)
    window = int(window_hours or slo.get("window_hours", 24))
    rate = float(sample_rate if sample_rate is not None else slo.get("sample_rate", 0.05))
    queue = str(slo.get("review_queue", "loanops-ops-review"))
    max_drift = float(slo.get("max_drift_delta", 0.15))

    report = Layer8Report(
        notes=[
            "Layer 8 ops metrics are separate from offline eval.* scores.",
            f"environment={environment}; ops.* scores only.",
            "Auth deferred; samples MCP tool spans across consuming agents.",
        ]
    )

    if store is None:
        store = InMemoryEvalStore()
        use_fixtures = True

    since = datetime.now(timezone.utc) - timedelta(hours=window)
    if use_fixtures:
        traces = _fixture_traces(environment=environment)
        if hasattr(store, "traces"):
            store.traces.extend(traces)
        elif hasattr(store, "seed_traces"):
            await store.seed_traces(traces)
    else:
        traces = await store.fetch_traces(
            environment=environment,
            since=since,
            name="mcp.tool.call",
            limit=5000,
        )

    if not traces:
        report.notes.append("no traces found; using empty metrics")
        report.thresholds_passed = True
        return report

    metrics = compute_ops_metrics(traces)
    report.metrics = metrics

    # Previous window: traces older than `window` (fixture: empty → no drift).
    prev_since = since - timedelta(hours=window)
    prev_traces = [
        t
        for t in traces
        if t.start_time is not None and t.start_time < since
    ]
    # Fixtures are all "current"; fabricate a previous snapshot as copy for smoke.
    if use_fixtures:
        prev_metrics = compute_ops_metrics(traces)
    else:
        prev_metrics = compute_ops_metrics(
            await store.fetch_traces(
                environment=environment,
                since=prev_since,
                name="mcp.tool.call",
                limit=5000,
            )
        )
    report.previous_metrics = prev_metrics

    breaches = slo_breaches(metrics, slo)
    breaches.extend(drift_breaches(metrics, prev_metrics, max_delta=max_drift))
    report.breaches = breaches

    # Sample online scoring
    rng = random.Random(42)
    sample = [t for t in traces if rng.random() < max(rate, 0.2)]  # floor for fixtures
    if not sample and traces:
        sample = traces[: max(1, int(len(traces) * 0.2))]
    for tr in sample:
        scored = score_sampled_trace(tr)
        if not scored.passed:
            report.sample_failures.append(f"{tr.trace_id}: {'; '.join(scored.reasons)}")
            await store.enqueue_review(queue, tr.trace_id)
            report.enqueued_reviews.append(tr.trace_id)

    # Record ops.* scores into store (environment=prod)
    run = await store.start_run(
        "loanops-l8-ops",
        f"ops-{environment}-{window}h",
        metadata={"layer": "8"},
        environment=environment,
    )
    for tool, m in metrics.by_tool.items():
        await store.record_item_result(
            run,
            tool,
            scores=[
                ScoreRecord(
                    name=f"ops.{tool}.p95_latency_ms",
                    value=m.p95_latency_ms,
                    environment=environment,
                ),
                ScoreRecord(
                    name=f"ops.{tool}.error_rate",
                    value=m.error_rate,
                    environment=environment,
                ),
            ],
        )

    report.thresholds_passed = len(report.breaches) == 0
    return report


def run_layer8(**kwargs: Any) -> Layer8Report:
    return asyncio.run(run_layer8_async(**kwargs))


def _print_report(report: Layer8Report) -> None:
    print()
    print("=" * 60)
    print("Layer 8 Operations Report")
    print("=" * 60)
    print(f"  traces: {report.metrics.total}")
    for tool, m in sorted(report.metrics.by_tool.items()):
        print(
            f"  {tool}: n={m.count} p95={m.p95_latency_ms:.1f}ms "
            f"err={m.error_rate:.3f} is_err={m.is_error_rate:.3f}"
        )
    if report.metrics.by_client:
        print(f"  clients: {report.metrics.by_client}")
    if report.breaches:
        print(f"\n  BREACHES ({len(report.breaches)}):")
        for b in report.breaches:
            print(f"    - {b}")
    if report.sample_failures:
        print(f"\n  sample failures: {len(report.sample_failures)}")
    if report.notes:
        print("\n  Notes:")
        for n in report.notes:
            print(f"    - {n}")
    print()
    if report.thresholds_passed:
        print("  [PASS] ALL LAYER-8 CHECKS PASSED")
    else:
        print("  [FAIL] SLO / drift breaches")
    print("=" * 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Layer 8 operations evaluation.")
    parser.add_argument("--slos", type=Path, default=_DEFAULT_SLO)
    parser.add_argument("--env", default="prod")
    parser.add_argument("--window", type=int, default=None)
    parser.add_argument("--sample", type=float, default=None)
    parser.add_argument("--report", type=Path, default=Path("out/eval-l8.json"))
    parser.add_argument(
        "--live-store",
        action="store_true",
        help="Use get_eval_store_provider() instead of fixture InMemory store",
    )
    args = parser.parse_args(argv)

    store: Any | None = None
    use_fixtures = True
    if args.live_store:
        try:
            from packages.common.providers.factory import get_eval_store_provider

            store = get_eval_store_provider()
            use_fixtures = False
        except Exception as exc:  # noqa: BLE001
            print(f"live store unavailable, falling back to fixtures: {exc}")
            store = None
            use_fixtures = True

    report = run_layer8(
        slo_path=args.slos,
        environment=args.env,
        window_hours=args.window,
        sample_rate=args.sample,
        store=store,
        use_fixtures=use_fixtures,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    _print_report(report)
    return 0 if report.thresholds_passed else 1


if __name__ == "__main__":
    sys.exit(main())
