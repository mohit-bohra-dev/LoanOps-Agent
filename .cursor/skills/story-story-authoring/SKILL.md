---
name: story-story-authoring
description: >-
  Standards for authoring a `[name].story.md` — the WHAT/WHY layer of a unit of
  work. Covers prioritized P1/P2/P3 user stories with priority rationale,
  independent-test descriptions, and Given/When/Then acceptance scenarios;
  stable-ID requirements (FR-/NFR-/SC-) with `[NEEDS CLARIFICATION]` markers;
  edge cases as questions; business-meaning key entities; out-of-scope; and the
  technology-agnostic boundary (no code, schemas, or implementation detail in
  the story). Use when creating, revising, or reviewing a story file, or
  deciding whether content belongs in the story versus a technical design.
promp:
  package: "story"
  version: "1.6.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "story-authoring"
---

# Story Authoring

Standards for writing `[name].story.md` — the WHAT and WHY layer of a unit of work. The story is read by stakeholders, by the `createStory` / `reviseStory` prompts that generate and edit it, by `syncStoryToJira` when it is pushed to a tracker, and by any reviewer who checks an implementation against it. It must stay technology-agnostic: it describes the user value and the requirements, never the implementation.

This skill covers the authoring judgment. The story's canonical section structure lives in `templates/story.md.template`; this skill is the standard for filling it well. The HOW layer — architecture, algorithms, code — lives outside the story (for example in a spec's `[name].spec.md`), never inside it.

## When to Use

- Writing a new `[name].story.md` from a feature description (`createStory`)
- Revising user stories, requirements, or success criteria on an existing story (`reviseStory`)
- Reviewing a story for completeness, testability, and boundary violations
- Deciding whether a piece of content belongs in the story or the technical design

## The WHAT/WHY Boundary

The story answers two questions only: **what** does the user need, and **why** does it matter. It never answers **how**. Every sentence is written in plain language a product owner or stakeholder can read without a technical decoder.

A useful test for any line: if it would change because an engineer picked a different library, framework, datastore, or algorithm, it does not belong in the story.

### Do NOT put implementation detail in the story

The following belong in the technical design (e.g. `[name].spec.md`), never in the story:

- Code examples or pseudocode of any kind
- Database schemas, table or column names, JSON field layouts
- File paths, function signatures, class or module names
- Specific technologies, libraries, or services (Redis, S3, a particular queue)
- Algorithms, complexity analysis, data structures

> **Correction — read this if you have seen an old standard.** An earlier version of some spec standards told story authors to "include code examples for all major components." **That guidance was wrong** and directly contradicts the technology-agnostic boundary. Do not put code examples in the story. Code examples and all implementation detail live in the technical design.

**Boundary in practice:**

- WRONG (story): "Store sessions in a Redis `sessions:*` key with a 30-minute TTL via `setex`."
- RIGHT (story): "A signed-in user's session expires after 30 minutes of inactivity."

The right version states the user-observable outcome and frees the design to choose any mechanism. The wrong version locks the design in before it exists and forces a story rewrite if the design changes.

When the deeper examples in `references/story-examples.md` (boundary section) show borderline cases, read them when judging whether a requirement has leaked implementation detail.

## Story Document Structure

Author these sections in order. The canonical structure lives in `templates/story.md.template`; this is the standard for filling it.

| Section | Required | Purpose |
|---|---|---|
| Header | Yes | Feature name, branch, created date, status, original user description |
| User Scenarios & Testing | Yes | Prioritized, independently testable user stories |
| Edge Cases | Yes | Boundary and error conditions, phrased as questions |
| Requirements | Yes | Functional (FR), Non-Functional (NFR), Key Entities |
| Success Criteria | Yes | Measurable outcomes (SC) |
| Out of Scope | Yes | What is explicitly NOT included, and why |
| Dependencies & Constraints | Optional | External dependencies, business/technical constraints (high-level) |
| Security & Privacy | Optional | Data collected, retention, access, regulatory needs |
| Open Questions | Optional | Unresolved questions with status |

