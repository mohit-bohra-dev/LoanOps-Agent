---
name: story-story-jira-lifecycle
description: >-
  How a story's Jira issue is driven through its tracker lifecycle — its workflow
  **state** (status transitions), its **assignment** (assignee), and its
  **estimate** (story points). Covers transitioning status via
  @./.cursor\skills\jira-update-jira-issues\SKILL.md with `transition`, reading the current assignee
  and estimate from @./.cursor\skills\jira-retrieve-jira\SKILL.md, the verify / ensure / set policy
  families, resolving the current user, and surfacing an assignee or re-point
  conflict before overwriting. Use when starting or completing work on a story,
  transitioning issue status, checking who a story is assigned to, or ensuring it
  carries the estimate a workflow validator requires. The three are orthogonal Jira
  operations, co-located here because all are tracker-lifecycle concerns the story
  layer drives through jira skills.
promp:
  package: "story"
  version: "1.6.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "story-jira-lifecycle"
---

# Story Jira Lifecycle: State + Assignment + Estimate

A story's tracker lifecycle has three independent dimensions:

- **State** — the issue's workflow status (e.g. `To Do` → `In Development` →
  `In Review` → `Done`).
- **Assignment** — who the issue is assigned to (the assignee).
- **Estimate** — the story-point value the issue carries.

State and assignment are fully independent. The estimate is independent too, with
one asymmetry worth knowing: a project's workflow can make it a **precondition for
a transition**, so an unpointed story may be unable to leave `Backlog` at all.

All three are driven by the story layer **only through `{{skill:jira.*}}` entry
points** — never by talking to Atlassian or the MCP directly. jira is usually
installed as a **transitive** dependency, for which the promp CLI emits skills and
agents but no command files, so its skills are the stable contract and the only
artifacts guaranteed to be on disk. Content sync (summary/description/AC) is a
separate concern; see `story-jira-sync`.

## When to Use

- Starting work on a story (`transitionStory` to an in-progress status)
- Completing work (`transitionStory` to a completion/review status)
- Checking that a story is assigned and assigning it (`assignStory`)
- Ensuring a story carries an estimate before a transition that requires one
  (`pointStory`)
- Any caller (e.g. a spec execution coordinator) that must move the issue's
  status or confirm/repair its assignment or estimate at the start or end of a run

| Lifecycle need | jira entry point | Distinguishing input |
|---|---|---|
| Read current status + assignee + estimate | `@./.cursor\skills\jira-retrieve-jira\SKILL.md` (`issueKey`) | — |
| Transition status | `@./.cursor\skills\jira-update-jira-issues\SKILL.md` (`issueKey`, `transition`) | `profileName: Story` |
| Set the assignee | `@./.cursor\skills\jira-update-jira-issues\SKILL.md` (`issueKey`, `assignee`) | `profileName: Story` |
| Set the estimate | `@./.cursor\skills\jira-update-jira-issues\SKILL.md` (`issueKey`, `storyPoints`) | `profileName: Story` |

The update skill serves every issue type, so each call site states
`profileName: Story`.

A transition and an assignment can ride along on a single update call, or each can
stand alone. Keep them as separate, intention-revealing operations unless you
deliberately want to do both at once.

## State: Status Transitions

Move the issue through its workflow with `@./.cursor\skills\jira-update-jira-issues\SKILL.md` and
the `transition` input:

- **At the start of work:** transition to the in-progress status, e.g.
  `transition="In Development"`.
- **At completion:** transition to the team's completion / review status.

A transition is just another update call — it can ride along with a field update or
stand alone (`issueKey` + `transition`, nothing else).

**Status names are team-specific.** "In Development" vs "In Progress" vs "Dev In
Progress" differ per board. Treat the configured value as opaque; do not assume a
canonical name. If `@./.cursor\skills\jira-update-jira-issues\SKILL.md` returns `TransitionError`
(`TRANSITION_FAILED`) the requested status is not reachable from the issue's
current state — surface that to the user rather than guessing an alternative.

## Assignment: Check and Set

Assignment is **checked in addition to state**: knowing a story is `In
Development` is not enough — it should also be assigned to whoever is doing the
work, so the tracker reflects reality.

### Reading the current assignee

