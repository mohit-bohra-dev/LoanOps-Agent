"""L9 validate + agreement smoke tests."""

from __future__ import annotations

from pathlib import Path

from packages.common.providers.eval_store import ReviewLabel
from packages.eval.governance.agreement import compute_agreement
from packages.eval.governance.calibrate import calibrate_judge
from packages.eval.governance.validate import jaccard, validate_governance

_DATA = Path(__file__).resolve()
for _p in _DATA.parents:
    if (_p / "data" / "eval" / "registry.jsonl").is_file():
        _ROOT = _p / "data"
        break
else:
    _ROOT = Path("data")


def test_validate_registry_passes() -> None:
    report = validate_governance(data_dir=_ROOT)
    assert report.passed, report.errors


def test_jaccard() -> None:
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert jaccard({"a"}, {"b"}) == 0.0


def test_agreement_and_calibrate() -> None:
    human = [
        ReviewLabel(queue="q", trace_id="t1", reviewer="a", label="pass", rubric="outcome"),
        ReviewLabel(queue="q", trace_id="t2", reviewer="a", label="fail", rubric="outcome"),
    ]
    other = [
        ReviewLabel(queue="q", trace_id="t1", reviewer="b", label="pass", rubric="outcome"),
        ReviewLabel(queue="q", trace_id="t2", reviewer="b", label="fail", rubric="outcome"),
    ]
    agr = compute_agreement(human + other)
    assert agr[0].percent_agreement == 1.0
    cal = calibrate_judge(human, other)
    assert "outcome" in cal.trusted_rubrics
