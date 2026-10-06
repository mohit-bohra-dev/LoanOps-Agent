---
name: spec-spec-design-review-rubric
description: >-
  The pre-implementation spec-DESIGN review methodology used by the
  spec-design-reviewer agent: the five design-review passes (requirement
  coverage of the story's acceptance criteria, architectural soundness,
  buildability of the plan, testability, and cross-artifact consistency), the
  1-5 per-pass scoring, the pass/fail verdict and must-fix rule, the strict /
  normal / lenient strictness modes, the ordered Required Changes change-set,
  and the section spec for the persisted design-review write-up. Use when
  reviewing a technical spec's DESIGN before any code is written — scoring
  whether the spec, plan, and README are complete, sound, buildable, and
  consistent with the story — not when reviewing an implementation against a
  spec (that is spec-review-rubric).
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "spec-design-review-rubric"
---

# Spec Design Review Rubric

The analytical method for reviewing a **spec's design before implementation begins**:
judge whether the authored spec artifacts (`README.md`, `[feature].spec.md`,
`[feature].plan.md`) completely, soundly, and buildably express the story — then
return a pass/fail verdict plus an ordered set of Required Changes the author must
address before the design gate opens.

This is the **design** counterpart to `spec-review-rubric`. The two never overlap:

| | Subject | When | Question |
|---|---|---|---|
| **spec-design-review-rubric** *(this skill)* | the spec artifacts themselves | **before** implementation | Is this design complete, sound, and buildable? |
| `spec-review-rubric` | the implementation vs. the spec | **after** implementation | Does the code match the spec? |

The verdict shape (`score` 1-5, `verdict` pass/fail, `mustFixCount`) matches the
author → review → revise cycle the nexus story-review flow already uses, so a
coordinator can loop this review against the author until the design passes.

## When to Use

- Reviewing a `[feature].spec.md` (with its README and plan) before executing it
- Scoring whether a spec's design is complete, sound, buildable, testable, and consistent
- Producing the ordered Required Changes a spec author revises against
- Deciding a design-quality gate's pass/fail verdict in an author → review → revise loop

## The Review Method

Run these five passes in order. Each produces a 1-5 score and any findings for its
dimension. The verdict (below) is computed from the pass scores and the must-fix
findings.

| Pass | Dimension | Scores |
|------|-----------|--------|
| 1 | Requirement coverage — every story requirement/AC is addressed by a design element | `coverage` |
| 2 | Architectural soundness — components, data flow, and decisions are coherent and justified | `soundness` |
| 3 | Buildability — the plan's phases/todos are specific and executable; the spec meets the depth bar | `buildability` |
| 4 | Testability — the testing strategy covers the story's test cases and acceptance criteria | `testability` |
| 5 | Consistency — README, spec, and plan agree; no contradictions or dangling references | `consistency` |

Read the story (local `[feature].story.md`, external file, or Jira issue per
`@./.cursor\skills\spec-spec-artifact-model\SKILL.md`) and all spec artifacts before scoring. The
buildability pass applies the depth bar from `@./.cursor\skills\spec-technical-spec-authoring\SKILL.md`;
the plan-structure checks apply `@./.cursor\skills\spec-spec-plan-format\SKILL.md`.

## The 1-5 Scale

Each pass is scored on this scale. A score of **1 or 2 on any pass is an automatic
must-fix** (the design cannot pass the gate with a failing dimension).

| Score | Meaning |
|-------|---------|
| 5 | Exemplary — no gaps; an outside engineer could build from it directly |
| 4 | Solid — minor, non-blocking improvements only |
| 3 | Acceptable — real gaps that should be addressed but do not block building |
| 2 | Weak — gaps that would cause wrong or divergent implementation (must-fix) |
| 1 | Missing/unsound — the dimension is absent or broken (must-fix) |

## Pass 1 — Requirement Coverage

Map **every** story requirement to a design element. Use the story's stable IDs
(`FR-`, `NFR-`, `SC-`) and acceptance criteria / acceptance scenarios; when the story
is a Jira issue, use its acceptance criteria and any enumerated AC/TC.

