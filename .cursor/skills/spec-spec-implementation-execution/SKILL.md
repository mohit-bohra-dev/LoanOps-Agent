---
name: spec-spec-implementation-execution
description: >-
  How the spec-execution agent implements one scoped unit (a phase or
  todo-group) of a spec and wires it into the system: the scoped-task
  discipline (create / modify / test / docs), the wiring discipline that
  connects every integration point — calls, route/command registration,
  config references, imports — so nothing is left defined-but-unwired, the
  assumption-vs-blocking-question contract for pre-confirmed small gaps versus
  larger unknowns, when a plan todo may be marked completed, and the tiered
  quality-gate strategy (detect aidev → repo package.json scripts →
  skip-with-note). Use when executing a scoped phase or todo, wiring an
  implementation into the rest of the codebase, deciding whether to assume or
  ask, marking todo progress, or running quality gates after implementing a
  unit.
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "spec-implementation-execution"
---

# Spec Implementation Execution

How to execute **one scoped unit** of a spec — a single phase (`p2`) or a
todo-group — and leave behind a *complete, wired* implementation. Guard against
two failure modes on every unit: implementing beyond the scoped unit, and
authoring code without wiring it into the system (a function defined but never
called, a route never registered, a config never read).

Three disciplines carry the load, in order on every unit:

1. **Scope** — implement only the assigned unit; resist scope creep.
2. **Wire** — connect every integration point and *verify* the unit is reachable
   from the running system, not just present in the tree.
3. **Verify & gate** — run quality gates, then update todos to match reality.

## When to Use

- Executing a scoped phase or todo-group of a spec implementation
- Wiring a newly authored unit into the rest of the codebase
- Deciding whether a small gap is a documented assumption or a blocking question
- Determining when a plan todo may move to `completed`
- Running quality gates after implementing a unit (aidev / repo scripts / skip)
- Executing fixes from a `[feature].review.md` work source

## The Scoped Unit

Work the unit you were handed — nothing more. The caller scopes execution to a
phase (e.g. `p2`) or a specific todo (e.g. `p2-register-command`); the plan's
todos are the authoritative task list and the matching body section is the
authoritative how. Read both from `[feature].plan.md` (see the
**`spec-plan-format`** skill for the frontmatter/body split and todo IDs, and
**`spec-artifact-model`** for where artifacts live).

Scope rules:

- Implement only the todos in the assigned unit. If you discover work outside
  the unit, **note it** (as an assumption or a follow-up) — do not silently
  expand scope to fix it.
- Pull *what* and *tracking* from the todos; pull *how* (file paths, code
  examples, test requirements) from the matching body phase section.
- Pull *why* and acceptance criteria from `[feature].story.md`, and technical
  design from `[feature].spec.md`, when the unit needs them.
- If a `[feature].review.md` is the work source, treat its **Critical/Major
  findings** and **MISSING/PARTIAL requirements** as the scoped unit, in that
  priority order.

## Implementing the Unit

A scoped unit is one or more of these task types. The mechanics of writing code
and tests are standard; what matters here is doing each type *scoped* and
*wired*.

| Task type | Do | Wiring obligation |
|-----------|----|-------------------|
| **Create** new file/module | Implement the interfaces/functions the body section specifies | Import/export it where consumers need it; register it (route, command, DI container, index) — a new file no one imports is dead code |
| **Modify** existing file | Read it first; make the change; **preserve existing behavior** and callers | Update every call site affected by a signature/behavior change |
| **Test** | Add tests for the unit's behavior and the spec's edge/error cases | Place them where the suite actually runs — an orphaned test file that no runner picks up does not count |
| **Docs** | Update only docs the spec requires for this unit (README rows, usage) | Link new docs from their index; verify commands/examples actually run |

Read existing files before changing them, follow the repo's established
conventions and patterns, and keep the change minimal and on-scope.

## Wiring Discipline

This is the core fix. **Authoring is not wiring.** A unit is done only when its
new behavior is reachable from the running system. After implementing, trace
every new or changed symbol to its consumer and confirm the connection exists.

Walk this integration-point checklist for the unit — for each item you
introduced, confirm the connecting edge is present:

- [ ] **Function / method** defined → it is **called** (or exported and called
      by a consumer). No defined-but-uncalled functions.
- [ ] **New file / module** created → it is **imported** somewhere that runs.
- [ ] **Route / endpoint / handler** added → it is **registered** with the
      router/server.
- [ ] **CLI command / subcommand** added → it is **registered** in the command
      index/parser.
- [ ] **Config key / env var / feature flag** added → it is **read** by code,
      and a default/sample is set where the repo expects one.
- [ ] **Event / message handler / subscriber** added → it is **subscribed** to
      the emitter/bus/queue.
- [ ] **DB migration / schema / model** added → it is **referenced** by the data
      layer and the migration is registered to run.
