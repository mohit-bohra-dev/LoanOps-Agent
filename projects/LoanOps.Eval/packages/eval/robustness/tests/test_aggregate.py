"""Unit tests for Wilson aggregation."""

from __future__ import annotations

from packages.eval.robustness.aggregate import aggregate_results, wilson_lower_bound


def test_wilson_perfect() -> None:
    assert wilson_lower_bound(5, 5) > 0.4


def test_aggregate_pass() -> None:
    rows = [
        {"case_id": "g001", "variant": "base", "passed": True},
        {"case_id": "g001", "variant": "base", "passed": True},
        {"case_id": "g001", "variant": "base", "passed": True},
        {"case_id": "g001", "variant": "base", "passed": True},
        {"case_id": "g001", "variant": "base", "passed": False},
    ]
    cases = aggregate_results(rows, min_pass_rates={"g001": 0.8})
    assert len(cases) == 1
    assert cases[0].pass_rate == 0.8
    assert cases[0].passed is True


def test_aggregate_fail_below_floor() -> None:
    rows = [
        {"case_id": "g001", "variant": "base", "passed": True},
        {"case_id": "g001", "variant": "base", "passed": False},
        {"case_id": "g001", "variant": "base", "passed": False},
        {"case_id": "g001", "variant": "base", "passed": False},
        {"case_id": "g001", "variant": "base", "passed": False},
    ]
    cases = aggregate_results(rows, min_pass_rates={"g001": 0.8})
    assert cases[0].passed is False
