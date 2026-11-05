"""Taxonomy + promote + traces unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from packages.common.providers.eval_store import ReviewLabel
from packages.eval.governance.promote import promote_candidates
from packages.eval.taxonomy import FAILURE_CATEGORIES, FeedbackRequest
from packages.eval.traces import build_agent_trace, persist_agent_trace, load_agent_trace
from packages.common.schemas import ToolCallItem


def test_fail_requires_category() -> None:
    with pytest.raises(ValueError):
        FeedbackRequest(trace_id="t1", label="fail")


def test_fail_ok() -> None:
    body = FeedbackRequest(
        trace_id="t1",
        label="fail",
        primary_category="incorrect_answer",
        severity="major",
        root_component="generation",
    )
    tax = body.taxonomy()
    assert tax is not None
    assert tax.primary_category in FAILURE_CATEGORIES


def test_build_and_persist_trace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_STORE__JSONL_DIR", str(tmp_path))
    from packages.common.settings import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    tr = build_agent_trace(
        trace_id="abc",
        user_query="when is payment due?",
        answer="Nov 20",
        tool_calls=[
            ToolCallItem(name="call_sse_api", args={"operation_id": "x"}, result_summary="due: Nov 20")
        ],
    )
    path = persist_agent_trace(tr)
    assert path.is_file()
    loaded = load_agent_trace("abc")
    assert loaded is not None
    assert loaded.spans[0].tool == "call_sse_api"
    get_settings.cache_clear()  # type: ignore[attr-defined]


def test_promote_fail_writes_draft(tmp_path: Path) -> None:
    labels = [
        ReviewLabel(
            queue="loanops-error-analysis",
            trace_id="tr-1",
            item_id="tr-1",
            reviewer="qa",
            label="fail",
            rubric="outcome",
            rubric_version="1",
            comment="wrong date",
        )
    ]
    report = promote_candidates(
        labels,
        out_dir=tmp_path / "candidates",
        registry_draft=tmp_path / "registry.draft.jsonl",
        taxonomy_by_trace={
            "tr-1": {
                "primary_category": "incorrect_answer",
                "severity": "major",
                "root_component": "generation",
            }
        },
    )
    assert report.draft_registry_rows == 1
    assert (tmp_path / "candidates" / "tr-1.jsonl").is_file()
    row = (tmp_path / "registry.draft.jsonl").read_text(encoding="utf-8")
    assert '"status": "draft"' in row
    assert "approved" not in row.split("status")[1][:20]