Fetch the issue with `@./.cursor\skills\jira-retrieve-jira\SKILL.md` and read the assignee from its
returned `assignee` field (the issue content also shows an **Assignee:** line).
A story with no assignee reads as unassigned (`null` / "Unassigned").

### Setting the assignee

Set it with `@./.cursor\skills\jira-update-jira-issues\SKILL.md` passing `assignee`. The value is a
Jira account id, or the token `me` to mean the current MCP-authenticated user (jira
resolves `me` to the caller's account id). When you want the issue assigned to
the person running the work, pass `assignee="me"`.

### The assignment policies

The `assign` operation takes a `policy` that decides what the check does:

| `policy` | Behavior |
|---|---|
| `verify` | Read-only. Report whether the story is assigned and to whom. Never mutate. |
| `ensure-assigned` *(default)* | If unassigned, assign per `assignee` (default `me`). If already assigned to the requested assignee, no-op. If assigned to **someone else**, surface the conflict and confirm before reassigning. |
| `assign` | Set the assignee to the requested value, surfacing a conflict first if it differs from the current assignee. |

Read `references/assignment-policy.md` for the full decision table, current-user
resolution, and how an assignee conflict is surfaced and confirmed.

## Estimate: Check and Set

An estimate is **checked in addition to state and assignment** because a workflow
validator can require it. The `point` operation persists a number; it never derives
one — deciding the value belongs to the nexus `/nexus.estimateStory` command,
exactly as deciding *who* should own a story sits outside the `assign` operation.

### Reading the current estimate

Fetch the issue with `@./.cursor\skills\jira-retrieve-jira\SKILL.md` and read its story-point value.
A story with no estimate reads as unpointed (`null`).

### Setting the estimate

Set it with `@./.cursor\skills\jira-update-jira-issues\SKILL.md` passing `storyPoints`. It is
written as a **bare number** — the field is numeric and rejects the
`{"value": …}` wrapper the select fields use. When `config.fieldIds.storyPoints`
is `null` the project does not expose the field; return `FieldNotConfiguredError`
and point at `@./.cursor\skills\jira-configure-jira\SKILL.md` rather than guessing a field id.

### The pointing policies

| `policy` | Behavior |
|---|---|
| `verify` | Read-only. Report whether the story is pointed and with what value. Never mutate. |
| `ensure-pointed` *(default)* | If unpointed, set `points`. If already at that value, no-op. If it carries a **different** value, surface the conflict and confirm before re-pointing. |
| `set` | Set the estimate to `points`, surfacing a conflict first if it differs from the current value. |

Read `references/pointing-policy.md` for the full decision table, the
sub-task restriction, and how a re-point conflict is surfaced and confirmed.

## Surface Before Reassigning

Assignment and pointing mirror the sync layer's "surface before overwriting"
philosophy. Reassigning a story **already assigned to someone else**, or
re-pointing one that already carries a different estimate, is never silent:
surface the current value and what the change would do, and confirm before
calling the update skill. Setting a value that is currently empty needs no
confirmation under the `ensure-*` policies — there is nothing to clobber.

## Config & Connection Remediation

The jira skills load and validate `.ai/jira.config.json` internally. When a
lifecycle call throws, relay it and point at the remediation:

| Symptom (thrown by jira) | Remediation |
|---|---|
| `TRANSITION_FAILED` | The target status is not reachable from the current status — report it and ask the user for the correct target; do not guess. When the message names a required field (commonly Story Points, sometimes Epic Link), the fix is to supply that field and retry, not to pick a different status. |
| `FIELD_VALIDATION_FAILED` on `storyPoints` | The issue type is not estimable (Sub-tasks carry no points) — relay verbatim; do not retry without the field. |
| `CONFIG_INVALID`, `PROJECT_NOT_IN_CONFIG` | Run `@./.cursor\skills\jira-configure-jira\SKILL.md` or `@./.cursor\skills\jira-verify-jira-config\SKILL.md`. |
| `CONNECTION_FAILED` | Atlassian MCP not connected/authenticated — surface as-is. |
| `ISSUE_NOT_FOUND` | The issue key does not exist — surface as-is. |

## Invocation Contract

This skill is invoked with one `operation` per call: `transition`, `assign`, or
`point`. Invoked by the `transitionStory`, `assignStory`, and `pointStory` prompts
respectively, or directly by any caller with the inputs below.

### Shared inputs and resolution

Every operation resolves the issue the same way, and every operation shares these
two inputs:

| Input | Type | Required | Description |
|---|---|---|---|
| `issueKey` | string | No | The Jira issue key (e.g. `PAY-512`). |
| `storyPath` | string | No | Path to the local `[name].story.md`; used to resolve a recorded issue key when `issueKey` is not given. |

One of `issueKey` or a `storyPath` with a recorded key is required. Resolve in that
order: use `issueKey` when provided, otherwise read the recorded key from
`storyPath` per `@./.cursor\skills\story-story-source-model\SKILL.md`. If neither resolves, raise
`NO_ISSUE_KEY` and stop — there is nothing to act on, and the story likely needs
`@./.cursor\skills\story-story-jira-sync\SKILL.md` first to create and link an issue.

### operation: transition

Move the story's issue to a target workflow status.

| Input | Type | Required | Description |
|---|---|---|---|
| `operation` | string | Yes | `transition`. |
| `status` | string | Yes | The target status name (e.g. `In Development`, `In Review`, `Done`). Team-specific and opaque — passed through verbatim. |

**Procedure:** resolve the issue key, then call
`@./.cursor\skills\jira-update-jira-issues\SKILL.md` with `profileName: Story`, `issueKey`, and
`transition = status`, with no field changes. See
[State: Status Transitions](#state-status-transitions) for the status-name rule.

```json
{
  "success": true,
  "issueKey": "PAY-512",
  "status": "In Development",
  "transitioned": true
}
```

| Field | Meaning |
|---|---|
| `success` | Whether the transition completed. |
| `issueKey` | The transitioned issue. |
| `status` | The target status requested. |
| `transitioned` | Whether the status actually changed (`false` on a no-op when already in the target status). |

### operation: assign

Check the story's assignment and, per policy, ensure it is assigned.

| Input | Type | Required | Description |
|---|---|---|---|
| `operation` | string | Yes | `assign`. |
| `assignee` | string | No | The desired assignee — a Jira account id, `me` for the current MCP-authenticated user, or `unassigned` to clear. Default `me`. |
| `policy` | string | No | `verify` \| `ensure-assigned` \| `assign`. Default `ensure-assigned`. See [the assignment policies](#the-assignment-policies). |

**Procedure:** resolve the issue key, read the current assignee with
`@./.cursor\skills\jira-retrieve-jira\SKILL.md`, then apply the policy — surfacing a conflict and
waiting for **confirm / skip** before any update call when the story is held by
someone else. Full decision table in `references/assignment-policy.md`.

```json
{
  "success": true,
  "issueKey": "PAY-512",
  "assigned": true,
  "assignee": "me",
  "changed": true,
  "conflict": null
}
```

| Field | Meaning |
|---|---|
| `success` | Whether the check completed. |
| `issueKey` | The issue checked. |
| `assigned` | Whether the story has any assignee after the check. |
| `assignee` | The resulting assignee (account id or display label), or `null` when unassigned. |
| `changed` | Whether this run mutated the assignee. |
| `conflict` | Present when the story was assigned to someone else — records the prior assignee and the resolution (`confirmed-reassign` / `skipped`); `null` otherwise. |

### operation: point

Check the story's estimate and, per policy, ensure it carries one.

| Input | Type | Required | Description |
|---|---|---|---|
| `operation` | string | Yes | `point`. |
| `points` | number | No | The desired estimate. Required for `ensure-pointed` and `set`; ignored by `verify`. Passed through opaquely — the team's scale is not validated here. |
| `policy` | string | No | `verify` \| `ensure-pointed` \| `set`. Default `ensure-pointed`. See [the pointing policies](#the-pointing-policies). |

**Procedure:** resolve the issue key, read the current estimate with
`@./.cursor\skills\jira-retrieve-jira\SKILL.md`, then apply the policy — surfacing a conflict and
waiting for **confirm / skip** before any update call when the story already
carries a different value. A missing `points` under a mutating policy is
`MISSING_POINTS`: this operation never invents an estimate. Full decision table in
`references/pointing-policy.md`.

```json
{
  "success": true,
  "issueKey": "PAY-512",
  "pointed": true,
  "points": 5,
  "changed": true,
  "conflict": null
}
```

| Field | Meaning |
|---|---|
| `success` | Whether the check completed. |
| `issueKey` | The issue checked. |
| `pointed` | Whether the story carries an estimate after the check. |
| `points` | The resulting estimate, or `null` when unpointed. |
| `changed` | Whether this run mutated the estimate. |
| `conflict` | Present when the story already carried a different estimate — records the prior value and the resolution (`confirmed-repoint` / `skipped`); `null` otherwise. |

### Errors

| Code | Operation | Raised when | Recovery |
|---|---|---|---|
| `NO_ISSUE_KEY` | all | No issue key was provided or recorded on the story. Carries `storyPath`. | Run `@./.cursor\skills\story-story-jira-sync\SKILL.md` to create and link an issue first. |
| `MISSING_POINTS` | `point` | `ensure-pointed` or `set` was requested without a `points` value. Carries `policy`. | Supply a value — e.g. from the nexus `/nexus.estimateStory` command. This operation never derives one. |
| `FIELD_NOT_CONFIGURED` | `point` | The project has no Story Points field (`fieldIds.storyPoints` is `null`). Carries `projectKey`. | Run `@./.cursor\skills\jira-configure-jira\SKILL.md` to discover the field; never guess a `customfield_NNN` id. |
| `TRANSITION_FAILED` | `transition` | Relayed from jira — the requested status is not reachable from the current status. | Report it and ask the user for the correct target; do not guess. When the message names a required field, supply that field and retry. |
| `FIELD_VALIDATION_FAILED` | `point` | Relayed from jira — the issue type is not estimable (Sub-tasks carry no points). | Relay verbatim; do not retry without the field. |
| `CONNECTION_FAILED` | all | Relayed from jira — Atlassian MCP not connected/authenticated. | Surface as-is. |
| `ISSUE_NOT_FOUND` | all | Relayed from jira — the issue key does not exist. | Surface as-is. |
| `UPDATE_FAILED` | `assign`, `point` | Relayed from jira — the update call failed. | Surface as-is. |

## Worked Examples

### Example 1 — Start of work: transition + assignment

A coordinator begins work on `PAY-512`:

1. `@./.cursor\skills\jira-retrieve-jira\SKILL.md` `issueKey="PAY-512"` → status `To Do`, assignee
   `null`.
2. Assignment (policy `ensure-assigned`, `assignee="me"`): unassigned → assign to
   me. `@./.cursor\skills\jira-update-jira-issues\SKILL.md` `profileName: Story`
   `issueKey="PAY-512"` `assignee="me"`.
3. State: `@./.cursor\skills\jira-update-jira-issues\SKILL.md` `profileName: Story`
   `issueKey="PAY-512"` `transition="In Development"`.

### Example 2 — Assignee conflict surfaced

`PAY-512` is already assigned to Dana; the coordinator runs as Sam with
`ensure-assigned`:

1. `@./.cursor\skills\jira-retrieve-jira\SKILL.md` → assignee `Dana`.
2. Requested assignee (`me` = Sam) differs from current (Dana) → **conflict.**
   Surface: "PAY-512 is assigned to Dana; reassign to you (Sam)? [confirm/skip]".
3. On confirm → `@./.cursor\skills\jira-update-jira-issues\SKILL.md` `assignee="me"`. On skip →
   leave Dana, note the story stays assigned to someone else.

### Example 3 — Completion transition

When every in-scope unit is done:

- `@./.cursor\skills\jira-update-jira-issues\SKILL.md` `profileName: Story` `issueKey="PAY-512"`
  `transition="In Review"` (team-configured completion status). On
  `TRANSITION_FAILED`, report that the target is not reachable and ask for the
  correct one.

## Reference Documents

- `references/assignment-policy.md` — The full assignment decision table, the
  `verify` / `ensure-assigned` / `assign` policies, current-user resolution
  (`me`), and the assignee-conflict surfacing/confirm flow. Read when running an
  assignment check or deciding whether to set, skip, or surface.
- `references/pointing-policy.md` — The full pointing decision table, the
  `verify` / `ensure-pointed` / `set` policies, the sub-task restriction, the
  unconfigured-field path, and the re-point conflict flow. Read when running a
  pointing check or when a transition is blocked for want of an estimate.
