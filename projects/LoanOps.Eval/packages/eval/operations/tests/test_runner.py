"""L8 fixture runner smoke."""

from __future__ import annotations

from pathlib import Path

from packages.eval.operations.layer8 import run_layer8

_DATA = Path(__file__).resolve()
for _p in _DATA.parents:
    if (_p / "data" / "eval" / "ops_slos.yaml").is_file():
        _SLO = _p / "data" / "eval" / "ops_slos.yaml"
        break
else:
    _SLO = Path("data/eval/ops_slos.yaml")


def test_fixture_layer8_passes() -> None:
    report = run_layer8(slo_path=_SLO, environment="prod", use_fixtures=True)
    assert report.thresholds_passed, report.breaches
    assert report.metrics.total >= 5
