"""Pydantic models for the eval harness data pipeline.

These models flow through: golden.jsonl → runner → metrics → report → JSON.
"""

from __future__ import annotations

from packages.common.schemas import AgentTurnOutput
from pydantic import BaseModel, Field


class GoldenExpected(BaseModel):
    """Expected outcome for a golden item."""

    refusal: bool = False
    escalation: str | None = None
    must_cite: list[str] = Field(default_factory=list)
    must_call_tools: list[str] = Field(default_factory=list)
    forbidden_phrases: list[str] = Field(default_factory=list)


class GoldenItem(BaseModel):
    """Single golden Q&A item loaded from ``data/golden.jsonl``."""

    id: str
    rep_prompt: str
    loan_id: str
    expected: GoldenExpected


class EvalItemResult(BaseModel):
    """Per-item evaluation result — golden input + agent output + timing."""

    golden_id: str
    rep_prompt: str
    expected: GoldenExpected
    output: AgentTurnOutput | None = None
    error: str | None = None
    latency_ms: float = 0.0
    cost_usd: float = 0.0


class MetricValues(BaseModel):
    """Aggregated metric scores across all items."""

    faithfulness: float | None = None
    answer_relevance: float | None = None
    citation_coverage: float = 0.0
    refusal_correctness: float = 0.0
    latency_p95_ms: float = 0.0
    cost_avg_usd: float = 0.0
    total_items: int = 0
    error_count: int = 0


class ThresholdBreach(BaseModel):
    """A single threshold violation."""

    metric: str
    threshold: float
    actual: float
    direction: str  # "gte" or "lte"


class EvalReport(BaseModel):
    """Full eval report — written to ``out/eval.json``."""

    metrics: MetricValues
    thresholds_passed: bool = False
    breaches: list[ThresholdBreach] = Field(default_factory=list)
    skipped_metrics: list[str] = Field(default_factory=list)
    items: list[EvalItemResult] = Field(default_factory=list)
