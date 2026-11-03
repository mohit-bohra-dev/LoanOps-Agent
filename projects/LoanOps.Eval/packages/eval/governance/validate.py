"""L9 validate — CI gate over registry + rubrics + case files."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class RegistryEntry(BaseModel):
    case_id: str
    layer: str
    version: str = "1"
    status: str = "draft"
    eval_methods: list[str] = Field(default_factory=list)
    rubric: str
    rubric_version: str
    source_trace_id: str | None = None
    reviewers: list[str] = Field(default_factory=list)
    last_reviewed: str | None = None


class ValidateReport(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _token_set(text: str) -> set[str]:
    return {t.lower() for t in text.replace(",", " ").split() if t.strip()}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_registry(path: Path) -> list[RegistryEntry]:
    return [RegistryEntry(**r) for r in _load_jsonl(path)]


def list_rubric_versions(rubrics_dir: Path) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    if not rubrics_dir.is_dir():
        return found
    for path in rubrics_dir.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        name = str(data.get("name") or path.stem.split(".")[0])
        version = str(data.get("version") or "1")
        found.add((name, version))
    return found


def _case_ids_from_layer_file(path: Path) -> set[str]:
    ids: set[str] = set()
    for row in _load_jsonl(path):
        if "id" in row:
            ids.add(str(row["id"]))
        elif "case_id" in row:
            ids.add(str(row["case_id"]))
    return ids


def validate_governance(
    *,
    data_dir: Path,
    stale_days: int = 180,
    today: date | None = None,
) -> ValidateReport:
    report = ValidateReport(passed=True)
    registry_path = data_dir / "eval" / "registry.jsonl"
    rubrics_dir = data_dir / "eval" / "rubrics"
    tools_snap = (
        data_dir.parent
        / "projects"
        / "LoanOps.Eval"
        / "packages"
        / "eval"
        / "mcp"
        / "snapshots"
        / "tools.json"
    )

    registry = load_registry(registry_path)
    if not registry:
        report.errors.append("registry.jsonl empty or missing")
        report.passed = False
        return report

    rubrics = list_rubric_versions(rubrics_dir)
    approved = {
        (e.case_id, e.layer): e for e in registry if e.status == "approved"
    }

    layer_files: list[tuple[str, Path]] = [
        ("golden", data_dir / "golden.jsonl"),
        ("2", data_dir / "eval" / "layer2_trajectories.jsonl"),
        ("3", data_dir / "eval" / "layer3_args.jsonl"),
        ("4", data_dir / "eval" / "layer4_trajectories.jsonl"),
        ("5", data_dir / "eval" / "layer5_outcomes.jsonl"),
        ("7", data_dir / "eval" / "layer7_variants.jsonl"),
    ]

    for layer, path in layer_files:
        if not path.is_file():
            report.warnings.append(f"missing case file: {path.name}")
            continue
        for case_id in _case_ids_from_layer_file(path):
            key = (case_id, layer)
            # golden layer also covers layer "golden"
            entry = approved.get(key)
            if entry is None and layer == "golden":
                entry = approved.get((case_id, "golden"))
            if entry is None:
                report.errors.append(
                    f"no approved registry entry for case={case_id} layer={layer}"
                )
                continue
            if (entry.rubric, entry.rubric_version) not in rubrics:
                report.errors.append(
                    f"missing rubric {entry.rubric}@v{entry.rubric_version} "
                    f"for {case_id}/{layer}"
                )

    # Stale review check
    now = today or date.today()
    for e in registry:
        if e.status != "approved" or not e.last_reviewed:
            continue
        try:
            reviewed = datetime.strptime(e.last_reviewed, "%Y-%m-%d").date()
        except ValueError:
            report.warnings.append(f"bad last_reviewed on {e.case_id}: {e.last_reviewed}")
            continue
        age = (now - reviewed).days
        if age > stale_days:
            report.warnings.append(
                f"stale case {e.case_id}/{e.layer}: last_reviewed {e.last_reviewed}"
            )

    # Near-duplicate prompts in golden
    golden = _load_jsonl(data_dir / "golden.jsonl")
    prompts = [(str(r["id"]), str(r.get("rep_prompt", ""))) for r in golden]
    for i in range(len(prompts)):
        for j in range(i + 1, len(prompts)):
            sim = jaccard(_token_set(prompts[i][1]), _token_set(prompts[j][1]))
            if sim >= 0.9:
                report.warnings.append(
                    f"near-duplicate prompts {prompts[i][0]} ~ {prompts[j][0]} "
                    f"(jaccard={sim:.2f})"
                )

    # Stale tool refs vs tools.json
    known_tools: set[str] = set()
    if tools_snap.is_file():
        raw = json.loads(tools_snap.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            for t in raw:
                if isinstance(t, dict) and "name" in t:
                    known_tools.add(str(t["name"]))
        elif isinstance(raw, dict) and "tools" in raw:
            for t in raw["tools"]:
                if isinstance(t, dict) and "name" in t:
                    known_tools.add(str(t["name"]))

    if known_tools:
        for path in [
            data_dir / "eval" / "layer2_trajectories.jsonl",
            data_dir / "eval" / "layer4_trajectories.jsonl",
        ]:
            for row in _load_jsonl(path):
                tools = list(row.get("observed_tools") or row.get("must_call_tools") or [])
                tools += list(row.get("required_steps") or [])
                for name in tools:
                    if name and name not in known_tools:
                        report.errors.append(
                            f"unknown tool {name!r} in {path.name} case {row.get('id')}"
                        )

    report.passed = len(report.errors) == 0
    return report
