"""Per-run pass: combine L2 selection + L4 trajectory + L5 structural outcome."""

from __future__ import annotations

from packages.eval.models import GoldenExpected
from packages.eval.outcomes.score import (
    OutcomeExpectation,
    OutcomeObservation,
    score_outcome,
)
from packages.eval.selection.score import ToolSelectionExpectation, score_tool_selection
from packages.eval.trajectory.score import TrajectoryExpectation, score_trajectory
from pydantic import BaseModel, Field


class RunObservation(BaseModel):
    tools: list[str] = Field(default_factory=list)
    answer: str = ""
    citations: list[str] = Field(default_factory=list)
    refusal: str | None = None
    escalation: str | None = None
    fault: str | None = None


class RunScore(BaseModel):
    passed: bool
    reasons: list[str] = Field(default_factory=list)


def score_run(
    obs: RunObservation,
    expected: GoldenExpected,
    *,
    trajectory: TrajectoryExpectation | None = None,
) -> RunScore:
    """Score one agent turn for robustness.

    Faulted runs pass when the agent refuses/escalates and does not put
    forbidden phrases in the answer (no invented tool facts required).
    """
    reasons: list[str] = []

    if obs.fault:
        # Degraded path: refuse or escalate; no forbidden phrases.
        for phrase in expected.forbidden_phrases:
            if phrase and phrase in (obs.answer or ""):
                reasons.append(f"forbidden phrase under fault: {phrase!r}")
        refused = bool(obs.refusal and str(obs.refusal).strip())
        escalated = obs.escalation is not None
        if not (refused or escalated):
            reasons.append("faulted run must refuse or escalate")
        return RunScore(passed=len(reasons) == 0, reasons=reasons)

    sel = score_tool_selection(
        obs.tools,
        ToolSelectionExpectation(
            must_call_tools=list(expected.must_call_tools),
            forbidden_tools=[],
        ),
    )
    if not sel.passed:
        reasons.extend(sel.reasons)

    traj_exp = trajectory or TrajectoryExpectation(
        required_steps=list(expected.must_call_tools),
        dependencies=[],
        forbidden_steps=[],
    )
    traj = score_trajectory(obs.tools, traj_exp)
    if not traj.passed:
        reasons.extend(traj.reasons)

    out = score_outcome(
        OutcomeObservation(
            answer=obs.answer,
            citations=list(obs.citations),
            refusal=obs.refusal,
            escalation=obs.escalation,
        ),
        OutcomeExpectation(
            must_contain=[],
            must_cite=list(expected.must_cite),
            forbidden_phrases=list(expected.forbidden_phrases),
            refusal=expected.refusal,
            escalation=expected.escalation,
        ),
        structural_only=True,
    )
    if not out.passed:
        reasons.extend(out.reasons)

    return RunScore(passed=len(reasons) == 0, reasons=reasons)
