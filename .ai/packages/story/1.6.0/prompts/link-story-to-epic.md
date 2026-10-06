# Link Story to Epic

Set, verify, or clear a story's parent **epic** — recording it locally and pushing the Epic Link / parent to Jira.

## Parameters

- **{{storyPath}}** (string, optional): Path to the local `[name].story.md` to link. Used to record the parent locally and to resolve a recorded story issue key.
- **{{issueKey}}** (string, optional): The story's Jira issue key (e.g. `PAY-512`). When omitted, resolved from `{{storyPath}}` per `story-source-model`.
- **{{parentEpic}}** (string, optional): The desired parent epic — a local `[name].epic.md` path **or** an epic Jira issue key, or `none` to clear. Required unless `policy=verify`.
- **{{policy}}** (string, optional): `verify` | `ensure-linked` | `link`. Default `ensure-linked`. See the skill's policy table.

One of `storyPath` or `issueKey` is required (to push to Jira a recorded story issue key must resolve; without one, the link is recorded locally only).

## Instructions

Load **{{skill:story-epic-linking}}** and execute its Invocation Contract with these inputs:

| Parameter | Skill input |
|---|---|
| `{{storyPath}}` | `storyPath` |
| `{{issueKey}}` | `issueKey` |
| `{{parentEpic}}` | `parentEpic` |
| `{{policy}}` | `policy` |

The skill owns parent-epic source detection, epic-file→issue-key resolution, the link policies, conflict surfacing, and the error catalogue. It loads **{{skill:story-source-model}}** when resolving keys from files, and pushes through **{{skill:jira.update-jira-issues}}** (`profileName: Story`, `parentKey`).

## Response Format

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

**Field descriptions:**

- `success`: Whether the operation completed.
- `storyPath` / `issueKey`: The story acted on.
- `parentEpicKey`: The resulting parent epic issue key, or `null` when unparented / unresolved.
- `linked`: Whether the story has a parent epic after the operation.
- `changed`: Whether this run mutated the parent (locally and/or in Jira).
- `pushedToJira`: Whether the parent was pushed to Jira (false when only recorded locally because the story or epic has no issue yet).
- `conflict`: Present when the story was under a different epic — records the prior parent and resolution (`confirmed-reparent` / `skipped`); `null` otherwise.

## Error Handling

Return the error and stop. See `story-epic-linking` (Invocation Contract → Errors) for the full detail and recovery.

- **NoIssueKeyError** (`NO_ISSUE_KEY`) — a Jira push was required but no story issue key resolved and the link could not be recorded locally either.
- **ConnectionError** (`CONNECTION_FAILED`), **IssueNotFoundError** (`ISSUE_NOT_FOUND`), **UpdateError** (`UPDATE_FAILED`) — relayed from jira verbatim.

An epic that has not been synced is **not** an error — the link is recorded locally and `pushedToJira` returns `false`.

## Notes

- **Parent epic may be a file or a key.** A local `[name].epic.md` is resolved to its Jira issue key before pushing; an epic that has not been synced records the link locally until the epic has a Jira issue.
- **Never re-parent silently.** A story under a different epic is surfaced and confirmed before re-parenting.
- **Linking lives in the story layer.** The epic package never sets parents on its children; this prompt is the single **parent** linking entry point.
- **Parent is not dependency.** This prompt only sets the Epic Link / parent relationship. Story-to-story dependency links ("blocked by a sibling story") are a different Jira mechanism — an issue link, not hierarchy — and belong to `linkStoryDependencies`. Never model a dependency as a parent: it would move the story out of its epic.
