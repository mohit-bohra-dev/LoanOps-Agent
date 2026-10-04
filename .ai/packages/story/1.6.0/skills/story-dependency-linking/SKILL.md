---
name: story-dependency-linking
description: >-
  How story-to-story **dependency** relationships ("this story cannot start until
  that one ships") are projected onto Jira as native issue links of type `Blocks`,
  via {{skill:jira.link-jira-issues}}. Covers the dependency-vs-parent distinction
  (a sideways peer link, never hierarchy), the direction rule (`dependsOn` is the
  blocker / inward issue, `story` is the blocked / outward issue), resolving each
  story to its Jira issue key, dropping and reporting edges whose stories have no
  issue yet, batching one call per pass for idempotency, and relaying
  created / skipped / conflict / failed results without reinterpreting them. Use
  when pushing an epic's story dependency tree to Jira, linking a story as blocked
  by a sibling, or deciding whether a relationship is a dependency or a parent
  epic. For the parent-epic relationship, see story-epic-linking.
---

# Story ⇄ Story Dependency Linking

How the story layer projects a **sibling-dependency** graph onto Jira. The
dependency graph is authored in the planning artifacts (typically an epic's story
dependency table); this skill pushes it onto the tracker as native issue links so
build order is visible on the board.

The markdown stays the source of truth. This is a one-way projection: it never
reads Jira links back into the planning artifacts.

## When to Use

- The `linkStoryDependencies` prompt pushes a batch of dependency edges to Jira
- A backlog-sync pass projects an epic's story dependency tree onto the tracker
- Deciding whether a relationship between two stories is a dependency or a parent

## Dependency Is Not Parent

A story has two orthogonal relationship dimensions, and they use different Jira
mechanisms:

| Dimension | Relationship | Jira mechanism | Owning skill |
|---|---|---|---|
| Parent | Story belongs to an Epic | `parentKey` / Epic Link field | `{{skill:story-epic-linking}}` |
| Dependency | Story is blocked by a sibling Story | Issue link, type `Blocks` | **this skill** |

A dependency is a sideways link between peers; a parent is hierarchy. Conflating
them corrupts both graphs: modeling a dependency as a parent moves the story out
of its epic, and modeling a parent as a link leaves the story outside its epic
entirely. This skill never touches `parentKey`; `story-epic-linking` never creates
issue links.

## Direction: dependsOn Blocks Story

Every edge is `{ story, dependsOn }` and maps to a link as:

- `inwardIssue` = the `dependsOn` story — the predecessor that must finish first
- `outwardIssue` = the `story` — the dependent that has to wait
- `type` = `Blocks`

Read it back as a sentence: *dependsOn* **blocks** *story*.

This is the mapping most easily inverted, and inverting it produces a board that
tells the team to work in exactly the wrong order. Restate one edge as a sentence
before pushing a batch.

## Consuming the jira Layer

Every Atlassian operation goes through a jira **skill** entry point. This skill
never talks to Atlassian or the MCP directly and never re-implements link
discovery, direction resolution, or idempotency.

| Dependency need | jira entry point |
|---|---|
| Create the issue links for a batch of edges | `{{skill:jira.link-jira-issues}}` |

`jira.link-jira-issues` owns link-type discovery, direction resolution, existing-link
detection, and the `onTypeUnavailable` soft-fail. Pass the oriented batch and relay
its result.

## The Linking Method

### 1. Resolve every story to a Jira issue key

For each distinct story in the batch (both sides of every edge), detect its shape
and resolve an issue key per `{{skill:story-source-model}}`:

- An issue key (`^[A-Z][A-Z0-9]+-\d+$`) is used as-is.
- A local story path is resolved to its recorded key (frontmatter / status table).

**A story with no Jira issue cannot be linked.** Collect every unresolved story,
drop the edges that touch it, and report them as `unresolved` — do not guess a key
and do not fail the whole batch. Tell the user to run `{{skill:story-jira-sync}}`
for those stories first, then re-run. Links are pushed in a pass *after* stories
exist, so partial resolution is a normal intermediate state rather than an error.

### 2. Orient the edges

Convert each `{ story, dependsOn }` edge into a link entry with `inwardIssue`,
`outwardIssue`, and `type = Blocks` per [Direction](#direction-dependson-blocks-story).

- Expand a `dependsOn` array into one entry per predecessor.
- Drop self-edges (a story listed as depending on itself) and report them — they
  indicate a defect in the source dependency data, not something to push.

### 3. Push the batch through jira

Call `{{skill:jira.link-jira-issues}}` **once** with the whole batch: the oriented
entries, `type = Blocks`, and the caller's `comment`, `onTypeUnavailable`, and
`dryRun` values.

One batched call, not one call per edge: the jira skill reads each inward issue's
existing links once to stay idempotent, so batching avoids re-reading the same
issue repeatedly.

### 4. Relay the result

Relay the `created`, `skipped`, `conflicts`, and `failed` arrays without
reinterpreting them. In particular a **conflict** (the reverse link already
exists) means the two stories disagree about which blocks which — surface it for
the user to resolve rather than picking a side.

## Idempotency

Existing links are read before anything is created, so a dependency pass can run
on every sync without duplicating links. An edge that is already correct comes
back as `skipped` with `ALREADY_LINKED`, not as an error.

## Scope

Story-to-story only. Dependencies that cross epics, or point at non-story work,
are outside this skill's scope — the caller decides whether such an edge belongs
in Jira at all.

## Invocation Contract

Invoked by the `linkStoryDependencies` prompt, or directly by any caller with the
inputs below.

### Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `dependencies` | array | Yes | The edges to push. Each entry is `{ story, dependsOn }`, where both values are a local `[name].story.md` path **or** a story Jira issue key (auto-detected per `story-source-model`). `dependsOn` may be an array when a story has several predecessors. |
| `comment` | string | No | Comment to post on each blocked issue when the link is created — e.g. a pointer back to the epic's dependency table. |
| `onTypeUnavailable` | string | No | `skip` (default) or `fail`. Passed through to `{{skill:jira.link-jira-issues}}` for the case where the project defines no `Blocks` link type. |
| `dryRun` | boolean | No | Resolve and report the planned links without creating any. Default `false`. |

### Returns

```json
{
  "success": true,
  "linksCreated": [
    { "story": "AIP-521", "dependsOn": "AIP-520", "type": "Blocks" }
  ],
  "linksSkipped": [
    { "story": "AIP-522", "dependsOn": "AIP-520", "reason": "ALREADY_LINKED" }
  ],
  "conflicts": [],
  "unresolved": [
    { "story": "./publish-metrics.story.md", "reason": "NO_ISSUE_KEY" }
  ],
  "failed": []
}
```

| Field | Meaning |
|---|---|
| `success` | Whether the pass completed. `true` even when every link was already present or some stories were unresolved; `false` only when nothing could be attempted. |
| `linksCreated` | Edges newly linked in Jira. |
| `linksSkipped` | Edges already correct (`ALREADY_LINKED`) or skipped because the project defines no `Blocks` type (`TYPE_UNAVAILABLE`). |
| `conflicts` | Pairs where the reverse link already exists — reported, never overwritten. |
| `unresolved` | Stories with no Jira issue yet, and the edges dropped because of them. |
| `failed` | Per-edge failures with their codes. |

### Errors

| Code | Raised when | Recovery |
|---|---|---|
| `NO_ISSUE_KEY` | **No** story in the batch resolves to an issue key, so there is nothing to link. Carries the offending `stories` array. | Sync those stories first per `{{skill:story-jira-sync}}`, then re-run. |
| `CONNECTION_FAILED` | Relayed from `{{skill:jira.link-jira-issues}}` — Atlassian MCP not connected/authenticated. | Surface as-is; not a story-side fix. |
| `LINK_TYPE_UNAVAILABLE` | Relayed when the project defines no `Blocks` link type and `onTypeUnavailable = fail`. | Re-run with `onTypeUnavailable = skip`, or have the project define the link type. |
| `ISSUE_NOT_FOUND` | Relayed when a resolved issue key does not exist. | Surface as-is. |
| `PERMISSION_DENIED` | Relayed when the user lacks the Link Issues permission on the project. | Surface as-is. |

A partially unresolved batch is **not** an error — it returns `success: true` with
the dropped edges in `unresolved`.

## Worked Example

An epic's dependency table records that `normalize-events` depends on both
`define-event-schema` and `ingest-raw-events`; the first two are synced
(`AIP-520`, `AIP-521`), `normalize-events` is `AIP-522`, and `publish-metrics` has
no issue yet.

1. Resolve: `AIP-520`, `AIP-521`, `AIP-522` resolve; `./publish-metrics.story.md`
   does not → its edges are dropped and reported as `unresolved`.
2. Orient: `AIP-520` blocks `AIP-522`; `AIP-521` blocks `AIP-522`.
3. Push: one `{{skill:jira.link-jira-issues}}` call with both entries, `type = Blocks`.
4. Relay: one created, one already present (`ALREADY_LINKED`), the
   `publish-metrics` edge reported as `unresolved` with the advice to sync it and
   re-run.
