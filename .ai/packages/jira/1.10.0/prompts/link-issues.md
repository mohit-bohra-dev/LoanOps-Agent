# Link Jira Issues

Create directional links between existing Jira issues — `Blocks`, `Relates`, `Duplicate`, `Clones`.

Use this for **dependency and blocking relationships**. The parent Epic relationship is not an issue link — it is the `parentKey` input on `{{skill:jira.create-jira-issues}}` / `{{skill:jira.update-jira-issues}}`.

## Parameters

- **{{links}}** (array, required): The links to create. Each entry is `{ inwardIssue, outwardIssue, type?, comment? }`. Pass an array of one to create a single link.
- **{{type}}** (string, optional): Default link type for entries that omit their own. Defaults to `Blocks`. Matched case-insensitively against the types the instance defines, including their inward/outward descriptions.
- **{{comment}}** (string, optional): Default comment for entries that omit one. Posted on the **outward** issue.
- **{{onTypeUnavailable}}** (string, optional): `skip` (default) or `fail`. What to do when the instance does not define the requested link type. `skip` returns success with every link reported as skipped, so a caller's wider workflow is not blocked by a project-configuration gap.
- **{{dryRun}}** (boolean, optional): Resolve and report the planned links without creating any.

## Direction

For directional types, **`inwardIssue` is the blocker and `outwardIssue` is the blocked issue** — read it as the sentence *inward* **blocks** *outward*.

Translating from a dependency graph: for an edge where `dependent` needs `predecessor`, pass `inwardIssue = predecessor`, `outwardIssue = dependent`.

So "AIP-20 is blocked by AIP-10" is `inwardIssue: AIP-10, outwardIssue: AIP-20`. Getting this backwards produces a link that tells the team to do the work in the wrong order, so confirm one link as a sentence before running a batch.

## Instructions

Load `{{skill:jira.link-jira-issues}}` and execute it with these inputs.

| Skill input | Value |
|---|---|
| `links` | `{{links}}` |
| `type` | `{{type}}` (default `Blocks`) |
| `comment` | `{{comment}}` (only if provided) |
| `onTypeUnavailable` | `{{onTypeUnavailable}}` (default `skip`) |
| `dryRun` | `{{dryRun}}` (default `false`) |

The skill validates the MCP connection, resolves the requested type against the types the instance actually defines, reads existing links on each inward issue so already-correct links are skipped and re-runs are safe, creates only the missing links one at a time, and reports created / skipped / conflicting / failed links.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "resolvedType": "Blocks",
  "created": [{ "inwardIssue": "AIP-10", "outwardIssue": "AIP-20", "type": "Blocks" }],
  "skipped": [{ "inwardIssue": "AIP-10", "outwardIssue": "AIP-21", "type": "Blocks", "reason": "ALREADY_LINKED" }],
  "conflicts": [],
  "failed": [],
  "availableTypes": ["Blocks", "Clones", "Duplicate", "Relates"]
}
```

`success` is `true` whenever the pass completed — including when every link was skipped because it already existed or the type is unavailable. It is `false` only when nothing could be attempted. A reversed existing link comes back in `conflicts` with both directions named rather than being overwritten.

## Error Handling

Errors are surfaced as returned by the `link-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`) — Atlassian MCP server unreachable or unauthenticated
- `LinkTypeUnavailableError` (`LINK_TYPE_UNAVAILABLE`) — requested type not defined and `onTypeUnavailable = fail`; includes `availableTypes`
- `IssueNotFoundError` (`ISSUE_NOT_FOUND`) — per-link; an issue key did not resolve
- `PermissionError` (`PERMISSION_DENIED`) — the user lacks the Link Issues permission on the project

```json
{ "code": "CONNECTION_FAILED", "message": "Unable to connect to Atlassian MCP server", "details": "..." }
```
