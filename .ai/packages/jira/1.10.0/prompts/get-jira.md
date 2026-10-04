# Get Jira Ticket

Retrieve a specific Jira ticket by issue key, with optional download to a local markdown file.

## Parameters

- **{{issueKey}}** (string, required): The Jira issue key to retrieve
  - Format: `PROJECT-NUMBER` (e.g., `CET-123`, `PLAT-456`)
  - Must contain a project prefix, hyphen, and numeric ID
  - Case-insensitive (normalized to uppercase)

- **{{download}}** (boolean, optional): Whether to save the ticket as a markdown file
  - Default value: `false`
  - When true, saves to `jira/{issueKey}_{sanitized_summary}.md`

## Instructions

Load `{{skill:jira.retrieve-jira}}` and execute it with these inputs.

| Skill input | Value |
|---|---|
| `issueKey` | `{{issueKey}}` |
| `download` | `{{download}}` (default `false`) |

The skill validates the MCP connection, fetches the issue, formats it as a structured markdown document, saves it when `download` is true, and verifies the result.

Return the skill's response unchanged.

## Response Format

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

`assignee` is the display name, or `null` / `"Unassigned"` when the issue has no assignee. `filePath` is present only when `download=true`.

## Error Handling

Errors are surfaced as returned by the `retrieve-jira` skill:

- `ConnectionError` (`CONNECTION_FAILED`) — the Atlassian MCP server is unreachable or unauthenticated
- `IssueNotFoundError` (`ISSUE_NOT_FOUND`) — the key does not exist or the user cannot view the issue
- `DownloadError` (`DOWNLOAD_FAILED`) — the markdown file could not be written

```json
{ "code": "ISSUE_NOT_FOUND", "message": "Jira issue 'CET-999' not found", "issueKey": "CET-999" }
```
