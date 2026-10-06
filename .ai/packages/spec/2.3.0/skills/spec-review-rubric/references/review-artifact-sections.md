# Review Artifact Section Spec

The section list for the persisted `[feature].review.md` artifact the spec-review
agent writes. This is a section spec, not a template engine — author the file as
standard markdown using these sections in this order. Read when writing the review
file.

## File

- **Path:** `[feature].review.md` in the spec directory (alongside `[feature].story.md`,
  `[feature].spec.md`, `[feature].plan.md`).
- **Consistency:** the numbers in this file (health score, coverage, findings, tracker
  accuracy) must match the returned JSON result exactly. The artifact is the
  human-readable view of the same review.

## Sections (in order)

### 1. Title & Metadata

A heading and a one-line metadata block.

```markdown
# Spec Implementation Review: [feature]

Scope: full · Strictness: normal · Reviewed: 2026-06-10
```

### 2. Summary & Health Score

The headline numbers plus a one-paragraph narrative using the health band reading.

```markdown
## Summary

**Health Score:** 82/100 · **Requirement Coverage:** 87% · **Test Coverage:** good · **Tracker Accuracy:** 91%

<one paragraph: overall state, what is solid, what blocks sign-off>
```

### 3. Requirement Coverage

The coverage matrix — one row per requirement with verdict, evidence, and notes.

```markdown
## Requirement Coverage

| Requirement | Verdict | Evidence | Notes |
|-------------|---------|----------|-------|
| FR-001 | IMPLEMENTED | cleanup.ts:L42 | — |
| FR-002 | PARTIAL | cleanup.ts:L80 | Missing edge-case handling |
| FR-005 | MISSING | — | No evidence found |
```

### 4. Test Coverage

Expected vs. found, the quality band, and the list of missing areas.

```markdown
## Test Coverage

Expected: 8 · Found: 6 · Quality: good

Missing areas:
- Integration tests for CLI commands
```

### 5. Findings

Findings grouped by severity (Critical → Major → Minor → Info). Each finding shows its
ID, title, category, description, spec reference, and recommendation. Omit a severity
subsection when it has no findings.

```markdown
## Findings

### Critical
- **F-001 — Missing password reset flow** (requirement)
  - <description with evidence>
  - Spec: story.md - FR-012
  - Recommendation: <specific fix>

### Major
- **F-002 — Reconnection logic differs from spec** (technical)
  - ...

### Minor
### Info
```

### 6. Plan-Todo Accuracy

The tracker accuracy percentage and the discrepancies found.

```markdown
## Plan-Todo Accuracy

Accuracy: 91% · False completions: 2 · Unreported completions: 1

- p2-command-tests — marked completed, no tests found (false completion)
- p3-docs — implemented but still pending (unreported completion)
```

### 7. Recommendations

The prioritized action list, grouped by urgency.

```markdown
## Recommendations

### Immediate (Critical / Major)
1. ...

### Short-term (Minor)
1. ...

### Future (Info)
1. ...
```

### 8. Positive Notes

What was done well — the `positiveNotes` entries.

```markdown
## Positive Notes

- Core cleanup algorithm matches the spec exactly.
- Error handling follows the spec patterns consistently.
```

### 9. Scoped Work Source

A standardized closing note that makes the file actionable by `executeSpec`. Include
this section verbatim in intent: it tells a follow-up execution pass that this file is
its scoped work source and what to treat as actionable.

```markdown
## Scoped Work Source

This review can be fed back to `executeSpec` via the `reviewArtifact` parameter as the
scoped work source for a fix pass. An executor acting on this file should treat the
following as the work to do, in priority order:

1. Every **Critical** and **Major** finding above.
2. Every requirement marked **MISSING** or **PARTIAL** in the coverage matrix.
3. Missing test areas listed under Test Coverage.

Minor and Info findings are optional follow-ups. Re-run the review after the fix pass
to confirm the findings are resolved.
```
