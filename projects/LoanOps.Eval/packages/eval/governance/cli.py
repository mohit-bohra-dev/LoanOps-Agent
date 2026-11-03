"""Layer 9 governance CLI."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from packages.common.providers.eval_store import ReviewLabel
from packages.common.providers.testing import InMemoryEvalStore
from packages.eval.governance.agreement import compute_agreement
from packages.eval.governance.calibrate import calibrate_judge
from packages.eval.governance.promote import promote_candidates
from packages.eval.governance.sync import sync_approved
from packages.eval.governance.validate import validate_governance


def _repo_data_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data" / "golden.jsonl").is_file():
            return parent / "data"
    return here.parents[5] / "data"


def _cmd_validate(args: argparse.Namespace) -> int:
    report = validate_governance(data_dir=args.data)
    print(json.dumps(report.model_dump(), indent=2))
    if report.warnings:
        print(f"\n{len(report.warnings)} warning(s)", file=sys.stderr)
    return 0 if report.passed else 1


async def _cmd_sync_async(args: argparse.Namespace) -> int:
    if args.mock:
        store = InMemoryEvalStore()
    else:
        try:
            from packages.common.providers.factory import get_eval_store_provider

            store = get_eval_store_provider()
        except Exception as exc:  # noqa: BLE001
            print(f"eval store unavailable, using InMemory: {exc}")
            store = InMemoryEvalStore()
    counts = await sync_approved(store, data_dir=args.data)
    print(json.dumps(counts, indent=2))
    return 0


def _cmd_sync(args: argparse.Namespace) -> int:
    return asyncio.run(_cmd_sync_async(args))


def _cmd_agreement(args: argparse.Namespace) -> int:
    store = InMemoryEvalStore()
    # Fixture labels for CI / demo
    labels = [
        ReviewLabel(
            queue="loanops-ops-review",
            trace_id="t1",
            reviewer="alice",
            label="pass",
            rubric="outcome",
            rubric_version="1",
        ),
        ReviewLabel(
            queue="loanops-ops-review",
            trace_id="t1",
            reviewer="bob",
            label="pass",
            rubric="outcome",
            rubric_version="1",
        ),
        ReviewLabel(
            queue="loanops-ops-review",
            trace_id="t2",
            reviewer="alice",
            label="pass",
            rubric="outcome",
            rubric_version="1",
        ),
        ReviewLabel(
            queue="loanops-ops-review",
            trace_id="t2",
            reviewer="bob",
            label="fail",
            rubric="outcome",
            rubric_version="1",
        ),
    ]
    reports = compute_agreement(labels)
    for r in reports:
        for tid in r.disagreements:
            # best-effort enqueue to adjudication (in-memory)
            store.queues.setdefault("loanops-adjudication", []).append(tid)
    print(json.dumps([r.model_dump() for r in reports], indent=2))
    return 0


def _cmd_calibrate(args: argparse.Namespace) -> int:
    human = [
        ReviewLabel(
            queue="q",
            trace_id="t1",
            reviewer="alice",
            label="pass",
            rubric="outcome",
        ),
        ReviewLabel(
            queue="q",
            trace_id="t2",
            reviewer="alice",
            label="fail",
            rubric="outcome",
        ),
    ]
    judge = [
        ReviewLabel(
            queue="q",
            trace_id="t1",
            reviewer="llm_judge",
            label="pass",
            rubric="outcome",
        ),
        ReviewLabel(
            queue="q",
            trace_id="t2",
            reviewer="llm_judge",
            label="fail",
            rubric="outcome",
        ),
    ]
    report = calibrate_judge(human, judge)
    print(json.dumps(report.model_dump(), indent=2))
    return 0


def _cmd_promote(args: argparse.Namespace) -> int:
    labels = [
        ReviewLabel(
            queue="loanops-adjudication",
            trace_id="cand-001",
            item_id="cand-001",
            reviewer="adjudicator",
            label="approved",
            rubric="outcome",
            rubric_version="1",
            comment="promoted from ops review",
        )
    ]
    out = args.out or (args.data / "eval" / "candidates")
    draft = args.draft or (args.data / "eval" / "registry.draft.jsonl")
    report = promote_candidates(labels, out_dir=out, registry_draft=draft)
    print(json.dumps(report.model_dump(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Layer 9 evaluation governance")
    parser.add_argument(
        "--data",
        type=Path,
        default=_repo_data_dir(),
        help="Repo data/ directory",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="CI gate: registry + rubrics + stale/dupes")
    p_val.set_defaults(func=_cmd_validate)

    p_sync = sub.add_parser("sync", help="Push approved cases to EvalStore")
    p_sync.add_argument("--mock", action="store_true")
    p_sync.set_defaults(func=_cmd_sync)

    p_agr = sub.add_parser("agreement", help="Inter-reviewer agreement + adjudication queue")
    p_agr.set_defaults(func=_cmd_agreement)

    p_cal = sub.add_parser("calibrate", help="LLM-judge vs human kappa")
    p_cal.set_defaults(func=_cmd_calibrate)

    p_pro = sub.add_parser("promote", help="Write candidate cases for PR (never approved)")
    p_pro.add_argument("--out", type=Path, default=None)
    p_pro.add_argument("--draft", type=Path, default=None)
    p_pro.set_defaults(func=_cmd_promote)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
