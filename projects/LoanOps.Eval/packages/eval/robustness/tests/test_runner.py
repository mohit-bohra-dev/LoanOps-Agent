"""Layer 7 canned runner smoke."""

from __future__ import annotations

from pathlib import Path

from packages.eval.robustness.layer7 import run_layer7

_DATA = Path(__file__).resolve()
for _p in _DATA.parents:
    if (_p / "data" / "eval" / "layer7_replays.jsonl").is_file():
        _ROOT = _p
        break
else:
    _ROOT = Path(".")


def test_canned_layer7_passes() -> None:
    report = run_layer7(
        variants_path=_ROOT / "data/eval/layer7_variants.jsonl",
        replays_path=_ROOT / "data/eval/layer7_replays.jsonl",
        golden_path=_ROOT / "data/golden.jsonl",
        traj_path=_ROOT / "data/eval/layer4_trajectories.jsonl",
        live=False,
    )
    assert report.thresholds_passed, report.breaches
    assert report.metrics["pass_rate"] >= 0.8
