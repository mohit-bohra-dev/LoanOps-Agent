---
name: link-jira-issues
description: Create directional links between Jira issues (Blocks, Relates, Duplicate, Clones) via the Atlassian MCP server. Discovers the link types the instance actually defines, resolves link direction correctly, skips links that already exist, and soft-fails when a requested type is unavailable. Use for dependency/blocking relationships between issues — not for parent/Epic Link, which is the `parentKey` input on the `create-jira-issues` / `update-jira-issues` skills.
---

# Link Jira Issues

Creates issue links between existing Jira issues. Handles link-type discovery, direction resolution, idempotency, and batch linking.

## Scope

This skill covers **issue links** — the sideways relationships Jira models as link types (`Blocks`, `Relates`, `Duplicate`, `Clones`). It does **not** cover the parent/child relationship between a Story and its Epic: that is the `parentKey` input on the `create-jira-issues` / `update-jira-issues` skills, not an issue link. Using a link where a parent is meant produces an issue that looks related in the UI but is not in the epic's hierarchy.

## Prerequisites

- Atlassian MCP server reachable (this skill invokes `validate-mcp-connection` in Step 1)
- The user holds the **Link Issues** permission on every project involved
- Both issues in each pair already exist — this skill links, it never creates

## Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `links` | array | yes | One or more links to create. Each entry: `{ inwardIssue, outwardIssue, type, comment? }`. A single link is an array of one. |
| `type` | string | no | Default link type applied to any entry that omits its own (default `"Blocks"`). |
| `comment` | string | no | Default comment applied to entries that omit one. Posted on the **outward** issue. |
| `onTypeUnavailable` | enum | no | `skip` (default) or `fail`. What to do when the instance does not define the requested link type. |
| `dryRun` | boolean | no | When true, resolve and report the planned links without creating any. |

## Direction — Read This Before Using `Blocks`

Link direction is the single easiest thing to get backwards, and a reversed dependency link is worse than none: it tells the team to do the work in exactly the wrong order.

For a directional type, the Atlassian API takes the **inward** issue as the *subject* of the link type and the **outward** issue as its *object*:

- **`inwardIssue` is the blocker.** It is the issue that must be finished first.
- **`outwardIssue` is the blocked issue.** It is the issue that has to wait.

Read it as a sentence: *inward* **blocks** *outward*. So "AIP-20 is blocked by AIP-10" is created as `inwardIssue: AIP-10, outwardIssue: AIP-20`.

Translating from a dependency graph: for an edge **predecessor → dependent** (the dependent needs the predecessor), pass `inwardIssue = predecessor` and `outwardIssue = dependent`.

Before creating a batch, restate one link as a sentence and confirm it reads the way the caller intends. For non-directional types like `Relates`, direction is cosmetic and this does not apply.

## Workflow

### Step 1: Validate the MCP Connection

Invoke `{{skill:validate-mcp-connection}}` to confirm connectivity and obtain `cloudId`. On failure return `ConnectionError` (`CONNECTION_FAILED`) and stop — no link work is possible.

### Step 2: Discover the Available Link Types

Call `mcp_atlassian_getIssueLinkTypes` with `cloudId`.

**Do not assume `Blocks` exists.** Link types are configured per instance and administrators rename and remove them; a hardcoded name is the most common cause of a failing link batch.

Match the requested type against the returned list **case-insensitively**, and accept a match on the type's inward or outward description as well as its name (an instance may name the type `Dependency` with descriptions `blocks` / `is blocked by`).

When no match is found:

- `onTypeUnavailable = skip` (default) — create nothing, return `success: true` with every link in `skipped` and reason `TYPE_UNAVAILABLE`, and list the type names the instance **does** define so the caller can pick one. A missing link type is a project-configuration gap, not a caller error, and it must not fail the wider workflow that requested the links.
- `onTypeUnavailable = fail` — return `LinkTypeUnavailableError` (`LINK_TYPE_UNAVAILABLE`) with the available names.

### Step 3: Read Existing Links (Idempotency)

