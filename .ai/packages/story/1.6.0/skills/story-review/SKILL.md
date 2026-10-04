---
name: story-review
description: >-
  Standard methodology for reviewing a [name].story.md and producing a written
  verdict. Defines the eight-dimension grading rubric (format & structure, value
  & clarity, INVEST, acceptance-criteria quality, requirements & traceability,
  scope & independence, cross-story coherence, boundary discipline), the 1–5
  scoring scale, the overall-score and pass/fail rules, the cross-review analysis
  performed via the arbor search package ({{skill:arbor.kb-search}}), and the
  standard write-up saved under .ai/working/. Use when reviewing a story, scoring
  it, or deciding whether it passes — grading against the story-authoring
  standards (and a caller-supplied format contract when provided).
---

# Story Review

How to review a `[name].story.md`, grade it against a standard rubric, ground the
review in cross-story/prior-art analysis via arbor search, and emit a written
verdict (a saved write-up plus an overall score and a pass/fail). This is the
counterpart to `story-authoring`: authoring produces a story; review evaluates one
against the same standards and returns an actionable verdict.

The review **never edits the story** — it only reads the story, grades it, writes
a review document, and returns the verdict. Acting on a failing review (revising
the story) is the author's job, driven by the review the caller passes back.

## When to Use

- The `review-story` prompt or the `story-reviewer` agent evaluates a story
- A caller (e.g. nexus `create-story`) runs an author → review → revise cycle and
  needs a scored, written verdict to decide pass/fail and drive revisions
- Deciding whether a story meets the bar for its parent epic and the backlog

## The Grading Rubric

Score each of the eight dimensions from **1 to 5** (5 = excellent, 3 = acceptable,
1 = unacceptable). Grade against `{{skill:story-authoring}}` and the active
`formatContract`.

| # | Dimension | What a 5 looks like |
|---|---|---|
| 1 | **Format & Structure** | Conforms exactly to the format contract — all required sections present, non-empty, in order; frontmatter complete. |
| 2 | **Value & Clarity** | Clear user value; "As a / I want / so that" reads cleanly; understandable to a non-technical stakeholder. |
| 3 | **INVEST** | Independent, Negotiable, Valuable, Estimable, Small, Testable — all hold. |
| 4 | **Acceptance-Criteria Quality** | Specific, testable criteria (Given/When/Then or checkbox); covers happy path, edge cases, and error conditions; relevant user types appear as criteria, not as separate stories. |
| 5 | **Requirements & Traceability** | Complete; stable IDs where the format uses them; unknowns marked `[NEEDS CLARIFICATION]` rather than guessed; aligns with the parent epic's goals. |
| 6 | **Scope & Independence** | One feature or discrete portion — not duplicated per persona or technical layer; dependencies are realistic and named. |
| 7 | **Cross-Story Coherence** | No duplication, overlap, or conflict with sibling stories/epics/prior art; consistent terminology (see Cross-Review Analysis). |
| 8 | **Boundary Discipline** | Stays within the format's abstraction level — technology-agnostic where required; no implementation leakage. |

### Overall score

`overall = mean(dimension scores)`, rounded to one decimal (1.0–5.0).

### Verdict (pass/fail)

- **pass** when **all** of: `overall ≥ 4.0` **and** every dimension `≥ 3` **and**
  there are no open **CRITICAL** or **HIGH** findings.
- **fail** otherwise.

The threshold is deliberately strict so an author → review → revise cycle
converges on a genuinely solid story rather than a barely-acceptable one.

### Findings and severity

Record concrete findings, each with a severity, a location (section/line), the
issue, and a specific recommendation:

| Severity | Meaning |
|---|---|
| **CRITICAL** | Blocks acceptance — missing required section, untestable AC, duplicates an existing story, boundary violation that breaks the format. |
| **HIGH** | Should fix before acceptance — a dimension scored 2, a material gap. |
| **MEDIUM** | Improve — a dimension scored 3 with a clear upgrade path. |
| **LOW** | Nice-to-have polish. |

**Must-fix = CRITICAL + HIGH.** These are the changes a failing review hands back
to the author.

## Cross-Review Analysis (via arbor)

Every review performs **cross-review analysis** — checking the story against
sibling stories, parent/related epics, and prior art — grounded through the arbor
search package. This is what powers dimension 7 (Cross-Story Coherence).

