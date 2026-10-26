"""Layer 4 trajectory scorer — pure, no LLM, no I/O.

Constraint-based path checks over ordered tool names. Not exact-sequence-only.
"""

from __future__ import annotations

from collections.abc import Sequence

from packages.eval.selection.score import KNOWN_MCP_TOOLS
from pydantic import BaseModel, Field


class TrajectoryExpectation(BaseModel):
    """What Layer 4 expects of an ordered tool-name list."""

    required_steps: list[str] = Field(default_factory=list)
    # Each pair (before, after): first before must precede first after.
    dependencies: list[list[str]] = Field(default_factory=list)
    forbidden_steps: list[str] = Field(default_factory=list)
    # Each inner list is an alternative "all of these" path. Pass if any set ⊆ observed.
    # When set, required_steps is unused for the presence check (deps/forbidden still apply).
    allowed_path_sets: list[list[str]] = Field(default_factory=list)


class TrajectoryResult(BaseModel):
    passed: bool
    reasons: list[str] = Field(default_factory=list)
    observed: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    forbidden_hit: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    dep_failures: list[str] = Field(default_factory=list)


def _first_index(observed: list[str], name: str) -> int | None:
    try:
        return observed.index(name)
    except ValueError:
        return None


def _check_dependencies(
    observed: list[str],
    dependencies: list[list[str]],
) -> list[str]:
    """Return human-readable dep failure strings."""
    fails: list[str] = []
    for dep in dependencies:
        if len(dep) != 2:
            fails.append(f"invalid dependency pair (need [before, after]): {dep}")
            continue
        before, after = dep[0], dep[1]
        after_i = _first_index(observed, after)
        if after_i is None:
            # after absent → dep not checked
            continue
        before_i = _first_index(observed, before)
        if before_i is None:
            fails.append(
                f"dependency {before!r} before {after!r}: "
                f"{after!r} present but {before!r} missing"
            )
        elif before_i >= after_i:
            fails.append(
                f"dependency {before!r} before {after!r}: "
                f"first {before!r} at {before_i}, first {after!r} at {after_i}"
            )
    return fails


def score_trajectory(
    observed_tools: Sequence[str],
    expectation: TrajectoryExpectation,
    *,
    known_tools: frozenset[str] = KNOWN_MCP_TOOLS,
) -> TrajectoryResult:
    """Score whether an ordered tool-name path is valid.

    Rules:
    - Unknown names (not in known_tools) fail.
    - Any forbidden_steps hit fails.
    - Dependencies: first before must precede first after (if after present).
    - If allowed_path_sets is non-empty: pass when observed covers one full set
      (required_steps unused for presence). Deps/forbidden still apply.
    - Else if required_steps non-empty: every required name must appear ≥1.
    - Else (no required, no alts): pass only if observed is empty (refusal).
    - Extras between/around required steps are allowed (no exact-sequence matcher).
    """
    observed = [str(n) for n in observed_tools]
    observed_set = set(observed)
    reasons: list[str] = []

    unknown = sorted(n for n in observed_set if n not in known_tools)
    if unknown:
        reasons.append(f"unknown tools: {unknown}")

    forbidden = set(expectation.forbidden_steps)
    forbidden_hit = sorted(observed_set & forbidden)
    if forbidden_hit:
        reasons.append(f"forbidden steps called: {forbidden_hit}")

    dep_failures = _check_dependencies(observed, expectation.dependencies)
    reasons.extend(dep_failures)

    missing_required: list[str] = []
    alts = expectation.allowed_path_sets
    must = expectation.required_steps

    if alts:
        covered = False
        for alt in alts:
            needed = set(alt)
            if needed and needed.issubset(observed_set):
                covered = True
                break
            if not needed and not observed_set:
                covered = True
                break
        if not covered:
            reasons.append(
                "no allowed_path_set covered by observed tools "
                f"(sets={alts}, observed={sorted(observed_set)})"
            )
    elif must:
        missing_required = sorted(set(must) - observed_set)
        if missing_required:
            reasons.append(f"missing required steps: {missing_required}")
    else:
        if observed_set:
            reasons.append(
                f"expected no tools on refusal/empty case, got {sorted(observed_set)}"
            )

    return TrajectoryResult(
        passed=len(reasons) == 0,
        reasons=reasons,
        observed=observed,
        missing_required=missing_required,
        forbidden_hit=forbidden_hit,
        unknown=unknown,
        dep_failures=dep_failures,
    )
