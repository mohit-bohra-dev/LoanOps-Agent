"""Layer 3 runner smoke tests (canned only — no LLM)."""

from __future__ import annotations

import json
from pathlib import Path

from packages.eval.arguments.layer3 import run_canned, run_layer3

_DATA = Path(__file__).resolve()
for _p in _DATA.parents:
    if (_p / "data" / "eval" / "layer3_args.jsonl").is_file():
        _ARGS = _p / "data" / "eval" / "layer3_args.jsonl"
        break
else:
    _ARGS = Path("data/eval/layer3_args.jsonl")


def test_canned_args_all_pass() -> None:
    results = run_canned(_ARGS)
    assert len(results) >= 5
    failed = [r for r in results if not r.passed]
    assert failed == [], [f"{r.id}: {r.detail}" for r in failed]


def test_run_layer3_default_no_live() -> None:
    report = run_layer3(args_path=_ARGS, live=False)
    assert report.thresholds_passed
    assert report.live_skipped is False
    assert all(c.source == "canned" for c in report.cases)
    assert report.metrics["pass_rate"] == 1.0


def test_args_cover_golden_ids() -> None:
    ids = {
        json.loads(line)["id"]
        for line in _ARGS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    assert {"g001", "g002", "g003", "g004", "g006"}.issubset(ids)
