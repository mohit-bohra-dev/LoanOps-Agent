# packages/eval - Eval harness
#
# Runner:  python -m packages.eval.run --golden data/golden.jsonl --report out/eval.json
# Validate: python -m packages.eval.validate_data

from packages.eval.metrics import (
    compute_citation_coverage,
    compute_cost_avg,
    compute_latency_p95,
    compute_refusal_correctness,
)
from packages.eval.models import (
    EvalItemResult,
    EvalReport,
    GoldenExpected,
    GoldenItem,
    MetricValues,
    ThresholdBreach,
)
from packages.eval.run import run_eval
from packages.eval.thresholds import THRESHOLDS, check_thresholds

__all__ = [
    "THRESHOLDS",
    "EvalItemResult",
    "EvalReport",
    "GoldenExpected",
    "GoldenItem",
    "MetricValues",
    "ThresholdBreach",
    "check_thresholds",
    "compute_citation_coverage",
    "compute_cost_avg",
    "compute_latency_p95",
    "compute_refusal_correctness",
    "run_eval",
]
