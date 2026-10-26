"""Unit tests for Layer 4 ``score_trajectory``."""

from __future__ import annotations

from packages.eval.trajectory.score import TrajectoryExpectation, score_trajectory


def test_required_steps_pass() -> None:
    r = score_trajectory(
        ["search_sse_apis", "call_sse_api"],
        TrajectoryExpectation(
            required_steps=["search_sse_apis", "call_sse_api"],
        ),
    )
    assert r.passed
    assert r.reasons == []


def test_required_missing_fails() -> None:
    r = score_trajectory(
        ["search_sse_apis"],
        TrajectoryExpectation(
            required_steps=["search_sse_apis", "call_sse_api"],
        ),
    )
    assert not r.passed
    assert "call_sse_api" in r.missing_required


def test_dependency_order_pass() -> None:
    r = score_trajectory(
        ["search_sse_apis", "search_docs", "call_sse_api"],
        TrajectoryExpectation(
            required_steps=["search_sse_apis", "call_sse_api"],
            dependencies=[["search_sse_apis", "call_sse_api"]],
        ),
    )
    assert r.passed


def test_dependency_violation_fails() -> None:
    r = score_trajectory(
        ["call_sse_api", "search_sse_apis"],
        TrajectoryExpectation(
            required_steps=["search_sse_apis", "call_sse_api"],
            dependencies=[["search_sse_apis", "call_sse_api"]],
        ),
    )
    assert not r.passed
    assert any("dependency" in x for x in r.reasons)
    assert r.dep_failures


def test_dependency_after_without_before_fails() -> None:
    r = score_trajectory(
        ["call_sse_api"],
        TrajectoryExpectation(
            required_steps=[],
            dependencies=[["search_sse_apis", "call_sse_api"]],
        ),
    )
    assert not r.passed
    assert any("missing" in x for x in r.dep_failures)


def test_dependency_not_checked_when_after_absent() -> None:
    r = score_trajectory(
        ["search_docs"],
        TrajectoryExpectation(
            required_steps=["search_docs"],
            dependencies=[["search_sse_apis", "call_sse_api"]],
        ),
    )
    assert r.passed
    assert r.dep_failures == []


def test_forbidden_fails() -> None:
    r = score_trajectory(
        ["search_sse_apis", "call_sse_api"],
        TrajectoryExpectation(
            required_steps=["search_sse_apis"],
            forbidden_steps=["call_sse_api"],
        ),
    )
    assert not r.passed
    assert "call_sse_api" in r.forbidden_hit


def test_unknown_tool_fails() -> None:
    r = score_trajectory(
        ["search_sse_apis", "invented_tool_xyz"],
        TrajectoryExpectation(required_steps=["search_sse_apis"]),
    )
    assert not r.passed
    assert "invented_tool_xyz" in r.unknown


def test_refusal_empty_passes() -> None:
    r = score_trajectory(
        [],
        TrajectoryExpectation(required_steps=[], allowed_path_sets=[]),
    )
    assert r.passed


def test_refusal_with_tools_fails() -> None:
    r = score_trajectory(
        ["search_docs"],
        TrajectoryExpectation(required_steps=[]),
    )
    assert not r.passed
    assert any("expected no tools" in x for x in r.reasons)


def test_allowed_path_sets_either_alt_passes() -> None:
    exp = TrajectoryExpectation(
        required_steps=["search_sse_apis"],  # ignored when alts present
        allowed_path_sets=[
            ["search_sse_apis", "call_sse_api"],
            ["search_docs"],
        ],
    )
    assert score_trajectory(["search_docs"], exp).passed
    assert score_trajectory(
        ["search_sse_apis", "call_sse_api", "list_sse_apis"], exp
    ).passed
    assert not score_trajectory(["search_sse_apis"], exp).passed


def test_extras_between_steps_ok() -> None:
    """Extras between required steps are allowed — not exact-sequence-only."""
    r = score_trajectory(
        ["search_sse_apis", "list_sse_apis", "search_docs", "call_sse_api"],
        TrajectoryExpectation(
            required_steps=["search_sse_apis", "call_sse_api"],
            dependencies=[["search_sse_apis", "call_sse_api"]],
        ),
    )
    assert r.passed


def test_docs_before_search_ok_when_dep_only_search_before_call() -> None:
    r = score_trajectory(
        ["search_docs", "search_sse_apis", "call_sse_api"],
        TrajectoryExpectation(
            required_steps=["search_sse_apis", "call_sse_api", "search_docs"],
            dependencies=[["search_sse_apis", "call_sse_api"]],
        ),
    )
    assert r.passed
