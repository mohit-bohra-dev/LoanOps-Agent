---
name: spec-spec-review-rubric
description: >-
  The spec-implementation review methodology used by the spec-review agent:
  the requirement-coverage matrix (IMPLEMENTED / PARTIAL / MISSING plus a
  coverage percentage), test-coverage assessment with quality bands, plan-todo
  accuracy (false vs. unreported completions), the finding taxonomy (five
  categories plus critical/major/minor/info severity), the strict / normal /
  lenient strictness modes, the 0-100 health-score method, and the section
  spec for the persisted [feature].review.md artifact. Use when reviewing a
  spec implementation, scoring implementation health, classifying or
  prioritizing findings, assessing requirement or test coverage, reconciling
  plan todos, or writing the review artifact.
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "spec-review-rubric"
---

# Spec Review Rubric

The analytical method for reviewing an implementation against its spec: classify how
completely the implementation satisfies the spec, score its health, taxonomize the
problems found, and persist the result as a `[feature].review.md` artifact that a
follow-up `executeSpec` pass can consume.

This method is **schema-bound**. Its outputs populate the `reviewSpecImplementation`
`returns` object exactly, so the enums and field shapes below are not free choices —
they are the contract the calling prompt and downstream tooling depend on. See
[Invocation Contract](#invocation-contract) before emitting results.

## When to Use

- Reviewing a completed or in-progress spec implementation against story / spec / plan
- Computing an implementation health score
- Classifying findings by category and severity, or prioritizing them
- Assessing requirement coverage or test coverage
- Reconciling plan todos against the real codebase
- Writing the persisted `[feature].review.md` review artifact

## The Review Method

Run these passes in order. Each pass produces one part of the result object; later
passes depend on earlier outputs (findings reference coverage gaps; the health score
consumes all of them).

| Pass | Produces | Result field |
|------|----------|--------------|
| 1. Requirement coverage | per-requirement verdicts + coverage % | `requirementCoverage` |
| 2. Test coverage | expected vs. found + quality band + gaps | `testCoverage` |
| 3. Plan-todo accuracy | false / unreported completions + accuracy % | `trackerAccuracy` |
| 4. Findings | categorized, severity-ranked findings | `findings` |
| 5. Health score | 0-100 composite + summary + recommendations | `healthScore`, `recommendations`, `positiveNotes` |

The `scope` parameter narrows which passes run: `requirements` → Pass 1 only,
`tests` → Pass 2 only, `technical` → Pass 4 over technical-design adherence, `phase`
→ all passes restricted to one plan phase, `full` (default) → every pass.

## Pass 1 — Requirement Coverage

Classify **every** functional requirement (FR), non-functional requirement (NFR),
and acceptance scenario against the actual code. Each requirement gets one verdict:

| Verdict | Meaning | Counts in |
|---------|---------|-----------|
| `IMPLEMENTED` | Behavior present and matches the spec | `implemented` |
| `PARTIAL` | Present but incomplete (missing edge cases, partial behavior) | `partial` |
| `MISSING` | No implementation evidence found | `missing` |
| `UNABLE_TO_VERIFY` | Cannot be confirmed by static review (runtime-only behavior) | *(excluded — see below)* |

**Every verdict must cite evidence** — a `file.ts:L42` reference for IMPLEMENTED /
PARTIAL, or "no evidence found" for MISSING. A verdict without evidence is not valid.

**Coverage percentage** (populates `requirementCoverage.percentage`):

```text
percentage = round( (implemented + 0.5 × partial) ÷ total × 100 )
```

`total` = `implemented + partial + missing`. Keep these four counts internally
consistent: `total` must equal their sum. `UNABLE_TO_VERIFY` requirements are **not**
folded into the counts (they would distort coverage as either a pass or a gap);
instead surface each one as a finding (category `requirement`) and recommend the
manual verification needed.

## Pass 2 — Test Coverage

Compare the spec's test plan against the tests actually present.

- `testFilesExpected` — count of test files/areas the spec calls for.
- `testFilesFound` — count of test files that map to the feature.
- `missingAreas` — specific untested areas (e.g., `"integration tests for CLI commands"`).
- `qualityAssessment` — one band (enum: `excellent` | `good` | `adequate` | `poor`):

| Band | Criteria |
|------|----------|
| `excellent` | All expected areas covered — unit + integration + edge + error paths; tests are well-named, follow Arrange/Act/Assert, mock only at boundaries, run independently |
| `good` | Core areas covered with minor gaps (a few edge cases or one integration area missing); quality is solid |
| `adequate` | Happy path covered but notable gaps (edge/error/integration) or quality issues (over-mocking, weak assertions) |
| `poor` | Little or no meaningful coverage, or tests exist but assert little / are tightly coupled |

Quality (the band) and quantity (`found ÷ expected`) are distinct signals — a suite
can hit every expected file yet still be `poor`. Judge the band on what the tests
*verify*, not just how many files exist.

## Pass 3 — Plan-Todo Accuracy

Reconcile the plan's frontmatter todos against the real implementation state. The
two failure modes and the status lifecycle are defined in the **`spec-plan-format`**
skill — read it for the definitions of *false completion* and *unreported completion*
and for progress math. This pass applies that vocabulary to the review:

- `falseCompletions` — count of todos with `status: completed` but no implementation evidence.
- `unreportedCompletions` — count of done-but-unmarked todos (`pending`/`in_progress`).
- `percentage` — accuracy of tracking (populates `trackerAccuracy.percentage`):

```text
percentage = round( accurateTodos ÷ totalTodos × 100 )
```

A todo is **accurate** when its `status` matches the verified implementation state.
Surface every false completion as a finding (category `tracking`) — a todo marked
done with no code is a misleading signal, not a cosmetic issue.

## Pass 4 — Findings

Each problem becomes one finding. Every finding has a **category** and a **severity**.

**Categories** (enum — `requirement` | `technical` | `test` | `documentation` | `tracking`):

| Category | Use for |
|----------|---------|
| `requirement` | Unmet / partially met FR, NFR, or acceptance scenario |
| `technical` | Deviation from the spec's architecture, API, or data design |
| `test` | Missing tests or test-quality problems |
| `documentation` | Missing or stale docs, comments, or READMEs the spec requires |
| `tracking` | Plan-todo inaccuracy (false / unreported completion) |

**Severities** (enum — `critical` | `major` | `minor` | `info`):

| Severity | Meaning |
|----------|---------|
| `critical` | Missing core functionality, security gap, or broken contract — blocks sign-off |
| `major` | Significant deviation, missing tests on a key path, or incomplete feature |
| `minor` | Style deviation, small documentation gap, or low-impact improvement |
| `info` | Observation or suggestion — including intentional improvements over the spec |

For the full finding object shape, ID convention, per-severity fix actions, and the
mapping from these severities to the org code-review standard
(`critical`/`high`/`medium`/`low`), read
`references/finding-format-and-severity.md`. **Do not emit the org enum** in the
returns object — the `findings[].severity` field stays `critical`/`major`/`minor`/`info`.

## Strictness Modes

The `strictness` parameter changes the *thresholds* used in Passes 1 and 4 — not the
health-score formula. Stricter modes reclassify borderline requirements downward and
flag more deviations; the score then follows naturally from those inputs.

| Mode | Requirement classification | What to flag | Severity calibration |
|------|----------------------------|--------------|----------------------|
| `strict` | `IMPLEMENTED` only if it fully matches the spec including edge cases; any shortfall → `PARTIAL` | Every deviation, including stylistic and documentation | Escalate borderline findings one band; still record intentional improvements as `info` |
| `normal` *(default)* | `IMPLEMENTED` if core behavior matches; tolerate minor stylistic variance | Significant deviations, missing tests, incomplete features | Severities as defined; documented intentional improvements → `info`, not penalized |
| `lenient` | `IMPLEMENTED` if functionally present; tolerate partial non-core requirements | Only critical gaps and missing core functionality | De-escalate non-functional concerns one band; suppress `info` and minor doc nits |

When a deviation is an intentional improvement over the spec, classify it `info` (not
`critical`) regardless of mode, and recommend updating the spec to match.

## Pass 5 — Health Score

`healthScore` is a 0-100 composite of the measured passes, capped by the worst
unresolved finding.

**Component scores (each 0-100):**

- `coverageScore` = `requirementCoverage.percentage`
- `testScore` = `round( bandValue × min(1, testFilesFound ÷ max(1, testFilesExpected)) )`,
  where `bandValue` is `excellent=100`, `good=85`, `adequate=70`, `poor=40`
- `trackerScore` = `trackerAccuracy.percentage`

**Weighted base** (requirement coverage dominates — it is the primary measure of
whether the implementation matches the spec):

```text
base = 0.55 × coverageScore + 0.25 × testScore + 0.20 × trackerScore
```

For a scoped review that skips a pass (e.g., `requirements` scope has no test or
tracker pass), drop the missing terms and renormalize the remaining weights to sum
to 1.

**Severity ceiling** (unresolved high-severity problems cap health regardless of base):

- Any `critical` finding → `healthScore ≤ 70`
- Else any `major` finding → `healthScore ≤ 85`
- Else → no cap

```text
healthScore = round( min(base, ceiling) )   // clamped to 0-100
```

**Band interpretation** (for the summary narrative, not a separate field):

| Score | Reading |
|-------|---------|
| 90-100 | Excellent — ready to ship |
| 75-89 | Good — minor follow-ups only |
| 60-74 | Fair — address majors before sign-off |
| 0-59 | Poor — significant gaps remain |

`recommendations` is the prioritized action list (critical/major first); `positiveNotes`
records what was done well. Both are arrays of strings.

## Writing the Review Artifact

The spec-review agent persists the full review as `[feature].review.md` in the spec
directory, in addition to returning the JSON result. The artifact's section list and
the "Scoped Work Source" note that lets `executeSpec` consume it are specified in
`references/review-artifact-sections.md` — read it when authoring the file. Keep the
artifact and the returned JSON consistent: the same health score, coverage, findings,
and tracker numbers appear in both.

## Invocation Contract

A caller invokes this skill to review one implementation against its spec. The run gathers
evidence read-only from the codebase, runs the passes above, persists
`[feature].review.md`, and returns the structured result. There is no mode input — `scope`
narrows which passes run.

### Inputs

| Input | Type | Required | Meaning |
|---|---|---|---|
| `featureName` | string | no | The spec to review; resolves `.ai/specs/<featureName>` when `specDirectory` is absent, and names the persisted `[featureName].review.md`. |
| `specDirectory` | string | no | Path to the spec directory (absolute or relative). Defaults to `.ai/specs/<featureName>`. |
| `scope` | `full` \| `requirements` \| `technical` \| `tests` \| `phase` | no (default `full`) | Which passes run, per [The Review Method](#the-review-method). |
| `phase` | string | **yes when `scope: phase`** | The phase name or todo-id prefix from `[featureName].plan.md` (e.g. `"Phase 2"`, `"p2"`). |
| `strictness` | `strict` \| `normal` \| `lenient` | no (default `normal`) | Classification and severity thresholds, per [Strictness Modes](#strictness-modes). |

When neither `featureName` nor `specDirectory` is given, ask which spec to review.

### Procedure

1. **Resolve the spec directory** (`specDirectory`, else `.ai/specs/<featureName>`).
2. **Load the operational model.** Operate as `@./.cursor\agents\spec-review.md`, whose definition owns
   the reviewer's role, its read-only constraint, and its return contract. This skill is the
   method it applies.
3. **Run the passes** the `scope` selects, in order, gathering evidence read-only from the
   implementation. Every requirement verdict cites evidence.
4. **Persist `[feature].review.md`** in the spec directory per
   [Writing the Review Artifact](#writing-the-review-artifact). The artifact and the returned
   JSON must agree on every number.
5. **Return** the shape below with `reviewArtifactPath` set to the persisted file.

Never modify implementation code — the only file written is the review artifact. Never
fabricate a result: on an error, return it and stop.

### Returns

The result object must use these exact field names and enum values — they match the
`reviewSpecImplementation` `returns` schema:

- `success` — boolean
- `featureName` — the reviewed feature
- `healthScore` — number 0-100
- `requirementCoverage` — `{ total, implemented, partial, missing, percentage }`
- `findings[]` — `{ id, severity, category, title, description, specReference?, recommendation }`
  - `severity` ∈ `critical` | `major` | `minor` | `info`
  - `category` ∈ `requirement` | `technical` | `test` | `documentation` | `tracking`
  - `specReference` is included whenever a spec section applies
- `testCoverage` — `{ testFilesExpected, testFilesFound, qualityAssessment, missingAreas[] }`
  - `qualityAssessment` ∈ `excellent` | `good` | `adequate` | `poor`
- `trackerAccuracy` — `{ percentage, falseCompletions, unreportedCompletions }`
- `recommendations[]`, `positiveNotes[]` — arrays of strings
- `reviewArtifactPath` — path to the persisted `[feature].review.md`, consumable as the
  `reviewArtifact` input to `@./.cursor\skills\spec-spec-implementation-execution\SKILL.md`

Never introduce new enum values for `severity`, `category`, or `qualityAssessment`,
and never rename these fields.

### Errors

| Code | When | Recovery to offer |
|---|---|---|
| `SPEC_NOT_FOUND` | The resolved spec directory does not exist, or both the story and `[feature].spec.md` are missing | Check the feature name and that the directory exists |
| `INSUFFICIENT_SPEC` | Artifacts exist but contain no parseable requirements or technical design | Add technical detail to the spec, then re-review |
| `NO_IMPLEMENTATION` | None of the files the spec expects exist and no related code can be found | Implement the spec before reviewing it |

## Worked Example

A `full`, `normal`-strictness review of a feature with 6 functional requirements:

- **Pass 1 — coverage:** 4 `IMPLEMENTED` (each cited, e.g. `cleanup.ts:L42`), 1 `PARTIAL`
  (`cleanup.ts:L80`, missing edge case), 1 `MISSING` (no evidence). `total = 6`.
  `percentage = round((4 + 0.5×1) ÷ 6 × 100) = 75`. → `coverageScore = 75`.
- **Pass 2 — tests:** expected 5, found 4, quality `good` (85).
  `testScore = round(85 × min(1, 4÷5)) = 68`. `missingAreas: ["CLI integration tests"]`.
- **Pass 3 — tracker:** 8 todos, 1 false completion → 7 accurate.
  `percentage = round(7 ÷ 8 × 100) = 88`. `falseCompletions: 1`. → `trackerScore = 88`.
- **Pass 4 — findings:** `F-001` major/requirement (the `MISSING` FR), `F-002` minor/test
  (CLI integration gap), `F-003` major/tracking (the false completion). Highest = major.
- **Pass 5 — health:** `base = 0.55×75 + 0.25×68 + 0.20×88 = 75.85`. A major finding (no
  critical) caps at 85, which does not bind. `healthScore = round(min(75.85, 85)) = 76` —
  the **Good** band: minor follow-ups, no blockers.

`recommendations` leads with the major findings (`F-001`, `F-003`); `positiveNotes`
records the four cleanly implemented requirements. All of these numbers also appear in
the persisted `[feature].review.md`.

## Reference Documents

- `references/finding-format-and-severity.md` — Full finding object shape, the `F-NNN`
  ID convention, per-category and per-severity definitions with fix actions, the
  severity → org code-review (`critical`/`high`/`medium`/`low`) mapping, and example
  findings. Read when constructing or prioritizing findings.
- `references/review-artifact-sections.md` — Section-by-section spec for the
  `[feature].review.md` artifact, including the "Scoped Work Source" note that lets
  `executeSpec` consume it. Read when writing the persisted review file.