1. Build a query from the story's title, its `## Story Description`, and its key
   acceptance-criteria terms (and the parent epic's theme when known).
2. Run **{{skill:arbor.kb-search}}** with that `query` (pass `filters` such as
   `spaces`/`dateRange` when targeting Confluence/Jira is useful). Results come
   back **grouped by source, each cited**.
3. Compare the returned stories/pages/issues against the story under review:
   - **Duplication** — another story already delivers this capability → CRITICAL.
   - **Overlap / boundary blur** — a sibling story shares scope → HIGH/MEDIUM.
   - **Conflict** — contradictory acceptance criteria or terminology → HIGH.
   - **Missing dependency** — related work this story should depend on → MEDIUM.
4. Record the query, the sources searched, the cited related artifacts, and the
   coherence assessment in the write-up's Cross-Review Analysis section.

**Soft-fail, never block.** arbor search is best-effort: if no sources are wired
(`NO_KBS_ATTACHED`) or a source is degraded/unauthenticated, note it in the
write-up ("cross-review analysis limited: no sources available") and grade
dimension 7 from the sibling stories readable on disk instead. Never abort the
review because arbor is unavailable.

## The Write-Up

Produce one review document per invocation and save it to
`{outputDir}/{story-name}.review.md` (default `outputDir` =
`.ai/working/story-reviews`). Overwrite the same path on each iteration of a cycle
(latest verdict wins); note the `iteration` in the header. Follow
`references/review-writeup-template.md` for the exact structure: verdict + overall
score, the per-dimension scorecard with rationale, the findings list by severity,
the cross-review analysis (cited), and — on a fail — an ordered **Required
Changes** list mapping to the must-fix findings so the author can act on it
directly.

Keep the write-up on disk and return only its path, the overall score, and the
verdict to the caller (per `disk-based-data-flow` — the review body stays on
disk).

## Invocation Contract

Invoked by the `reviewStory` prompt and the `{{agent:story-reviewer}}` agent (which
formats the return as its own status envelope), or directly by any caller with the
inputs below.

### Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `storyPath` | string | Yes | Path to the `[name].story.md` to review. |
| `formatContract` | string | No | The format the story must conform to — a template path or an inline section-contract (e.g. a caller's story-format rule). When absent, grade against the package's `story.md.template` and `{{skill:story-authoring}}`. |
| `outputDir` | string | No | Where to write the review. Default `.ai/working/story-reviews`. |
| `iteration` | number | No | The review pass number in a cycle (1, 2, …), recorded in the write-up header. Default `1`. |
| `context` | string | No | Grounding the caller already gathered (parent epic, sibling stories, cited research) so the review need not re-derive it. |

### Procedure

1. **Read the story** at `storyPath` and, when reachable, the parent epic and
   sibling stories for coherence. If no readable story exists, raise
   `STORY_NOT_FOUND` and stop.
2. **Grade** all eight rubric dimensions 1–5, recording findings with severity,
   location, and a specific recommendation.
3. **Run cross-review analysis** per [Cross-Review Analysis](#cross-review-analysis-via-arbor)
   — best-effort; note the limitation and continue when no sources are wired.
4. **Compute** the overall score (mean) and the verdict per the rule above.
5. **Write the review** to `{outputDir}/{story-name}.review.md` following
   `references/review-writeup-template.md`; on a fail, include the ordered
   **Required Changes** list.
6. **Return** the result below — the write-up body stays on disk.

### Returns

```json
{
  "success": true,
  "reviewPath": ".ai/working/story-reviews/payment-retries.review.md",
  "score": 4.2,
  "verdict": "pass",
  "iteration": 1,
  "mustFixCount": 0,
  "summary": "The story is well-formed and independently testable; one MEDIUM polish item on edge-case coverage."
}
```

| Field | Meaning |
|---|---|
| `success` | Whether the review was produced. |
| `reviewPath` | Path to the saved review write-up. |
| `score` | Overall score, 1.0–5.0 (mean of the eight dimensions). |
| `verdict` | `pass` or `fail` per the rule above. |
| `iteration` | The review pass number. |
| `mustFixCount` | Count of open CRITICAL + HIGH findings (the must-fix set). |
| `summary` | One-line verdict rationale. |

### Errors

| Code | Raised when | Recovery |
|---|---|---|
| `STORY_NOT_FOUND` | No readable story file exists at `storyPath`. Carries `storyPath`. | Check the path, or author the story first per `{{skill:story-authoring}}`. |

An unavailable or degraded arbor source is **not** an error — it is noted in the
write-up and dimension 7 is graded from the sibling stories on disk.

## Reference Documents

- `references/review-writeup-template.md` — The exact structure of the review
  write-up (header, verdict, scorecard, findings, cross-review analysis, required
  changes). Follow it when writing the review document.
