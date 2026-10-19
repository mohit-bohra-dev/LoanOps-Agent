"""Unit tests for Layer 2 ``score_tool_selection``."""

from __future__ import annotations

from packages.eval.selection.score import (
    ToolSelectionExpectation,
    score_tool_selection,
)


def test_required_pass() -> None:
    r = score_tool_selection(
        ["search_sse_apis", "call_sse_api", "search_docs"],
        ToolSelectionExpectation(
            must_call_tools=["search_sse_apis", "call_sse_api", "search_docs"]
        ),
    )
    assert r.passed
    assert r.reasons == []


def test_required_extras_ok() -> None:
    r = score_tool_selection(
        ["search_sse_apis", "call_sse_api", "search_docs", "list_sse_apis"],
        ToolSelectionExpectation(must_call_tools=["search_sse_apis", "call_sse_api"]),
    )
    assert r.passed


def test_required_missing_fails() -> None:
    r = score_tool_selection(
        ["search_sse_apis"],
        ToolSelectionExpectation(
            must_call_tools=["search_sse_apis", "call_sse_api"]
        ),
    )
    assert not r.passed
    assert "call_sse_api" in r.missing_required


def test_similar_tool_confusion_fails() -> None:
    """``search_capabilities`` is not a substitute for ``search_sse_apis``."""
    r = score_tool_selection(
        ["search_capabilities", "call_sse_api"],
        ToolSelectionExpectation(
            must_call_tools=["search_sse_apis", "call_sse_api"]
        ),
    )
    assert not r.passed
    assert "search_sse_apis" in r.missing_required


def test_allowed_tool_sets_either_alt_passes() -> None:
    exp = ToolSelectionExpectation(
        must_call_tools=["search_sse_apis"],  # ignored when alts present
        allowed_tool_sets=[
            ["search_sse_apis", "call_sse_api"],
            ["search_docs"],
        ],
    )
    assert score_tool_selection(["search_docs"], exp).passed
    assert score_tool_selection(
        ["search_sse_apis", "call_sse_api", "list_sse_apis"], exp
    ).passed
    assert not score_tool_selection(["search_sse_apis"], exp).passed


def test_forbidden_fails() -> None:
    r = score_tool_selection(
        ["search_sse_apis", "call_sse_api"],
        ToolSelectionExpectation(
            must_call_tools=["search_sse_apis"],
            forbidden_tools=["call_sse_api"],
        ),
    )
    assert not r.passed
    assert "call_sse_api" in r.forbidden_hit


def test_refusal_empty_passes() -> None:
    r = score_tool_selection(
        [],
        ToolSelectionExpectation(must_call_tools=[], allowed_tool_sets=[]),
    )
    assert r.passed


def test_refusal_with_tools_fails() -> None:
    r = score_tool_selection(
        ["search_docs"],
        ToolSelectionExpectation(must_call_tools=[]),
    )
    assert not r.passed
    assert any("expected no tools" in reason for reason in r.reasons)


def test_unknown_tool_fails() -> None:
    r = score_tool_selection(
        ["search_sse_apis", "invented_tool_xyz"],
        ToolSelectionExpectation(must_call_tools=["search_sse_apis"]),
    )
    assert not r.passed
    assert "invented_tool_xyz" in r.unknown


def test_order_ignored() -> None:
    r = score_tool_selection(
        ["search_docs", "call_sse_api", "search_sse_apis"],
        ToolSelectionExpectation(
            must_call_tools=["search_sse_apis", "call_sse_api", "search_docs"]
        ),
    )
    assert r.passed
