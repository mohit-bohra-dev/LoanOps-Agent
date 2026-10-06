---
name: spec-spec-jira-sync
description: >-
  How a spec's story is delta-synced to its Jira issue: resolving the spec's
  `[featureName].story.md` from a feature name, delegating the sync itself to
  the story package's `story-jira-sync` skill (create on first sync, push only
  the changed fields on every sync after), mapping the story-package result back
  into the spec response shape, and relaying story/jira errors verbatim rather
  than repairing them in the spec layer. Use when syncing a spec's story to
  Jira, creating a Jira issue for a newly authored spec, re-syncing after a
  story change, or diagnosing a spec-to-Jira sync failure — not when
  transitioning status or assigning an issue during execution.
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "spec-jira-sync"
---

# Spec Jira Sync

How a spec's story reaches Jira and stays in step with it. This skill is a **thin
locating-and-delegating layer**: it resolves which story file a spec's sync is
about, hands the sync to the story package, and maps the result back into the
spec's response shape.

## When to Use

- Syncing a spec's `[featureName].story.md` to Jira for the first time (create)
- Re-syncing after the story changed (delta push)
- Creating and linking a Jira issue for a spec that has none yet
- Diagnosing a sync failure and deciding whether it is a spec-layer or a
  story/jira-layer problem

