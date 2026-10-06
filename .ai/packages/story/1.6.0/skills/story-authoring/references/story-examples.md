# Story Examples

Paired good/bad examples with rationale for each part of `[name].story.md`. Each pair shows the same intent done right and done wrong, so the failure mode is concrete. Read the section that matches what you are drafting or reviewing.

---

## User Stories

A well-formed story is a standalone slice of value with a priority, a rationale, an independent-test description, and acceptance scenarios.

### Good

```markdown
### User Story 1 - Quick Package Cleanup (Priority: P1)

As a developer, I want old package versions removed automatically after installation
so that my disk space is freed without manual intervention.

**Why this priority**: This is the core value proposition and solves the primary
user pain point of accumulating unused versions. Everything else builds on it.

**Independent Test**: Install a package, upgrade it, and verify the old version is
gone. Delivers value on its own even if no other story ships.

**Acceptance Scenarios**:

1. **Given** I have package v1.0.0 installed, **When** I install v2.0.0, **Then** v1.0.0 is removed.
2. **Given** I have several versions installed, **When** I run install, **Then** only the latest required version remains.
```

**Why it works:** Plain user value, a real priority rationale, a test that stands alone, and outcome-focused scenarios. A product owner can read it without a technical glossary.

### Bad (too technical)

```markdown
### User Story 1 - Implement cleanup algorithm

Implement a semver-based version cleanup algorithm using the `findVersionsToKeep`
function that scans the `.ai/packages` directory and removes unused versions based
on `promp.json` dependencies.
```

**Why it fails:** This is HOW, not WHAT/WHY. It names a function and a directory, describes an algorithm, and carries no priority, rationale, independent-test description, or acceptance scenarios. It belongs in the technical design, not the story.

### Bad (not independently testable)

```markdown
### User Story 2 - Add a flag to the cleanup command (Priority: P2)

As a developer, I want a `--dry-run` flag.

**Why this priority**: Nice to have.
**Independent Test**: N/A — only works once cleanup (Story 1) exists.
```

**Why it fails:** "N/A — only works once Story 1 exists" is the tell. A story that cannot be tested on its own is not a separate story. Either fold the dry-run behavior into the cleanup story or re-slice so it delivers standalone value. "Nice to have" is not a rationale.

---

## Acceptance Scenarios

Scenarios assert what the user observes, in Given/When/Then form.

### Good

```markdown
1. **Given** my session has been idle for 30 minutes, **When** I take any action, **Then** I am returned to the sign-in screen.
2. **Given** I sign in again, **When** I return to the page I left, **Then** my unsaved draft is still present.
```

**Why it works:** Each Then is a user-observable outcome. No mention of how the session or the draft is stored.

### Bad

```markdown
1. **Given** a session row exists in Redis, **When** the TTL expires, **Then** the `sessions:*` key is evicted and `auth_state` is set to `null`.
```

**Why it fails:** The Then asserts on a datastore key and an internal field — implementation leaked into the scenario. Rewrite as the user-visible effect ("the user is signed out and prompted to sign in again").

---

## Requirements and Stable IDs

Functional requirements use `FR-`, non-functional use `NFR-`, both zero-padded and stable.

### Good

```markdown
### Functional Requirements

- **FR-001**: System MUST remove a package version once no installed package depends on it.
- **FR-002**: Users MUST be able to preview which versions would be removed before any deletion occurs.
- **FR-003**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified — email/password, SSO, OAuth?]

### Non-Functional Requirements

- **NFR-001**: Cleanup MUST complete within 5 seconds for a directory of up to 500 versions.
- **NFR-002**: System MUST never remove a version that an installed package still depends on.
```

**Why it works:** "System MUST" / "Users MUST be able to" phrasing, capability-focused, with an honest `[NEEDS CLARIFICATION]` marker on the undecided item. IDs are sequential and prefixed.

### Bad

```markdown
### Requirements

- The `cleanup()` function in `cleanup.ts` deletes folders under `.ai/packages/`.
- Should probably be fast.
- Use `semver.satisfies()` to decide what to keep.
```

**Why it fails:** No IDs, so nothing can cite these from the design or review. It names a function, a file, and a library (HOW). "Should probably be fast" is neither a requirement nor measurable. Unknowns are hand-waved instead of marked.

### ID stability anti-pattern

```markdown
Before: FR-001, FR-002, FR-003
After dropping the old FR-002 and renumbering: FR-001, FR-002 (was FR-003)
```

**Why it fails:** The design cited "FR-003" for a behavior that is now "FR-002," and the old FR-002's number was silently reused. Retire dropped IDs and append new ones; never renumber.

---

## Success Criteria

Success criteria are measurable AND technology-agnostic.

### Good

```markdown
- **SC-001**: A developer recovers at least 80% of space used by stale versions without any manual step.
- **SC-002**: 95% of cleanup runs complete without the developer noticing a pause (perceived as instant).
- **SC-003**: Support tickets about "disk full from .ai/packages" drop to zero within one release cycle.
```

**Why it works:** Concrete numbers tied to user/business outcomes. None of them assume an implementation.

### Bad

```markdown
- **SC-001**: The cleanup feature works well.
- **SC-002**: The `cleanup()` function returns in under 200ms.
```

**Why it fails:** "Works well" is not measurable. The second is an implementation metric on a named function — a performance target for the design, not a user-observable success criterion.

---

## Key Entities

Describe what an entity means to the business and how it relates — not how it is stored.

### Good

```markdown
- **Package Version** — a specific released version of an installed package; may be required by zero or more other packages.
- **Dependency** — a relationship declaring that one package needs a particular version range of another.
```

**Why it works:** Business meaning and relationships, no storage detail.

### Bad

```markdown
- **Package Version** — `package_versions` table: `id` (UUID PK), `name` (varchar), `semver` (varchar), `installed_at` (timestamptz), indexed on `(name, semver)`.
```

**Why it fails:** Table name, column types, primary key, and index — pure schema. This is data-model content for the technical design.

---

## Boundary Violations (story vs design)

These are the borderline cases where implementation detail slips into the story. When reviewing, watch for them.

| Story line | Verdict | Fix |
|---|---|---|
| "A signed-in user's session expires after 30 minutes of inactivity." | OK | — |
| "Store sessions in Redis with a 30-minute TTL." | Leak | State the expiry as user-observable behavior; let the design pick Redis. |
| "Users can export their report as a file they can open in a spreadsheet." | OK | — |
| "Generate a CSV via the `csv-stringify` library and stream it from `/export`." | Leak | Name the capability (export to spreadsheet), not the library or endpoint. |
| "The system handles up to 10,000 concurrent users." | OK (NFR) | — |
| "Use a connection pool of 50 and horizontal autoscaling at 70% CPU." | Leak | That is the mechanism — move to the design's performance/architecture sections. |
| "What happens when two users edit the same record at once?" (edge case) | OK | — |
| "On concurrent edits, take an optimistic lock and retry up to 3 times." | Leak | Keep the edge case as a question; the resolution is a design decision. |

**Rule of thumb:** if the line would have to change because an engineer chose a different tool, framework, or algorithm, it is a leak — move it to the technical design and leave the user-observable intent in the story.
