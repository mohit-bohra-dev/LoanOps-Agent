# Point Story

Check a story's Jira **story-point estimate** and, per policy, ensure it carries one — surfacing a conflict before overwriting an estimate the team already set.

## Parameters

- **{{issueKey}}** (string, optional): The Jira issue key (e.g. `PAY-512`).
- **{{storyPath}}** (string, optional): Path to the local `[name].story.md`; used to resolve a recorded issue key when `issueKey` is not given.
- **{{points}}** (number, optional): The desired estimate. Required for `ensure-pointed` and `set`; ignored by `verify`.
- **{{policy}}** (string, optional): `verify` | `ensure-pointed` | `set`. Default `ensure-pointed`. See the skill's policy table.

One of `issueKey` or a `storyPath` with a recorded key is required.

## Instructions

Load **{{skill:story-jira-lifecycle}}** and execute its Invocation Contract with `operation: point` and these inputs:

| Parameter | Skill input |
|---|---|
| — | `operation` = `point` |
| `{{issueKey}}` | `issueKey` |
| `{{storyPath}}` | `storyPath` |
| `{{points}}` | `points` |
| `{{policy}}` | `policy` |

The skill owns issue-key resolution, the pointing policies (`references/pointing-policy.md`), conflict surfacing, the unconfigured-field path, and the error catalogue. It loads **{{skill:story-source-model}}** when resolving a key from a file, reads the current estimate through **{{skill:jira.retrieve-jira}}**, and sets it through **{{skill:jira.update-jira-issues}}** (`profileName: Story`, `storyPoints`).

**This prompt persists an estimate; it does not derive one.** Deciding the number is a judgment-bearing concern that belongs to the nexus `/nexus.estimateStory` command, exactly as deciding *who* should own a story sits outside `assignStory`.

## Response Format

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

**Field descriptions:**

- `success`: Whether the check completed.
- `issueKey`: The issue checked.
- `pointed`: Whether the story carries an estimate after the check.
- `points`: The resulting estimate, or `null` when unpointed.
- `changed`: Whether this run mutated the estimate.
- `conflict`: Present when the story already carried a different estimate — records the prior value and the resolution (`confirmed-repoint` / `skipped`); `null` otherwise.

## Error Handling

Return the error and stop. See `story-jira-lifecycle` (Invocation Contract → Errors) for the full detail and recovery.

- **NoIssueKeyError** (`NO_ISSUE_KEY`) — no issue key was provided or recorded; run `syncStoryToJira` first to create and link an issue.
- **MissingPointsError** (`MISSING_POINTS`) — a mutating policy was requested without `{{points}}`; this prompt never invents an estimate.
- **FieldNotConfiguredError** (`FIELD_NOT_CONFIGURED`) — the project has no Story Points field (`fieldIds.storyPoints` is `null`); re-run jira config discovery rather than guessing a field id.
- **ConnectionError** (`CONNECTION_FAILED`), **IssueNotFoundError** (`ISSUE_NOT_FOUND`), **UpdateError** (`UPDATE_FAILED`), **FieldValidationError** (`FIELD_VALIDATION_FAILED`, e.g. points on a Sub-task) — relayed from jira verbatim.

## Notes

- **Estimates are checked in addition to state and assignment.** A coordinator typically runs `assignStory`, `pointStory`, and `transitionStory` together — all tracker-lifecycle concerns, but independent operations.
- **Pointing has a one-way coupling to state.** When `transitionStory` fails with `TRANSITION_FAILED` and the message names Story Points, run `pointStory` and retry the transition; picking a different target status is not the fix.
- **Never re-point silently.** An existing estimate is a recorded team decision, usually from a planning session — overwriting it destroys that signal.
- **Sub-tasks are not estimable.** jira rejects `storyPoints` for the `Sub-task` profile; relay the error rather than retrying without the field.
- **The scale is the team's.** Fibonacci, linear, or t-shirt-mapped — the value is passed through opaquely and validated by Jira, not by this prompt.
