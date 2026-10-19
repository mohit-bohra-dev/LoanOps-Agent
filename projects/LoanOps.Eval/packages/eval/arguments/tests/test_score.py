"""Unit tests for Layer 3 ``score_tool_args``."""

from __future__ import annotations

from packages.eval.arguments.score import (
    ArgConstraint,
    ObservedCall,
    ToolArgsExpectation,
    score_tool_args,
)


def _call(name: str, **args: object) -> ObservedCall:
    return ObservedCall(name=name, args=dict(args))


def test_required_key_pass() -> None:
    r = score_tool_args(
        [_call("search_docs", query="escrow", top_k=5)],
        ToolArgsExpectation(
            constraints=[
                ArgConstraint(tool="search_docs", required_keys=["query"]),
            ]
        ),
    )
    assert r.passed


def test_missing_required_key_fails() -> None:
    r = score_tool_args(
        [_call("search_docs", top_k=5)],
        ToolArgsExpectation(
            constraints=[
                ArgConstraint(tool="search_docs", required_keys=["query"]),
            ]
        ),
    )
    assert not r.passed
    assert any("missing required key" in x for x in r.reasons)


def test_bad_type_fails() -> None:
    r = score_tool_args(
        [_call("search_docs", query=42)],
        ToolArgsExpectation(
            constraints=[
                ArgConstraint(
                    tool="search_docs",
                    required_keys=["query"],
                    types={"query": "str"},
                ),
            ]
        ),
    )
    assert not r.passed
    assert any("expected str" in x for x in r.reasons)


def test_wrong_loan_id_fails() -> None:
    r = score_tool_args(
        [
            _call(
                "call_sse_api",
                operation_id="getScheduledPayments",
                method="GET",
                path_params={"loanId": "999999"},
            )
        ],
        ToolArgsExpectation(
            constraints=[
                ArgConstraint(
                    tool="call_sse_api",
                    required_keys=["operation_id"],
                    equals={"method": "GET"},
                    path_params_equals={"loanId": "100245"},
                ),
            ]
        ),
    )
    assert not r.passed
    assert any("path_params_equals" in x for x in r.reasons)


def test_contains_pass() -> None:
    r = score_tool_args(
        [_call("search_sse_apis", query="escrow analysis for loan")],
        ToolArgsExpectation(
            constraints=[
                ArgConstraint(
                    tool="search_sse_apis",
                    required_keys=["query"],
                    contains={"query": "escrow"},
                ),
            ]
        ),
    )
    assert r.passed


def test_forbid_body_fails() -> None:
    r = score_tool_args(
        [
            _call(
                "call_sse_api",
                operation_id="x",
                method="GET",
                body={"amount": 1},
            )
        ],
        ToolArgsExpectation(
            constraints=[
                ArgConstraint(
                    tool="call_sse_api",
                    required_keys=["operation_id"],
                    forbid_keys=["body"],
                ),
            ]
        ),
    )
    assert not r.passed
    assert any("body" in x for x in r.reasons)


def test_post_method_side_effect_fails() -> None:
    r = score_tool_args(
        [
            _call(
                "call_sse_api",
                operation_id="x",
                method="POST",
            )
        ],
        ToolArgsExpectation(
            constraints=[
                ArgConstraint(tool="call_sse_api", required_keys=["operation_id"]),
            ]
        ),
    )
    assert not r.passed
    assert any("must be GET" in x for x in r.reasons)


def test_unknown_tool_fails() -> None:
    r = score_tool_args(
        [_call("invented_tool_xyz", query="x")],
        ToolArgsExpectation(
            constraints=[ArgConstraint(tool="invented_tool_xyz")],
        ),
    )
    assert not r.passed
    assert any("unknown tools" in x for x in r.reasons)


def test_refusal_empty_passes() -> None:
    r = score_tool_args([], ToolArgsExpectation(constraints=[]))
    assert r.passed


def test_refusal_with_calls_fails() -> None:
    r = score_tool_args(
        [_call("search_docs", query="x")],
        ToolArgsExpectation(constraints=[]),
    )
    assert not r.passed


def test_structural_only_skips_equals() -> None:
    r = score_tool_args(
        [
            _call(
                "call_sse_api",
                operation_id="getScheduledPayments",
                method="GET",
                path_params={"loanId": "999999"},
            )
        ],
        ToolArgsExpectation(
            constraints=[
                ArgConstraint(
                    tool="call_sse_api",
                    required_keys=["operation_id"],
                    equals={"method": "GET"},
                    path_params_equals={"loanId": "100245"},
                    forbid_keys=["body"],
                ),
            ]
        ),
        structural_only=True,
    )
    assert r.passed


def test_any_matching_call_satisfies_constraint() -> None:
    r = score_tool_args(
        [
            _call("call_sse_api", operation_id="wrong", method="GET"),
            _call(
                "call_sse_api",
                operation_id="getScheduledPayments",
                method="GET",
                path_params={"loanId": "100245"},
            ),
        ],
        ToolArgsExpectation(
            constraints=[
                ArgConstraint(
                    tool="call_sse_api",
                    equals={"operation_id": "getScheduledPayments"},
                    path_params_equals={"loanId": "100245"},
                ),
            ]
        ),
    )
    assert r.passed
