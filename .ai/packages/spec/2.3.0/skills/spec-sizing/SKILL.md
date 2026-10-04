---
name: spec-sizing
description: >-
  How the spec-research agent judges whether a spec is one executable block and,
  when it is not, how to recommend a split. Covers the one-block principle, a
  signal-based sizing rubric (independent deliverables, unrelated-subsystem
  spread, mixed concerns, independent P1 stories, no single definition-of-done),
  the `single-block` vs `should-split` verdict returned to the coordinator, the
  split strategy along independently-testable story/deliverable boundaries into
  separate `.ai/specs/<child>/` specs, and the rule that splitting is a
  recommendation to the user — never an automatic action. Use when assessing spec
  size, deciding single-block vs should-split, or recommending how to break an
  oversized spec into smaller specs.
---

# Spec Sizing

How to judge whether a spec is the right size to execute, and how to recommend a split when it is not. This skill is used by the `spec-research` agent during its Phase 0 grounding pass: after reading the spec and the codebase, it produces a **sizing verdict** that the `spec-execution-coordinator` acts on before any execution begins.

This skill covers sizing judgment only. Gathering codebase context and classifying gaps belong to `spec-research-grounding`; artifact roles, naming, and directory layout belong to `spec-artifact-model`; the plan's phase/todo structure belongs to `spec-plan-format`.

## When to Use

- Assessing whether a spec is one executable block before executing it
- Producing the `single-block` vs `should-split` verdict for the coordinator
- Recommending how to break an oversized spec into smaller, independent specs
- Deciding whether a long, multi-phase spec is genuinely too big or just deep

## The One-Block Principle

A single spec should be **one block of executable work**: one coherent deliverable, with a connected wiring path, that can be carried through from research to done as a single thread.

Oversized specs are the failure this principle prevents. When a spec bundles several independent deliverables, execution loses the thread across them — it drifts, skips integration between unrelated parts, and falsely marks todos done because no single definition-of-done holds the whole thing together. Right-sizing the spec *before* execution is cheaper than recovering a half-wired implementation after.

## The Decisive Test

Ask one question:

> **Can the spec be cut along a line such that each side is independently executable, testable, and shippable — and neither side has to be wired up before the other?**

- **No clean cut exists** (everything wires into one deliverable) → `single-block`.
- **A clean independent cut exists** → the spec is really two or more specs → `should-split`.

The split line is **independence**, not length. A spec is too big when it contains independent deliverables, not when it contains many steps toward one deliverable.

## Sizing Signals

Each signal is split pressure. Look for them while reading the story and grounding the spec in the codebase.

| # | Signal | What it looks like |
|---|--------|--------------------|
| S1 | Independent deliverables | Two or more outcomes that each deliver user value on their own ("add SSO **and** rebuild the dashboard"). |
| S2 | Unrelated-subsystem spread | Work touches subsystems that share no wiring path; a change in one neither depends on nor affects the other. |
| S3 | Mixed concerns | A feature bundled with an unrelated refactor or infra change that could ship by itself. |
| S4 | Multiple independent P1 stories | Several top-priority stories, each a standalone MVP per its own independent-test description, with no shared foundation. |
| S5 | No single definition-of-done | You cannot write one coherent "done" for the spec; "done" is really "these N separate things are each done." |
| S6 | Oversized plan | So many phases/todos that one execution thread can't track integration across them — **decisive only when the phases also decompose along independent-deliverable lines** (see [Length Is Not a Split](#length-is-not-a-split)). |

## Verdict

Return one verdict to the coordinator:

