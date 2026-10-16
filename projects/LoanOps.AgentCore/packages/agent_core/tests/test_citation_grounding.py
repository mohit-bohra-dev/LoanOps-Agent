"""Tests for citation grounding (doc-graphrag P1)."""

from __future__ import annotations

import json

from packages.agent_core._citation_grounding import (
    GroundingReport,
    extract_paths_and_texts,
    ground_citations,
    policy_citation_grounded,
)
from packages.agent_core._output_parser import parse_agent_output
from packages.common.schemas import ToolCallItem


def _search_docs_summary() -> str:
    return (
        "- [sop] hardship/forbearance.md (score=0.910)\n"
        "  Forbearance may pause payments for eligible hardship.\n"
        "- [sop] hardship/disaster-forbearance.md (score=0.880)\n"
        "  Disaster forbearance applies after a declared disaster."
    )


def test_extract_paths_from_search_docs() -> None:
    tools = [ToolCallItem(name="search_docs", args={"query": "x"}, result_summary=_search_docs_summary())]
    paths, texts = extract_paths_and_texts(tools)
    assert "hardship/forbearance.md" in paths
    assert "hardship/disaster-forbearance.md" in paths
    assert texts


def test_search_docs_prefixed_as_tool_not_policy() -> None:
    raw = json.dumps(
        {
            "answer": "ok",
            "citations": [{"source": "search_docs", "snippet": "hit"}],
            "confidence": 0.9,
            "requires_human_approval": True,
        }
    )
    out = parse_agent_output(raw)
    assert out.citations[0].source == "tool:search_docs"


def test_ground_drops_ungrounded_policy_when_tools_ran() -> None:
    data: dict = {
        "citations": [
            {"id": 1, "source": "policy:hardship/forbearance.md", "snippet": "Forbearance may pause"},
            {"id": 2, "source": "policy:made-up/nope.md", "snippet": "invented"},
            {"id": 3, "source": "tool:search_docs", "snippet": "ok"},
        ]
    }
    tools = [ToolCallItem(name="search_docs", args={}, result_summary=_search_docs_summary())]
    report = ground_citations(data, tools)
    sources = {c["source"] for c in data["citations"]}
    assert "policy:hardship/forbearance.md" in sources
    assert "policy:made-up/nope.md" not in sources
    assert "tool:search_docs" in sources
    assert report.dropped_ungrounded == 1
    assert isinstance(report, GroundingReport)


def test_ground_skips_when_no_recorded_tools() -> None:
    data: dict = {
        "citations": [
            {"id": 1, "source": "policy:escrow/annual-analysis.md", "snippet": "Annual"},
        ]
    }
    report = ground_citations(data, None)
    assert len(data["citations"]) == 1
    assert report.dropped_ungrounded == 0


def test_ground_drops_bad_snippet() -> None:
    data: dict = {
        "citations": [
            {
                "id": 1,
                "source": "policy:hardship/forbearance.md",
                "snippet": "this snippet is not in the tool result at all",
            },
        ]
    }
    tools = [ToolCallItem(name="search_docs", args={}, result_summary=_search_docs_summary())]
    report = ground_citations(data, tools)
    assert data["citations"] == []
    assert report.dropped_bad_snippet == 1


def test_policy_citation_grounded_fragment() -> None:
    paths = {"hardship/forbearance.md"}
    assert policy_citation_grounded("policy:hardship/forbearance.md#sec-1", paths)
