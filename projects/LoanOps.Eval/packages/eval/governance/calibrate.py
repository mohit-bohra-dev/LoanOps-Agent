"""Calibrate LLM-judge scores vs human labels (kappa ≥ 0.6 → trusted)."""

from __future__ import annotations

from packages.common.providers.eval_store import ReviewLabel
from packages.eval.governance.agreement import AgreementReport, compute_agreement
from pydantic import BaseModel, Field

TRUST_KAPPA: float = 0.6


class CalibrateReport(BaseModel):
    trusted_rubrics: list[str] = Field(default_factory=list)
    untrusted_rubrics: list[str] = Field(default_factory=list)
    agreements: list[AgreementReport] = Field(default_factory=list)


def calibrate_judge(
    human_labels: list[ReviewLabel],
    judge_labels: list[ReviewLabel],
    *,
    min_kappa: float = TRUST_KAPPA,
) -> CalibrateReport:
    """Treat judge as a second reviewer named ``llm_judge``."""
    combined = list(human_labels) + list(judge_labels)
    agreements = compute_agreement(combined)
    report = CalibrateReport(agreements=agreements)
    for a in agreements:
        if a.kappa >= min_kappa:
            report.trusted_rubrics.append(a.rubric)
        else:
            report.untrusted_rubrics.append(a.rubric)
    return report
