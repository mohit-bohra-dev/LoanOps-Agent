"""Promote adjudicated review items to candidate JSONL (never writes approved)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.common.providers.eval_store import ReviewLabel
from packages.eval.taxonomy import is_promotable_label
from pydantic import BaseModel, Field


class PromoteReport(BaseModel):
    written: list[str] = Field(default_factory=list)
    draft_registry_rows: int = 0
    skipped: list[str] = Field(default_factory=list)


def promote_candidates(
    labels: list[ReviewLabel],
    *,
    out_dir: Path,
    registry_draft: Path,
    taxonomy_by_trace: dict[str, dict[str, Any]] | None = None,
) -> PromoteReport:
    """Write candidates/*.jsonl + append draft registry rows for PR review.

    Accepts fail/bad (regression) and pass/approve labels. Never sets status=approved.
    Requires ``source_trace_id`` (from ReviewLabel.trace_id). Fail labels should carry
    taxonomy via ``taxonomy_by_trace`` when available.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    report = PromoteReport()
    tax_map = taxonomy_by_trace or {}
    rows: list[dict[str, object]] = []
    for lab in labels:
        if not is_promotable_label(lab.label):
            report.skipped.append(lab.trace_id)
            continue
        if not lab.trace_id:
            report.skipped.append(lab.item_id or "missing-trace")
            continue
        tax = tax_map.get(lab.trace_id) or {}
        case_id = lab.item_id or lab.trace_id
        case: dict[str, object] = {
            "id": case_id,
            "source_trace_id": lab.trace_id,
            "reviewer": lab.reviewer,
            "rubric": lab.rubric,
            "rubric_version": lab.rubric_version,
            "label": lab.label,
            "comment": lab.comment,
            "primary_category": tax.get("primary_category"),
            "severity": tax.get("severity"),
            "root_component": tax.get("root_component"),
        }
        path = out_dir / f"{case_id}.jsonl"
        path.write_text(json.dumps(case) + "\n", encoding="utf-8")
        report.written.append(str(path))
        rows.append(
            {
                "case_id": case_id,
                "layer": "golden",
                "version": "1",
                "status": "draft",
                "eval_methods": ["outcome"],
                "rubric": lab.rubric or "outcome",
                "rubric_version": lab.rubric_version or "1",
                "source_trace_id": lab.trace_id,
                "reviewers": [lab.reviewer],
                "last_reviewed": None,
                "primary_category": tax.get("primary_category"),
            }
        )
    if rows:
        registry_draft.parent.mkdir(parents=True, exist_ok=True)
        with registry_draft.open("a", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        report.draft_registry_rows = len(rows)
    return report
