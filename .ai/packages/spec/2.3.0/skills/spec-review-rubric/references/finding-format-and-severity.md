# Finding Format & Severity

The complete finding object, the category and severity definitions, and the mapping
to the org code-review severity standard. Read when constructing, classifying, or
prioritizing findings in Pass 4.

## Finding Object

Each finding is one object in the `findings` array:

```json
{
  "id": "F-001",
  "severity": "major",
  "category": "requirement",
  "title": "Missing global package support",
  "description": "FR-005 specifies global package cleanup but no implementation was found in the cleanup module or its tests.",
  "specReference": "story.md - FR-005",
  "recommendation": "Implement global package cleanup as specified in spec.md Section 8.3."
}
```

### Field rules

| Field | Required | Rule |
|-------|----------|------|
| `id` | yes | `F-NNN`, zero-padded, sequential within the review (`F-001`, `F-002`, …). Assign in order of discovery |
| `severity` | yes | One of `critical` / `major` / `minor` / `info` (see below) |
| `category` | yes | One of `requirement` / `technical` / `test` / `documentation` / `tracking` |
| `title` | yes | One concise line naming the problem |
| `description` | yes | What is wrong and the evidence (cite `file.ts:Lxx` or "no evidence found") |
| `specReference` | when applicable | The spec location the finding traces to (e.g., `story.md - FR-012`, `spec.md - Section 4.2`). Include whenever a spec section applies |
| `recommendation` | yes | A specific, actionable fix — never "improve this". Name the change |

A finding without an actionable `recommendation` is not valid.

## Categories

| Category | Use for |
|----------|---------|
| `requirement` | An FR, NFR, or acceptance scenario that is unmet or partially met |
| `technical` | A deviation from the spec's architecture, API contract, data model, or error-handling design |
| `test` | Missing tests, or tests that exist but are low quality / cover the wrong thing |
| `documentation` | Missing or stale documentation, comments, or READMEs the spec requires |
| `tracking` | Plan-todo inaccuracy — a false completion or an unreported completion |

## Severities

| Severity | Definition | Action |
|----------|------------|--------|
| `critical` | Missing core functionality, a security gap, or a broken contract | Must fix before sign-off — caps health at 70 |
| `major` | A significant deviation, missing tests on a key path, or an incomplete feature | Should fix before sign-off — caps health at 85 |
| `minor` | A style deviation, a small documentation gap, or a low-impact improvement | Fix in follow-up |
| `info` | An observation, a suggestion, or an intentional improvement over the spec | No action required; note it |

`info` is the correct severity for an intentional, sensible deviation that improves on
the spec — do not flag those as problems. Recommend updating the spec to match instead.

## Mapping to the Org Code-Review Standard

The org code-review standard uses `critical` / `high` / `medium` / `low`. This review
method keeps its own four-band enum (`critical` / `major` / `minor` / `info`) because
that is what the `reviewSpecImplementation` `returns` schema and its consumers depend
on. Use this table only when **communicating** a spec-review finding in code-review
terms (e.g., a human cross-referencing both systems):

| spec-review `severity` | Org code-review severity | Rationale |
|------------------------|--------------------------|-----------|
| `critical` | Critical | Blocks merge / sign-off in both systems |
| `major` | High | Significant; should fix before merge |
| `minor` | Medium | Fix in a follow-up |
| `info` | Low | Nice-to-have / observation |

**Do not emit the org enum** in the returns object. The `findings[].severity` field is
always one of `critical` / `major` / `minor` / `info`. The mapping is a reading aid,
not an output format.

## Example Findings

### Critical — missing core functionality (requirement)

```json
{
  "id": "F-001",
  "severity": "critical",
  "category": "requirement",
  "title": "Missing password reset flow",
  "description": "FR-012 specifies password reset via email but no implementation exists in the auth module or its routes.",
  "specReference": "story.md - FR-012, User Story 3",
  "recommendation": "Implement the password reset flow as specified in spec.md Section 5, including the email-token endpoint and expiry handling."
}
```

### Major — technical deviation

```json
{
  "id": "F-002",
  "severity": "major",
  "category": "technical",
  "title": "Reconnection logic differs from spec",
  "description": "spec.md Section 4.2 specifies exponential backoff with jitter, but the implementation uses a fixed 5s retry (socket.ts:L88).",
  "specReference": "spec.md - Section 4.2 Reconnection Strategy",
  "recommendation": "Replace the fixed retry with exponential backoff plus jitter as designed in Section 4.2."
}
```

### Tracking — false completion

```json
{
  "id": "F-003",
  "severity": "major",
  "category": "tracking",
  "title": "Todo p2-command-tests marked completed but no tests exist",
  "description": "Todo p2-command-tests has status: completed in the plan frontmatter, but no test file exists at the path it names.",
  "specReference": "package-version-cleanup.plan.md - p2-command-tests",
  "recommendation": "Either write the missing tests or reset the todo status to pending to keep tracking accurate."
}
```
