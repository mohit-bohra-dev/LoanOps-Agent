---
name: retrieve-jira
description: >-
  Retrieves a single Jira issue by key via the Atlassian MCP server, extracts its
  fields (summary, description, status, priority, assignee, reporter, type,
  labels, sprint, dates, comments), formats them as a structured markdown
  document, and optionally saves that document to `jira/{issueKey}_{slug}.md`.
  Use when fetching the details of one Jira ticket. For many issues at once, use
  `download-jiras`.
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  skill: "retrieve-jira"
---

# Retrieve Jira Ticket

Fetches one Jira issue by its key and returns structured data plus a formatted markdown rendering, with an optional local download.

## When to Use

- Reading a single ticket's details by key (e.g., `PROJ-123`)
- Pulling a ticket into context before implementing, reviewing, or updating it
- Saving one ticket to markdown for offline reference

For several issues matching a JQL query or a key list, use `download-jiras`. To modify a ticket, use `update-jira-issues`.

## Prerequisites

- Atlassian MCP server reachable (this skill invokes `validate-mcp-connection` in Step 1)
- The user has permission to view the issue

## Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `issueKey` | string | yes | The issue key to retrieve, formatted `PROJECT-NUMBER` (e.g., `"CET-123"`). Case-insensitive — normalized to uppercase before the call. |
| `download` | boolean | no | When `true`, save the formatted markdown to `jira/{issueKey}_{sanitized_summary}.md`. Default `false`. |

## Workflow

### Step 1: Validate the MCP Connection

Invoke the `validate-mcp-connection` skill. Capture `cloudId` and confirm Jira access.

**CRITICAL STOP CONDITION:** If validation fails after 2 retries, return `ConnectionError` (`CONNECTION_FAILED`) and stop.

### Step 2: Fetch the Issue

Normalize `issueKey` to uppercase, then call `mcp_atlassian_getJiraIssue` with `cloudId` and `issueIdOrKey`.

Extract and structure:

| Field | Source |
|---|---|
| Key | Issue key — must match the requested key |
| Summary | Issue title |
| Status | Current status name (e.g., `In Progress`, `Done`) |
| Priority | Priority name (e.g., `High`, `Medium`) |
| Assignee | Display name, or `null` / `"Unassigned"` when the issue has no assignee |
| Reporter | Display name of the reporter |
| Type | Issue type (`Story`, `Bug`, `Task`, …) |
| Description | Full description in markdown |
| Labels | Array of labels |
| Sprint | Current sprint name, when the project tracks sprints |
| Created / Updated | Timestamps |
| Comments | Recent comments with author and date |

Confirm the returned key matches the request and that `summary` and `status` are present. Description may legitimately be empty.

**CRITICAL STOP CONDITION:** If the issue is not found, return `IssueNotFoundError` (`ISSUE_NOT_FOUND`) with the requested key and stop.

On a transient API failure, retry up to 2 times with a brief delay before returning `ConnectionError`.

### Step 3: Format as Markdown

Render the extracted data as a structured document:

```markdown
# {KEY}: {Summary}

**Status:** {Status} | **Priority:** {Priority} | **Type:** {Type}
**Assignee:** {Assignee} | **Reporter:** {Reporter}
**Created:** {Created} | **Updated:** {Updated}
**Labels:** {Labels}
**Sprint:** {Sprint}

## Description

{Description content}

## Comments

### {Author} - {Date}
{Comment body}
```

Include every field that is available; omit the line for a field the project does not populate rather than printing an empty label.

### Step 4: Download (Conditional)

Only when `download = true`:

1. Create the `jira/` directory if it does not exist.
2. Generate the filename `{issueKey}_{sanitized_summary}.md` — replace spaces in the summary with hyphens, strip characters invalid in filenames, lowercase the summary portion, and truncate the whole name to 80 characters.
3. Write the formatted markdown and verify the file exists with matching content.

On write failure, retry once. If it still fails, return `DownloadError` (`DOWNLOAD_FAILED`) with the issue key.

### Step 5: Present and Return

Display the formatted content. When downloaded, confirm the file path. Return the response below.

## Output Contract

### Success Response

```json
{
  "success": true,
  "issueKey": "CET-123",
  "summary": "Implement user authentication",
  "status": "In Progress",
  "assignee": "Jane Doe",
  "content": "# CET-123: Implement user authentication\n\n**Status:** In Progress\n...",
  "filePath": "jira/CET-123_implement-user-authentication.md"
}
```

| Field | Meaning |
|---|---|
| `success` | Whether retrieval completed |
| `issueKey` | The Jira issue key |
| `summary` | Issue title |
| `status` | Current status name |
| `assignee` | Display name of the current assignee, or `null` / `"Unassigned"` when there is none (also shown on the **Assignee:** line in `content`) |
| `content` | The full formatted markdown from Step 3 |
| `filePath` | Path to the saved file — present only when `download = true` |

### Errors

| Code | When |
|---|---|
| `CONNECTION_FAILED` | MCP server not configured, OAuth expired, or network failure (Step 1) |
| `ISSUE_NOT_FOUND` | The issue key does not exist, the project does not exist, or the user lacks permission to view it (Step 2) |
| `DOWNLOAD_FAILED` | Filesystem write denied, disk full, or an invalid filename was generated (Step 4) |

```json
{ "code": "ISSUE_NOT_FOUND", "message": "Jira issue 'CET-999' not found", "issueKey": "CET-999" }
```

## Notes

- Issue keys are case-insensitive and are normalized to uppercase before the API call.
- `download` creates a `jira/` directory in the current workspace when one does not exist.
- Very large issues may have their comment list truncated by the API; the most recent comments are prioritized.

## Reference Documents

- `../validate-mcp-connection/SKILL.md` — invoked in Step 1
- `../download-jiras/SKILL.md` — batch counterpart for many issues at once
- `../update-jira-issues/SKILL.md` — the write path for an existing issue
