"""Eval improvement platform APIs — feedback, traces, health, promote."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from packages.common.providers.eval_store import ReviewLabel
from packages.common.providers.factory import get_eval_store_provider
from packages.common.settings import get_settings
from packages.eval.governance.promote import promote_candidates
from packages.eval.taxonomy import FeedbackRequest, is_promotable_label
from packages.eval.traces import list_agent_traces, load_agent_trace, load_review_records
from pydantic import BaseModel, Field

router = APIRouter(prefix="/eval", tags=["eval"])


class FeedbackResponse(BaseModel):
    ok: bool = True
    queue: str
    trace_id: str


class PromoteBody(BaseModel):
    trace_id: str
    reviewer: str = "anonymous"
    queue: str = "loanops-error-analysis"


class PromoteResponse(BaseModel):
    ok: bool = True
    written: list[str] = Field(default_factory=list)
    draft_registry_rows: int = 0


class HealthResponse(BaseModel):
    layers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    ops_separate: bool = True
    review_coverage_7d: float | None = None
    release_gate: dict[str, Any] = Field(default_factory=dict)


class MatrixRow(BaseModel):
    trace_id: str
    user_query: str
    final_answer: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    spans: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: float = 0.0
    token_usage: dict[str, int] = Field(default_factory=dict)
    pipeline_hits: dict[str, Any] = Field(default_factory=dict)
    model: str | None = None
    rounds_used: int = 0
    validation_retries: int = 0
    confidence: float | None = None
    status: str | None = None
    model_critique: str | None = None
    model_outcome: str | None = None
    human_critique: str | None = None
    human_outcome: str | None = None
    alignment: int | None = None
    primary_category: str | None = None
    severity: str | None = None
    root_component: str | None = None
    department: str | None = None
    recommended_action: str | None = None
    suggested_answer: str | None = None
    flags: list[str] = Field(default_factory=list)
    span_refs: list[str] = Field(default_factory=list)
    reviewer: str | None = None
    promoted_draft: bool = False
    agent_version: str = "agent v1.4"
    mcp_version: str = "mcp v1.2"
    loan_id: str | None = None


class MatrixResponse(BaseModel):
    rows: list[MatrixRow] = Field(default_factory=list)
    agreement_rate: float = 0.0
    total_reviewed: int = 0


def _label_to_outcome(label: str | None) -> str | None:
    if not label:
        return None
    lab = label.lower().strip()
    if lab in {"pass", "good", "approve", "approved"}:
        return "good"
    if lab in {"fail", "bad", "incorrect"}:
        return "bad"
    if lab in {"needs_review", "review"}:
        return "needs_review"
    return None


def _compute_alignment(model_outcome: str | None, human_outcome: str | None) -> int | None:
    if not model_outcome or not human_outcome:
        return None
    if model_outcome == "needs_review" or human_outcome == "needs_review":
        return None
    return 1 if model_outcome == human_outcome else 0


def _latest_review_by_trace(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in records:
        tid = str(row.get("trace_id") or "")
        if not tid:
            continue
        latest[tid] = row  # last write wins (append-only log)
    return latest


def _promoted_trace_ids() -> set[str]:
    root = Path("data/eval/candidates")
    if not root.is_dir():
        return set()
    ids: set[str] = set()
    for path in root.glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            tid = row.get("source_trace_id") or row.get("id")
            if tid:
                ids.add(str(tid))
    return ids


def _load_layer_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"passed": None, "missing": True}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"passed": None, "error": "unreadable"}
    passed = data.get("thresholds_passed")
    if passed is None and "suites" in data:
        # L1-style
        suites = data.get("suites") or {}
        passed = all(bool(s.get("passed", True)) for s in suites.values()) if suites else None
    return {
        "passed": passed,
        "at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
        "path": str(path),
    }


@router.post("/feedback", response_model=FeedbackResponse)
async def post_feedback(body: FeedbackRequest) -> FeedbackResponse:
    """Record human review + taxonomy; enqueue for annotation."""
    try:
        tax = body.taxonomy()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    store = get_eval_store_provider()
    await store.enqueue_review(body.queue, body.trace_id)
    label = ReviewLabel(
        queue=body.queue,
        trace_id=body.trace_id,
        item_id=body.trace_id,
        reviewer=body.reviewer,
        label=body.label,
        rubric=body.rubric,
        rubric_version=body.rubric_version,
        comment=body.comment,
        created_at=datetime.now(timezone.utc),
    )
    # Persist via seed helper path (labels jsonl)
    seed = getattr(store, "seed_review_labels", None)
    if callable(seed):
        await seed([label])
    else:
        # Fallback: comment-only enqueue already done
        pass

    from packages.eval.traces import append_review_record

    record: dict[str, Any] = label.model_dump(mode="json")
    if tax is not None:
        record["taxonomy"] = tax.model_dump()
    if body.model_critique is not None:
        record["model_critique"] = body.model_critique
    if body.model_outcome is not None:
        record["model_outcome"] = body.model_outcome
    if body.suggested_answer is not None:
        record["suggested_answer"] = body.suggested_answer
    if body.recommended_action is not None:
        record["recommended_action"] = body.recommended_action
    if body.flags:
        record["flags"] = list(body.flags)
    append_review_record(record)
    await store.flush()
    return FeedbackResponse(ok=True, queue=body.queue, trace_id=body.trace_id)


@router.get("/matrix", response_model=MatrixResponse)
async def get_matrix(limit: int = 100) -> MatrixResponse:
    """Join AgentTraces with latest human reviews for the spreadsheet matrix."""
    traces = list_agent_traces(limit=limit)
    reviews = _latest_review_by_trace(load_review_records())
    promoted = _promoted_trace_ids()
    rows: list[MatrixRow] = []
    aligned = 0
    compared = 0
    for tr in traces:
        rev = reviews.get(tr.trace_id) or {}
        tax = rev.get("taxonomy") if isinstance(rev.get("taxonomy"), dict) else {}
        model_outcome = rev.get("model_outcome")
        human_outcome = _label_to_outcome(str(rev.get("label")) if rev.get("label") else None)
        alignment = _compute_alignment(
            str(model_outcome) if model_outcome else None,
            human_outcome,
        )
        if alignment is not None:
            compared += 1
            aligned += alignment
        rows.append(
            MatrixRow(
                trace_id=tr.trace_id,
                user_query=tr.user_query,
                final_answer=tr.final_answer,
                citations=[c.model_dump(mode="json") for c in tr.citations],
                spans=[s.model_dump(mode="json") for s in tr.spans],
                latency_ms=tr.latency_ms,
                token_usage=dict(tr.token_usage),
                pipeline_hits=tr.pipeline_hits.model_dump(mode="json"),
                model=tr.model,
                rounds_used=tr.rounds_used,
                validation_retries=tr.validation_retries,
                confidence=tr.confidence,
                status=tr.status,
                model_critique=rev.get("model_critique"),
                model_outcome=str(model_outcome) if model_outcome else None,
                human_critique=rev.get("comment"),
                human_outcome=human_outcome,
                alignment=alignment,
                primary_category=tax.get("primary_category") or rev.get("primary_category"),
                severity=tax.get("severity") or rev.get("severity"),
                root_component=tax.get("root_component") or rev.get("root_component"),
                department=tax.get("department") or rev.get("department"),
                recommended_action=rev.get("recommended_action"),
                suggested_answer=rev.get("suggested_answer"),
                flags=list(rev.get("flags") or tax.get("flags") or []),
                span_refs=list(tax.get("span_refs") or rev.get("span_refs") or []),
                reviewer=rev.get("reviewer"),
                promoted_draft=tr.trace_id in promoted,
            )
        )
    rate = (aligned / compared) if compared else 0.0
    return MatrixResponse(rows=rows, agreement_rate=round(rate, 4), total_reviewed=compared)


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str) -> dict[str, Any]:
    """Load persisted AgentTrace (local jsonl/eval_store)."""
    trace = load_agent_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="trace not found")
    settings = get_settings()
    host = getattr(settings.telemetry.langfuse, "host", None) if hasattr(settings, "telemetry") else None
    payload = trace.model_dump(mode="json")
    if host:
        payload["langfuse_url"] = f"{host.rstrip('/')}/trace/{trace_id}"
    return payload


@router.get("/health", response_model=HealthResponse)
async def eval_health() -> HealthResponse:
    """Layer health from out/eval-*.json — offline only (ops separate)."""
    out = Path("out")
    mapping = {
        "1": out / "eval-mcp-l1.json",
        "2": out / "eval-l2.json",
        "3": out / "eval-l3.json",
        "4": out / "eval-l4.json",
        "5": out / "eval-l5.json",
        "6": out / "eval-l6.json",
        "7": out / "eval-l7.json",
        "8": out / "eval-l8.json",
        "9": out / "eval-l9.json",
        "golden": out / "eval.json",
    }
    layers = {k: _load_layer_report(p) for k, p in mapping.items()}
    reasons: list[str] = []
    for k, info in layers.items():
        if info.get("missing"):
            continue
        if info.get("passed") is False:
            reasons.append(f"layer {k} failed")
    return HealthResponse(
        layers=layers,
        ops_separate=True,
        review_coverage_7d=None,
        release_gate={"ready": len(reasons) == 0 and any(not v.get("missing") for v in layers.values()), "reasons": reasons},
    )


@router.post("/promote", response_model=PromoteResponse)
async def post_promote(body: PromoteBody) -> PromoteResponse:
    """Promote reviews for a trace into draft golden candidates (never approved)."""
    store = get_eval_store_provider()
    labels = await store.fetch_review_labels(body.queue)
    matched = [lab for lab in labels if lab.trace_id == body.trace_id]
    if not matched:
        # Also scan data/eval/reviews.jsonl
        path = Path("data/eval/reviews.jsonl")
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("trace_id") != body.trace_id:
                    continue
                matched.append(
                    ReviewLabel(
                        queue=row.get("queue") or body.queue,
                        trace_id=body.trace_id,
                        item_id=row.get("item_id") or body.trace_id,
                        reviewer=body.reviewer or row.get("reviewer") or "anonymous",
                        label=str(row.get("label") or "fail"),
                        rubric=row.get("rubric"),
                        rubric_version=row.get("rubric_version"),
                        comment=row.get("comment"),
                    )
                )
    promotable = [lab for lab in matched if is_promotable_label(lab.label)]
    if not promotable:
        raise HTTPException(status_code=404, detail="no promotable labels for trace")
    report = promote_candidates(
        promotable,
        out_dir=Path("data/eval/candidates"),
        registry_draft=Path("data/eval/registry.draft.jsonl"),
    )
    return PromoteResponse(
        ok=True,
        written=report.written,
        draft_registry_rows=report.draft_registry_rows,
    )