Not for status transitions or assignment during execution — those are the
tracker **lifecycle**, owned by `@./.cursor\skills\story-story-jira-lifecycle\SKILL.md` and driven
by the `spec-execution-coordinator`. See [Lifecycle Is Separate](#lifecycle-is-separate).

## The Boundary

Everything about *how* a sync works belongs to the **story** package:

| Owned by `@./.cursor\skills\story-story-jira-sync\SKILL.md` | Owned here |
|---|---|
| The delta-sync method (get → diff → push only what changed) | Resolving the spec's story file from `featureName` |
| Acceptance-criteria append vs. replace | Mapping the story result into the spec response shape |
| Conflict surfacing and confirmation before overwrite | Deciding when the spec layer itself must error out |
| Story-source detection and recording the issue key back | Pointing the user at the right recovery |

Never re-implement the sync method here, and never reach into the jira package
or Atlassian directly from the spec layer.

## Invocation Contract

### Inputs

| Input | Type | Required | Meaning |
|---|---|---|---|
| `featureName` | string | one of `featureName` / `storySource` | The spec whose story to sync. Locates `.ai/specs/<featureName>/` and its `<featureName>.story.md`. |
| `storySource` | string | one of `featureName` / `storySource` | The sync target — a story **file path** or a Jira **issue key**. Passed through; the story package auto-detects the shape. When it is an issue key, the existing issue is **updated**, never re-created. |
| `projectKey` | string | no | Target Jira project for a first-sync create. When omitted, the jira config's default project is used. Passed through. |

When neither `featureName` nor `storySource` is given, ask which spec to sync
before proceeding — do not guess a spec.

### Procedure

1. **Resolve the spec's story file.** When `featureName` is given, resolve
   `.ai/specs/<featureName>/<featureName>.story.md` as `storyPath`. Use
   `@./.cursor\skills\spec-spec-artifact-model\SKILL.md` for the artifact naming and for story-source
   detection when the story is external.
2. **Stop if there is nothing to sync.** If neither the spec's story file nor
   `storySource` resolves to syncable content, return `SPEC_NOT_FOUND` and stop
   — **do not call the story package** against an unresolved story.
3. **Delegate the sync.** Invoke `@./.cursor\skills\story-story-jira-sync\SKILL.md` with
   `storyPath` (the resolved story file), `storySource` (when provided), and
   `projectKey` (when provided). It runs the delta sync, surfaces and resolves
   Jira-side conflicts, pushes only the delta, and records the issue key back
   into the story. Surface its permission prompts and conflict confirmations to
   the user as-is — never auto-confirm an overwrite on its behalf.
4. **Map the result back.** Carry `featureName` through and pass `issueKey`,
   `fieldsChanged`, and `conflictReport` from the story-package result into the
   returned shape.

### Returns

```json
{
  "success": true,
  "featureName": "payment-retries",
  "issueKey": "PAY-512",
  "fieldsChanged": ["summary", "acceptanceCriteria"],
  "conflictReport": null
}
```

| Field | Meaning |
|---|---|
| `success` | Whether the sync completed — including a clean no-op when nothing changed. |
| `featureName` | The spec that was synced. |
| `issueKey` | The created or updated Jira issue key. |
| `fieldsChanged` | Fields actually pushed (`summary`, `description`, `acceptanceCriteria`). Empty when the story already matched Jira. |
| `conflictReport` | Object describing surfaced divergences and their resolution, or `null` when there were no conflicts. |

An empty `fieldsChanged` with `success: true` is the expected result of a
no-change sync, not a failure.

### Errors

`SPEC_NOT_FOUND` is the only error this layer raises. Everything else is relayed
verbatim from the story package (which in turn relays the jira skills) — the spec
layer never repairs or reclassifies a downstream error.

| Code | Raised by | When | Recovery to offer |
|---|---|---|---|
| `SPEC_NOT_FOUND` | this skill | The spec directory or its `[featureName].story.md` cannot be located, and no `storySource` resolves to syncable content | Verify `featureName` / `storySource`; author the spec first if it does not exist |
| `STORY_NOT_FOUND` | story | The story file could not be located | Correct the path |
| `CONNECTION_FAILED` | jira, via story | The Atlassian MCP server is not connected or authenticated | Connect/authenticate the MCP server, then re-run |
| `ISSUE_NOT_FOUND` | jira, via story | The issue key does not exist | Correct the key, or omit it to create a new issue |
| `CONFIG_INVALID` | jira, via story | `.ai/jira.config.json` is malformed | Run `@./.cursor\skills\jira-configure-jira\SKILL.md` or `@./.cursor\skills\jira-verify-jira-config\SKILL.md` |
| `PROJECT_NOT_IN_CONFIG` | jira, via story | The requested project is not in the jira config | Add the project via `@./.cursor\skills\jira-configure-jira\SKILL.md` |
| `DEFAULT_PROJECT_KEY_MISSING` | jira, via story | No `projectKey` was given and the config has no default | Pass `projectKey`, or set a default via `@./.cursor\skills\jira-configure-jira\SKILL.md` |

On a `SPEC_NOT_FOUND`:

```json
{
  "code": "SPEC_NOT_FOUND",
  "message": "No spec or story file found for feature: payment-retries",
  "featureName": "payment-retries"
}
```

## Story Is Truth, Jira Is Transport

The sync pushes; it does not pull. The local story is authoritative and the issue
is the downstream copy. The one exception is **conflict surfacing**: when the
issue diverged from the story since the last sync, the story package surfaces the
divergence and confirms before any overwrite. Relay that confirmation to the
user; never resolve it silently in the spec layer.

## Lifecycle Is Separate

Syncing content and driving the tracker lifecycle are different operations with
different owners:

| Operation | Owner | Driven by |
|---|---|---|
| Create / update the issue's content | `@./.cursor\skills\story-story-jira-sync\SKILL.md` (via this skill) | A sync request, or the offer after a local story is authored |
| Status transitions | `@./.cursor\skills\story-story-jira-lifecycle\SKILL.md` (`operation: transition`) | `spec-execution-coordinator`, at run start and completion |
| Assignment | `@./.cursor\skills\story-story-jira-lifecycle\SKILL.md` (`operation: assign`) | `spec-execution-coordinator`, at run start |

Do not transition or assign from this skill, and do not sync content from the
lifecycle skill.

## Worked Example

Spec `payment-retries` has a local story and no recorded issue key.

1. **Resolve** — `.ai/specs/payment-retries/payment-retries.story.md` exists →
   `storyPath` resolved. No `storySource`, no `projectKey`.
2. **Delegate** — `@./.cursor\skills\story-story-jira-sync\SKILL.md` finds no issue key on the
   story, so this is a first sync: it creates the issue in the jira config's
   default project and records `PAY-512` back into the story.
3. **Map back** — return `success: true`, `issueKey: "PAY-512"`,
   `fieldsChanged: ["summary", "description", "acceptanceCriteria"]`,
   `conflictReport: null`.

A later re-sync after only the acceptance criteria changed returns the same shape
with `fieldsChanged: ["acceptanceCriteria"]` — the delta, not the whole story.