- Each requirement is `ADDRESSED` (a specific spec section/decision satisfies it),
  `PARTIAL` (touched but underspecified), or `UNADDRESSED` (no design for it).
- Every `PARTIAL`/`UNADDRESSED` requirement is a finding; an `UNADDRESSED` functional
  requirement or acceptance criterion is **must-fix**.
- Cite the design location for `ADDRESSED` (e.g. `spec.md › Architecture › Stage 2`)
  and "no design found" for `UNADDRESSED`.

Score: 5 = every requirement addressed and traceable; 3 = a few partials; ≤2 = a core
requirement unaddressed.

## Pass 2 — Architectural Soundness

Judge whether the design would actually work and is justified.

- Components have clear responsibilities and interfaces; the data flow is complete
  (no step produces an output nothing consumes, none consumes an undefined input).
- Technical decisions state rationale, alternatives with why-not, and consequences
  (per `@./.cursor\skills\spec-technical-spec-authoring\SKILL.md`); a decision that is a bare assertion is a finding.
- Integration points name method, contract, and error handling. Reused/existing
  capabilities are invoked through stable contracts, not re-implemented.
- No unsound mechanism (a race, an unhandled failure path on a critical route, a
  contract that cannot hold). An unsound core mechanism is **must-fix**.

Score: 5 = coherent, justified, no gaps; ≤2 = a mechanism that would not work or a
core decision left unjustified.

## Pass 3 — Buildability

Judge whether an engineer who was **not** in the design conversation could implement
this without re-designing it — the depth bar from `@./.cursor\skills\spec-technical-spec-authoring\SKILL.md`.

- Each applicable spec section meets its depth bar (algorithms have pseudocode; data
  models have validation rules; decisions have alternatives; file structure separates
  new vs. modified with a purpose each).
- The plan's phases decompose into specific, verifiable `p{N}-slug` todos that map to
  the spec's file changes (per `@./.cursor\skills\spec-spec-plan-format\SKILL.md`); no phase is a vague
  "implement the feature".
- Nothing critical is deferred to "TBD" without an Open Technical Question capturing it.

Score: 5 = transcription-not-invention throughout; 3 = a section or phase needs
deepening; ≤2 = the spec gestures at an approach instead of specifying it.

## Pass 4 — Testability

Judge whether the design can be verified.

- The testing strategy names concrete scenarios mapped to the story's `FR-`/`SC-` IDs
  and acceptance criteria / test cases — not "we'll write unit tests".
- Each acceptance criterion / test case has a corresponding test or verification path.
- For a promp-package spec (artifacts, not code), "tests" legitimately means contract
  checks, `package-analyzer` rubric evaluation, and manifest/`promp validate` — the
  strategy must still say how each requirement is verified.

Score: 5 = every AC/TC has a verification path; ≤2 = no meaningful verification strategy.

## Pass 5 — Consistency

Judge whether the artifacts agree with each other and the story.

- README, spec, and plan describe the same feature, file set, and scope — no
  contradictions (e.g. the plan builds a file the spec never mentions, or the README
  promises a capability the spec drops).
- Cross-links resolve (`@./.cursor\skills\spec-spec-artifact-model\SKILL.md` cross-link rules); the story
  reference is consistent across artifacts; no leftover `{{placeholder}}` markers.
- Requirement IDs referenced in the spec/plan exist in the story.

Score: 5 = fully consistent; ≤2 = contradictions that would mislead the implementer.

## Strictness Modes

`strictness` changes the classification thresholds in Passes 1-5, not the verdict rule.

| Mode | Effect |
|------|--------|
| `strict` | Any shortfall against the depth bar or an unmapped requirement is a must-fix; flag stylistic and documentation gaps too. |
| `normal` *(default)* | Flag gaps that would cause wrong or divergent implementation; tolerate minor stylistic variance. |
| `lenient` | Flag only gaps that block building — unaddressed core requirements, unsound mechanisms, contradictions. Suppress minor/nice-to-have findings. |

## The Verdict

Compute the verdict from the pass scores and findings:

```text
overall = round1( mean(coverage, soundness, buildability, testability, consistency) )
mustFixCount = number of findings marked must-fix
             (every score ≤ 2 contributes at least one must-fix finding)

verdict = pass   when mustFixCount == 0 AND overall >= 3.5
        = fail   otherwise
```

