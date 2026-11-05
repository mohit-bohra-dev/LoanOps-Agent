"""Offline retrieval stage scores from a small golden JSONL (CI-safe)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class StageCaseResult(BaseModel):
    id: str
    stage: str
    passed: bool
    detail: str = ""


class RetrievalReport(BaseModel):
    cases: list[StageCaseResult] = Field(default_factory=list)
    thresholds_passed: bool = False
    metrics: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


def _load_cases(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _recall_at_k(got: list[str], expect: list[str], k: int) -> float:
    if not expect:
        return 1.0
    top = set(got[:k])
    hits = sum(1 for e in expect if e in top)
    return hits / len(expect)


def score_case(row: dict[str, Any]) -> list[StageCaseResult]:
    """Score one fixture row with precomputed ``retrieved`` lists (no live network)."""
    case_id = str(row.get("id") or "unknown")
    expect = row.get("expect") or {}
    retrieved = row.get("retrieved") or {}
    out: list[StageCaseResult] = []
    mapping = [
        ("capability_search", "capability_ids", "eakg"),
        ("api_index", "operation_ids", "api_index"),
        ("sop_retrieval", "doc_ids", "docs"),
    ]
    for stage, expect_key, ret_key in mapping:
        exp_list = [str(x) for x in (expect.get(expect_key) or [])]
        got_list = [str(x) for x in (retrieved.get(ret_key) or [])]
        if not exp_list:
            continue
        score = _recall_at_k(got_list, exp_list, k=5)
        out.append(
            StageCaseResult(
                id=case_id,
                stage=stage,
                passed=score >= 1.0,
                detail=f"recall@5={score:.2f}",
            )
        )
    return out


def run_retrieval_stages(cases_path: Path) -> RetrievalReport:
    rows = _load_cases(cases_path)
    report = RetrievalReport()
    if not rows:
        report.notes.append(f"no cases at {cases_path}")
        report.thresholds_passed = True  # empty = skip
        return report
    for row in rows:
        report.cases.extend(score_case(row))
    fails = [c for c in report.cases if not c.passed]
    report.thresholds_passed = len(fails) == 0
    report.metrics["case_count"] = float(len(report.cases))
    report.metrics["pass_rate"] = (
        (len(report.cases) - len(fails)) / len(report.cases) if report.cases else 1.0
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("data/eval/retrieval_stages.jsonl"),
    )
    parser.add_argument("--report", type=Path, default=Path("out/eval-retrieval.json"))
    args = parser.parse_args()
    report = run_retrieval_stages(args.cases)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    raise SystemExit(0 if report.thresholds_passed else 1)


if __name__ == "__main__":
    main()
