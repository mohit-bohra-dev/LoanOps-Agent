# Story Review Write-Up Template

The exact structure of the review document the reviewer saves to
`{outputDir}/{story-name}.review.md` (default `outputDir` =
`.ai/working/story-reviews`). Fill every placeholder. Keep the story body out of
this file — reference the story by path.

```markdown
# Story Review: {story-name}

- **Story:** {storyPath}
- **Reviewed:** {YYYY-MM-DD}
- **Iteration:** {n}
- **Format contract:** {formatContract path/name, or "story package default"}

## Verdict

**{PASS | FAIL}** — Overall score: **{X.X}/5**

{One- to two-sentence summary of the story's state and the single most important
reason for the verdict.}

## Scorecard

| # | Dimension | Score | Rationale |
|---|---|---|---|
| 1 | Format & Structure | {1-5} | {why} |
| 2 | Value & Clarity | {1-5} | {why} |
| 3 | INVEST | {1-5} | {why} |
| 4 | Acceptance-Criteria Quality | {1-5} | {why} |
| 5 | Requirements & Traceability | {1-5} | {why} |
| 6 | Scope & Independence | {1-5} | {why} |
| 7 | Cross-Story Coherence | {1-5} | {why} |
| 8 | Boundary Discipline | {1-5} | {why} |
| — | **Overall (mean)** | **{X.X}** | — |

## Findings

List every finding, highest severity first. Omit a severity heading if it has no
findings.

### [CRITICAL] {finding title}
- **Location:** {section / line}
- **Issue:** {what is wrong}
- **Recommendation:** {specific, actionable fix}

### [HIGH] {finding title}
- **Location:** …
- **Issue:** …
- **Recommendation:** …

### [MEDIUM] {finding title}
- …

### [LOW] {finding title}
- …

## Cross-Review Analysis (arbor)

- **Query:** {the query used}
- **Sources searched:** {e.g. arbor-kbs, jira-confluence — or "none available"}
- **Related artifacts (cited):**
  - {title} — {citation} — {duplication | overlap | conflict | dependency | none}
- **Coherence assessment:** {duplication/overlap/conflict/dependency findings, or
  "no coherence issues found". If arbor was unavailable, state:
  "cross-review analysis limited: no sources available; assessed against sibling
  stories on disk only."}

## Required Changes (FAIL only)

An ordered, actionable list — one entry per must-fix (CRITICAL/HIGH) finding — that
the author must address on the next revision. Omit this section entirely on a PASS.

1. {change} (addresses: {finding title})
2. …
```

## Notes

- The **Required Changes** section is what the caller hands back to the author on
  a fail (via `reviewPath`); make each item self-contained and specific enough to
  action without re-reading the whole review.
- On a **PASS**, omit **Required Changes**; MEDIUM/LOW findings may remain as
  optional polish.
- Overwrite the same review path on each cycle iteration; the `Iteration` header
  records which pass produced the current verdict.