- `score` returned to the caller is `overall` (1-5, one decimal).
- A `pass` means the design is good enough to implement — not that it is perfect;
  `should-fix` findings can be recorded for later without blocking.
- A `fail` returns the ordered Required Changes as the authoritative change set for the
  author's revise pass.

## Required Changes

Findings become an **ordered, actionable** Required Changes list — must-fix first,
then should-fix. Each item is a specific change the author can make, not a complaint.

| Field | Content |
|-------|---------|
| `id` | `RC-001`, `RC-002`, … (stable within one review) |
| `severity` | `must-fix` (blocks the gate) or `should-fix` (record, non-blocking) |
| `pass` | which pass raised it (`coverage` / `soundness` / `buildability` / `testability` / `consistency`) |
| `location` | the artifact + section to change (e.g. `spec.md › Technical Decisions › Decision 4`) |
| `change` | the specific, actionable change to make |
| `why` | the gap it closes (the requirement missed, the ambiguity, the contradiction) |

A finding without an actionable `change` is not a valid Required Change — rewrite it
until the author knows exactly what to do.

## The Design-Review Write-Up

The spec-design-reviewer persists the full review to its `outputDir` (e.g.
`.ai/working/spec-design-reviews/[feature]-[iteration].md`) and returns its path. The
numbers in the write-up (verdict, overall score, per-pass scores, mustFixCount) MUST
equal what the agent returns to its caller. Sections, in order:

1. **Header** — feature, story reference, iteration, strictness, date.
2. **Verdict** — `pass` | `fail`, `overall` score, `mustFixCount`, one-line rationale.
3. **Pass Scores** — a row per pass: dimension, score (1-5), one-sentence justification.
4. **Requirement Coverage** — the requirement → design-element map with ADDRESSED /
   PARTIAL / UNADDRESSED verdicts and citations.
5. **Required Changes** — the ordered table above, must-fix first. On a `pass` with no
   must-fix items, state "No blocking changes" and list any should-fix items.
6. **Strengths** — what the design does well (so a revise pass does not regress it).

## Worked Example

A `normal`-strictness review of a spec whose story has 8 acceptance criteria (AC-1…AC-8):

- **Pass 1 coverage = 4** — AC-1…AC-7 each map to a design element (cited); AC-8
  (unready-input refusal) is only mentioned in prose with no mechanism → `PARTIAL`,
  finding `RC-001` (should-fix).
- **Pass 2 soundness = 5** — stages, data flow, and decisions are coherent and justified.
- **Pass 3 buildability = 3** — one plan phase ("wire the gates") is not decomposed into
  verifiable todos → `RC-002` (must-fix, buildability score 3 with a must-fix item).
- **Pass 4 testability = 4** — TC-1…TC-4 map to verification paths; one lacks a concrete check → `RC-003` (should-fix).
- **Pass 5 consistency = 5** — README, spec, plan agree; links resolve.
- **Verdict:** `overall = round1(mean(4,5,3,4,5)) = 4.2`, but `mustFixCount = 1` (`RC-002`)
  → **fail**. Required Changes: `RC-002` (must-fix) first, then `RC-001`, `RC-003`.

A filled Required Changes row and coverage-map entries look like:

| id | severity | pass | location | change | why |
|----|----------|------|----------|--------|-----|
| RC-002 | must-fix | buildability | `plan.md › Phase 4 "wire the gates"` | Decompose Phase 4 into verifiable `p4-*` todos — one per gate plus traceability — each naming the artifact it changes | The phase is a single vague task; an implementer cannot tell when it is done (AC-3, AC-5) |

Coverage-map entries cite the design location per requirement:

- `AC-7 (traceability) → ADDRESSED → spec.md › Data Model › Traceability`
- `AC-8 (unready-input refusal) → PARTIAL → spec.md › Edge Cases (prose only, no mechanism)`

The author revises against those Required Changes; the next iteration re-scores and, if
`RC-002` is resolved and no new must-fix appears, returns `pass`.

## Invocation Contract

