"""Unit tests for Layer 5 ``score_outcome``."""

from __future__ import annotations

from packages.eval.outcomes.score import (
    OutcomeExpectation,
    OutcomeObservation,
    ToolResultSnippet,
    score_outcome,
)


def _obs(**kwargs: object) -> OutcomeObservation:
    return OutcomeObservation(**kwargs)  # type: ignore[arg-type]


def test_facts_present_and_grounded_pass() -> None:
    r = score_outcome(
        _obs(
            answer="Next payments: 2026-11-01, 2026-12-01.",
            citations=["tool:call_sse_api"],
            tool_results=[
                ToolResultSnippet(
                    name="call_sse_api",
                    text="scheduled: 2026-11-01, 2026-12-01",
                )
            ],
        ),
        OutcomeExpectation(
            must_contain=["2026-11-01", "2026-12-01"],
            must_cite=["tool:call_sse_api"],
        ),
    )
    assert r.passed


def test_missing_fact_fails() -> None:
    r = score_outcome(
        _obs(
            answer="Next payment soon.",
            citations=["tool:call_sse_api"],
            tool_results=[
                ToolResultSnippet(name="call_sse_api", text="2026-11-01")
            ],
        ),
        OutcomeExpectation(
            must_contain=["2026-11-01"],
            must_cite=["tool:call_sse_api"],
        ),
    )
    assert not r.passed
    assert "2026-11-01" in r.missing_facts


def test_ungrounded_fact_fails() -> None:
    r = score_outcome(
        _obs(
            answer="Payment on 2026-11-01.",
            citations=["tool:call_sse_api"],
            tool_results=[
                ToolResultSnippet(name="call_sse_api", text="no dates here")
            ],
        ),
        OutcomeExpectation(
            must_contain=["2026-11-01"],
            must_cite=["tool:call_sse_api"],
        ),
    )
    assert not r.passed
    assert "2026-11-01" in r.ungrounded_facts


def test_citation_miss_fails() -> None:
    r = score_outcome(
        _obs(
            answer="Escrow rose $35.",
            citations=["tool:call_sse_api"],
            tool_results=[
                ToolResultSnippet(name="call_sse_api", text="increase $35")
            ],
        ),
        OutcomeExpectation(
            must_contain=["$35"],
            must_cite=["policy:escrow/annual-analysis.md", "tool:call_sse_api"],
        ),
    )
    assert not r.passed
    assert any("policy:escrow" in c for c in r.missing_cites)


def test_forbidden_phrase_fails() -> None:
    r = score_outcome(
        _obs(answer="The refinance rate is 6%.", citations=[]),
        OutcomeExpectation(
            refusal=True,
            forbidden_phrases=["rate", "refinance"],
        ),
    )
    # refusal expected but also forbidden in answer
    assert not r.passed
    assert "rate" in r.forbidden_hit or "refinance" in r.forbidden_hit


def test_refusal_pass() -> None:
    r = score_outcome(
        _obs(answer="", refusal="Out of scope."),
        OutcomeExpectation(
            refusal=True,
            forbidden_phrases=["rate", "refinance", "APR"],
        ),
    )
    assert r.passed


def test_refusal_missing_fails() -> None:
    r = score_outcome(
        _obs(answer="I cannot help with that.", refusal=None),
        OutcomeExpectation(refusal=True),
    )
    assert not r.passed
    assert any("refusal" in x for x in r.reasons)


def test_escalation_category_pass() -> None:
    r = score_outcome(
        _obs(
            answer="",
            refusal="Escalating per policy.",
            escalation="complaint_or_regulatory",
        ),
        OutcomeExpectation(
            escalation="complaint_or_regulatory",
            forbidden_phrases=["answer"],
        ),
    )
    assert r.passed


def test_escalation_wrong_category_fails() -> None:
    r = score_outcome(
        _obs(answer="", escalation="fraud"),
        OutcomeExpectation(escalation="complaint_or_regulatory"),
    )
    assert not r.passed
    assert any("escalation category" in x for x in r.reasons)


def test_structural_only_skips_facts() -> None:
    r = score_outcome(
        _obs(
            answer="Paraphrased without exact dates.",
            citations=["tool:call_sse_api"],
            tool_results=[],
        ),
        OutcomeExpectation(
            must_contain=["2026-11-01"],
            must_cite=["tool:call_sse_api"],
        ),
        structural_only=True,
    )
    assert r.passed


def test_happy_path_unexpected_refusal_fails() -> None:
    r = score_outcome(
        _obs(
            answer="Payment info.",
            citations=["tool:call_sse_api"],
            refusal="Out of scope.",
            tool_results=[
                ToolResultSnippet(name="call_sse_api", text="Payment info.")
            ],
        ),
        OutcomeExpectation(
            must_contain=["Payment info."],
            must_cite=["tool:call_sse_api"],
            refusal=False,
        ),
    )
    assert not r.passed
