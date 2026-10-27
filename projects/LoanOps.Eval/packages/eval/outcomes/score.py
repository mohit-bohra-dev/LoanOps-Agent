"""Layer 5 outcome scorer — pure, no LLM, no I/O.

Deterministic checks: facts in answer + tool text, citations, forbidden phrases,
refusal / escalation. Not tool selection, args, or call order.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field


class ToolResultSnippet(BaseModel):
    name: str
    text: str = ""


class OutcomeObservation(BaseModel):
    """What the agent produced for one case."""

    answer: str = ""
    citations: list[str] = Field(default_factory=list)
    tool_results: list[ToolResultSnippet] = Field(default_factory=list)
    refusal: str | None = None
    escalation: str | None = None  # category string when set


class OutcomeExpectation(BaseModel):
    """What Layer 5 expects of an observation."""

    must_contain: list[str] = Field(default_factory=list)
    must_cite: list[str] = Field(default_factory=list)
    forbidden_phrases: list[str] = Field(default_factory=list)
    refusal: bool = False
    escalation: str | None = None


class OutcomeResult(BaseModel):
    passed: bool
    reasons: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    ungrounded_facts: list[str] = Field(default_factory=list)
    missing_cites: list[str] = Field(default_factory=list)
    forbidden_hit: list[str] = Field(default_factory=list)


def _cite_stem(mc: str) -> str:
    """must_cite stem before '#' (matches compute_citation_coverage)."""
    return mc.split("#")[0]


def _citation_matches(must_cite: str, sources: Sequence[str]) -> bool:
    stem = _cite_stem(must_cite)
    return any(cs.startswith(stem) for cs in sources)


def _tool_corpus(tool_results: Sequence[ToolResultSnippet]) -> str:
    return "\n".join(t.text for t in tool_results)


def score_outcome(
    observation: OutcomeObservation | dict[str, Any],
    expectation: OutcomeExpectation,
    *,
    structural_only: bool = False,
) -> OutcomeResult:
    """Score final answer against evidence.

    Rules:
    - Facts (must_contain): each appears in answer; each also appears in tool_results
      text (grounding). Skipped when structural_only or must_contain empty.
    - Citations: every must_cite prefix matches ≥1 citation source. Happy-path with
      non-empty must_cite also requires ≥1 citation.
    - Forbidden phrases: any substring in answer fails.
    - Refusal: refusal=true requires non-empty refusal string; facts not required.
    - Escalation: category must match; refusal text allowed; facts not required.
    """
    if isinstance(observation, dict):
        obs = OutcomeObservation(**observation)
    else:
        obs = observation

    reasons: list[str] = []
    missing_facts: list[str] = []
    ungrounded_facts: list[str] = []
    missing_cites: list[str] = []
    forbidden_hit: list[str] = []

    answer = obs.answer or ""
    is_refusal = expectation.refusal
    is_escalation = expectation.escalation is not None

    # Forbidden phrases always apply to answer text.
    for phrase in expectation.forbidden_phrases:
        if phrase and phrase in answer:
            forbidden_hit.append(phrase)
    if forbidden_hit:
        reasons.append(f"forbidden phrases in answer: {forbidden_hit}")

    if is_escalation:
        expected_cat = expectation.escalation
        actual_cat = obs.escalation
        if actual_cat != expected_cat:
            reasons.append(
                f"escalation category: expected {expected_cat!r}, got {actual_cat!r}"
            )
        # Facts / citations not required on escalate path.
        return OutcomeResult(
            passed=len(reasons) == 0,
            reasons=reasons,
            missing_facts=[],
            ungrounded_facts=[],
            missing_cites=[],
            forbidden_hit=forbidden_hit,
        )

    if is_refusal:
        if not (obs.refusal and str(obs.refusal).strip()):
            reasons.append("expected refusal but refusal string missing/empty")
        # Facts / citations not required on refusal path.
        return OutcomeResult(
            passed=len(reasons) == 0,
            reasons=reasons,
            missing_facts=[],
            ungrounded_facts=[],
            missing_cites=[],
            forbidden_hit=forbidden_hit,
        )

    # Happy path: must not have refused or escalated unexpectedly.
    if obs.refusal is not None and str(obs.refusal).strip():
        reasons.append(f"unexpected refusal on happy-path: {obs.refusal!r}")
    if obs.escalation is not None:
        reasons.append(f"unexpected escalation on happy-path: {obs.escalation!r}")

    # Citations
    cites = list(obs.citations)
    for mc in expectation.must_cite:
        if not _citation_matches(mc, cites):
            missing_cites.append(mc)
    if missing_cites:
        reasons.append(f"missing citations: {missing_cites}")
    if expectation.must_cite and not cites:
        reasons.append("happy-path requires at least one citation when must_cite set")

    # Facts + grounding (skipped on live structural path)
    if not structural_only and expectation.must_contain:
        corpus = _tool_corpus(obs.tool_results)
        for fact in expectation.must_contain:
            if fact not in answer:
                missing_facts.append(fact)
            elif fact not in corpus:
                ungrounded_facts.append(fact)
        if missing_facts:
            reasons.append(f"missing facts in answer: {missing_facts}")
        if ungrounded_facts:
            reasons.append(
                f"facts in answer but not in tool_results: {ungrounded_facts}"
            )

    return OutcomeResult(
        passed=len(reasons) == 0,
        reasons=reasons,
        missing_facts=missing_facts,
        ungrounded_facts=ungrounded_facts,
        missing_cites=missing_cites,
        forbidden_hit=forbidden_hit,
    )
