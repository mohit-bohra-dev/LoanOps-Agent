"""Promote adjudicated review items to candidate JSONL (never writes approved)."""

from __future__ import annotations

import json
from pathlib import Path

from packages.common.providers.eval_store import ReviewLabel
from pydantic import BaseModel, Field


class PromoteReport(BaseModel):
    written: list[str] = Field(default_factory=list)
    draft_registry_rows: int = 0


def promote_candidates(
    labels: list[ReviewLabel],
    *,
    out_dir: Path,
    registry_draft: Path,
) -> PromoteReport:
    """Write candidates/*.jsonl + append draft registry rows for PR review."""
    out_dir.mkdir(parents=True, exist_ok=True)
    report = PromoteReport()
    approved = [lab for lab in labels if lab.label.lower() in {"pass", "approve", "approved"}]
    rows: list[dict[str, object]] = []
    for lab in approved:
        case = {
            "id": lab.item_id or lab.trace_id,
            "source_trace_id": lab.trace_id,
            "reviewer": lab.reviewer,
            "rubric": lab.rubric,
            "rubric_version": lab.rubric_version,
            "label": lab.label,
            "comment": lab.comment,
        }
        path = out_dir / f"{case['id']}.jsonl"
        path.write_text(json.dumps(case) + "\n", encoding="utf-8")
        report.written.append(str(path))
        rows.append(
            {
                "case_id": case["id"],
                "layer": "golden",
                "version": "1",
                "status": "draft",
                "eval_methods": ["outcome"],
                "rubric": lab.rubric or "outcome",
                "rubric_version": lab.rubric_version or "1",
                "source_trace_id": lab.trace_id,
                "reviewers": [lab.reviewer],
                "last_reviewed": None,
            }
        )
    if rows:
        registry_draft.parent.mkdir(parents=True, exist_ok=True)
        with registry_draft.open("a", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        report.draft_registry_rows = len(rows)
    return report
