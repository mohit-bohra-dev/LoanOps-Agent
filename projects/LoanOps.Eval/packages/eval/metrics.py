"""Metric computation functions for the eval harness.

All functions are pure — they take ``EvalItemResult`` lists and return floats.
No provider imports; no I/O.
"""

from __future__ import annotations

import math

from packages.eval.models import EvalItemResult


def compute_citation_coverage(results: list[EvalItemResult]) -> float:
    """Fraction of non-refusal/non-escalation items that have correct citations.

    An item passes citation_coverage if:
    - All ``must_cite`` sources appear in the agent's ``output.citations``
    - The agent produced at least one citation (for happy-path items)

    Items with ``expected.refusal=True`` or ``expected.escalation`` set are
    excluded from the denominator (they are not expected to cite).

    Returns 1.0 if all eligible items pass, 0.0 if none.
    Returns 1.0 if there are no eligible items (vacuously true).
    """
    eligible: list[EvalItemResult] = []
    for r in results:
        if r.output is None or r.error is not None:
            continue
        if r.expected.refusal or r.expected.escalation is not None:
            continue
        eligible.append(r)

    if not eligible:
        return 1.0

    passed = 0
    for r in eligible:
        assert r.output is not None  # noqa: S101 — guarded above
        citation_sources = {c.source for c in r.output.citations}
        must_cite = set(r.expected.must_cite)

        # Each must_cite entry must appear as a prefix in at least one citation source
        all_cited = all(
            any(cs.startswith(mc.split("#")[0]) for cs in citation_sources) for mc in must_cite
        )
        has_any = len(r.output.citations) > 0

        if all_cited and has_any:
            passed += 1

    return passed / len(eligible)


def compute_refusal_correctness(results: list[EvalItemResult]) -> float:
    """Accuracy of refusal and escalation classification.

    For each item:
    - If ``expected.refusal`` is True: agent must have set ``output.refusal``
    - If ``expected.refusal`` is False and no escalation: agent must NOT have set refusal
    - If ``expected.escalation`` is set: agent must have set ``output.escalation``
      with matching category
    - If ``expected.escalation`` is None: agent must NOT have set escalation

    Returns accuracy (correct / total evaluated items).
    """
    evaluated = 0
    correct = 0

    for r in results:
        if r.output is None or r.error is not None:
            continue

        evaluated += 1
        output = r.output

        # Check escalation correctness
        escalation_expected = r.expected.escalation
        escalation_actual_category = output.escalation.category if output.escalation else None
        escalation_ok = escalation_expected == escalation_actual_category

        # Check refusal correctness — but skip refusal check for escalation items,
        # because the agent always sets refusal="Escalating per policy" on those.
        if escalation_expected is not None:
            # For escalation items, only check escalation category match
            refusal_ok = True
        else:
            refusal_expected = r.expected.refusal
            refusal_actual = output.refusal is not None
            refusal_ok = refusal_expected == refusal_actual

        if refusal_ok and escalation_ok:
            correct += 1

    if evaluated == 0:
        return 1.0

    return correct / evaluated


def compute_latency_p95(results: list[EvalItemResult]) -> float:
    """95th percentile latency in milliseconds.

    Returns 0.0 if no valid results.
    """
    latencies = [r.latency_ms for r in results if r.output is not None]
    if not latencies:
        return 0.0

    latencies.sort()
    idx = math.ceil(0.95 * len(latencies)) - 1
    idx = max(0, min(idx, len(latencies) - 1))
    return latencies[idx]


def compute_cost_avg(results: list[EvalItemResult]) -> float:
    """Average cost per turn in USD. Informational — no gate threshold.

    Returns 0.0 if no valid results.
    """
    costs = [r.cost_usd for r in results if r.output is not None]
    if not costs:
        return 0.0
    return sum(costs) / len(costs)