Optional sections are included only when they carry real content. An empty optional section is noise — omit it.

## Format-Pluggable Authoring

`createStory` / `reviseStory` accept an optional `template` parameter — a path to a template file or an inline section-contract. When provided, **author against that format** instead of the package's default `story.md.template`: produce exactly the sections the caller's contract specifies, in its order, with its frontmatter. The authoring *judgment* in this skill still applies (the WHAT/WHY boundary, independently testable stories, measurable success criteria, stable IDs, marking unknowns) even when the section names differ.

This is how a caller such as `nexus` keeps its own strict story format (e.g. a fixed seven-section structure with `## Story Description` / `## Acceptance Criteria` / `## Definition of Done` / …) while reusing this package's authoring and Jira sync. Honor the caller's contract for structure; apply the judgment where the contract allows.

## Prioritized User Stories

User stories are the most important part of the story file. Each story is a standalone slice of value.

### Each story MUST have

1. **A priority** — `P1`, `P2`, `P3`, … where P1 is most critical.
2. **A plain-language description** — written as user value, no technical jargon. The `As a / I want / So that` form is encouraged but the value must be clear either way.
3. **A priority rationale** — *why* this priority level (`**Why this priority**:`).
4. **An independent-test description** — how this story can be implemented and tested *on its own* (`**Independent Test**:`).
5. **Acceptance scenarios** — one or more in `Given / When / Then` form.

### Independently testable is non-negotiable

Each story must be independently developable, testable, deployable, and demonstrable. If you implemented only the P1 story and nothing else, you must still have a viable MVP that delivers real value. If a story cannot stand alone — if it only makes sense once another story ships — it is not a separate story; fold it in or re-slice.

### Acceptance scenarios

Write scenarios as observable behavior, not internal steps:

```
1. **Given** I have a draft order, **When** I submit it, **Then** I receive an order confirmation number.
2. **Given** my payment is declined, **When** I submit the order, **Then** I see the decline reason and the order is not placed.
```

Keep the Then clause about what the user observes. A scenario whose Then asserts on a database row, an internal function call, or a log line has leaked implementation detail — rewrite it as the user-visible outcome.

For more good/bad story pairs with rationale, read `references/story-examples.md` (user-story section) when drafting or reviewing stories.

## Requirements with Stable IDs

Requirements get stable, prefixed, zero-padded identifiers so the design, plan, and review can cite them precisely.

| Prefix | Category | Phrasing |
|---|---|---|
| `FR-001` | Functional Requirement | "System MUST …" or "Users MUST be able to …" |
| `NFR-001` | Non-Functional Requirement | Performance, scalability, availability, security, compliance, usability |
| `SC-001` | Success Criterion | A measurable outcome that proves the feature succeeded |

### ID stability

IDs are identifiers, not positions. Once assigned, never renumber them:

- **Append** new requirements at the next available number.
- When a requirement is dropped, retire its ID — do not reuse the number for something new.
- Never renumber the list to "tidy it up." Other artifacts cite these IDs by number, and renumbering silently breaks those references.

### Mark the unknowns

When a requirement is unclear or a decision has not been made, do not guess and do not silently omit it. Mark it inline:

```
- **FR-007**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified — email/password, SSO, OAuth?]
- **NFR-004**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]
```

`[NEEDS CLARIFICATION]` is a first-class signal that the story is not yet ready for implementation. Reviewers look for these markers.

### Success Criteria must be measurable AND agnostic

A success criterion names a concrete, observable metric and stays free of implementation:

