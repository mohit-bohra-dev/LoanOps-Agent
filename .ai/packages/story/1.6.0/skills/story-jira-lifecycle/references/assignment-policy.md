# Assignment Policy

How `assignStory` decides whether to read, set, skip, or surface a story's Jira
assignee. Assignment is checked **in addition to** state so the tracker reflects
who is actually doing the work. All mutation goes through
`{{skill:jira.update-jira-issues}}` (`assignee`); all reads through
`{{skill:jira.retrieve-jira}}` (`assignee`).

## The Three Policies

| `policy` | Reads | Mutates? | Behavior |
|---|---|---|---|
| `verify` | yes | no | Report assignment state only: assigned or unassigned, and to whom. Never call the jira update skill. |
| `ensure-assigned` *(default)* | yes | conditionally | Make sure the story has the intended assignee. See the decision table below. |
| `assign` | yes | yes (after conflict check) | Force the assignee to the requested value, surfacing a conflict first if the current assignee differs. |

## The `assignee` Input

`assignStory` resolves the desired assignee from its `assignee` parameter:

| `assignee` value | Meaning |
|---|---|
| `me` *(default)* | The current MCP-authenticated user. Pass `assignee="me"` straight through to `{{skill:jira.update-jira-issues}}`; jira resolves it to the caller's account id. |
| a Jira account id (e.g. `712020:7652…`) | Assign that specific account. |
| `unassigned` | Clear the assignee (only meaningful for `assign`). |

Arbitrary display names (e.g. "Dana Lee") are **not** resolvable from the story
layer — jira needs an account id or `me`. If a caller supplies a bare name,
surface that an account id (or `me`) is required rather than guessing.

## `ensure-assigned` Decision Table

This is the default policy and the one a coordinator runs at the start of work.
Let *current* = the issue's current assignee, *desired* = the resolved `assignee`
(default `me`).

| Current assignee | Action |
|---|---|
| Unassigned | Assign to *desired*. No confirmation needed — nothing is being clobbered. `{{skill:jira.update-jira-issues}}` `assignee=<desired>`. |
| Already *desired* | No-op. Report "already assigned to <desired>." |
| Someone **else** | **Conflict.** Do not reassign silently. Surface who holds it and confirm before reassigning (see below). |

## Resolving the Current User

When `assignee="me"`, you do not need to resolve the account id yourself — pass
`me` to `{{skill:jira.update-jira-issues}}` and let jira resolve it. To *compare* the
current assignee against "me" for the conflict check, rely on jira's resolution:
the cleanest path is to let jira compare, or fetch the current user's identity
through the same connection jira uses. When in doubt, treat "current assignee is
non-empty and you cannot confirm it is the current user" as a possible conflict
and surface it — err toward asking, exactly as the sync layer errs toward not
overwriting.

## Surfacing an Assignee Conflict

When the current assignee is someone other than the desired assignee, halt the
mutation and surface it:

```text
Assignment on PAY-512
  Currently assigned to: Dana Lee
  Would assign to:       you (current user)
  Reassign? [confirm / skip]
```

| User choice | Action |
|---|---|
| **Confirm** | `{{skill:jira.update-jira-issues}}` `issueKey=<key>` `assignee=<desired>`. |
| **Skip** | Leave the current assignee. Note in the report that the story stays assigned to someone else by the user's choice. |

Never reassign a story held by someone else without explicit confirmation.

## Output of an Assignment Check

`assignStory` reports a small, stable shape so callers (including a spec
coordinator) can act on it:

- `assigned` — whether the story has any assignee after the check.
- `assignee` — the resulting assignee (account id or display label), or `null`.
- `changed` — whether this run mutated the assignee.
- `conflict` — present when the story was assigned to someone else; records the
  prior assignee and how it was resolved (`confirmed-reassign` / `skipped`).

## Relationship to State

Assignment and state are **independent**. A story can be `In Development` but
unassigned (a gap this check closes), or assigned but still `To Do`. A coordinator
typically runs both at the start of a run: ensure assignment, then transition
state. Neither implies the other; do both explicitly.
