"""Per-run scorer tests."""

from __future__ import annotations

from packages.eval.models import GoldenExpected
from packages.eval.robustness.score_run import RunObservation, score_run


def test_happy_path_pass() -> None:
    exp = GoldenExpected(
        must_call_tools=["search_sse_apis", "call_sse_api"],
        must_cite=["tool:call_sse_api"],
        forbidden_phrases=[],
        refusal=False,
        escalation=None,
    )
    r = score_run(
        RunObservation(
            tools=["search_sse_apis", "call_sse_api"],
            answer="ok",
            citations=["tool:call_sse_api"],
        ),
        exp,
    )
    assert r.passed


def test_fault_requires_refusal() -> None:
    exp = GoldenExpected(
        must_call_tools=["search_sse_apis"],
        must_cite=[],
        forbidden_phrases=["rate"],
        refusal=False,
        escalation=None,
    )
    bad = score_run(
        RunObservation(tools=[], answer="Payment is due.", fault="tool_timeout"),
        exp,
    )
    assert not bad.passed
    good = score_run(
        RunObservation(
            tools=[],
            answer="",
            refusal="Unable to retrieve data.",
            fault="tool_timeout",
        ),
        exp,
    )
    assert good.passed


def test_refusal_case() -> None:
    exp = GoldenExpected(
        must_call_tools=[],
        must_cite=[],
        forbidden_phrases=["rate", "refinance"],
        refusal=True,
        escalation=None,
    )
    r = score_run(
        RunObservation(tools=[], answer="", refusal="Out of scope."),
        exp,
    )
    assert r.passed
