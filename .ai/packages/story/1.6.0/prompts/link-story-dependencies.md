# Link Story Dependencies

Push story-to-story **dependency** relationships to Jira as native issue links (`Blocks` / `is blocked by`).

## Parameters

- **{{dependencies}}** (array, required): The dependency edges to push. Each entry is `{ story, dependsOn }`, where both values are a local `[name].story.md` path **or** a story Jira issue key (auto-detected per `story-source-model`). `dependsOn` may be an array when a story has several predecessors. Direction: `dependsOn` is the blocker, `story` is the blocked issue.
- **{{comment}}** (string, optional): Comment to post on each blocked issue when the link is created — for example a pointer back to the epic's dependency table.
- **{{onTypeUnavailable}}** (string, optional): `skip` (default) or `fail`, for the case where the project defines no `Blocks` link type.
- **{{dryRun}}** (boolean, optional): Resolve and report the planned links without creating any.

## Instructions

Load **{{skill:story-dependency-linking}}** and execute its Invocation Contract with these inputs:

| Parameter | Skill input |
|---|---|
| `{{dependencies}}` | `dependencies` |
| `{{comment}}` | `comment` |
| `{{onTypeUnavailable}}` | `onTypeUnavailable` |
| `{{dryRun}}` | `dryRun` |

The skill owns the direction rule (`dependsOn` blocks `story`), issue-key resolution, edge orientation, self-edge and unresolved-story handling, batching, and the error catalogue. It loads **{{skill:story-source-model}}** for story-path → issue-key resolution, and delegates every Atlassian operation to **{{skill:jira.link-jira-issues}}**, which discovers the link type and stays idempotent.

Dependencies are **not** parents. This prompt never touches `parentKey`; the parent-epic dimension belongs to `linkStoryToEpic`.

## Response Format

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

**Field descriptions:**

- `success`: Whether the pass completed. `true` even when every link was already present or some stories were unresolved; `false` only when nothing could be attempted.
- `linksCreated`: Edges newly linked in Jira.
- `linksSkipped`: Edges already correct (`ALREADY_LINKED`) or skipped because the project defines no `Blocks` type (`TYPE_UNAVAILABLE`).
- `conflicts`: Pairs where the reverse link already exists — reported, never overwritten.
- `unresolved`: Stories with no Jira issue yet, and the edges dropped because of them.
- `failed`: Per-edge failures with their codes.

## Error Handling

Return the error and stop. See `story-dependency-linking` (Invocation Contract → Errors) for the full detail and recovery.

- **NoIssueKeyError** (`NO_ISSUE_KEY`) — **no** story in the batch has a Jira issue, so there is nothing to link; carries the offending `stories`. Sync those stories first.
- **ConnectionError** (`CONNECTION_FAILED`), **LinkTypeUnavailableError** (`LINK_TYPE_UNAVAILABLE`), **IssueNotFoundError** (`ISSUE_NOT_FOUND`), **PermissionError** (`PERMISSION_DENIED`) — relayed from jira verbatim.

A partially unresolved batch is **not** an error — it returns `success: true` with the dropped edges in `unresolved`.

## Notes

- **Dependencies are links, parents are not.** Keeping them separate is what keeps the epic hierarchy and the dependency graph from corrupting each other.
- **Idempotent.** Existing links are read before anything is created, so this can run on every sync without duplicating links.
- **Markdown stays the source of truth.** The dependency graph is authored in the planning artifacts; this prompt projects it onto Jira. It never reads Jira links back into the markdown.
- **Story-to-story only.** Dependencies that cross epics, or point at non-story work, are outside this prompt's scope — the caller decides whether such an edge belongs in Jira at all.