- GOOD (`SC-001`): "Users complete checkout in under 90 seconds at the median."
- GOOD (`SC-002`): "95% of users complete the primary task on first attempt."
- WEAK: "Checkout is fast." (not measurable)
- WRONG: "The checkout API returns in under 200ms." (implementation metric, not user-observable outcome — belongs in the design's performance section)

When in doubt about phrasing a measurable criterion, read `references/story-examples.md` (requirements and success-criteria sections).

## Edge Cases as Questions

List edge cases as open questions, not as answered designs. The question form keeps the story in the problem space and flags what the design must resolve:

```
- What happens when a user submits the same order twice within seconds?
- How does the system behave when the payment provider is unavailable?
- What occurs when the cart is empty at submission?
```

Phrasing them as questions (rather than "the system retries the payment") is deliberate — the *answer* is a technical decision that belongs in the design.

## Key Entities (business meaning, not schema)

When the feature involves data, describe entities by what they *represent* to the business and how they relate — never how they are stored:

- GOOD: "**Order** — a customer's request to purchase one or more items; belongs to one customer and has a status lifecycle."
- WRONG: "**Order** — `orders` table with `order_id` (UUID PK), `customer_id` FK, `status` enum column."

No table names, column types, keys, indexes, or serialization formats. Those are design content.

## Out of Scope

State explicitly what the feature does NOT include, each with a brief reason. This prevents scope creep and sets expectations:

```
- Bulk order import — out of scope for v1; revisit after single-order flow ships.
- Multi-currency pricing — handled by the existing pricing service, not this feature.
```

## Pre-Handoff Check

Before treating a story as ready, confirm:

- [ ] Every user story has a priority, a priority rationale, an independent-test description, and at least one Given/When/Then scenario.
- [ ] The P1 story alone would deliver a viable MVP.
- [ ] Functional, non-functional, and success-criteria items all have stable, prefixed IDs.
- [ ] Success criteria are measurable and free of implementation metrics.
- [ ] No code, schemas, file paths, technologies, or algorithms appear anywhere in the file.
- [ ] Unknowns are marked `[NEEDS CLARIFICATION]` rather than guessed or omitted.
- [ ] Key entities describe business meaning, not storage.

If any check fails, fix it before the story is treated as ready for design or sync.

## Invocation Contract

This skill is invoked in one of two **modes**. `create` authors a new story file;
`revise` edits an existing one in place. The standards above apply to both — the
modes differ only in how the file is reached and what "done" means.

Invoked by the `createStory` and `reviseStory` prompts, or directly by any caller
with the inputs below. Companion skills: `@./.cursor\skills\story-story-source-model\SKILL.md` for path
resolution, naming, and the recorded issue key; `@./.cursor\skills\story-story-epic-linking\SKILL.md` when
a `parentEpic` is supplied.

### mode: create

Author a new `[name].story.md` from a feature description.

#### Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `mode` | string | Yes | `create`. |
| `name` | string | No | Kebab-case name for the unit of work (e.g. `payment-retries`); names the `[name].story.md` file. Ask the user when absent. |
| `description` | string | No | One-line description of what the feature does and the problem it solves. Ask the user when absent. |
| `storyPath` | string | No | Where to write the story. A directory (file created as `<dir>/[name].story.md`) or a full file path. Defaults to `./[name].story.md`. |
| `parentEpic` | string | No | Parent epic to record — a local `[name].epic.md` path **or** an epic Jira issue key. Recorded locally; applied to Jira on first sync. |
| `template` | string | No | A template path **or** an inline section-contract overriding `templates/story.md.template`. See [Format-Pluggable Authoring](#format-pluggable-authoring). |
| `offerSync` | boolean | No | Whether to offer a first Jira sync after authoring. Default `true`. Offered as an option — never run automatically. |

#### Procedure

1. **Gather and validate inputs.** If `name` or `description` is missing, ask the
   user, keeping the discussion on WHAT/WHY rather than implementation detail.
   Validate `name` is kebab-case (lowercase letters, digits, and hyphens; starts
   with a letter) — otherwise raise `INVALID_NAME` and stop.
2. **Resolve the output path** from `storyPath` per `@./.cursor\skills\story-story-source-model\SKILL.md`
   (directory → `<dir>/[name].story.md`; full path → as given; absent →
   `./[name].story.md`). If a story already exists there, raise `STORY_EXISTS` and
   stop — the `revise` mode edits an existing story.
3. **Author the story.** Resolve the format (`template` when supplied, otherwise
   `templates/story.md.template`) and fill every required section against the
   description per the standards above. Replace every placeholder — leave no
   `{{…}}` markers behind. Keep the file technology-agnostic: no code, schemas,
   file paths, technologies, or algorithms.
4. **Record the parent epic** when `parentEpic` is provided, per
   `@./.cursor\skills\story-story-epic-linking\SKILL.md` (frontmatter only). The Jira parent link is
   applied on first sync — do not call jira here.
5. **Offer a Jira sync** when `offerSync` is not `false`: offer to run
   `@./.cursor\skills\story-story-jira-sync\SKILL.md` to create the issue. Present it as an option — do
   not run it automatically and do not block the return on the user's choice.

#### Returns

```json
{
  "success": true,
  "name": "payment-retries",
  "storyPath": "./payment-retries.story.md",
  "filesCreated": ["./payment-retries.story.md"]
}
```

| Field | Meaning |
|---|---|
| `success` | Whether the story was created. |
| `name` | The kebab-case name. |
| `storyPath` | Path to the created story file. |
| `filesCreated` | Paths of the files created. |

### mode: revise

Apply a described change to an existing `[name].story.md` in place.

#### Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `mode` | string | Yes | `revise`. |
| `storyPath` | string | Yes | Path to the existing `[name].story.md` to revise. |
| `changes` | string | No | What is changing and why. Ask the user when missing or ambiguous, before editing anything. |
| `reviewPath` | string | No | Path to a `@./.cursor\skills\story-story-review\SKILL.md` write-up whose **Required Changes** are the authoritative change set for this revision. |
| `template` | string | No | A template path **or** an inline section-contract describing the format to conform to. |
| `offerSync` | boolean | No | Whether to offer a Jira re-sync after editing. Default `true`. |

#### Procedure

1. **Locate the story.** Resolve `storyPath`; if no readable story file exists
   there, raise `STORY_NOT_FOUND` and stop. Note any recorded Jira issue key per
   `@./.cursor\skills\story-story-source-model\SKILL.md` for the re-sync offer.
2. **Understand the change.** If `changes` is missing or ambiguous and no
   `reviewPath` was supplied, ask the user **what** is changing and **why** before
   editing anything. When a `reviewPath` is supplied, read the review and drive the
   revision from its Required Changes.
3. **Apply the edit** in place per the standards above (against `template` when
   provided) — add and amend rather than wholesale replace. Preserve stable
   requirement IDs: append new ones at the next number, retire dropped ones, never
   renumber. Keep the file technology-agnostic; mark an undecided point
   `[NEEDS CLARIFICATION: …]` rather than guessing.
4. **Offer a Jira re-sync** when `offerSync` is not `false` and the story is (or
   should be) linked to a Jira issue: offer to run `@./.cursor\skills\story-story-jira-sync\SKILL.md` so
   the issue reflects the new story. Do not run it automatically.

#### Returns

```json
{
  "success": true,
  "storyPath": "./payment-retries.story.md",
  "changesSummary": "Added a P2 backoff user story and SC-006; clarified the retry-limit edge case."
}
```

| Field | Meaning |
|---|---|
| `success` | Whether the revision was applied. |
| `storyPath` | Path to the revised story file. |
| `changesSummary` | One- to two-sentence summary of what changed and why. |

### Errors

| Code | Mode | Raised when | Recovery |
|---|---|---|---|
| `INVALID_NAME` | `create` | `name` is not kebab-case. Carries `providedName`. | Supply a kebab-case name. |
| `STORY_EXISTS` | `create` | A story file already exists at the resolved path. Carries `storyPath`. | Use `mode: revise` to edit it, or choose a different path. |
| `STORY_NOT_FOUND` | `revise` | No readable story file exists at `storyPath`. Carries `storyPath`. | Check the path, or use `mode: create` to author a new story. |

## Reference Documents

- `references/story-examples.md` — Paired good/bad examples with rationale for user stories, requirements and stable IDs, success criteria, key entities, and boundary violations. Read when drafting or reviewing a story and you need a concrete model for a specific section, or when judging whether content has leaked across the story/design boundary.
