"""Layer 3 tool-argument scorer — pure, no LLM, no I/O."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from packages.eval.selection.score import KNOWN_MCP_TOOLS
from pydantic import BaseModel, Field

TypeName = Literal["str", "int", "bool", "dict", "list"]

_TYPE_MAP: dict[str, type] = {
    "str": str,
    "int": int,
    "bool": bool,
    "dict": dict,
    "list": list,
}


def _body_present(body: Any) -> bool:
    return body not in (None, "", {}, [])


def _get(args: Mapping[str, Any], key: str) -> tuple[bool, Any]:
    """Return (found, value). Supports dotted keys like ``path_params.loanId``."""
    if "." not in key:
        if key not in args:
            return False, None
        return True, args[key]
    cur: Any = args
    for part in key.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


class ObservedCall(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ArgConstraint(BaseModel):
    """Clauses that one observed call of ``tool`` must satisfy."""

    tool: str
    required_keys: list[str] = Field(default_factory=list)
    types: dict[str, TypeName] = Field(default_factory=dict)
    equals: dict[str, Any] = Field(default_factory=dict)
    contains: dict[str, str] = Field(default_factory=dict)
    forbid_keys: list[str] = Field(default_factory=list)
    # Nested equals under path_params (loanId, etc.).
    path_params_equals: dict[str, Any] = Field(default_factory=dict)


class ToolArgsExpectation(BaseModel):
    constraints: list[ArgConstraint] = Field(default_factory=list)


class ToolArgsResult(BaseModel):
    passed: bool
    reasons: list[str] = Field(default_factory=list)
    observed: list[ObservedCall] = Field(default_factory=list)


def _check_call_clauses(
    args: Mapping[str, Any],
    constraint: ArgConstraint,
    *,
    structural_only: bool,
) -> list[str]:
    """Return clause failure reasons for one call (empty = match)."""
    fails: list[str] = []

    for key in constraint.required_keys:
        found, val = _get(args, key)
        if not found or val is None:
            fails.append(f"missing required key {key!r}")

    for key, tname in constraint.types.items():
        found, val = _get(args, key)
        if not found or val is None:
            fails.append(f"type check missing key {key!r}")
            continue
        expected_type = _TYPE_MAP[tname]
        if not isinstance(val, expected_type):
            fails.append(
                f"key {key!r} expected {tname}, got {type(val).__name__}"
            )

    if not structural_only:
        for key, expected in constraint.equals.items():
            found, val = _get(args, key)
            if not found or val != expected:
                fails.append(f"equals {key!r}: expected {expected!r}, got {val!r}")

        for key, needle in constraint.contains.items():
            found, val = _get(args, key)
            if not found or not isinstance(val, str) or needle not in val:
                fails.append(f"contains {key!r}: {needle!r} not in {val!r}")

        for key, expected in constraint.path_params_equals.items():
            pp = args.get("path_params")
            if not isinstance(pp, Mapping) or pp.get(key) != expected:
                got = pp.get(key) if isinstance(pp, Mapping) else None
                fails.append(
                    f"path_params_equals {key!r}: expected {expected!r}, got {got!r}"
                )

    for key in constraint.forbid_keys:
        if key in args and _body_present(args[key]):
            fails.append(f"forbidden key {key!r} present")

    return fails


def _side_effect_call_sse(args: Mapping[str, Any]) -> list[str]:
    fails: list[str] = []
    if _body_present(args.get("body")):
        fails.append("call_sse_api body is not allowed")
    method = args.get("method")
    if method is not None and str(method).strip().upper() != "GET":
        fails.append(f"call_sse_api method must be GET, got {method!r}")
    return fails


def score_tool_args(
    observed_calls: Sequence[ObservedCall | Mapping[str, Any]],
    expectation: ToolArgsExpectation,
    *,
    known_tools: frozenset[str] = KNOWN_MCP_TOOLS,
    structural_only: bool = False,
) -> ToolArgsResult:
    """Score argument contents (not tool selection, order, or answer text).

    Each constraint must be satisfied by at least one observed call of that tool.
    Side-effect rules always apply to every ``call_sse_api`` call.
    When ``structural_only`` is True (live path), skip equals/contains/path_params_equals.
    """
    calls: list[ObservedCall] = []
    for raw in observed_calls:
        if isinstance(raw, ObservedCall):
            calls.append(raw)
        else:
            calls.append(
                ObservedCall(
                    name=str(raw["name"]),
                    args=dict(raw.get("args") or {}),
                )
            )

    reasons: list[str] = []

    unknown = sorted({c.name for c in calls if c.name not in known_tools})
    if unknown:
        reasons.append(f"unknown tools: {unknown}")

    for call in calls:
        if call.name == "call_sse_api":
            se = _side_effect_call_sse(call.args)
            if se:
                reasons.extend(f"{call.name}: {r}" for r in se)

    constraints = expectation.constraints
    if not constraints and not calls:
        return ToolArgsResult(passed=len(reasons) == 0, reasons=reasons, observed=calls)

    if not constraints and calls:
        reasons.append(
            f"expected no tool calls on refusal/empty case, got {[c.name for c in calls]}"
        )
        return ToolArgsResult(
            passed=False,
            reasons=reasons,
            observed=calls,
        )

    for constraint in constraints:
        candidates = [c for c in calls if c.name == constraint.tool]
        if not candidates:
            reasons.append(f"no call matching constraint for tool {constraint.tool!r}")
            continue
        matched = False
        candidate_fails: list[str] = []
        for cand in candidates:
            fails = _check_call_clauses(
                cand.args, constraint, structural_only=structural_only
            )
            if not fails:
                matched = True
                break
            candidate_fails.append("; ".join(fails))
        if not matched:
            reasons.append(
                f"constraint for {constraint.tool!r} unmatched: "
                + " | ".join(candidate_fails)
            )

    return ToolArgsResult(
        passed=len(reasons) == 0,
        reasons=reasons,
        observed=calls,
    )
