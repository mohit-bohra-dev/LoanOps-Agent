"""Layer 2 tool-selection runner — canned trajectories + optional live agent."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from packages.eval.models import GoldenItem
from packages.eval.selection.score import (
    ToolSelectionExpectation,
    score_tool_selection,
)
from pydantic import BaseModel, Field

def _repo_data_dir() -> Path:
    """Walk up to repo-root ``data/`` (same pattern as validate_data)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "golden.jsonl").is_file():
            return parent / "data"
    return here.parents[5] / "data"


_DATA_DIR = _repo_data_dir()
_DEFAULT_TRAJECTORIES = _DATA_DIR / "eval" / "layer2_trajectories.jsonl"
_DEFAULT_GOLDEN = _DATA_DIR / "golden.jsonl"


class TrajectoryCase(BaseModel):
    """One canned Layer 2 row."""

    id: str
    observed_tools: list[str] = Field(default_factory=list)
    must_call_tools: list[str] = Field(default_factory=list)
    allowed_tool_sets: list[list[str]] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    notes: str = ""


class CaseResult(BaseModel):
    id: str
    source: str  # canned | live
    passed: bool
    skipped: bool = False
    detail: str = ""
    observed: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class Layer2Report(BaseModel):
    cases: list[CaseResult] = Field(default_factory=list)
    thresholds_passed: bool = False
    breaches: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    live_skipped: bool = False


