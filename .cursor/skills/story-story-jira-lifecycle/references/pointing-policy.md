# Pointing Policy

How `pointStory` decides whether to read, set, skip, or surface a story's Jira
story-point estimate. Pointing is checked **in addition to** state and assignment
because many project workflows validate on it — a story with no points can be
blocked from leaving `Backlog` no matter who it is assigned to. All mutation goes
through `{{skill:jira.update-jira-issues}}` (`storyPoints`); all reads through
`{{skill:jira.retrieve-jira}}`.

`pointStory` **persists** an estimate; it never derives one. Deciding the number
is a separate, judgment-bearing concern — see the nexus `/nexus.estimateStory`
command. This mirrors `assignStory`, which sets an assignee but never decides who
should own the work.

## The Three Policies

| `policy` | Reads | Mutates? | Behavior |
|---|---|---|---|
| `verify` | yes | no | Report the current estimate only: pointed or unpointed, and with what value. Never call the jira update skill. |
| `ensure-pointed` *(default)* | yes | conditionally | Make sure the story carries an estimate. See the decision table below. |
| `set` | yes | yes (after conflict check) | Force the estimate to the requested value, surfacing a conflict first when the story already carries a different one. |

## The `points` Input

| `points` value | Meaning |
|---|---|
| a number (e.g. `5`) | The estimate to persist. Written as a **bare number** — the configured Story Points field is numeric and rejects the `{"value": …}` option wrapper the select fields use. |
| omitted | Valid only for `verify`. For `ensure-pointed` / `set`, a missing value is a `MissingPointsError` — this prompt does not invent an estimate. |

Point scales are team-specific (Fibonacci, linear, t-shirt-mapped-to-numbers).
Treat the value as opaque: pass through whatever the caller supplies and let Jira
reject values the field does not accept, rather than validating against an
assumed scale.

## `ensure-pointed` Decision Table

This is the default policy and the one a coordinator runs before trying to move a
story out of `Backlog`. Let *current* = the issue's existing estimate, *desired* =
the supplied `points`.

| Current estimate | Action |
|---|---|
| Unpointed (`null`) | Set to *desired*. No confirmation needed — nothing is being clobbered. `{{skill:jira.update-jira-issues}}` `storyPoints=<desired>`. |
| Already *desired* | No-op. Report "already pointed at <desired>." |
| A **different** number | **Conflict.** Do not re-point silently. Surface both values and confirm (see below). |

## Surfacing a Re-Point Conflict

An existing estimate is a recorded team decision — often the output of a planning
session. Overwriting it silently destroys that signal, so halt and surface:

```text
Estimate on PAY-512
  Currently pointed at: 3
  Would set to:         8
  Re-point? [confirm / skip]
```

| User choice | Action |
|---|---|
| **Confirm** | `{{skill:jira.update-jira-issues}}` `issueKey=<key>` `storyPoints=<desired>`. |
| **Skip** | Leave the existing estimate. Note in the report that the story keeps its prior points by the user's choice. |

Never overwrite an existing estimate without explicit confirmation.

## Sub-tasks Are Not Estimable

Sub-tasks do not carry story points. `{{skill:jira.update-jira-issues}}` rejects
`storyPoints` for the `Sub-task` profile with `FieldValidationError` rather than
dropping it silently; relay that verbatim instead of retrying without the field.

## When the Field Is Not Configured

The estimate lives in a per-project custom field resolved from
`config.fieldIds.storyPoints`. When that is `null`, the project either does not
expose Story Points or the config predates it. Return `FieldNotConfiguredError`
and point the user at `{{skill:jira.configure-jira}}` to (re-)discover the field —
do **not** guess a `customfield_NNN` id.

## Output of a Pointing Check

`pointStory` reports a small, stable shape so callers can act on it:

- `pointed` — whether the story carries an estimate after the check.
- `points` — the resulting estimate, or `null` when unpointed.
- `changed` — whether this run mutated the estimate.
- `conflict` — present when the story already carried a different estimate;
  records the prior value and how it was resolved (`confirmed-repoint` /
  `skipped`).

## Relationship to State and Assignment

All three dimensions are **independent**, but pointing has a one-way coupling to
state that the other two do not: a workflow validator can make the estimate a
*precondition* for a transition. When `transitionStory` fails with
`TRANSITION_FAILED` and the message names Story Points, run `pointStory` first
and retry the transition — that ordering is the fix, not a different target
status.
