"""Layer 2 tool-selection scorer — pure, no LLM, no I/O."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, Field

# Same 10 tools registered on the LoanOps MCP server (Layer 1).
KNOWN_MCP_TOOLS: frozenset[str] = frozenset(
    {
        "search_sse_apis",
        "list_sse_apis",
        "call_sse_api",
        "search_docs",
        "search_capabilities",
        "explain_capability",
        "find_providers",
        "impact_of_change",
        "describe_application",
        "search_code",
    }
)


class ToolSelectionExpectation(BaseModel):
    """What Layer 2 expects of an observed tool-name list."""

    must_call_tools: list[str] = Field(default_factory=list)
    # Each inner list is an alternative "all of these" set. Pass if any set ⊆ observed.
    allowed_tool_sets: list[list[str]] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)


class ToolSelectionResult(BaseModel):
    passed: bool
    reasons: list[str] = Field(default_factory=list)
    observed: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    forbidden_hit: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)


def score_tool_selection(
    observed_tools: Sequence[str],
    expectation: ToolSelectionExpectation,
    *,
    known_tools: frozenset[str] = KNOWN_MCP_TOOLS,
) -> ToolSelectionResult:
    """Score which tools were chosen (order ignored).

    Rules:
    - Unknown names (not in known_tools) fail.
    - Any forbidden_tools hit fails.
    - If allowed_tool_sets is non-empty: pass when observed covers one full set
      (and still respects forbidden / unknown). must_call_tools is ignored for
      the required check when alternatives are provided.
    - Else if must_call_tools non-empty: every required name must appear at least once.
    - Else (no required, no alternatives): pass only if observed is empty
      (refusal / no-tool cases).
    """
    observed = [str(n) for n in observed_tools]
    observed_set = set(observed)
    reasons: list[str] = []

    unknown = sorted(n for n in observed_set if n not in known_tools)
    if unknown:
        reasons.append(f"unknown tools: {unknown}")

    forbidden = set(expectation.forbidden_tools)
    forbidden_hit = sorted(observed_set & forbidden)
    if forbidden_hit:
        reasons.append(f"forbidden tools called: {forbidden_hit}")

    missing_required: list[str] = []
    alts = expectation.allowed_tool_sets
    must = expectation.must_call_tools

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
                "no allowed_tool_set covered by observed tools "
                f"(sets={alts}, observed={sorted(observed_set)})"
            )
    elif must:
        missing_required = sorted(set(must) - observed_set)
        if missing_required:
            reasons.append(f"missing required tools: {missing_required}")
    else:
        # No tools expected (refusal / no-call).
        if observed_set:
            reasons.append(
                f"expected no tools on refusal/empty case, got {sorted(observed_set)}"
            )

    passed = len(reasons) == 0
    return ToolSelectionResult(
        passed=passed,
        reasons=reasons,
        observed=observed,
        missing_required=missing_required,
        forbidden_hit=forbidden_hit,
        unknown=unknown,
    )