For each distinct issue appearing as an `inwardIssue`, call `mcp_atlassian_getJiraIssue` and read its `issuelinks`. Build the set of links that already exist.

This step is what makes the skill safe to re-run. Jira **will** create a second identical link if asked, and duplicates are tedious to clean up by hand.

Classify each requested link:

- **Already present** (same type, same pair, same direction) — `skipped`, reason `ALREADY_LINKED`.
- **Present but reversed** (same type and pair, opposite direction) — do **not** silently create the correct one alongside it, which would leave the issue asserting both directions. Report it as a `conflict` with both directions spelled out and let the caller decide.
- **Absent** — proceed to Step 4.

### Step 4: Create the Missing Links

When `dryRun = true`, stop here: report the resolved type and the classification from Step 3 with every remaining link listed as planned, and create nothing. The response keeps its normal shape, with the would-be creations in `created` and `dryRun: true` set on the envelope.

For each remaining link, call `mcp_atlassian_createIssueLink` with:

- `cloudId` from Step 1
- `inwardIssue`, `outwardIssue` per the direction rules above
- `type` — the **resolved** name from Step 2, not the caller's raw string
- `comment` when provided, plus `contentFormat: "markdown"`

Create links one at a time and record each outcome. A failure on one link does not abort the rest: collect the error, continue, and report per-link results. Partial success is the normal outcome for a large batch against a project with mixed permissions.

Per-link failures to expect:

- Either issue does not exist or is not visible → `ISSUE_NOT_FOUND` for that entry.
- The user lacks the **Link Issues** permission on the project → `PERMISSION_DENIED`. Report it once for the whole batch rather than repeating it per link; it will not resolve on retry.

### Step 5: Report

Return the per-link outcome (see Response). State plainly how many links were created, skipped, and failed, and name the reason for each skip — a caller re-running a sync needs to distinguish "already correct" from "could not do it".

## Response

```json
{
  "success": true,
  "cloudId": "uuid",
  "resolvedType": "Blocks",
  "created": [
    { "inwardIssue": "AIP-10", "outwardIssue": "AIP-20", "type": "Blocks" }
  ],
  "skipped": [
    { "inwardIssue": "AIP-10", "outwardIssue": "AIP-21", "type": "Blocks", "reason": "ALREADY_LINKED" }
  ],
  "conflicts": [
    { "inwardIssue": "AIP-30", "outwardIssue": "AIP-31", "type": "Blocks", "detail": "Reverse link already exists (AIP-31 blocks AIP-30)" }
  ],
  "failed": [
    { "inwardIssue": "AIP-40", "outwardIssue": "AIP-99", "type": "Blocks", "code": "ISSUE_NOT_FOUND" }
  ],
  "availableTypes": ["Blocks", "Clones", "Duplicate", "Relates"]
}
```

`success` is `true` when the skill completed its pass, including when every link was skipped. It is `false` only when the run could not proceed at all — no connection, or `onTypeUnavailable = fail` with the type missing.

## Errors

- `ConnectionError` (`CONNECTION_FAILED`) — the Atlassian MCP server is unreachable or unauthenticated.
- `LinkTypeUnavailableError` (`LINK_TYPE_UNAVAILABLE`) — the requested type is not defined and `onTypeUnavailable = fail`. Includes `availableTypes`.
- `IssueNotFoundError` (`ISSUE_NOT_FOUND`) — per-link; the issue key does not resolve.
- `PermissionError` (`PERMISSION_DENIED`) — the user cannot link issues in this project.

## Notes

- **Links are not parents.** The Epic Link / parent relationship is the `parentKey` input on `create-jira-issues` / `update-jira-issues`. Never model epic membership as an issue link.
- **One direction per pair per type.** Jira renders the inverse automatically: creating "A blocks B" makes B show "is blocked by A". Creating both is duplication, not thoroughness.
- **Re-running is safe** because of Step 3. Callers syncing a dependency graph on every run should rely on that rather than tracking what they linked previously.
