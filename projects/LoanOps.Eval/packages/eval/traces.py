"""Canonical AgentTrace envelope for Observe / feedback."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from packages.common.schemas import CitationItem, EscalationItem, ToolCallItem
from packages.common.settings import get_settings
from pydantic import BaseModel, Field

SpanKind = Literal["turn", "llm", "tool", "subtool", "safety", "validator"]
TraceStatus = Literal["ok", "refused", "escalated", "error"]


class TraceSpan(BaseModel):
    span_id: str
    parent_span_id: str | None = None
    name: str
    kind: SpanKind = "tool"
    tool: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    result: str | None = None
    result_summary: str | None = None
    start_offset_ms: float = 0.0
    latency_ms: float = 0.0
    is_error: bool = False
    error_message: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    token_usage: dict[str, int] = Field(default_factory=dict)
    model: str | None = None


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
    timestamp: str = ""
    confidence: float | None = None
    model: str | None = None
    rounds_used: int = 0
    validation_retries: int = 0
    status: TraceStatus = "ok"
    error: str | None = None


_DOC_HIT_RE = re.compile(
    r"^- \[[^\]]+\]\s+(\S+)\s+\(score=([0-9.]+)\)",
    re.MULTILINE,
)

_SPAN_KINDS: frozenset[str] = frozenset(
    {"turn", "llm", "tool", "subtool", "safety", "validator"}
)


def _as_span_kind(value: str) -> SpanKind:
    if value in _SPAN_KINDS:
        return value  # type: ignore[return-value]
    return "subtool"


def _tool_spans_from_calls(
    trace_id: str,
    tool_calls: list[ToolCallItem] | None,
    parent_span_id: str | None,
) -> list[TraceSpan]:
    spans: list[TraceSpan] = []
    for i, tc in enumerate(tool_calls or []):
        spans.append(
            TraceSpan(
                span_id=f"{trace_id}-tool-{i}",
                parent_span_id=parent_span_id,
                name="mcp.tool.call",
                kind="tool",
                tool=tc.name,
                args=dict(tc.args),
                result_summary=tc.result_summary,
                result=tc.result_summary,
                latency_ms=float(getattr(tc, "latency_ms", 0.0) or 0.0),
                is_error=bool(getattr(tc, "is_error", False))
                or (
                    tc.result_summary.lower().startswith("error")
                    if tc.result_summary
                    else False
                ),
                attributes=dict(getattr(tc, "attributes", {}) or {}),
            )
        )
    return spans


def _spans_from_buffer(trace_id: str) -> list[TraceSpan]:
    try:
        from packages.common.providers.telemetry import drain_trace_spans

        buffered = drain_trace_spans(trace_id)
        if not buffered:
            # Langfuse may mint a different id; drain whatever is left.
            buffered = drain_trace_spans()
    except Exception:  # noqa: BLE001
        return []
    out: list[TraceSpan] = []
    for b in buffered:
        args: dict[str, Any] = {}
        if isinstance(b.input, dict):
            args = dict(b.input)
        result = None
        if isinstance(b.output, str):
            result = b.output
        elif b.output is not None:
            try:
                result = json.dumps(b.output, default=str)[:4000]
            except Exception:  # noqa: BLE001
                result = str(b.output)[:4000]
        out.append(
            TraceSpan(
                span_id=b.span_id,
                parent_span_id=b.parent_span_id,
                name=b.name,
                kind=_as_span_kind(b.kind),
                tool=b.tool,
                args=args,
                result=result,
                result_summary=result[:500] if result else None,
                start_offset_ms=b.start_offset_ms,
                latency_ms=b.latency_ms,
                is_error=b.is_error,
                error_message=b.error_message,
                attributes=dict(b.attributes),
                token_usage=dict(b.usage),
                model=b.model,
            )
        )
    return out


def _pipeline_from_spans_and_tools(
    spans: list[TraceSpan],
    tool_calls: list[ToolCallItem] | None,
) -> PipelineHits:
    hits = PipelineHits()
    for span in spans:
        name = span.name
        attrs = span.attributes or {}
        if name == "docs.vector_search" or name == "docs.rerank":
            for row in attrs.get("hits") or []:
                if isinstance(row, dict):
                    hits.docs.append(row)
        elif name == "api_index.search":
            for row in attrs.get("hits") or []:
                if isinstance(row, dict):
                    hits.api_index.append(row)
        elif name.startswith("eakg."):
            hits.eakg.append(
                {
                    "operation": attrs.get("operation") or name,
                    "binding_count": attrs.get("binding_count"),
                    "is_error": span.is_error,
                }
            )
    # Fallback: parse search_docs markdown when spans lacked structured hits.
    if not hits.docs:
        for tc in tool_calls or []:
            if tc.name != "search_docs":
                continue
            for m in _DOC_HIT_RE.finditer(tc.result_summary or ""):
                try:
                    hits.docs.append(
                        {"path": m.group(1), "score": float(m.group(2))}
                    )
                except Exception:  # noqa: BLE001
                    continue
    return hits


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
    token_usage: dict[str, int] | None = None,
    confidence: float | None = None,
    model: str | None = None,
    rounds_used: int = 0,
    validation_retries: int = 0,
    status: TraceStatus = "ok",
    error: str | None = None,
    spans: list[TraceSpan] | None = None,
) -> AgentTrace:
    """Build a trace from turn output fields + buffered telemetry spans."""
    buffered = spans if spans is not None else _spans_from_buffer(trace_id)
    if buffered:
        final_spans = buffered
    else:
        final_spans = _tool_spans_from_calls(trace_id, tool_calls, parent_span_id)

    usage = dict(token_usage or {})
    if not usage:
        prompt = 0
        completion = 0
        for s in final_spans:
            prompt += int(s.token_usage.get("prompt_tokens") or s.token_usage.get("prompt") or 0)
            completion += int(
                s.token_usage.get("completion_tokens") or s.token_usage.get("completion") or 0
            )
        if prompt or completion:
            usage = {
                "prompt": prompt,
                "completion": completion,
                "total": prompt + completion,
                "prompt_tokens": prompt,
                "completion_tokens": completion,
            }

    resolved_model = model
    if not resolved_model:
        for s in final_spans:
            if s.model:
                resolved_model = s.model
                break

    llm_rounds = {s.attributes.get("round_idx") for s in final_spans if s.kind == "llm"}
    llm_rounds.discard(None)
    resolved_rounds = rounds_used or len(llm_rounds)
    val_retries = validation_retries or max(
        0,
        len([s for s in final_spans if s.kind == "validator"]) - 1,
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
        spans=final_spans,
        pipeline_hits=_pipeline_from_spans_and_tools(final_spans, tool_calls),
        latency_ms=latency_ms,
        token_usage=usage,
        timestamp=datetime.now(UTC).isoformat(),
        confidence=confidence,
        model=resolved_model,
        rounds_used=resolved_rounds,
        validation_retries=max(0, val_retries),
        status=status,
        error=error,
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
