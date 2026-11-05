"""Canonical AgentTrace envelope for Observe / feedback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from packages.common.schemas import CitationItem, EscalationItem, ToolCallItem
from packages.common.settings import get_settings
from pydantic import BaseModel, Field


class TraceSpan(BaseModel):
    span_id: str
    parent_span_id: str | None = None
    name: str
    tool: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    result: str | None = None
    result_summary: str | None = None
    latency_ms: float = 0.0
    is_error: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)


class PipelineHits(BaseModel):
    eakg: list[dict[str, Any]] = Field(default_factory=list)
    api_index: list[dict[str, Any]] = Field(default_factory=list)
    docs: list[dict[str, Any]] = Field(default_factory=list)
    graph_rag: list[dict[str, Any]] = Field(default_factory=list)
    code: list[dict[str, Any]] = Field(default_factory=list)


class AgentTrace(BaseModel):
    trace_id: str
    environment: Literal["prod", "eval", "local"] = "local"
    session_id: str | None = None
    user_query: str
    final_answer: str = ""
    citations: list[CitationItem] = Field(default_factory=list)
    refusal: str | None = None
    escalation: EscalationItem | None = None
    spans: list[TraceSpan] = Field(default_factory=list)
    pipeline_hits: PipelineHits = Field(default_factory=PipelineHits)
    latency_ms: float = 0.0
    token_usage: dict[str, int] = Field(default_factory=dict)
    cost_usd: float | None = None


def build_agent_trace(
    *,
    trace_id: str,
    user_query: str,
    answer: str = "",
    citations: list[CitationItem] | None = None,
    tool_calls: list[ToolCallItem] | None = None,
    refusal: str | None = None,
    escalation: EscalationItem | None = None,
    environment: Literal["prod", "eval", "local"] = "local",
    session_id: str | None = None,
    parent_span_id: str | None = None,
    latency_ms: float = 0.0,
) -> AgentTrace:
    """Build a trace from turn output fields (tool calls → spans)."""
    spans: list[TraceSpan] = []
    for i, tc in enumerate(tool_calls or []):
        spans.append(
            TraceSpan(
                span_id=f"{trace_id}-tool-{i}",
                parent_span_id=parent_span_id,
                name="mcp.tool.call",
                tool=tc.name,
                args=dict(tc.args),
                result_summary=tc.result_summary,
                result=tc.result_summary,
                is_error=tc.result_summary.lower().startswith("error")
                if tc.result_summary
                else False,
            )
        )
    return AgentTrace(
        trace_id=trace_id,
        environment=environment,
        session_id=session_id,
        user_query=user_query,
        final_answer=answer,
        citations=list(citations or []),
        refusal=refusal,
        escalation=escalation,
        spans=spans,
        latency_ms=latency_ms,
    )


def _traces_dir() -> Path:
    settings = get_settings()
    root = Path(settings.eval_store.jsonl_dir)
    path = root / "agent_traces"
    path.mkdir(parents=True, exist_ok=True)
    return path


def persist_agent_trace(trace: AgentTrace) -> Path:
    """Write full AgentTrace JSON for GET /eval/traces/{id} (local-first)."""
    path = _traces_dir() / f"{trace.trace_id}.json"
    path.write_text(trace.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_agent_trace(trace_id: str) -> AgentTrace | None:
    path = _traces_dir() / f"{trace_id}.json"
    if not path.is_file():
        return None
    return AgentTrace.model_validate_json(path.read_text(encoding="utf-8"))


def list_agent_traces(*, limit: int = 200) -> list[AgentTrace]:
    """Load recent AgentTrace JSON files (newest mtime first)."""
    root = _traces_dir()
    files = sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[AgentTrace] = []
    for path in files[:limit]:
        try:
            out.append(AgentTrace.model_validate_json(path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
    return out


def load_review_records() -> list[dict[str, Any]]:
    """Load all review rows from data/eval/reviews.jsonl (or eval_store fallback)."""
    repo_reviews = Path("data/eval/reviews.jsonl")
    settings = get_settings()
    path = repo_reviews if Path("data/eval").is_dir() else Path(settings.eval_store.jsonl_dir) / "reviews.jsonl"
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def append_review_record(record: dict[str, Any]) -> Path:
    """Append taxonomy-rich review to data/eval/reviews.jsonl when possible."""
    settings = get_settings()
    # Prefer repo data/eval when present; else eval_store dir.
    repo_reviews = Path("data/eval/reviews.jsonl")
    if Path("data/eval").is_dir():
        path = repo_reviews
    else:
        path = Path(settings.eval_store.jsonl_dir) / "reviews.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")
    return path