- [ ] **Dependency** added to the manifest → it is **imported and used** (and
      the lockfile updated).
- [ ] **Export** added to a public surface → it is **re-exported** through the
      package's entry/index if consumers reach it that way.

Verification, not assumption: for each new symbol, find its call/registration
site by searching the codebase. If you cannot find one and the spec implies the
unit should be active, the unit is **not** wired — finish the connection before
moving on. If the spec intentionally defers wiring to a later phase, record that
as an assumption so it is not mistaken for an omission.

A unit that passes type-checks and tests can still be unwired (a registered-
nowhere command compiles fine). Wiring is a *separate* check from compilation
and tests — do all three.

## Assumptions vs. Blocking Questions

You operate a three-path contract. Never silently guess on a real unknown.

- **Pre-confirmed small gap → assume and record.** When the gap is small and
  within the latitude the coordinator/research pass already granted (a naming
  choice, an obvious default, a local convention), make the reasonable choice,
  proceed, and **record the assumption** (what you assumed and why) so the
  coordinator can document it in the deliverable.
- **Larger unknown beyond that latitude → ask.** When resolving the gap could
  change the design, the contract, or the scope — or when two reasonable choices
  lead to materially different implementations — **stop and return a blocking
  question.** Do not assume past the pre-confirmed small-gap boundary.
- **Unrecoverable failure → return an error.** When the unit cannot be completed
  after reasonable retries (persistent gate failure you cannot fix on-scope,
  missing prerequisite), return an error with what blocked you.

The test for "small": if you would be comfortable having the assumption listed
in the deliverable for the user to glance at and correct later, it is small. If
it warrants a decision before code is written, it is a blocking question.

## Updating Plan Todos

Record progress in `[feature].plan.md`'s frontmatter todos. The status
lifecycle, the edit discipline (touch only the `status` field), and the
false-vs-unreported-completion failure modes are defined in the
**`spec-plan-format`** skill — follow it; do not restate its mechanics here.

The one rule this skill adds: **a todo moves to `completed` only when its work
is implemented, wired, and gate-verified.** A unit that is authored but not
wired, or whose gates have not been run (or explicitly noted as skipped), is
still `in_progress`. Move a todo to `in_progress` when you start it. If you did
work no todo covers, add a todo for it with the correct `p{N}-` prefix rather
than leaving it untracked.

## Quality Gates (Tiered)

After implementing and wiring the unit, run quality gates using the **first
available tier**. aidev is **optional and runtime-detected** — never assume it
is present; always run the detection algorithm first.

1. **aidev present** — `.ai/project.json` (valid JSON, `version === 1`) **and** a
   resolvable `@pennymac/aidev` CLI. Run `aidev workflow run -p <repo>` (list the
   steps first with `aidev workflow list -p <repo>`). On failure, fix at the
   source following aidev's own triage.
2. **else repo scripts** — detect `package.json` scripts (test, lint, typecheck,
   build) and run the available ones in dependency order.
3. **else skip-with-note** — no runnable gates; record a noted assumption in the
   deliverable that gates were skipped and recommend setting them up.

The full ordered detection algorithm, the `aidev_present` definition, the
invocation table, the conditional aidev triage references, the tier-2 fallback
script behavior, and the bootstrap suggestion live in
`references/quality-gate-detection.md` — **read it before running gates.**

Gate discipline: fix failures at the source before marking the unit complete.
Never disable a check, lower a threshold, or skip a failing test to make gates
pass — an unfixable failure is a blocking question or an error, not a silent
pass. Whichever tier ran (and which commands), record it so the coordinator can
report it.

## Returning Results

Return a single status to the caller (the coordinator), never talking to the
user directly:

- **success** — the scoped unit is implemented, wired, and gate-verified.
  Report: todos completed, files changed, tests added, gate tier + results, and
  any **assumptions** recorded for documentation.
- **questions** — a larger unknown blocked the unit. Report the specific
  question(s) and what you need to proceed; do not assume past the unit.
- **error** — the unit could not be completed after retries. Report what blocked
  you, the partial work done, and recommended next steps.

## Worked Example

Scope: the single todo `p2-register-command` — "Add a `prune` CLI command."

1. **Scope & read** — `p2-register-command` is the only assigned todo. Read its
   body section: create `src/commands/prune.ts` and wire it into the CLI.
2. **Implement** — set the todo `in_progress`; create `prune.ts` exporting the
   command; add `prune.test.ts` next to the suite that runs.
3. **Wire** — author is not done: search for the command index
   (`src/commands/index.ts`). The new command is *not* registered there, so the
   CLI cannot reach it. Register it. Confirm the registration edge now exists.
4. **Gate** — detect: no `.ai/project.json`, but `package.json` has `test` and
   `lint:check`. Tier 2 — run both; fix a lint failure at the source; re-run green.