A caller invokes this skill to run the design gate on one spec. The run reads the story and
the authored artifacts, scores the five passes, persists the write-up, and returns the
verdict. There is no mode input.

### Inputs

| Input | Type | Required | Meaning |
|---|---|---|---|
| `featureName` | string | no | The spec to review; resolves `.ai/specs/<featureName>` when `specDirectory` is absent. |
| `specDirectory` | string | no | Path to the spec directory. Defaults to `.ai/specs/<featureName>`. |
| `storySource` | string | no | The approved story the design is measured against — a story **file path**, a Jira **issue key**, or the local `[featureName].story.md` (detected by shape). Defaults to the local story in the spec directory. |
| `strictness` | `strict` \| `normal` \| `lenient` | no (default `normal`) | Classification thresholds per [Strictness Modes](#strictness-modes). |
| `outputDir` | string | no (default `.ai/working/spec-design-reviews/`) | Where the write-up is persisted. |
| `iteration` | number | no (default `1`) | The review pass number; names the write-up and tracks the author → review → revise loop. |

When neither `featureName` nor `specDirectory` is given, ask which spec to review and stop
— do not start a review without a resolved spec directory.

### Procedure

1. **Resolve the spec directory** (`specDirectory`, else `.ai/specs/<featureName>`). If it
   does not exist, return `SPEC_NOT_FOUND` and stop.
2. **Load the operational model.** Operate as `@./.cursor\agents\spec-design-reviewer.md`, whose
   definition owns the reviewer's role, constraints, and return contract. This skill is the
   method it applies.
3. **Run the five passes** in order per [The Review Method](#the-review-method), scoring
   each 1–5 and recording findings.
4. **Compute the verdict** per [The Verdict](#the-verdict) and order the Required Changes
   must-fix first.
5. **Persist the write-up** to `outputDir` as `[feature]-[iteration].md` per
   [The Design-Review Write-Up](#the-design-review-write-up). Its numbers MUST equal the
   returned ones.
6. **Return** the shape below.

The reviewer is an investigator: it never rewrites the spec artifacts, and there is **no
`questions` path** — an unreachable story source becomes a must-fix coverage finding while
the other four passes still run.

### Returns

```json
{
  "status": "success",
  "reviewPath": ".ai/working/spec-design-reviews/payment-retries-1.md",
  "verdict": "fail",
  "score": 4.2,
  "mustFixCount": 1,
  "shouldFixCount": 2,
  "passScores": { "coverage": 4, "soundness": 5, "buildability": 3, "testability": 4, "consistency": 5 },
  "summary": "fail — overall 4.2; 1 must-fix (undecomposed gate phase), 2 should-fix."
}
```

| Field | Meaning |
|---|---|
| `verdict` | `pass` (opens implementation) or `fail` (return to the author with the Required Changes). |
| `score` | `overall`, 1–5 to one decimal — the rounded mean of the five pass scores. |
| `mustFixCount` / `shouldFixCount` | Counts of Required Changes by severity. `pass` requires `mustFixCount == 0` **and** `score >= 3.5`. |
| `passScores` | The five per-pass scores. |
| `reviewPath` | The persisted write-up — consumable as the `reviewPath` input to `@./.cursor\skills\spec-technical-spec-authoring\SKILL.md` (`mode: revise`). |

### Errors

| Code | When | Recovery to offer |
|---|---|---|
| `SPEC_NOT_FOUND` | The spec directory or `[featureName].spec.md` does not exist | Check the feature name, or author the spec first |
| `INSUFFICIENT_SPEC` | The artifacts exist but contain no parseable design to review | Deepen the spec, then re-review |
| `WRITE_FAILED` | The write-up could not be persisted after the review computed | Resolve the write failure; the computed verdict and score are included so the result is not lost |

## Constraints on the Method

- Review the **design**, never the implementation — no code exists yet at this stage.
- Never rewrite the spec artifacts; produce findings the author acts on (the reviewer
  is an investigator).
- Keep the write-up numbers identical to the returned verdict/score/mustFixCount.
- Do not invent requirements the story does not state; coverage is measured against the
  story, and a spec that over-builds beyond the story is a `should-fix` scope note.
