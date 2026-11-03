"""Pass-rate aggregation + Wilson lower bound for Layer 7."""

from __future__ import annotations

import math
from collections import defaultdict

from packages.eval.robustness.thresholds import DEFAULT_MIN_PASS_RATE, WILSON_Z
from pydantic import BaseModel, Field


class VariantAgg(BaseModel):
    case_id: str
    variant: str
    n: int
    passes: int
    pass_rate: float
    wilson_lower: float
    min_pass_rate: float
    passed: bool


class CaseAgg(BaseModel):
    case_id: str
    n: int
    passes: int
    pass_rate: float
    wilson_lower: float
    min_pass_rate: float
    passed: bool
    variants: list[VariantAgg] = Field(default_factory=list)


def wilson_lower_bound(passes: int, n: int, z: float = WILSON_Z) -> float:
    """Wilson score interval lower bound for a binomial proportion."""
    if n <= 0:
        return 0.0
    phat = passes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = phat + z2 / (2.0 * n)
    margin = z * math.sqrt((phat * (1.0 - phat) + z2 / (4.0 * n)) / n)
    return max(0.0, (centre - margin) / denom)


def aggregate_results(
    rows: list[dict[str, object]],
    *,
    min_pass_rates: dict[str, float] | None = None,
    default_min: float = DEFAULT_MIN_PASS_RATE,
) -> list[CaseAgg]:
    """Aggregate per-case / per-variant pass rates from replay or live rows.

    Each row needs: case_id, variant, passed (bool).
    """
    rates = min_pass_rates or {}
    by_case_variant: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for row in rows:
        case_id = str(row["case_id"])
        variant = str(row.get("variant", "base"))
        passed = bool(row["passed"])
        by_case_variant[(case_id, variant)].append(passed)

    by_case: dict[str, list[VariantAgg]] = defaultdict(list)
    for (case_id, variant), flags in sorted(by_case_variant.items()):
        n = len(flags)
        passes = sum(1 for f in flags if f)
        rate = passes / n if n else 0.0
        floor = rates.get(case_id, default_min)
        by_case[case_id].append(
            VariantAgg(
                case_id=case_id,
                variant=variant,
                n=n,
                passes=passes,
                pass_rate=rate,
                wilson_lower=wilson_lower_bound(passes, n),
                min_pass_rate=floor,
                passed=rate >= floor,
            )
        )

    out: list[CaseAgg] = []
    for case_id, variants in sorted(by_case.items()):
        flags = [f for v in variants for f in [True] * v.passes + [False] * (v.n - v.passes)]
        # Prefer summing counts
        n = sum(v.n for v in variants)
        passes = sum(v.passes for v in variants)
        rate = passes / n if n else 0.0
        floor = rates.get(case_id, default_min)
        out.append(
            CaseAgg(
                case_id=case_id,
                n=n,
                passes=passes,
                pass_rate=rate,
                wilson_lower=wilson_lower_bound(passes, n),
                min_pass_rate=floor,
                passed=rate >= floor and all(v.passed for v in variants),
                variants=variants,
            )
        )
        _ = flags  # silence unused in some mypy configs
    return out