- **`single-block`** — one coherent deliverable, a connected wiring path, and a single definition-of-done. Stay as one spec even with several phases. This is the default; do not split a cohesive deliverable.
- **`should-split`** — the [decisive test](#the-decisive-test) finds a clean independent cut, **or** multiple strong signals co-occur (e.g., S1 + S2, or S3 + S5).

When signals conflict, the decisive test wins: if no clean independent cut exists, it is `single-block` regardless of how large it feels.

## Length Is Not a Split

A long, multi-phase spec is **not** automatically `should-split`. The execution model already handles length: research runs once, then execution loops **one scoped phase/todo-group per invocation**, so a deep but connected plan is executed in bounded steps without losing the thread.

Only split when the length comes with **independence** — phases that each produce a standalone deliverable. If every phase depends on the prior one and they wire into a single outcome, it is `single-block`; let scoped per-phase execution carry it.

## Split Strategy

When the verdict is `should-split`, propose (do not create) the breakdown:

1. **Find the cut lines.** The natural seams are independently-testable user-story / deliverable boundaries — the story's P1/P2/P3 prioritization and per-story independent-test descriptions already mark them.
2. **Define each child as its own spec.** Each child becomes a separate `.ai/specs/<child>/` directory with its own full artifact set (`README.md`, `[child].story.md`, `[child].spec.md`, `[child].plan.md`), named with a kebab-case feature name that describes its standalone deliverable.
3. **Re-test each child.** Apply the [decisive test](#the-decisive-test) to every proposed child — each must itself be `single-block`. If a proposed child is still too big, cut it again.
4. **Note ordering, not coupling.** True independent deliverables have no hard ordering dependency. If you find that child B cannot be wired until child A exists, that coupling is a sign the cut was wrong — reconsider whether A and B are really phases of one spec rather than two specs. Record a recommended sequence only as guidance.

## Recommendation, Not Auto-Split

Sizing is analysis and recommendation **only**. It never creates spec directories or moves files.

- `spec-research` returns the verdict and, when `should-split`, the proposed breakdown to the coordinator.
- The coordinator **recommends** the split to the user and waits for the decision. It does not create `.ai/specs/<child>/` directories as a side effect of sizing.
- If the user declines the split, execution proceeds on the spec as-is.
- A new spec is created only through the normal `createSpec` flow, after the user chooses to split.

Never treat `should-split` as a trigger to restructure the spec automatically.

## The Verdict Hand-Off

Return the sizing result in this shape (carry it inside the larger context brief `spec-research` returns):

```yaml
sizing:
  verdict: single-block        # single-block | should-split
  rationale: >-
    One or two sentences: which signals fired (or why none did) and the
    result of the decisive test.
  proposed_split:              # present ONLY when verdict = should-split
    - feature: sso-login       # kebab-case child feature name
      deliverable: "Standalone value this child ships on its own"
      covers: "Which stories / requirements / phases land here"
    - feature: admin-audit-log
      deliverable: "..."
      covers: "..."
  ordering_note: >-            # optional guidance only, never a hard dependency
    Recommended sequence and any soft prerequisite among the children.
```

`proposed_split` is a recommendation for the coordinator to present to the user — not an instruction to build anything.

## Examples

### `single-block` — cohesive deliverable

Spec: "Add a 30-minute inactivity session timeout to the existing auth flow." Phases: add the timeout check, surface the re-login prompt, add tests. Several phases, but all wire into one auth behavior; no phase ships as independent value.

→ **`single-block`.** No clean independent cut. Execute as one spec.

### `should-split` — bundled independent deliverables

Spec: "Add SSO login, build an admin audit-log dashboard, and migrate the user table to a new schema." Three outcomes (S1), in unrelated subsystems (S2), each shippable alone (S4), with no single definition-of-done (S5).

→ **`should-split`.** Recommend three child specs: `sso-login`, `admin-audit-log`, `user-schema-migration` — each its own `.ai/specs/<child>/`. Present the recommendation to the user; do not create the directories. The hand-off:

```yaml
sizing:
  verdict: should-split
  rationale: >-
    Three independent deliverables (S1) in unrelated subsystems (S2), each
    shippable alone (S4); the decisive test finds clean independent cuts.
  proposed_split:
    - feature: sso-login
      deliverable: "Users can sign in via the corporate identity provider"
      covers: "Story P1 + FR-001..FR-004; plan phases p1-p2"
    - feature: admin-audit-log
      deliverable: "Admins can view a searchable audit-log dashboard"
      covers: "Story P2 + FR-005..FR-009; plan phase p3"
    - feature: user-schema-migration
      deliverable: "User records migrated to the new schema with zero data loss"
      covers: "Story P3 + NFR-002; plan phases p4-p5"
  ordering_note: "Independent; sequence by team capacity. No hard prerequisite."
```

### `single-block` — long but connected (don't over-split)

Spec: "Build the data-import pipeline: parse → validate → load → report." Many phases and todos, but each stage consumes the previous stage's output and they wire into one pipeline; no stage delivers user value on its own.

→ **`single-block`.** Length alone (S6) is not decisive here — the phases do not decompose into independent deliverables. Scoped per-phase execution handles the depth.

## Pre-Handoff Check

Before returning a sizing verdict, confirm:

- [ ] The decisive test was applied — a clean independent cut either exists or it does not.
- [ ] The verdict is exactly `single-block` or `should-split`, with a one-or-two-sentence rationale.
- [ ] Length alone did not drive a `should-split`; a long-but-connected spec was kept `single-block`.
- [ ] On `should-split`, every proposed child is itself `single-block`, named in kebab-case, with its deliverable and coverage stated.
- [ ] The result is framed as a recommendation; no spec directories were created or files moved.
