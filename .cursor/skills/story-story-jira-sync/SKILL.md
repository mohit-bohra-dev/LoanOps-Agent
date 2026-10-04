---
name: story-story-jira-sync
description: >-
  Delta-sync methodology for keeping a `[name].story.md` and its Jira issue in
  step, consuming the jira package only through {{skill:jira.*}} skill entry
  points. Covers the get → diff → update loop, first-sync create vs
  subsequent update, acceptance-criteria append vs replace (acMergeMode),
  surfacing and confirming Jira-side conflicts before overwriting, and
  config-bootstrap remediation. Use when syncing a story to Jira, creating or
  updating a Jira issue from a story, diffing a local story against its issue,
  or resolving a sync conflict. For status transitions and assignment, see
  story-jira-lifecycle; for source detection and recording the key, see
  story-source-model.
promp:
  package: "story"
  version: "1.6.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "story-jira-sync"
---

# Story ⇄ Jira Sync

How the story workflow pushes a story to Jira. The story layer owns the
**parsing and diff**; the `jira` package owns all Atlassian transport. The story
layer never re-implements Jira and never talks to Atlassian or the MCP directly —
it composes jira's skill entry points.

This skill covers **content** sync (summary / description / acceptance criteria).
Lifecycle operations — status transitions and assignment — live in the
`story-jira-lifecycle` skill. Story-source detection and recording the issue key
back live in the `story-source-model` skill. The parent-epic link (the Epic Link /
`parentKey`) lives in the `story-epic-linking` skill; the sync rides a recorded
parent along on the create/update call but does not own the linking method.

## When to Use

- The `syncStoryToJira` prompt syncs a story to a Jira issue
- A caller offers to sync a freshly authored or revised story
- Deciding first-sync create vs subsequent update, or replace vs append for AC
- Resolving a divergence between a local story and its Jira issue

## Core Principle: Story Is Truth, Jira Is Transport

`[name].story.md` is the **source of truth** for content authored in code. Jira
is downstream: the sync pushes the story's state onto the issue.

Two hard rules follow:

1. **Consume Jira through its skills only.** Every Atlassian operation goes
   through a `{{skill:jira.*}}` entry point. Never call the Atlassian MCP
   directly, never re-implement config loading or ADF construction, and never
   assume a jira `.cursor/commands` slash command exists — jira is usually
   installed as a **transitive** dependency, for which the promp CLI emits skills
   and agents but **no command files**. Its skills are therefore the stable
   contract and the only artifacts guaranteed to be on disk. The boundary itself
   is unchanged: story parses and diffs, jira transports.