5. **Resolve a gap** — the body did not specify the `--dry-run` default. That is a
   small, pre-confirmed gap → assume `false`, record the assumption. (If it had
   instead been "which storage backend?", that would be a blocking question.)
6. **Complete & return** — implemented + wired + gates green → move
   `p2-register-command` to `completed`. Return `success` with the file list,
   gate tier (repo scripts: `test`, `lint:check`), and the recorded `--dry-run`
   assumption for the coordinator to document.

## Invocation Contract

Everything above governs **one scoped unit**. A caller can also invoke this skill to run
a spec **end to end** — the research → triage → scoped-execution loop that produces those
units in the first place. That whole-spec run is what this contract specifies; the
per-unit disciplines above are what each iteration of its loop applies.

There is no mode input: scope is expressed by the optional selectors below. With none of
them, the full plan runs.

### Inputs

| Input | Type | Required | Meaning |
|---|---|---|---|
| `featureName` | string | no | The spec to execute; resolves `.ai/specs/<featureName>/`. When absent, ask which spec to execute once the run has control. |
| `phase` | string | no | Scope the run to one phase — a phase prefix from the plan (`p1`, `p2`) or a phase name. |
| `task` | string | no | Scope the run to one todo id from the plan frontmatter (e.g. `p1-create-utility`). |
| `reviewArtifact` | string | no | Path to a `[featureName].review.md`. When given, the review's **findings** — not the plan's phases — become the work source for the loop. |

### Procedure

1. **Resolve the spec directory.** When `featureName` is given and
   `.ai/specs/<featureName>/` does not exist, return `SPEC_NOT_FOUND` and stop — do not
   start a run against a spec that is not there.
2. **Load the operational model.** Operate as `@./.cursor\agents\spec-execution-coordinator.md`,
   whose definition owns the loop, its delegation model, and its user-facing contract,
   together with `@./.cursor\skills\spec-spec-plan-format\SKILL.md` and `@./.cursor\skills\spec-spec-artifact-model\SKILL.md`.
3. **Run the loop** as the coordinator defines it: ground the spec once via
   `@./.cursor\agents\spec-research.md`; triage the open questions it surfaces (answer from context,
   escalate only genuine unknowns, record answers on the story); recommend a split when
   sizing says `should-split` and let the user decide; then execute **one unit per
   iteration** via `@./.cursor\agents\spec-execution.md`, applying the scope, wiring, and gate
   disciplines above to each.
4. **Drive the tracker lifecycle** through the story package —
   `@./.cursor\skills\story-story-jira-lifecycle\SKILL.md` with `operation: assign` at the start and
   `operation: transition` at the start and on completion. Never reach into Atlassian from
   here.
5. **Return** the progress summary below when the loop ends, on completion, escalation, or
   error.

The coordinator is the only agent that talks to the user during the run; sub-agents return
to it, not to the user. Blocking questions and sub-agent errors are handled in-conversation
by the coordinator rather than returned as errors from this contract.

### Returns

```json
{
  "success": true,
  "featureName": "package-version-cleanup",
  "phase": "Phase 2: CLI Integration",
  "todosCompleted": [
    "p2-create-command: Create prune command file",
    "p2-command-options: Add command options"
  ],
  "todosRemaining": 86,
  "percentComplete": 30,
  "assumptionsMade": [
    "Reused the existing logger instead of adding a dependency (documented in spec.md)"
  ],
  "openQuestionsRaised": [],
  "filesChanged": [
    "packages/cli/src/commands/prune.ts (created)",
    "packages/cli/src/index.ts (modified)"
  ]
}
```

| Field | Meaning |
|---|---|
| `success` | Whether the in-scope work completed without an unrecoverable error. |
| `featureName` | The spec that was executed. |
| `phase` | The phase scope of the run, or `null` when the full plan ran. |
| `todosCompleted` | Todos completed this run, each as `id: summary`. |
| `todosRemaining` | Count of todos not yet complete across the plan. |
| `percentComplete` | Overall plan completion (0–100) after this run. |
| `assumptionsMade` | Confirmed assumptions execution acted within, each noting where it was documented. |
| `openQuestionsRaised` | Big open questions raised this run and their disposition — answered from context, recorded on the story, or escalated. |
| `filesChanged` | Files created or modified, aggregated from the execution units. |

### Errors

| Code | When | Recovery to offer |
|---|---|---|
| `SPEC_NOT_FOUND` | `featureName` resolves to a `.ai/specs/<featureName>/` directory that does not exist, checked before the run starts | Check the spelling, or author the spec first |

## Reference Documents

- `references/quality-gate-detection.md` — The ordered aidev-vs-repo-scripts-vs-
  skip detection algorithm, the `aidev_present` definition, the invocation
  strategy table, the conditional `{{rule:aidev.workflowTriage}}` /
  `{{skill:aidev.*}}` triage references, the tier-2 `package.json` script
  fallback, and the bootstrap suggestion. Read before running quality gates.
