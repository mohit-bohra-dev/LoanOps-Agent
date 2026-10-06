---
name: story-epic-linking
description: >-
  How a story is linked to its parent epic — both in the local `[name].story.md`
  (recording the parent in frontmatter) and in Jira (the Epic Link / parent
  relationship, pushed via {{skill:jira.*}} `parentKey`). Covers parent-epic
  source detection (a local `[name].epic.md` path vs an epic Jira issue key),
  resolving an epic file to its recorded issue key, the verify / ensure-linked /
  link policies, and surfacing a conflict before re-parenting a story that
  already belongs to a different epic. Use when setting, verifying, or clearing a
  story's parent epic, or when carrying the parent link into a story sync.
---

# Story ⇄ Epic Linking

A story belongs under a parent **epic**. This skill defines how the story layer
records that relationship locally and pushes it to Jira — always through
`{{skill:jira.*}}` entry points, never by talking to Atlassian or the MCP
directly. It is the parent-awareness counterpart to `story-jira-sync` (content)
and `story-jira-lifecycle` (state + assignment + estimate).

## When to Use

- The `linkStoryToEpic` prompt sets, verifies, or clears a story's parent epic
- Story authoring or a story sync carries a parent epic into Jira on create/update
- Deciding whether a provided parent value is an epic file path or an epic issue
  key, and resolving a local epic file to its Jira issue key

## The Two Sides of a Link

A link has a **local** side and a **Jira** side. Keep both in step:

> **Scope: parent only.** This skill covers the Story → Epic **parent** relationship. Story-to-story **dependency** links (`Blocks` / `is blocked by`) are a separate Jira mechanism — a sideways issue link rather than hierarchy — owned by `{{skill:story-dependency-linking}}`. Do not model a dependency as a parent; it would move the story out of its epic.

| Side | Where | How |
|---|---|---|
| Local | The story's frontmatter — an `epic:` (or `parent:`) key recording the parent epic (a relative `[name].epic.md` path and/or the epic's Jira issue key) | Written by the story layer when a parent is set |
| Jira | The Story issue's parent / Epic Link field | Pushed via `{{skill:jira.create-jira-issues}}` / `{{skill:jira.update-jira-issues}}` (`profileName: Story`) with `parentKey` (the epic's Jira **issue key**) |

The Jira side needs the epic's **issue key**. The local side may reference the
epic by file path, issue key, or both.

## Parent-Epic Source Detection

The desired parent is a single value that is **either** an epic file path **or**
an epic Jira issue key, auto-detected by shape — the same heuristic the
`story-source-model` skill uses for stories:

| Value shape | Example | Meaning |
|---|---|---|
| Epic issue key | `AIP-100`, `PROJ-4567` | The parent epic already lives in Jira. Use it directly as `parentKey`. |
| Filesystem path | `../ai-portal.epic.md` | A local epic file. Resolve it to its recorded Jira issue key before pushing to Jira (see below). |
| `none` / `unassigned` | — | Clear the parent. |

Heuristic: an issue key matches `^[A-Z][A-Z0-9]+-\d+$` with no path separators or
extension; anything containing `/`, `\`, `.`, or a file extension is a path; when
ambiguous, treat it as a path.

## Resolving an Epic File to Its Issue Key

When the parent is given as a local `[name].epic.md` path, read that epic's
recorded Jira issue key (its frontmatter `jira:` key, per the epic package's
`epic-source-model`). Then:

- **Epic has a recorded issue key** → use it as `parentKey` and push to Jira.
- **Epic has no issue key yet** → it has not been synced. Record the local link
  in the story frontmatter, and tell the user the epic must be synced first —
  via the epic package's `epic-jira-sync` skill — before the parent can be
  pushed to Jira. Do not invent or guess a key.

## The Link Policies

The link operation takes a `policy` that decides what it does:

| `policy` | Behavior |
|---|---|
| `verify` | Read-only. Report the story's current parent (local + Jira) and whether they agree. Never mutate. |
| `ensure-linked` *(default)* | If the story has no parent, set it to the desired epic. If already linked to the desired epic, no-op. If linked to a **different** epic, surface the conflict and confirm before re-parenting. |
| `link` | Set the parent to the desired epic, surfacing a conflict first if it differs from the current parent. |

## Pushing the Link to Jira

- **The story already has a Jira issue** → `{{skill:jira.update-jira-issues}}` with
  `profileName: Story`, `issueKey`, and `parentKey=<epic issue key>` (or
  `parentKey="unassigned"` to clear). Track `parent` in the changed fields.
- **The story has no Jira issue yet** → record the parent locally only; it will be
  applied on the next sync, which passes `parentKey` to
  `{{skill:jira.create-jira-issues}}` on first sync. See `{{skill:story-jira-sync}}`.

## Surface Before Re-Parenting

Re-parenting a story that **already belongs to a different epic** is never silent
— it mirrors the sync layer's "surface before overwriting" rule. Show the current
parent and the proposed parent and confirm before pushing the update:

```text
Parent on PAY-512
  Currently under epic: AIP-100 (AI Portal)
  Would move to:        AIP-205 (Billing Revamp)
  Re-parent? [confirm / skip]