2. **Push, don't pull (by default).** The story drives the issue. The one
   exception is conflict surfacing: when Jira has diverged, you stop and confirm
   before overwriting — see [Conflicts](#conflicts-surface-before-overwriting).

| Story need | jira entry point | Distinguishing input |
|---|---|---|
| Fetch the remote baseline | `@./.cursor\skills\jira-retrieve-jira\SKILL.md` (`issueKey`) | — |
| First sync — create the issue | `@./.cursor\skills\jira-create-jira-issues\SKILL.md` | `profileName: Story` |
| Subsequent sync — update changed fields | `@./.cursor\skills\jira-update-jira-issues\SKILL.md` | `profileName: Story` |
| Bootstrap missing config | `@./.cursor\skills\jira-configure-jira\SKILL.md` | — |
| Diagnose invalid/drifted config | `@./.cursor\skills\jira-verify-jira-config\SKILL.md` | — |

The create and update skills serve every issue type, so each call site states
`profileName: Story` — omitting it leaves the issue type ambiguous.

## The Delta-Sync Method

Run these four steps in order. Steps 1–3 are story-owned; step 4 is the only one
that mutates Jira.

### 1. Resolve the target and fetch the baseline

Detect whether you already have a Jira issue using `@./.cursor\skills\story-story-source-model\SKILL.md`
(story-source detection).

- **Issue key known** → fetch the remote baseline with
  `@./.cursor\skills\jira-retrieve-jira\SKILL.md` passing `issueKey`. Use its returned `summary`,
  `status`, and `content` (markdown) as the comparison baseline.
- **No issue yet** → there is nothing to fetch; this is a first sync (step 4
  creates the issue).

### 2. Parse the local story

Read `[name].story.md` and extract the syncable content: the title, the
description body, and the acceptance-criteria list. The story layer owns this
parse — `jira` only transports the values you hand it. For the exact section →
field extraction, read `references/field-mapping.md`.

### 3. Diff local vs remote

Compare the parsed story against the fetched baseline, field by field
(summary, description, acceptance-criteria list). Produce the **delta**: the set
of fields whose local value differs from Jira. Unchanged fields are *not* part
of the delta and must not be pushed.

- On a **first sync** every mapped field is "new" — the whole story is the delta.
- If the diff finds Jira-side edits that conflict with local content, do not
  silently overwrite — go to [Conflicts](#conflicts-surface-before-overwriting).

### 4. Push only the delta

- **First sync (no issue):** `@./.cursor\skills\jira-create-jira-issues\SKILL.md` with
  `profileName: Story`, `summary` (required), `description`, `acceptanceCriteria`,
  and optional `projectKey` (falls back to jira config's `defaultProjectKey` when
  omitted). Capture the returned `issueKey` and record it (see
  `@./.cursor\skills\story-story-source-model\SKILL.md`, "Recording the Key").
- **Subsequent sync:** `@./.cursor\skills\jira-update-jira-issues\SKILL.md` with
  `profileName: Story`, `issueKey`, and **only the changed fields**. Passing a
  field that did not change re-writes it needlessly and muddies the jira approval
  diff.

## Acceptance Criteria: Append vs Replace

`@./.cursor\skills\jira-update-jira-issues\SKILL.md` takes an **`acMergeMode`** input that controls
how `acceptanceCriteria` is applied:

| `acMergeMode` | Effect | jira default |
|---|---|---|
| `append` | Merges new AC items into the existing AC field; unchanged bullets are preserved | — |
| `replace` | Overwrites the whole AC field with the supplied list | ✅ default |

**Story delta-sync prefers `append`.** When pushing an AC delta, set
`acMergeMode="append"` so newly authored criteria are added without clobbering
bullets a teammate may have refined in Jira. The jira default is `replace`, so
you must pass `append` explicitly — omitting it overwrites the field.

Use `replace` only when the story has deliberately **rewritten or removed** AC
items and the story is authoritative for the full list (e.g. an AC was deleted
in code and must disappear from Jira). Append cannot express a deletion; replace
can. When in doubt during a routine sync, append.

`acMergeMode` only affects the AC field and is ignored when no
`acceptanceCriteria` is provided.

## Story-Source Detection

The sync target is a single value that is **either** a story file path **or** a
Jira issue key, auto-detected by shape. The detection rule lives in the
`story-source-model` skill — load it for the canonical heuristic (issue keys
match `^[A-Z][A-Z0-9]+-\d+$` with no path separators or extension; anything with
`/`, `\`, `.`, or a file extension is a path; ambiguous → treat as a path).

Apply the result here:

| Detected shape | Sync behavior |
|---|---|
| Issue key (e.g. `ABC-123`) | An issue already exists. Fetch it, diff, and **update** it — never create a duplicate. |
| File path | A local story. Look for a recorded issue key (story frontmatter / status table). If found → update that issue; if none → first sync → create. |

## Conflicts: Surface Before Overwriting

The story is the source of truth, but the agent does **not** blindly overwrite
Jira. When step 3's diff shows the Jira side changed in a way that conflicts with
local content, **stop, surface the divergence, and get confirmation before
pushing.**

Read `references/conflict-handling.md` for the full flow: which differences count
as a conflict vs a clean push, how to present the field-by-field divergence, and
what the user's confirm / skip / abort choices do.

## Config & Bootstrap Remediation

The jira skills load and validate `.ai/jira.config.json` internally — the story
layer does **not** read or validate it. When config is missing or invalid, the
create/update skills throw; surface those errors and point the user at the
remediation entry points:

| Symptom (thrown by jira) | Remediation |
|---|---|
| `CONFIG_INVALID`, `PROJECT_NOT_IN_CONFIG`, `DEFAULT_PROJECT_KEY_MISSING` | Run `@./.cursor\skills\jira-configure-jira\SKILL.md` to bootstrap, or `@./.cursor\skills\jira-verify-jira-config\SKILL.md` to diagnose drift |
| `CONNECTION_FAILED` | Atlassian MCP not connected/authenticated — surface as-is; it is not a story-side fix |

Relay the thrown `code` and `message` to the user verbatim; do not attempt to
repair Jira config from the story layer.

## Invocation Contract

Invoked by the `syncStoryToJira` prompt, or directly by any caller with the inputs
below.

### Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `storySource` | string | No | The sync target — **either** a story file path **or** a Jira issue key (e.g. `PAY-512`, `./payment-retries.story.md`), auto-detected by shape per `@./.cursor\skills\story-story-source-model\SKILL.md`. When it is an issue key, the existing issue is **updated**, never re-created. |
| `storyPath` | string | No | Explicit path to the local `[name].story.md` when `storySource` is an issue key or omitted. Used to locate the content to diff. |
| `projectKey` | string | No | Target Jira project for a first-sync create. When omitted, the jira config's default project is used. |

At least one of `storySource` or `storyPath` is needed to locate the story. If
neither resolves to readable content, ask the user before proceeding.

### Procedure

1. **Resolve the story and detect the source** per
   [step 1](#1-resolve-the-target-and-fetch-the-baseline). Produce `storyFilePath`,
   `issueKey` (the existing key if known, else `null`), and `syncMode` (`create`
   when no key, `update` when a key resolves).
   **Stop condition:** if the story file cannot be located, raise
   `STORY_NOT_FOUND` and stop — do not call any jira skill.
2. **Fetch the remote baseline** with `@./.cursor\skills\jira-retrieve-jira\SKILL.md` when
   `issueKey` is known; skip on a first sync. Surface `ISSUE_NOT_FOUND` or
   `CONNECTION_FAILED` verbatim.
3. **Parse and diff** per [steps 2–3](#2-parse-the-local-story), classifying the
   AC change to choose `acMergeMode` and flagging any Jira-side divergence as a
   conflict.
4. **Resolve conflicts before pushing** per `references/conflict-handling.md`:
   surface field by field, take a confirm / skip / abort decision, and capture the
   outcome as `conflictReport`.
   **Stop condition:** push no field until conflicts are confirmed or resolved.
5. **Push the delta** per [step 4](#4-push-only-the-delta). On a create, pass
   `parentKey` when the story records a parent epic (resolved to the epic's issue
   key per `@./.cursor\skills\story-story-epic-linking\SKILL.md`); on an update, include `parentKey` only
   when the recorded parent changed since the last sync.
6. **Record the key and return.** On a first-sync create, record the returned
   `issueKey` back into the story per `@./.cursor\skills\story-story-source-model\SKILL.md` so the next
   sync updates instead of creating a duplicate.

### Returns

```json
{
  "success": true,
  "storyPath": "./payment-retries.story.md",
  "issueKey": "PAY-512",
  "fieldsChanged": ["summary", "acceptanceCriteria"],
  "conflictReport": null
}
```

| Field | Meaning |
|---|---|
| `success` | Whether the sync completed (including a clean no-op when nothing changed). |
| `storyPath` | The local story that was synced. |
| `issueKey` | The created or updated Jira issue key. |
| `fieldsChanged` | The fields actually pushed (`summary`, `description`, `acceptanceCriteria`). Empty when the story already matched Jira. |
| `conflictReport` | An object describing surfaced divergences and their resolution, or `null` when there were no conflicts. |

### Errors

| Code | Raised when | Recovery |
|---|---|---|
| `STORY_NOT_FOUND` | The story file cannot be located from `storySource` / `storyPath`. Carries `storyPath`. | Check the path, or author the story first per `@./.cursor\skills\story-story-authoring\SKILL.md`. |
| `CONNECTION_FAILED` | Relayed from jira — Atlassian MCP not connected/authenticated. | Surface as-is; not a story-side fix. |
| `ISSUE_NOT_FOUND` | Relayed from jira — the issue key does not exist. | Surface as-is. |
| `CONFIG_INVALID`, `PROJECT_NOT_IN_CONFIG`, `DEFAULT_PROJECT_KEY_MISSING` | Relayed from jira — `.ai/jira.config.json` is missing, invalid, or drifted. | Point the user at `@./.cursor\skills\jira-configure-jira\SKILL.md` or `@./.cursor\skills\jira-verify-jira-config\SKILL.md`. |

Every jira error is relayed with its `code` and `message` verbatim — the story
layer does not repair them.

## Worked Examples

### Example 1 — First sync (file-path source, append AC)

`storySource` is `./payment-retries.story.md`; no recorded issue key.

1. Detect: path → no existing issue → first sync.
2. Parse the story: summary, description, three AC bullets.
3. Diff: first sync → entire story is the delta.
4. `@./.cursor\skills\jira-create-jira-issues\SKILL.md` with `profileName: Story`, `summary`,
   `description`, `acceptanceCriteria` (the three bullets), `projectKey` omitted
   (config default). Returns `PAY-512`.
5. Record `PAY-512` per `@./.cursor\skills\story-story-source-model\SKILL.md` so the next sync updates.

### Example 2 — Subsequent delta sync (issue-key source)

`storySource` is `PAY-512`. The story added one AC bullet and edited the summary;
the description is unchanged.

1. Detect: issue key → existing issue → update path.
2. `@./.cursor\skills\jira-retrieve-jira\SKILL.md` `issueKey="PAY-512"` → baseline.
3. Diff: `summary` changed, `acceptanceCriteria` gained one item, `description`
   unchanged. Delta = `{ summary, acceptanceCriteria }`.
4. `@./.cursor\skills\jira-update-jira-issues\SKILL.md` with `profileName: Story`,
   `issueKey="PAY-512"`, the new `summary`, the AC list, and
   **`acMergeMode="append"`** — the new bullet is added, the existing bullets are
   preserved, and `description` is left out of the call.

## Reference Documents

- `references/field-mapping.md` — The `[name].story.md` section → Jira field
  mapping (summary / description / acceptance-criteria), how to extract and
  normalize each field, and how the per-field diff decides what enters the delta.
  Read in steps 2–3 of the delta-sync method.
- `references/conflict-handling.md` — The conflict-surfacing flow: what counts as
  a conflict, how to present the divergence field-by-field, and the
  confirm / skip / abort resolution. Read when step 3's diff shows Jira-side
  changes.
