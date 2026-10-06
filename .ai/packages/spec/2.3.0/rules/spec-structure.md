---
description: Guardrails for spec work under `.ai/specs/`: the required artifact set and `[featureName].X.md` naming, the story (WHAT/WHY) vs spec (HOW) boundary, and the directive to load the spec package's skills before creating, updating, executing, or reviewing a spec.
globs:
  - ".ai/specs/**"
alwaysApply: true
---

# Spec Structure Guardrails

Non-negotiable boundaries for specification work. The detailed authoring standards live in the spec package's skills — this rule enforces only the constraints that must hold regardless of which skill is loaded.

## Load Skills Before Spec Work

Before creating, updating, executing, or reviewing a spec, load the spec package's skills rather than working from memory:

- `spec-artifact-model` — artifact roles, directory layout, cross-links
- `spec-plan-format` — Cursor plan YAML and todo conventions
- `technical-spec-authoring` — technical design section standards
- `spec-review-rubric` — coverage matrix and finding taxonomy
- `spec-implementation-execution` — task execution and quality gates

Do not apply spec standards from memory. Load the relevant skill first.

Story content (`[featureName].story.md` — WHAT/WHY) is owned by the **story package**: author it with `{{skill:story.story-authoring}}` (`mode: create`), edit it with the same skill in `mode: revise`, and sync/transition/assign it via `{{skill:story.story-jira-sync}}` and `{{skill:story.story-jira-lifecycle}}`. Do not author story content from spec skills.

## Required Artifacts and Naming

A spec lives in `.ai/specs/<featureName>/` and contains exactly:

| Artifact | Required | Purpose |
|---|---|---|
| `README.md` | Yes | Front door and navigation; absorbs the executive summary |
| `[featureName].story.md` | Yes | User stories and requirements (WHAT/WHY) |
| `[featureName].spec.md` | Yes | Technical design (HOW) |
| `[featureName].plan.md` | Yes | Cursor-format implementation plan with todos |
| `[featureName].review.md` | Optional | Implementation review output (created by `reviewSpecImplementation`) |

Naming constraints:

- Every artifact except `README.md` is prefixed with the feature name: `[featureName].X.md`.
- `README.md` is the only executive summary. Never create a separate `SUMMARY.md`.
- Never use a bare `story.md` or `spec.md` — always prefix with the feature name.

## Story vs Spec Boundary

The story and the spec answer different questions. Keep them separate:

- **Story (`[featureName].story.md`) = WHAT and WHY.** User-focused and technology-agnostic. No code examples, schemas, or implementation detail.
- **Spec (`[featureName].spec.md`) = HOW.** Architecture, data models, algorithms, and code examples belong here.

### Example

**Bad** — implementation detail in the story:

```markdown
## Requirement
Store sessions in a Redis `sessions:*` key with a 30-minute TTL via `setex`.
```

Why this fails: it locks the design into Redis before the technical design exists and forces a story rewrite if the design changes. Stakeholders reading for value get implementation noise instead.

**Good** — capability in the story, mechanism in the spec:

```markdown
## Requirement
A signed-in user's session expires after 30 minutes of inactivity.
```

Why this works: it states the user-observable outcome. The spec is then free to choose Redis, a database, or another mechanism without touching the story.