```

Linking a story that is **unparented** needs no confirmation under
`ensure-linked` — there is nothing to clobber.

## Config & Connection Remediation

The jira skills load and validate `.ai/jira.config.json` internally. Relay any
thrown `CONFIG_INVALID` / `PROJECT_NOT_IN_CONFIG` / `CONNECTION_FAILED` /
`ISSUE_NOT_FOUND` verbatim and point the user at `{{skill:jira.configure-jira}}` /
`{{skill:jira.verify-jira-config}}` for config issues — exactly as `story-jira-sync`
does. Do not repair Jira config from the story layer.

## Invocation Contract

Invoked by the `linkStoryToEpic` prompt, or directly by any caller with the inputs
below.

### Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `storyPath` | string | No | Path to the local `[name].story.md` to link. Used to record the parent locally and to resolve a recorded story issue key. |
| `issueKey` | string | No | The story's Jira issue key (e.g. `PAY-512`). When omitted, resolved from `storyPath` per `{{skill:story-source-model}}`. |
| `parentEpic` | string | No | The desired parent epic — a local `[name].epic.md` path **or** an epic Jira issue key, or `none` to clear. Required unless `policy = verify`; ask the user when absent. |
| `policy` | string | No | `verify` \| `ensure-linked` \| `link`. Default `ensure-linked`. See [The Link Policies](#the-link-policies). |

One of `storyPath` or `issueKey` is required. Pushing to Jira needs a recorded story
issue key; without one, the link is recorded locally only.

### Procedure

1. **Resolve the story.** Resolve the local story from `storyPath` when provided,
   and the story's Jira issue key from `issueKey` or the story's recorded key per
   `{{skill:story-source-model}}`. If neither resolves, the link can still be
   recorded locally — note that the Jira push happens on the next sync.
2. **Resolve the desired parent** per
   [Parent-Epic Source Detection](#parent-epic-source-detection) and
   [Resolving an Epic File to Its Issue Key](#resolving-an-epic-file-to-its-issue-key).
3. **Apply the policy** per [The Link Policies](#the-link-policies), surfacing and
   confirming a re-parent conflict before pushing.
4. **Push and record.** When the story has a Jira issue, push via
   `{{skill:jira.update-jira-issues}}` (`profileName: Story`, `issueKey`,
   `parentKey`). Always record the parent in the story frontmatter.

### Returns

```json
{
  "success": true,
  "storyPath": "./payment-retries.story.md",
  "issueKey": "PAY-512",
  "parentEpicKey": "AIP-100",
  "linked": true,
  "changed": true,
  "pushedToJira": true,
  "conflict": null
}
```

| Field | Meaning |
|---|---|
| `success` | Whether the operation completed. |
| `storyPath` / `issueKey` | The story acted on. |
| `parentEpicKey` | The resulting parent epic issue key, or `null` when unparented / unresolved. |
| `linked` | Whether the story has a parent epic after the operation. |
| `changed` | Whether this run mutated the parent (locally and/or in Jira). |
| `pushedToJira` | Whether the parent was pushed to Jira (`false` when only recorded locally because the story or epic has no issue yet). |
| `conflict` | Present when the story was under a different epic — records the prior parent and resolution (`confirmed-reparent` / `skipped`); `null` otherwise. |

### Errors

| Code | Raised when | Recovery |
|---|---|---|
| `NO_ISSUE_KEY` | A Jira push was required but no story issue key resolved and the link could not be recorded locally either. Carries `storyPath`. | Run `{{skill:story-jira-sync}}` to create and link an issue, or pass `storyPath` to record the parent locally. |
| `CONNECTION_FAILED` | Relayed from jira — Atlassian MCP not connected/authenticated. | Surface as-is. |
| `ISSUE_NOT_FOUND` | Relayed from jira — the story or epic issue key does not exist. | Surface as-is. |
| `UPDATE_FAILED` | Relayed from jira — the update call failed. | Surface as-is. |

An epic that has not been synced is **not** an error — the link is recorded locally
and `pushedToJira` returns `false`.

## Worked Examples

### Example 1 — Link an existing story to an epic by issue key

`storyPath="./payment-retries.story.md"`, `parentEpic="AIP-100"`, policy
`ensure-linked`, story has issue `PAY-512`, currently unparented:

1. Detect `AIP-100` as an issue key → use directly as `parentKey`.
2. Story is unparented → no conflict.
3. `{{skill:jira.update-jira-issues}}` `profileName: Story` `issueKey="PAY-512"`
   `parentKey="AIP-100"`.
4. Record `epic: AIP-100` in the story frontmatter.

### Example 2 — Link by local epic path, epic not yet synced

`parentEpic="../ai-portal.epic.md"`, the epic has no recorded issue key:

1. Detect a path → read the epic's frontmatter → no `jira:` key.
2. Record the local link (`epic: ../ai-portal.epic.md`) in the story.
3. Tell the user to sync the epic first via the epic package's `epic-jira-sync`
   skill; the Jira parent will be applied on the next story sync.

### Example 3 — Re-parent conflict

Story `PAY-512` is under `AIP-100`; `parentEpic="AIP-205"`, policy `ensure-linked`:

1. Current parent (`AIP-100`) differs from desired (`AIP-205`) → **conflict.**
2. Surface and confirm. On confirm → `{{skill:jira.update-jira-issues}}`
   `profileName: Story` `issueKey="PAY-512"` `parentKey="AIP-205"`; update the
   frontmatter. On skip → leave `AIP-100`, note the divergence.
