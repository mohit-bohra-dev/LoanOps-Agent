"""Deterministic SOP process extractor (ADR-028). No LLM at runtime."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

EXTRACTOR_ID = "process_rules"
EXTRACTOR_VERSION = "1.0.0"

_PROC_ID = re.compile(r"(DP\d+-[A-Za-z]+\d+\.v\d+)", re.IGNORECASE)
_EFFECTIVE = re.compile(
    r"(?:Effective Date|Date Revised):\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)
_SECTION = re.compile(
    r"^#{1,3}\s*\*{0,2}\s*(Purpose|Scope|Procedures|Monitoring and Reporting|"
    r"Training|Authority|Related Policies(?: and Procedures)?|Document Maintenance|"
    r"Job Aid|Procedure)\s*\*{0,2}\s*$",
    re.IGNORECASE,
)
_ORDERED = re.compile(r"^(\d+)\.\s+(.+)$")
_BULLET = re.compile(r"^(\s*)[-*]\s+(.+)$")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_PAGE_ID = re.compile(r"/pages/(\d+)")
_IF_YES_NO = re.compile(r"^If\s+(yes|no)\b[,\s]*(.*)$", re.IGNORECASE)
_IF_WHEN = re.compile(r"^(If|When)\s+(.+?),\s*(.+)$", re.IGNORECASE)
_WAIT_THEN = re.compile(
    r"wait until .+ (?:then|and) (?:analyze|process)",
    re.IGNORECASE,
)
_OVERRIDE = re.compile(r"\b(Important:|do it anyway)\b", re.IGNORECASE)
_THRESHOLDS = (
    (re.compile(r"(\d+)\s+calendar\s+days?", re.I), "calendar_days"),
    (re.compile(r"(\d+)\s+business\s+days?", re.I), "business_days"),
    (re.compile(r"(?:>=|≥)\s*(\d+)\s+months?", re.I), "months"),
    (re.compile(r"(\d+)\s+months?", re.I), "months"),
    (re.compile(r"(\d+)\s+days?", re.I), "days_unspecified"),
)

_MAX_LABEL = 120


@dataclass
class NeedsReview:
    reason: str
    section: str
    ordinal: int
    kind: str


@dataclass
class Threshold:
    text: str
    value: int
    unit: str


@dataclass
class TransitionDraft:
    id: str
    from_step: str
    to_step: str | None
    guard_label: str
    kind: str = "normal"
    source_section: str = "Procedures"
    source_ordinal: int = 0


@dataclass
class StepDraft:
    id: str
    label: str
    kind: str  # start|task|decision|end
    source_section: str
    source_ordinal: int
    systems: list[str] = field(default_factory=list)
    thresholds: list[Threshold] = field(default_factory=list)
    capability_keys: list[str] = field(default_factory=list)
    sop_role_label: str = ""


@dataclass
class ChildStub:
    process_id: str
    title: str
    page_id: str
    url: str


@dataclass
class ProcessDraft:
    process_id: str
    title: str
    procedure_id: str
    effective_date: str
    page_id: str
    page_url: str
    source_version: int
    source_hash: str
    source_completeness: str
    lost_features: list[str]
    extraction_status: str
    regulations: list[str]
    steps: list[StepDraft]
    transitions: list[TransitionDraft]
    children: list[ChildStub]
    needs_review: list[NeedsReview]
    extractor_version: str = EXTRACTOR_VERSION
    maps_hash: str = ""
    related_page_ids: list[str] = field(default_factory=list)


@dataclass
class CuratedMaps:
    systems: dict[str, list[str]]
    regulations: dict[str, list[str]]
    terminal_phrases: list[str]
    capability_phrases: list[dict[str, Any]]
    version_blob: str

    @property
    def maps_hash(self) -> str:
        return hashlib.sha256(self.version_blob.encode("utf-8")).hexdigest()[:16]


def load_maps(maps_dir: Path) -> CuratedMaps:
    systems_raw = _load_yaml(maps_dir / "systems.yaml")
    regs_raw = _load_yaml(maps_dir / "regulations.yaml")
    term_raw = _load_yaml(maps_dir / "terminal_phrases.yaml")
    caps_raw = _load_yaml(maps_dir / "capability_phrases.yaml")
    systems = {
        str(item["id"]): [str(x) for x in item.get("labels", [])]
        for item in systems_raw.get("items", [])
        if isinstance(item, dict) and item.get("id")
    }
    regulations = {
        str(item["id"]): [str(x) for x in item.get("labels", [])]
        for item in regs_raw.get("items", [])
        if isinstance(item, dict) and item.get("id")
    }
    phrases = [str(p) for p in term_raw.get("phrases", [])]
    caps = [c for c in caps_raw.get("items", []) if isinstance(c, dict)]
    blob = json.dumps(
        {
            "systems": systems_raw.get("version"),
            "regulations": regs_raw.get("version"),
            "terminal": term_raw.get("version"),
            "caps": caps_raw.get("version"),
            "systems_items": systems,
            "reg_items": regulations,
            "phrases": phrases,
            "caps_items": caps,
        },
        sort_keys=True,
    )
    return CuratedMaps(systems, regulations, phrases, caps, blob)


def extract_page(
    markdown: str,
    meta: dict[str, Any],
    maps: CuratedMaps,
) -> ProcessDraft:
    page_id = str(meta.get("page_id") or "")
    title = str(meta.get("title") or "Untitled")
    process_id = str(meta.get("process_id") or _slug(title))
    version = int(meta.get("version") or 0)
    url = str(meta.get("url") or "")
    lost = [str(x) for x in (meta.get("lost_features") or [])]
    lossy = bool(meta.get("lossy_conversion")) or bool(lost)
    source_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    completeness = "lossy_unverified" if lossy else "complete_unverified"

    proc_match = _PROC_ID.search(markdown)
    procedure_id = proc_match.group(1) if proc_match else ""
    eff_match = _EFFECTIVE.search(markdown)
    effective_date = eff_match.group(1) if eff_match else ""

    sections = _split_sections(markdown)
    needs: list[NeedsReview] = []
    if not procedure_id:
        needs.append(
            NeedsReview("missing_procedure_id", "header", 0, "header")
        )

    regulations = _match_gazetteer(markdown, maps.regulations)
    children = _extract_hub_children(sections, markdown)
    related = _extract_related_page_ids(sections.get("Related Policies and Procedures", "")
                                       or sections.get("Related Policies", ""))

    steps: list[StepDraft] = []
    transitions: list[TransitionDraft] = []
    procedures_body = (
        sections.get("Procedures")
        or sections.get("Job Aid")
        or sections.get("Procedure")
        or ""
    )

    if children and not procedures_body.strip():
        # Hub page: single start stub pointing at children.
        start = StepDraft(
            id=f"{process_id}_start",
            label=_clip(f"Hub: {title}"),
            kind="start",
            source_section="Topics",
            source_ordinal=0,
        )
        steps.append(start)
        extraction_status = "partial" if needs else "full"
        return ProcessDraft(
            process_id=process_id,
            title=title,
            procedure_id=procedure_id,
            effective_date=effective_date,
            page_id=page_id,
            page_url=url,
            source_version=version,
            source_hash=source_hash,
            source_completeness=completeness,
            lost_features=lost,
            extraction_status=extraction_status,
            regulations=regulations,
            steps=steps,
            transitions=transitions,
            children=children,
            needs_review=needs,
            maps_hash=maps.maps_hash,
            related_page_ids=related,
        )

    steps, transitions, step_needs = _extract_steps(
        process_id, procedures_body, maps
    )
    needs.extend(step_needs)

    if not any(s.kind == "start" for s in steps) and steps:
        steps[0].kind = "start"

    extraction_status = "partial" if needs else ("full" if steps else "stub")
    return ProcessDraft(
        process_id=process_id,
        title=title,
        procedure_id=procedure_id,
        effective_date=effective_date,
        page_id=page_id,
        page_url=url,
        source_version=version,
        source_hash=source_hash,
        source_completeness=completeness,
        lost_features=lost,
        extraction_status=extraction_status,
        regulations=regulations,
        steps=steps,
        transitions=transitions,
        children=children,
        needs_review=needs,
        maps_hash=maps.maps_hash,
        related_page_ids=related,
    )


def extract_from_paths(
    md_path: Path,
    meta_path: Path,
    maps_dir: Path,
) -> ProcessDraft:
    markdown = md_path.read_text(encoding="utf-8")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    maps = load_maps(maps_dir)
    return extract_page(markdown, meta, maps)


def draft_to_dict(draft: ProcessDraft) -> dict[str, Any]:
    return asdict(draft)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:80]


def _clip(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= _MAX_LABEL:
        return cleaned
    return cleaned[: _MAX_LABEL - 1].rstrip() + "…"


def _split_sections(markdown: str) -> dict[str, str]:
    lines = markdown.splitlines()
    sections: dict[str, list[str]] = {"_preamble": []}
    current = "_preamble"
    for line in lines:
        m = _SECTION.match(line.strip())
        if m:
            current = m.group(1).strip()
            # Normalize aliases
            if current.lower() == "procedure":
                current = "Procedures"
            if current.lower() == "job aid":
                current = "Job Aid"
            if current.lower().startswith("related policies"):
                current = "Related Policies and Procedures"
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v) for k, v in sections.items()}


def _extract_hub_children(
    sections: dict[str, str], markdown: str
) -> list[ChildStub]:
    blob = markdown
    if "Topics" in markdown:
        # Prefer the Topics block when present.
        idx = markdown.lower().find("topics")
        blob = markdown[idx:]
    children: list[ChildStub] = []
    seen: set[str] = set()
    for title, href in _LINK.findall(blob):
        pm = _PAGE_ID.search(href)
        if not pm:
            continue
        page_id = pm.group(1)
        if page_id in seen:
            continue
        seen.add(page_id)
        pid = _slug(title)
        children.append(
            ChildStub(
                process_id=pid,
                title=title.strip(),
                page_id=page_id,
                url=href if href.startswith("http") else f"https://pennymac.atlassian.net{href}",
            )
        )
    return children


def _extract_related_page_ids(body: str) -> list[str]:
    ids: list[str] = []
    for _, href in _LINK.findall(body):
        pm = _PAGE_ID.search(href)
        if pm:
            ids.append(pm.group(1))
    return ids


def _match_gazetteer(text: str, table: dict[str, list[str]]) -> list[str]:
    hits: list[str] = []
    lower = text.lower()
    for sid, labels in table.items():
        for lab in labels:
            if lab.lower() in lower:
                hits.append(sid)
                break
    return hits


def _match_capability_keys(text: str, maps: CuratedMaps) -> list[str]:
    keys: list[str] = []
    lower = text.lower()
    for item in maps.capability_phrases:
        phrases = [str(p) for p in item.get("phrases", [])]
        op_key = str(item.get("operation_key") or "")
        if not op_key:
            continue
        if any(p.lower() in lower for p in phrases):
            keys.append(op_key)
    return keys


def _extract_thresholds(text: str) -> list[Threshold]:
    found: list[Threshold] = []
    for pattern, unit in _THRESHOLDS:
        for m in pattern.finditer(text):
            found.append(
                Threshold(text=m.group(0), value=int(m.group(1)), unit=unit)
            )
        if found and unit != "days_unspecified":
            # Prefer more specific units; skip bare days if calendar/business hit.
            break
    # De-dupe by text
    uniq: dict[str, Threshold] = {t.text: t for t in found}
    return list(uniq.values())


def _is_terminal(text: str, phrases: list[str]) -> bool:
    lower = text.lower()
    return any(p.lower() in lower for p in phrases)


def _extract_steps(
    process_id: str,
    body: str,
    maps: CuratedMaps,
) -> tuple[list[StepDraft], list[TransitionDraft], list[NeedsReview]]:
    steps: list[StepDraft] = []
    transitions: list[TransitionDraft] = []
    needs: list[NeedsReview] = []
    lines = body.splitlines()
    i = 0
    ordinal = 0
    while i < len(lines):
        line = lines[i]
        om = _ORDERED.match(line.strip())
        if not om:
            i += 1
            continue
        ordinal = int(om.group(1))
        text = om.group(2).strip()
        step_id = f"{process_id}_s{ordinal}"
        kind = "task"
        systems = _match_gazetteer(text, maps.systems)
        thresholds = _extract_thresholds(text)
        caps = _match_capability_keys(text, maps)
        if _is_terminal(text, maps.terminal_phrases):
            kind = "end"
        if _WAIT_THEN.search(text):
            needs.append(
                NeedsReview(
                    "action_plus_jump",
                    "Procedures",
                    ordinal,
                    "branch",
                )
            )
        if _OVERRIDE.search(text):
            needs.append(
                NeedsReview(
                    "override_exception",
                    "Procedures",
                    ordinal,
                    "override",
                )
            )
        step = StepDraft(
            id=step_id,
            label=_clip(text),
            kind=kind,
            source_section="Procedures",
            source_ordinal=ordinal,
            systems=systems,
            thresholds=thresholds,
            capability_keys=caps,
        )
        steps.append(step)

        # Collect nested bullets belonging to this step.
        j = i + 1
        branch_labels: list[tuple[str, str]] = []
        while j < len(lines):
            bm = _BULLET.match(lines[j])
            if bm is None:
                stripped = lines[j].strip()
                if stripped == "":
                    j += 1
                    continue
                if stripped.startswith("#") or _ORDERED.match(stripped):
                    break
                j += 1
                continue
            bullet = bm.group(2).strip()
            if _WAIT_THEN.search(bullet):
                needs.append(
                    NeedsReview(
                        "action_plus_jump",
                        "Procedures",
                        ordinal,
                        "branch",
                    )
                )
            if _OVERRIDE.search(bullet):
                needs.append(
                    NeedsReview(
                        "override_exception",
                        "Procedures",
                        ordinal,
                        "override",
                    )
                )
                tr_id = f"{process_id}_t{ordinal}_override"
                transitions.append(
                    TransitionDraft(
                        id=tr_id,
                        from_step=step_id,
                        to_step=None,
                        guard_label="override",
                        kind="override",
                        source_section="Procedures",
                        source_ordinal=ordinal,
                    )
                )
            yn = _IF_YES_NO.match(bullet)
            if yn:
                label = yn.group(1).capitalize()
                rest = yn.group(2).strip()
                branch_labels.append((label, rest or bullet))
                j += 1
                continue
            iw = _IF_WHEN.match(bullet)
            if iw:
                guard = _clip(iw.group(2))
                rest = iw.group(3).strip()
                branch_labels.append((guard, rest))
                j += 1
                continue
            # Unrecognized nested structure.
            if bullet.lower().startswith("if ") or bullet.lower().startswith("when "):
                needs.append(
                    NeedsReview(
                        "unsupported_branch_grammar",
                        "Procedures",
                        ordinal,
                        "branch",
                    )
                )
            j += 1
        i = j

        if branch_labels:
            step.kind = "decision"
            for idx, (label, rest) in enumerate(branch_labels):
                to_step: str | None
                if _is_terminal(rest, maps.terminal_phrases):
                    end_id = f"{process_id}_s{ordinal}_end_{idx}"
                    steps.append(
                        StepDraft(
                            id=end_id,
                            label=_clip(rest),
                            kind="end",
                            source_section="Procedures",
                            source_ordinal=ordinal,
                        )
                    )
                    to_step = end_id
                elif "continue" in rest.lower() and "next" in rest.lower():
                    to_step = f"{process_id}_s{ordinal + 1}"
                elif "analyze the account" in rest.lower() or rest.lower().startswith(
                    "analyze"
                ):
                    end_id = f"{process_id}_s{ordinal}_analyze_{idx}"
                    steps.append(
                        StepDraft(
                            id=end_id,
                            label=_clip(rest),
                            kind="end",
                            source_section="Procedures",
                            source_ordinal=ordinal,
                        )
                    )
                    to_step = end_id
                else:
                    to_step = None
                    needs.append(
                        NeedsReview(
                            f"unresolved_branch:{label}",
                            "Procedures",
                            ordinal,
                            "branch",
                        )
                    )
                transitions.append(
                    TransitionDraft(
                        id=f"{process_id}_t{ordinal}_{idx}",
                        from_step=step_id,
                        to_step=to_step,
                        guard_label=label,
                        kind="normal",
                        source_section="Procedures",
                        source_ordinal=ordinal,
                    )
                )
        elif kind != "end" and steps:
            # Sequential default to next ordered step (wired later if exists).
            pass

    # Wire sequential transitions for non-decision task steps.
    by_ord = {
        s.source_ordinal: s
        for s in steps
        if s.id.endswith(f"_s{s.source_ordinal}") or re.search(r"_s\d+$", s.id)
    }
    ordered_pat = re.compile(rf"{re.escape(process_id)}_s\d+$")
    ordered_ids = [s.id for s in steps if ordered_pat.fullmatch(s.id)]
    for idx, sid in enumerate(ordered_ids):
        step = next(s for s in steps if s.id == sid)
        if step.kind == "decision" or step.kind == "end":
            continue
        # Already has outgoing?
        if any(t.from_step == sid for t in transitions):
            continue
        if idx + 1 < len(ordered_ids):
            nxt = ordered_ids[idx + 1]
            transitions.append(
                TransitionDraft(
                    id=f"{process_id}_seq_{idx}",
                    from_step=sid,
                    to_step=nxt,
                    guard_label="next",
                    kind="normal",
                    source_section="Procedures",
                    source_ordinal=step.source_ordinal,
                )
            )
        else:
            # Last task with no terminal → needs review
            if step.kind != "end":
                needs.append(
                    NeedsReview(
                        "missing_terminal_path",
                        "Procedures",
                        step.source_ordinal,
                        "structure",
                    )
                )

    # Resolve continue-to-next that pointed at missing ids.
    existing = {s.id for s in steps}
    for tr in transitions:
        missing = tr.to_step is not None and tr.to_step not in existing
        label = tr.guard_label.lower()
        continue_like = label in {"yes", "next"} or "continue" in label
        if missing and continue_like:
            needs.append(
                NeedsReview(
                    f"dangling_continue:{tr.id}",
                    tr.source_section,
                    tr.source_ordinal,
                    "branch",
                )
            )
            tr.to_step = None

    _ = by_ord  # keep for clarity / future
    return steps, transitions, needs
