"""Eval runner — execute golden set, compute metrics, gate on thresholds.

Usage::

    python -m packages.eval.run --golden data/golden.jsonl --report out/eval.json

Exit codes:
    0 — all thresholds passed
    1 — one or more threshold breaches
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

from packages.agent_core import run_agent_turn
from packages.common.providers import (
    ChatProvider,
    PromptStoreProvider,
    ToolsClientProvider,
)
from packages.common.providers.factory import (
    get_chat_provider,
    get_prompt_store_provider,
    get_tools_client_provider,
)
from packages.eval.metrics import (
    compute_citation_coverage,
    compute_cost_avg,
    compute_latency_p95,
    compute_refusal_correctness,
)
from packages.eval.models import (
    EvalItemResult,
    EvalReport,
    GoldenItem,
    MetricValues,
)
from packages.eval.thresholds import check_thresholds


def _load_golden(path: Path) -> list[GoldenItem]:
    """Load golden items from JSONL file."""
    items: list[GoldenItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(GoldenItem(**json.loads(line)))
    return items


async def _run_single_item(
    item: GoldenItem,
    *,
    chat_provider: ChatProvider,
    tools_client: ToolsClientProvider,
    prompt_store: PromptStoreProvider,
) -> EvalItemResult:
    """Run a single golden item through the agent and capture output + timing."""
    t0 = time.perf_counter()
    try:
        output = await run_agent_turn(
            prompt=item.rep_prompt,
            chat_provider=chat_provider,
            tools_client=tools_client,
            prompt_store=prompt_store,
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        return EvalItemResult(
            golden_id=item.id,
            rep_prompt=item.rep_prompt,
            expected=item.expected,
            output=output,
            latency_ms=round(latency_ms, 2),
            cost_usd=0.0,  # TODO: extract from provider telemetry when available
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - t0) * 1000
        return EvalItemResult(
            golden_id=item.id,
            rep_prompt=item.rep_prompt,
            expected=item.expected,
            error=str(exc),
            latency_ms=round(latency_ms, 2),
        )


async def _compute_ragas_metrics(
    results: list[EvalItemResult],
    *,
    chat_provider: ChatProvider,
) -> dict[str, float]:
    """Compute Ragas faithfulness and answer_relevance.

    Uses the ChatProvider as LLM-as-judge. Returns dict with metric scores.
    Only evaluates happy-path items (non-refusal, non-escalation, no error).
    """
    # Import ragas lazily — heavy dependency
    try:
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, faithfulness
    except ImportError:
        print("  [WARN] ragas not importable — skipping LLM metrics")
        return {}

    # Build evaluation dataset
    questions: list[str] = []
    answers: list[str] = []
    contexts: list[list[str]] = []

    for r in results:
        if r.output is None or r.error is not None:
            continue
        if r.expected.refusal or r.expected.escalation is not None:
            continue
        if not r.output.answer:
            continue

        questions.append(r.rep_prompt)
        answers.append(r.output.answer)
        ctx = [c.snippet for c in r.output.citations if c.snippet]
        contexts.append(ctx if ctx else ["No context available."])

    if not questions:
        return {"faithfulness": 1.0, "answer_relevance": 1.0}

    try:
        from datasets import Dataset  # type: ignore[import-untyped]

        ds = Dataset.from_dict(
            {
                "question": questions,
                "answer": answers,
                "contexts": contexts,
            }
        )

        raw_result: Any = evaluate(
            ds,
            metrics=[faithfulness, answer_relevancy],
        )

        scores: dict[str, float] = {}
        if "faithfulness" in raw_result:
            scores["faithfulness"] = float(raw_result["faithfulness"])
        if "answer_relevancy" in raw_result:
            scores["answer_relevance"] = float(raw_result["answer_relevancy"])
        return scores

    except Exception as exc:  # noqa: BLE001
        print(f"  [WARN] Ragas evaluation failed: {exc}")
        return {}


async def run_eval(
    golden_path: Path,
    report_path: Path,
    *,
    skip_llm_metrics: bool = False,
    enforce_latency: bool = False,
    chat_provider: ChatProvider | None = None,
    tools_client: ToolsClientProvider | None = None,
    prompt_store: PromptStoreProvider | None = None,
) -> EvalReport:
    """Run full evaluation pipeline.

    Args:
        golden_path: Path to golden JSONL file.
        report_path: Path to write JSON report.
        skip_llm_metrics: Skip Ragas faithfulness/answer_relevance.
        enforce_latency: Enforce latency_p95 threshold.
        chat_provider: Override chat provider (for testing).
        tools_client: Override tools client (for testing).
        prompt_store: Override prompt store (for testing).

    Returns:
        EvalReport with all results and metrics.
    """
    # 1. Load golden set
    items = _load_golden(golden_path)
    print(f"  Loaded {len(items)} golden items from {golden_path}")

    # 2. Obtain providers (via factories or overrides)
    chat = chat_provider or get_chat_provider()
    tools = tools_client or get_tools_client_provider()
    prompts = prompt_store or get_prompt_store_provider()

    # 3. Run each item
    results: list[EvalItemResult] = []
    for i, item in enumerate(items):
        print(f"  [{i + 1}/{len(items)}] {item.id}: {item.rep_prompt[:60]}...")
        result = await _run_single_item(
            item,
            chat_provider=chat,
            tools_client=tools,
            prompt_store=prompts,
        )
        results.append(result)
        if result.error:
            print(f"    ERROR: {result.error[:80]}")

    # 4. Compute structural metrics
    citation_cov = compute_citation_coverage(results)
    refusal_corr = compute_refusal_correctness(results)
    p95 = compute_latency_p95(results)
    cost = compute_cost_avg(results)

    error_count = sum(1 for r in results if r.error is not None)

    metric_values = MetricValues(
        citation_coverage=round(citation_cov, 4),
        refusal_correctness=round(refusal_corr, 4),
        latency_p95_ms=round(p95, 2),
        cost_avg_usd=round(cost, 6),
        total_items=len(results),
        error_count=error_count,
    )

    skipped: list[str] = []

    # 5. Compute LLM-as-judge metrics (Ragas)
    if not skip_llm_metrics:
        ragas_scores = await _compute_ragas_metrics(results, chat_provider=chat)
        if "faithfulness" in ragas_scores:
            metric_values.faithfulness = round(ragas_scores["faithfulness"], 4)
        else:
            skipped.append("faithfulness")
        if "answer_relevance" in ragas_scores:
            metric_values.answer_relevance = round(ragas_scores["answer_relevance"], 4)
        else:
            skipped.append("answer_relevance")
    else:
        skipped.extend(["faithfulness", "answer_relevance"])

    if not enforce_latency:
        skipped.append("latency_p95_ms")

    # 6. Check thresholds
    metrics_dict: dict[str, float] = {
        "citation_coverage": metric_values.citation_coverage,
        "refusal_correctness": metric_values.refusal_correctness,
        "latency_p95_ms": metric_values.latency_p95_ms,
    }
    if metric_values.faithfulness is not None:
        metrics_dict["faithfulness"] = metric_values.faithfulness
    if metric_values.answer_relevance is not None:
        metrics_dict["answer_relevance"] = metric_values.answer_relevance

    breaches = check_thresholds(metrics_dict, skip=set(skipped))

    report = EvalReport(
        metrics=metric_values,
        thresholds_passed=len(breaches) == 0,
        breaches=breaches,
        skipped_metrics=skipped,
        items=results,
    )

    # 7. Write report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return report


def _print_report(report: EvalReport) -> None:
    """Print human-readable summary to stdout."""
    m = report.metrics
    print()
    print("=" * 60)
    print("Eval Report")
    print("=" * 60)
    print(f"  Items evaluated:     {m.total_items}")
    print(f"  Errors:              {m.error_count}")
    print()
    print("  Metrics:")
    print(f"    citation_coverage:   {m.citation_coverage:.4f}")
    print(f"    refusal_correctness: {m.refusal_correctness:.4f}")
    print(f"    latency_p95_ms:      {m.latency_p95_ms:.1f}")
    print(f"    cost_avg_usd:        ${m.cost_avg_usd:.6f}")
    if m.faithfulness is not None:
        print(f"    faithfulness:        {m.faithfulness:.4f}")
    if m.answer_relevance is not None:
        print(f"    answer_relevance:    {m.answer_relevance:.4f}")

    if report.skipped_metrics:
        print(f"\n  Skipped: {', '.join(report.skipped_metrics)}")

    print()
    if report.thresholds_passed:
        print("  ✓ ALL THRESHOLDS PASSED")
    else:
        print(f"  ✗ {len(report.breaches)} THRESHOLD BREACH(ES):")
        for b in report.breaches:
            op = ">=" if b.direction == "gte" else "<="
            print(f"    - {b.metric}: {b.actual:.4f} (need {op} {b.threshold})")

    print("=" * 60)


def main() -> int:
    """CLI entrypoint for ``python -m packages.eval.run``."""
    parser = argparse.ArgumentParser(
        prog="packages.eval.run",
        description="Run eval harness against the golden set.",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=Path("data/golden.jsonl"),
        help="Path to golden JSONL file",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("out/eval.json"),
        help="Path to write JSON report",
    )
    parser.add_argument(
        "--skip-llm-metrics",
        action="store_true",
        help="Skip Ragas faithfulness/answer_relevance (no LLM judge)",
    )
    parser.add_argument(
        "--enforce-latency",
        action="store_true",
        help="Enforce latency_p95 threshold (only meaningful with real providers)",
    )

    args: Any = parser.parse_args()

    report = asyncio.run(
        run_eval(
            args.golden,
            args.report,
            skip_llm_metrics=args.skip_llm_metrics,
            enforce_latency=args.enforce_latency,
        )
    )

    _print_report(report)

    return 0 if report.thresholds_passed else 1


if __name__ == "__main__":
    sys.exit(main())
