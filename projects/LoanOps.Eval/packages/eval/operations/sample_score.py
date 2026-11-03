"""Deterministic online scoring of sampled prod traces (no LLM judge)."""

from __future__ import annotations

from packages.common.providers.eval_store import TraceRecord
from pydantic import BaseModel, Field


class SampleScore(BaseModel):
    trace_id: str
    passed: bool
    reasons: list[str] = Field(default_factory=list)


def _looks_like_pii(text: str) -> bool:
    """Lightweight heuristic — prefer packages.safety when available."""
    try:
        from packages.safety import sanitize_inbound  # type: ignore[attr-defined]

        result = sanitize_inbound(text)
        # If sanitizer returns a different string, treat as PII hit.
        if isinstance(result, str) and result != text:
            return True
        if hasattr(result, "redacted") and getattr(result, "redacted"):
            return True
    except Exception:  # noqa: BLE001
        pass
    # Fallback patterns (synthetic only — no real PII in fixtures).
    lowered = text.lower()
    markers = ["ssn:", "social security", "password=", "api_key="]
    return any(m in lowered for m in markers)


def score_sampled_trace(tr: TraceRecord) -> SampleScore:
    reasons: list[str] = []
    blob = " ".join(
        [
            str(tr.input),
            str(tr.output),
            str(tr.attributes),
        ]
    )
    if _looks_like_pii(blob):
        reasons.append("possible PII/secrets in trace payload")
    if tr.is_error and tr.success:
        reasons.append("inconsistent success/is_error flags")
    # Structural: tool spans should name a tool.
    if tr.name == "mcp.tool.call" and not tr.attributes.get("tool"):
        reasons.append("mcp.tool.call missing tool attribute")
    return SampleScore(trace_id=tr.trace_id, passed=len(reasons) == 0, reasons=reasons)
