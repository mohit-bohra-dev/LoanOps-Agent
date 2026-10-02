"""Unit tests for eval metric computation functions.

Uses hand-crafted EvalItemResult objects — no providers needed.
"""

from __future__ import annotations

import pytest
from packages.common.schemas import AgentTurnOutput, CitationItem, EscalationItem
from packages.eval.metrics import (
    compute_citation_coverage,
    compute_cost_avg,
    compute_latency_p95,
    compute_refusal_correctness,
)
from packages.eval.models import EvalItemResult, GoldenExpected

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_result(
    *,
    golden_id: str = "t001",
    refusal_expected: bool = False,
    escalation_expected: str | None = None,
    must_cite: list[str] | None = None,
    answer: str = "Draft reply for borrower.",
    citations: list[CitationItem] | None = None,
    refusal: str | None = None,
    escalation: EscalationItem | None = None,
    latency_ms: float = 100.0,
    cost_usd: float = 0.01,
    error: str | None = None,
) -> EvalItemResult:
    """Build a test EvalItemResult with sane defaults."""
    output: AgentTurnOutput | None = None
    if error is None:
        output = AgentTurnOutput(
            answer=answer,
            citations=citations or [],
            tool_calls=[],
            requires_human_approval=True,
            confidence=0.9,
            refusal=refusal,
            escalation=escalation,
        )

    return EvalItemResult(
        golden_id=golden_id,
        rep_prompt="Test prompt",
        expected=GoldenExpected(
            refusal=refusal_expected,
            escalation=escalation_expected,
            must_cite=must_cite or [],
            must_call_tools=[],
            forbidden_phrases=[],
        ),
        output=output,
        error=error,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
    )


# ── citation_coverage ────────────────────────────────────────────────────


class TestCitationCoverage:
    """Tests for compute_citation_coverage."""

    def test_all_cited_returns_1(self) -> None:
        results = [
            _make_result(
                must_cite=["policy:escrow/annual-analysis.md"],
                citations=[
                    CitationItem(
                        id=1,
                        source="policy:escrow/annual-analysis.md#sec-2",
                        snippet="...",
                    )
                ],
            ),
        ]
        assert compute_citation_coverage(results) == 1.0

    def test_missing_citation_returns_less_than_1(self) -> None:
        results = [
            _make_result(
                must_cite=["policy:escrow/annual-analysis.md"],
                citations=[],  # No citations!
            ),
        ]
        assert compute_citation_coverage(results) == 0.0

    def test_refusal_items_excluded(self) -> None:
        """Refusal items should not count toward citation_coverage."""
        results = [
            _make_result(
                refusal_expected=True,
                answer="",
                refusal="Out of scope.",
                citations=[],
            ),
        ]
        # Vacuously true — no eligible items
        assert compute_citation_coverage(results) == 1.0

    def test_escalation_items_excluded(self) -> None:
        results = [
            _make_result(
                escalation_expected="safety",
                answer="",
                refusal="Escalating.",
                escalation=EscalationItem(category="safety", reason="Self-harm"),
                citations=[],
            ),
        ]
        assert compute_citation_coverage(results) == 1.0

    def test_mixed_pass_and_fail(self) -> None:
        results = [
            _make_result(
                golden_id="pass",
                must_cite=["tool:get_escrow_breakdown"],
                citations=[CitationItem(id=1, source="tool:get_escrow_breakdown", snippet="...")],
            ),
            _make_result(
                golden_id="fail",
                must_cite=["policy:payments/late-fee-waiver.md"],
                citations=[],  # Missing!
            ),
        ]
        assert compute_citation_coverage(results) == 0.5

    def test_empty_results(self) -> None:
        assert compute_citation_coverage([]) == 1.0

    def test_error_items_excluded(self) -> None:
        results = [_make_result(error="Agent failed")]
        assert compute_citation_coverage(results) == 1.0


# ── refusal_correctness ──────────────────────────────────────────────────


class TestRefusalCorrectness:
    """Tests for compute_refusal_correctness."""

    def test_correct_refusal(self) -> None:
        results = [
            _make_result(
                refusal_expected=True,
                answer="",
                refusal="Out of scope.",
            ),
        ]
        assert compute_refusal_correctness(results) == 1.0

    def test_missed_refusal(self) -> None:
        """Agent should have refused but answered instead."""
        results = [
            _make_result(
                refusal_expected=True,
                answer="Here is your rate...",
                refusal=None,  # Should have refused
            ),
        ]
        assert compute_refusal_correctness(results) == 0.0

    def test_false_refusal(self) -> None:
        """Agent refused but should not have."""
        results = [
            _make_result(
                refusal_expected=False,
                answer="",
                refusal="I cannot help.",  # Should not have refused
            ),
        ]
        assert compute_refusal_correctness(results) == 0.0

    def test_correct_escalation(self) -> None:
        results = [
            _make_result(
                escalation_expected="safety",
                answer="",
                refusal="Escalating.",
                escalation=EscalationItem(category="safety", reason="Self-harm"),
            ),
        ]
        assert compute_refusal_correctness(results) == 1.0

    def test_wrong_escalation_category(self) -> None:
        results = [
            _make_result(
                escalation_expected="safety",
                answer="",
                refusal="Escalating.",
                escalation=EscalationItem(category="fraud", reason="Wrong category"),
            ),
        ]
        assert compute_refusal_correctness(results) == 0.0

    def test_mixed_correct_and_incorrect(self) -> None:
        results = [
            _make_result(
                golden_id="correct",
                refusal_expected=True,
                answer="",
                refusal="Out of scope.",
            ),
            _make_result(
                golden_id="incorrect",
                refusal_expected=False,
                answer="",
                refusal="Should not have refused.",
            ),
        ]
        assert compute_refusal_correctness(results) == 0.5

    def test_empty_results(self) -> None:
        assert compute_refusal_correctness([]) == 1.0

    def test_happy_path_correct(self) -> None:
        """Non-refusal item correctly answered."""
        results = [
            _make_result(
                refusal_expected=False,
                answer="Here is the info.",
                refusal=None,
            ),
        ]
        assert compute_refusal_correctness(results) == 1.0


# ── latency_p95 ──────────────────────────────────────────────────────────


class TestLatencyP95:
    """Tests for compute_latency_p95."""

    def test_known_distribution(self) -> None:
        # 20 items: 1..20 ms. p95 = 19th item = 19.0
        results = [_make_result(latency_ms=float(i)) for i in range(1, 21)]
        assert compute_latency_p95(results) == 19.0

    def test_single_item(self) -> None:
        results = [_make_result(latency_ms=500.0)]
        assert compute_latency_p95(results) == 500.0

    def test_empty(self) -> None:
        assert compute_latency_p95([]) == 0.0

    def test_error_items_excluded(self) -> None:
        results = [_make_result(error="fail", latency_ms=9999.0)]
        assert compute_latency_p95(results) == 0.0


# ── cost_avg ─────────────────────────────────────────────────────────────


class TestCostAvg:
    """Tests for compute_cost_avg."""

    def test_average(self) -> None:
        results = [
            _make_result(cost_usd=0.01),
            _make_result(cost_usd=0.03),
        ]
        assert compute_cost_avg(results) == pytest.approx(0.02)

    def test_empty(self) -> None:
        assert compute_cost_avg([]) == 0.0

    def test_error_items_excluded(self) -> None:
        results = [_make_result(error="fail", cost_usd=99.0)]
        assert compute_cost_avg(results) == 0.0