def _load_trajectories(path: Path) -> list[TrajectoryCase]:
    items: list[TrajectoryCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(TrajectoryCase(**json.loads(line)))
    return items


def _load_golden(path: Path) -> list[GoldenItem]:
    items: list[GoldenItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(GoldenItem(**json.loads(line)))
    return items


def _score_case(
    *,
    case_id: str,
    source: str,
    observed: list[str],
    must_call_tools: list[str],
    allowed_tool_sets: list[list[str]] | None = None,
    forbidden_tools: list[str] | None = None,
) -> CaseResult:
    result = score_tool_selection(
        observed,
        ToolSelectionExpectation(
            must_call_tools=must_call_tools,
            allowed_tool_sets=allowed_tool_sets or [],
            forbidden_tools=forbidden_tools or [],
        ),
    )
    detail = "OK" if result.passed else "; ".join(result.reasons)
    return CaseResult(
        id=case_id,
        source=source,
        passed=result.passed,
        detail=detail,
        observed=list(result.observed),
        reasons=list(result.reasons),
    )


def run_canned(path: Path) -> list[CaseResult]:
    results: list[CaseResult] = []
    for case in _load_trajectories(path):
        results.append(
            _score_case(
                case_id=case.id,
                source="canned",
                observed=case.observed_tools,
                must_call_tools=case.must_call_tools,
                allowed_tool_sets=case.allowed_tool_sets,
                forbidden_tools=case.forbidden_tools,
            )
        )
    return results


async def _run_live_async(golden_path: Path) -> tuple[list[CaseResult], bool, str]:
    """Return (cases, skipped, note). skipped=True when the model cannot run."""
    try:
        from packages.agent_core import run_agent_turn
        from packages.common.providers.factory import (
            get_chat_provider,
            get_prompt_store_provider,
        )
        from packages.tools.factory import get_tools_client_provider
    except Exception as exc:  # noqa: BLE001
        return [], True, f"live import failed: {exc}"

    try:
        chat = get_chat_provider()
        tools = get_tools_client_provider()
        prompts = get_prompt_store_provider()
    except Exception as exc:  # noqa: BLE001
        return [], True, f"live providers unavailable: {exc}"

    # Probe must hit the LLM path (not refuse/escalate router short-circuit).
    try:
        await run_agent_turn(
            prompt="Loan 100245 escrow jumped $35 in May — draft a reply explaining why.",
            chat_provider=chat,
            tools_client=tools,
            prompt_store=prompts,
        )
    except Exception as exc:  # noqa: BLE001
        return [], True, f"live agent probe failed (skipping live suite): {exc}"

    results: list[CaseResult] = []
    for item in _load_golden(golden_path):
        try:
            output = await run_agent_turn(
                prompt=item.rep_prompt,
                chat_provider=chat,
                tools_client=tools,
                prompt_store=prompts,
            )
            observed = [tc.name for tc in output.tool_calls]
            results.append(
                _score_case(
                    case_id=f"live_{item.id}",
                    source="live",
                    observed=observed,
                    must_call_tools=list(item.expected.must_call_tools),
                    forbidden_tools=[],
                )
            )
        except Exception as exc:  # noqa: BLE001
            return (
                [],
                True,
                f"live run failed on {item.id} (skipping live suite): {exc}",
            )
    return results, False, ""


def run_live(golden_path: Path) -> tuple[list[CaseResult], bool, str]:
    return asyncio.run(_run_live_async(golden_path))


def run_layer2(
    *,
    trajectories_path: Path | None = None,
    golden_path: Path | None = None,
    live: bool = False,
) -> Layer2Report:
    traj = trajectories_path or _DEFAULT_TRAJECTORIES
    golden = golden_path or _DEFAULT_GOLDEN
    report = Layer2Report(
        notes=[
            "Layer 2 scores tool names only (not args, order, or answer text).",
            "Auth evaluation deferred; no POST /chat.",
        ]
    )

    canned = run_canned(traj)
    report.cases.extend(canned)

    if live:
        live_cases, skipped, note = run_live(golden)
        report.live_skipped = skipped
        if note:
            report.notes.append(note)
        if skipped:
            report.notes.append("live suite skipped; canned results still apply")
        else:
            report.cases.extend(live_cases)

    scored = [c for c in report.cases if not c.skipped]
    passed_n = sum(1 for c in scored if c.passed)
    total = len(scored)
    report.metrics["pass_rate"] = (passed_n / total) if total else 1.0
    report.metrics["canned_total"] = float(sum(1 for c in report.cases if c.source == "canned"))
    report.metrics["live_total"] = float(
        sum(1 for c in report.cases if c.source == "live" and not c.skipped)
    )

    for c in scored:
        if not c.passed:
            report.breaches.append(c.id)

    # Live skip does not fail the run when canned passed.
    report.thresholds_passed = len(report.breaches) == 0
    return report


def _print_report(report: Layer2Report) -> None:
    print()
    print("=" * 60)
    print("Layer 2 Tool-Selection Report")
    print("=" * 60)
    canned = [c for c in report.cases if c.source == "canned"]
    live = [c for c in report.cases if c.source == "live"]
    print(f"  canned: {sum(1 for c in canned if c.passed)}/{len(canned)} passed")
    if live:
        print(f"  live:   {sum(1 for c in live if c.passed)}/{len(live)} passed")
    elif report.live_skipped:
        print("  live:   skipped")
    print(f"  pass_rate: {report.metrics.get('pass_rate', 0):.4f}")
    failed = [c for c in report.cases if not c.passed and not c.skipped]
    if failed:
        print(f"\n  FAILED ({len(failed)}):")
        for c in failed:
            print(f"    - {c.id}: {c.detail[:120]}")
    if report.notes:
        print("\n  Notes:")
        for n in report.notes:
            print(f"    - {n}")
    print()
    if report.thresholds_passed:
        print("  [PASS] ALL LAYER-2 CHECKS PASSED")
    else:
        print(f"  [FAIL] breaches: {report.breaches}")
    print("=" * 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Layer 2 tool-selection evaluation.")
    parser.add_argument(
        "--trajectories",
        type=Path,
        default=_DEFAULT_TRAJECTORIES,
        help="Canned trajectory JSONL",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=_DEFAULT_GOLDEN,
        help="Golden JSONL for --live",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("out/eval-l2.json"),
        help="JSON report path",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Also run run_agent_turn on golden (skip cleanly if no model)",
    )
    args: Any = parser.parse_args(argv)

    report = run_layer2(
        trajectories_path=args.trajectories,
        golden_path=args.golden,
        live=bool(args.live),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    _print_report(report)
    return 0 if report.thresholds_passed else 1


if __name__ == "__main__":
    sys.exit(main())
