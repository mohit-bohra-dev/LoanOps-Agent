"""Inter-reviewer agreement helpers (percent agreement + Cohen's kappa)."""

from __future__ import annotations

from collections import Counter, defaultdict

from packages.common.providers.eval_store import ReviewLabel
from pydantic import BaseModel, Field


class AgreementReport(BaseModel):
    rubric: str
    n_pairs: int = 0
    percent_agreement: float = 0.0
    kappa: float = 0.0
    disagreements: list[str] = Field(default_factory=list)


def _cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    n = len(labels_a)
    if n == 0 or len(labels_b) != n:
        return 0.0
    agree = sum(1 for a, b in zip(labels_a, labels_b, strict=True) if a == b)
    po = agree / n
    cats = set(labels_a) | set(labels_b)
    ca = Counter(labels_a)
    cb = Counter(labels_b)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    if abs(1.0 - pe) < 1e-12:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1.0 - pe)


def compute_agreement(labels: list[ReviewLabel]) -> list[AgreementReport]:
    """Pair first two reviewers per (trace_id, rubric) for kappa."""
    by_key: dict[tuple[str, str], list[ReviewLabel]] = defaultdict(list)
    for lab in labels:
        rubric = lab.rubric or "unknown"
        by_key[(lab.trace_id, rubric)].append(lab)

    by_rubric_pairs: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    disagreements: dict[str, list[str]] = defaultdict(list)
    for (trace_id, rubric), labs in by_key.items():
        if len(labs) < 2:
            continue
        a, b = labs[0], labs[1]
        by_rubric_pairs[rubric].append((a.label, b.label, trace_id))
        if a.label != b.label:
            disagreements[rubric].append(trace_id)

    out: list[AgreementReport] = []
    for rubric, pairs in sorted(by_rubric_pairs.items()):
        la = [p[0] for p in pairs]
        lb = [p[1] for p in pairs]
        agree = sum(1 for a, b in zip(la, lb, strict=True) if a == b)
        n = len(pairs)
        out.append(
            AgreementReport(
                rubric=rubric,
                n_pairs=n,
                percent_agreement=(agree / n) if n else 0.0,
                kappa=_cohen_kappa(la, lb),
                disagreements=disagreements.get(rubric, []),
            )
        )
    return out
