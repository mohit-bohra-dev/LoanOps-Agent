"""Process graph structural validation (ADR-028 F2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.eakg.process_extract import ProcessDraft, TransitionDraft


@dataclass
class DecisionSheetRow:
    decision_step_id: str
    guard_label: str
    to_step_id: str | None
    source_section: str
    source_ordinal: int
    confirmed: bool = False


@dataclass
class ValidationResult:
    status: str  # pass | fail
    failures: list[str] = field(default_factory=list)
    decision_sheet: list[DecisionSheetRow] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "pass" and not self.failures


def validate_process(draft: ProcessDraft) -> ValidationResult:
    failures: list[str] = []
    steps = {s.id: s for s in draft.steps}
    starts = [s for s in draft.steps if s.kind == "start"]
    if draft.children and len(draft.steps) == 1 and draft.steps[0].kind == "start":
        # Hub with stubs: structural pass; children are stubs.
        return ValidationResult(status="pass", failures=[], decision_sheet=[])

    if len(starts) != 1:
        failures.append(f"expected_exactly_one_start got={len(starts)}")

    # Outgoing adjacency
    outgoing: dict[str, list[TransitionDraft]] = {sid: [] for sid in steps}
    for tr in draft.transitions:
        if tr.from_step not in steps:
            failures.append(f"dangling_from:{tr.id}")
            continue
        if tr.to_step is not None and tr.to_step not in steps:
            failures.append(f"dangling_to:{tr.id}->{tr.to_step}")
        outgoing.setdefault(tr.from_step, []).append(tr)

    # Decision completeness
    sheet: list[DecisionSheetRow] = []
    for step in draft.steps:
        if step.kind != "decision":
            continue
        outs = outgoing.get(step.id, [])
        labels = [t.guard_label for t in outs]
        if len(outs) < 2:
            failures.append(f"decision_needs_two_branches:{step.id}")
        if len(labels) != len(set(labels)):
            failures.append(f"duplicate_branch_labels:{step.id}")
        for tr in outs:
            if tr.to_step is None:
                failures.append(f"missing_branch_destination:{tr.id}")
            sheet.append(
                DecisionSheetRow(
                    decision_step_id=step.id,
                    guard_label=tr.guard_label,
                    to_step_id=tr.to_step,
                    source_section=tr.source_section,
                    source_ordinal=tr.source_ordinal,
                )
            )

    # Reachability from start
    if len(starts) == 1:
        start_id = starts[0].id
        reachable = _bfs(start_id, outgoing)
        for sid in steps:
            if sid not in reachable:
                failures.append(f"unreachable_step:{sid}")

        # Terminal path: every non-end reachable step must reach an end
        ends = {s.id for s in draft.steps if s.kind == "end"}
        if not ends and draft.steps:
            failures.append("no_end_step")
        for sid in reachable:
            if steps[sid].kind == "end":
                continue
            if not _can_reach_any(sid, outgoing, ends):
                failures.append(f"no_path_to_end:{sid}")

        # Unapproved cycles
        if _has_unapproved_cycle(outgoing, draft.transitions):
            failures.append("unapproved_cycle")

    # Orphans: steps with no in/out (except single start hub)
    incoming = {sid: 0 for sid in steps}
    for tr in draft.transitions:
        if tr.to_step in incoming:
            incoming[tr.to_step] += 1
    for sid, step in steps.items():
        if step.kind == "start":
            continue
        if incoming.get(sid, 0) == 0 and not outgoing.get(sid):
            failures.append(f"orphan_step:{sid}")

    # Cross-process transitions
    for tr in draft.transitions:
        if tr.to_step and not tr.to_step.startswith(draft.process_id):
            failures.append(f"cross_process_transition:{tr.id}")

    status = "pass" if not failures else "fail"
    return ValidationResult(status=status, failures=failures, decision_sheet=sheet)


def _bfs(
    start: str, outgoing: dict[str, list[TransitionDraft]]
) -> set[str]:
    seen: set[str] = set()
    queue = [start]
    while queue:
        cur = queue.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        for tr in outgoing.get(cur, []):
            if tr.to_step and tr.to_step not in seen:
                queue.append(tr.to_step)
    return seen


def _can_reach_any(
    start: str,
    outgoing: dict[str, list[TransitionDraft]],
    targets: set[str],
) -> bool:
    if not targets:
        return False
    seen: set[str] = set()
    queue = [start]
    while queue:
        cur = queue.pop(0)
        if cur in targets:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        for tr in outgoing.get(cur, []):
            if tr.to_step:
                queue.append(tr.to_step)
    return False


def _has_unapproved_cycle(
    outgoing: dict[str, list[TransitionDraft]],
    transitions: list[TransitionDraft],
) -> bool:
    """Detect cycles that are not exclusively via loopback transitions."""
    loopback_edges = {
        (t.from_step, t.to_step)
        for t in transitions
        if t.kind == "loopback" and t.to_step
    }
    # Tarjan-ish DFS
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {sid: WHITE for sid in outgoing}

    def dfs(node: str) -> bool:
        color[node] = GRAY
        for tr in outgoing.get(node, []):
            nxt = tr.to_step
            if not nxt:
                continue
            if (node, nxt) in loopback_edges:
                continue
            if color.get(nxt, WHITE) == GRAY:
                return True
            if color.get(nxt, WHITE) == WHITE and dfs(nxt):
                return True
        color[node] = BLACK
        return False

    return any(dfs(n) for n, c in color.items() if c == WHITE)
