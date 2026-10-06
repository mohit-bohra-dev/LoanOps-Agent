# Assign Story

Check a story's Jira **assignment** and, per policy, ensure it is assigned — surfacing a conflict before reassigning a story held by someone else.

## Parameters

- **{{issueKey}}** (string, optional): The Jira issue key (e.g. `PAY-512`).
- **{{storyPath}}** (string, optional): Path to the local `[name].story.md`; used to resolve a recorded issue key when `issueKey` is not given.
- **{{assignee}}** (string, optional): The desired assignee — a Jira account id, or the token `me` for the current MCP-authenticated user, or `unassigned` to clear. Default `me`.
- **{{policy}}** (string, optional): `verify` | `ensure-assigned` | `assign`. Default `ensure-assigned`. See the skill's policy table.

One of `issueKey` or a `storyPath` with a recorded key is required.

## Instructions

Load **{{skill:story-jira-lifecycle}}** and execute its Invocation Contract with `operation: assign` and these inputs:

| Parameter | Skill input |
|---|---|
| — | `operation` = `assign` |
| `{{issueKey}}` | `issueKey` |
| `{{storyPath}}` | `storyPath` |
| `{{assignee}}` | `assignee` |
| `{{policy}}` | `policy` |

The skill owns issue-key resolution, the assignment policies (`references/assignment-policy.md`), current-user resolution, conflict surfacing, and the error catalogue. It loads **{{skill:story-source-model}}** when resolving a key from a file, reads the current assignee through **{{skill:jira.retrieve-jira}}**, and sets it through **{{skill:jira.update-jira-issues}}** (`profileName: Story`, `assignee`).

## Response Format

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

**Field descriptions:**

- `success`: Whether the check completed.
- `issueKey`: The issue checked.
- `assigned`: Whether the story has any assignee after the check.
- `assignee`: The resulting assignee (account id or display label), or `null` when unassigned.
- `changed`: Whether this run mutated the assignee.
- `conflict`: Present when the story was assigned to someone else — records the prior assignee and the resolution (`confirmed-reassign` / `skipped`); `null` otherwise.

## Error Handling

Return the error and stop. See `story-jira-lifecycle` (Invocation Contract → Errors) for the full detail and recovery.

- **NoIssueKeyError** (`NO_ISSUE_KEY`) — no issue key was provided or recorded; run `syncStoryToJira` first to create and link an issue.
- **ConnectionError** (`CONNECTION_FAILED`), **IssueNotFoundError** (`ISSUE_NOT_FOUND`), **UpdateError** (`UPDATE_FAILED`) — relayed from jira verbatim.

## Notes

- **Assignment is checked in addition to state.** A coordinator typically runs `assignStory` and `transitionStory` together at the start of a run — both are tracker-lifecycle concerns but independent operations.
- **Never reassign silently.** A story held by someone else is surfaced and confirmed before reassigning.
- **`me` is resolved by jira.** Pass `assignee="me"` through; jira resolves it to the caller's account id. Arbitrary display names need an account id.
