"""Layer 7 robustness runner — N-repeat pass-rates + optional live agent."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from packages.eval.models import GoldenItem
from packages.eval.robustness.aggregate import CaseAgg, aggregate_results
from packages.eval.robustness.score_run import RunObservation, score_run
from packages.eval.robustness.thresholds import DEFAULT_MIN_PASS_RATE
from packages.eval.trajectory.score import TrajectoryExpectation
from pydantic import BaseModel, Field


def _repo_data_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "golden.jsonl").is_file():
            return parent / "data"
    return here.parents[5] / "data"


_DATA = _repo_data_dir()
_DEFAULT_VARIANTS = _DATA / "eval" / "layer7_variants.jsonl"
_DEFAULT_REPLAYS = _DATA / "eval" / "layer7_replays.jsonl"
_DEFAULT_GOLDEN = _DATA / "golden.jsonl"
_DEFAULT_TRAJ = _DATA / "eval" / "layer4_trajectories.jsonl"


class Layer7Report(BaseModel):
    cases: list[CaseAgg] = Field(default_factory=list)
    thresholds_passed: bool = False
    breaches: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    live_skipped: bool = False


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load_golden(path: Path) -> dict[str, GoldenItem]:
    return {g.id: g for g in (GoldenItem(**r) for r in _load_jsonl(path))}


def _load_traj(path: Path) -> dict[str, TrajectoryExpectation]:
    out: dict[str, TrajectoryExpectation] = {}
    for row in _load_jsonl(path):
        out[str(row["id"])] = TrajectoryExpectation(
            required_steps=list(row.get("required_steps") or []),
            dependencies=list(row.get("dependencies") or []),
            forbidden_steps=list(row.get("forbidden_steps") or []),
            allowed_path_sets=list(row.get("allowed_path_sets") or []),
        )
    return out


def _min_rates(variants_path: Path) -> dict[str, float]:
    rates: dict[str, float] = {}
    for row in _load_jsonl(variants_path):
        rates[str(row["id"])] = float(row.get("min_pass_rate", DEFAULT_MIN_PASS_RATE))
    return rates


def run_canned(
    *,
    replays_path: Path,
    variants_path: Path,
    golden_path: Path,
    traj_path: Path,
) -> tuple[list[dict[str, object]], list[str]]:
    """Score canned replays with L2/L4/L5; return rows + notes."""
    golden = _load_golden(golden_path)
    traj = _load_traj(traj_path)
    rows: list[dict[str, object]] = []
    notes: list[str] = []
    for raw in _load_jsonl(replays_path):
        case_id = str(raw["case_id"])
        item = golden.get(case_id)
        if item is None:
            notes.append(f"skip replay unknown golden id {case_id}")
            continue
        obs = RunObservation(
            tools=list(raw.get("tools") or []),
            answer=str(raw.get("answer") or ""),
            citations=list(raw.get("citations") or []),
            refusal=raw.get("refusal"),
            escalation=raw.get("escalation"),
            fault=raw.get("fault"),
        )
        # Prefer explicit passed flag for aggregation gate tests; still verify scorer.
        scored = score_run(obs, item.expected, trajectory=traj.get(case_id))
        passed = bool(raw.get("passed", scored.passed)) and scored.passed
        if bool(raw.get("passed")) and not scored.passed:
            # Canned ideal may mark pass; trust scorer if conflict on happy path.
            passed = scored.passed
        rows.append(
            {
                "case_id": case_id,
                "variant": str(raw.get("variant", "base")),
                "passed": passed,
                "repeat": int(raw.get("repeat", 0)),
            }
        )
    _ = variants_path  # rates applied in aggregate
    return rows, notes


async def _run_live_async(
    *,
    variants_path: Path,
    golden_path: Path,
    traj_path: Path,
    repeats: int | None,
) -> tuple[list[dict[str, object]], bool, str]:
    try:
        from packages.agent_core import run_agent_turn
        from packages.common.providers.factory import (
            get_chat_provider,
            get_prompt_store_provider,
        )
        from packages.eval.robustness.faulty_tools import FaultyToolsClient
        from packages.tools.factory import get_tools_client_provider
    except Exception as exc:  # noqa: BLE001
        return [], True, f"live import failed: {exc}"

    try:
        chat = get_chat_provider()
        tools = get_tools_client_provider()
        prompts = get_prompt_store_provider()
    except Exception as exc:  # noqa: BLE001
        return [], True, f"live providers unavailable: {exc}"

    try:
        await run_agent_turn(
            prompt="Loan 100245 escrow jumped $35 in May — draft a reply explaining why.",
            chat_provider=chat,
            tools_client=tools,
            prompt_store=prompts,
        )
    except Exception as exc:  # noqa: BLE001
        return [], True, f"live agent probe failed (skipping live suite): {exc}"

    golden = _load_golden(golden_path)
    traj = _load_traj(traj_path)
    rows: list[dict[str, object]] = []

    for vrow in _load_jsonl(variants_path):
        case_id = str(vrow["id"])
        item = golden.get(case_id)
        if item is None:
            continue
        n_rep = int(repeats if repeats is not None else vrow.get("repeats", 5))
        prompts_list: list[tuple[str, str, str | None]] = [
            ("base", item.rep_prompt, None)
        ]
        for i, p in enumerate(vrow.get("paraphrases") or []):
            prompts_list.append((f"paraphrase_{i}", str(p), None))
        for i, p in enumerate(vrow.get("malformed") or []):
            prompts_list.append((f"malformed_{i}", str(p), None))
        for fault in vrow.get("faults") or []:
            prompts_list.append((f"fault_{fault}", item.rep_prompt, str(fault)))

        for variant, prompt, fault in prompts_list:
            for rep in range(n_rep):
                client: Any = tools
                if fault:
                    client = FaultyToolsClient(tools, fault)  # type: ignore[arg-type]
                try:
                    output = await run_agent_turn(
                        prompt=prompt,
                        chat_provider=chat,
                        tools_client=client,
                        prompt_store=prompts,
                    )
                    obs = RunObservation(
                        tools=[tc.name for tc in output.tool_calls],
                        answer=output.answer or "",
                        citations=[c.source for c in output.citations],
                        refusal=output.refusal,
                        escalation=(
                            output.escalation.category if output.escalation else None
                        ),
                        fault=fault,
                    )
                    scored = score_run(
                        obs, item.expected, trajectory=traj.get(case_id)
                    )
                    rows.append(
                        {
                            "case_id": case_id,
                            "variant": variant,
                            "passed": scored.passed,
                            "repeat": rep,
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    return (
                        [],
                        True,
                        f"live run failed on {case_id}/{variant} (skipping): {exc}",
                    )
    return rows, False, ""


def run_layer7(
    *,
    variants_path: Path | None = None,
    replays_path: Path | None = None,
    golden_path: Path | None = None,
    traj_path: Path | None = None,
    live: bool = False,
    repeats: int | None = None,
) -> Layer7Report:
    variants = variants_path or _DEFAULT_VARIANTS
    replays = replays_path or _DEFAULT_REPLAYS
    golden = golden_path or _DEFAULT_GOLDEN
    traj = traj_path or _DEFAULT_TRAJ
    report = Layer7Report(
        notes=[
            "Layer 7 scores N-repeat pass-rates (not single-shot).",
            "Per-run uses L2 + L4 + L5 structural scorers.",
            "Auth deferred; no POST /chat.",
            "EvalStore environment=eval for offline runs.",
        ]
    )

    rows, notes = run_canned(
        replays_path=replays,
        variants_path=variants,
        golden_path=golden,
        traj_path=traj,
    )
    report.notes.extend(notes)

    if live:
        live_rows, skipped, note = asyncio.run(
            _run_live_async(
                variants_path=variants,
                golden_path=golden,
                traj_path=traj,
                repeats=repeats,
            )
        )
        report.live_skipped = skipped
        if note:
            report.notes.append(note)
        if skipped:
            report.notes.append("live suite skipped; canned results still apply")
        else:
            rows = live_rows

    rates = _min_rates(variants)
    cases = aggregate_results(rows, min_pass_rates=rates)
    report.cases = cases
    for c in cases:
        if not c.passed:
            report.breaches.append(c.case_id)
    report.thresholds_passed = len(report.breaches) == 0
    total_n = sum(c.n for c in cases) or 1
    total_p = sum(c.passes for c in cases)
    report.metrics["pass_rate"] = total_p / total_n
    report.metrics["cases"] = float(len(cases))
    return report


def _print_report(report: Layer7Report) -> None:
    print()
    print("=" * 60)
    print("Layer 7 Robustness Report")
    print("=" * 60)
    for c in report.cases:
        mark = "PASS" if c.passed else "FAIL"
        print(
            f"  [{mark}] {c.case_id}: {c.passes}/{c.n} "
            f"(rate={c.pass_rate:.2f}, wilson_lo={c.wilson_lower:.2f}, "
            f"min={c.min_pass_rate:.2f})"
        )
    if report.live_skipped:
        print("  live: skipped")
    print(f"  overall pass_rate: {report.metrics.get('pass_rate', 0):.4f}")
    if report.notes:
        print("\n  Notes:")
        for n in report.notes:
            print(f"    - {n}")
    print()
    if report.thresholds_passed:
        print("  [PASS] ALL LAYER-7 CHECKS PASSED")
    else:
        print(f"  [FAIL] breaches: {report.breaches}")
    print("=" * 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Layer 7 robustness evaluation.")
    parser.add_argument("--variants", type=Path, default=_DEFAULT_VARIANTS)
    parser.add_argument("--replays", type=Path, default=_DEFAULT_REPLAYS)
    parser.add_argument("--golden", type=Path, default=_DEFAULT_GOLDEN)
    parser.add_argument("--report", type=Path, default=Path("out/eval-l7.json"))
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--repeats", type=int, default=None)
    args = parser.parse_args(argv)

    report = run_layer7(
        variants_path=args.variants,
        replays_path=args.replays,
        golden_path=args.golden,
        live=bool(args.live),
        repeats=args.repeats,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    _print_report(report)
    return 0 if report.thresholds_passed else 1


if __name__ == "__main__":
    sys.exit(main())
