"""Eval gate thresholds — do not lower without explicit approval.

These match Section A.4 of ``docs/01-servicing-agent-prompts.md``.
"""

from __future__ import annotations

from packages.eval.models import ThresholdBreach

# ── Threshold definitions ────────────────────────────────────────────────
# (metric_name, threshold_value, direction)
# direction: "gte" = actual must be >= threshold; "lte" = actual must be <= threshold
THRESHOLDS: dict[str, tuple[float, str]] = {
    "faithfulness": (0.85, "gte"),
    "answer_relevance": (0.85, "gte"),
    "citation_coverage": (1.0, "gte"),
    "refusal_correctness": (0.95, "gte"),
    "latency_p95_ms": (4000.0, "lte"),
}


def check_thresholds(
    metrics: dict[str, float],
    *,
    skip: set[str] | None = None,
) -> list[ThresholdBreach]:
    """Check metrics against thresholds, return list of breaches.

    Args:
        metrics: metric_name → actual_value.
        skip: metric names to skip (e.g. LLM metrics when offline).

    Returns:
        List of breaches. Empty = all passed.
    """
    skip_set = skip or set()
    breaches: list[ThresholdBreach] = []

    for metric_name, (threshold, direction) in THRESHOLDS.items():
        if metric_name in skip_set:
            continue
        actual = metrics.get(metric_name)
        if actual is None:
            continue

        failed = (direction == "gte" and actual < threshold) or (
            direction == "lte" and actual > threshold
        )

        if failed:
            breaches.append(
                ThresholdBreach(
                    metric=metric_name,
                    threshold=threshold,
                    actual=actual,
                    direction=direction,
                )
            )

    return breaches
