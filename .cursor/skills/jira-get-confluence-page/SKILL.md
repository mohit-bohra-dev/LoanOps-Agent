---
name: jira-get-confluence-page
description: >-
  Retrieves a single Confluence page by numeric page ID or by title (exact match
  first, then contains), extracts its metadata and body, formats it as markdown,
  and optionally saves it to `confluence/{pageId}_{slug}.md`. Use when fetching
  one Confluence page. For many pages at once, use `download-confluence-pages`;
  for a topic-wide search and summary, use `search-summarize-confluence`.
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "get-confluence-page"
---

# Get Confluence Page

Resolves one Confluence page — by ID or by title — and returns its content in markdown, with an optional local download.

## When to Use

- Reading a specific Confluence page whose ID or title is known
- Pulling a runbook, standard, or design doc into context
- Saving a single page to markdown for offline reference

For a batch, use `download-confluence-pages`. For "find everything about X and summarize it", use `search-summarize-confluence`.

## Prerequisites

- Atlassian MCP server reachable (this skill invokes `validate-mcp-connection` in Step 1)
- The user has access to the page's space

## Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `pageIdentifier` | string | yes | A numeric page ID (e.g., `"123456789"`) or a page title to search for (e.g., `"Deployment Runbook"`). The identifier's shape selects the resolution path. |
| `download` | boolean | no | When `true`, save the formatted markdown to `confluence/{pageId}_{sanitized_title}.md`. Default `false`. |

## Workflow

### Step 1: Validate the MCP Connection

Invoke the `validate-mcp-connection` skill. Capture `cloudId` and confirm Confluence access.

**CRITICAL STOP CONDITION:** If validation fails after 2 retries, return `ConnectionError` (`CONNECTION_FAILED`) and stop.

### Step 2: Resolve the Page

Branch on the shape of `pageIdentifier`:

**Numeric — treat as a page ID.** Call `mcp_atlassian_getConfluencePage` with `cloudId` and `pageId` directly.

**Non-numeric — treat as a title.** Call `mcp_atlassian_searchConfluenceUsingCql` with `cql = title = "{pageIdentifier}"` (exact match). When that returns nothing, retry with `cql = title ~ "{pageIdentifier}"` (contains). Take the most recently modified match and fetch its full content with `mcp_atlassian_getConfluencePage`. When the title search returned several candidates, note the alternatives in the presented output so the user can tell a near-miss from the intended page.

Confirm the resolved page ID is present and numeric, the title is present, and the body is not empty.

**CRITICAL STOP CONDITION:** If no page resolves, return `PageNotFoundError` (`PAGE_NOT_FOUND`) with the supplied identifier and stop.

On a transient API failure, retry up to 2 times with a brief delay before returning `ConnectionError`.

### Step 3: Extract and Format

Extract: page ID, title, space key and name, author, created date, last modified date, version number, labels, ancestor hierarchy, and the body (the API returns markdown).

Render as:

```markdown
# {Title}

**Space:** {Space Name} ({Space Key})
**Author:** {Author} | **Last Modified:** {Last Modified}
**Version:** {Version} | **Labels:** {Labels}

---

{Page body content}
```

### Step 4: Download (Conditional)

Only when `download = true`:

1. Create the `confluence/` directory if it does not exist.
2. Generate the filename `{page_id}_{sanitized_title}.md` — replace spaces in the title with hyphens, strip characters invalid in filenames, lowercase the title portion, and truncate the whole name to 80 characters.
3. Write the formatted markdown and verify the file exists with matching content.

On write failure, retry once. If it still fails, return `DownloadError` (`DOWNLOAD_FAILED`) with the page ID.

### Step 5: Present and Return

Display the formatted content, confirm the file path when downloaded, and note any alternative title matches from Step 2. Return the response below.

## Output Contract

### Success Response

```json
{
  "success": true,
  "pageId": "123456789",
  "title": "API Design Guidelines",
  "content": "# API Design Guidelines\n\n**Space:** Engineering (ENG)\n...",
  "filePath": "confluence/123456789_api-design-guidelines.md"
}
```

| Field | Meaning |
|---|---|
| `success` | Whether retrieval completed |
| `pageId` | The resolved Confluence page ID |
| `title` | Page title |
| `content` | The full formatted markdown from Step 3 |
| `filePath` | Path to the saved file — present only when `download = true` |

### Errors

| Code | When |
|---|---|
| `CONNECTION_FAILED` | MCP server not configured, OAuth expired, or network failure (Step 1) |
| `PAGE_NOT_FOUND` | The page ID does not exist, the title search returned no matches, or the user lacks permission to view the page (Step 2) |
| `DOWNLOAD_FAILED` | Filesystem write denied, disk full, or an invalid filename was generated (Step 4) |

```json
{ "code": "PAGE_NOT_FOUND", "message": "Confluence page 'Nonexistent Page' not found", "pageIdentifier": "Nonexistent Page" }
```

## Notes

- Title resolution tries an exact match before a contains match, and picks the most recently modified candidate when several remain.
- A permission failure on a space surfaces as `PAGE_NOT_FOUND`; report the space key alongside the message when the API supplies it.
- `download` creates a `confluence/` directory in the current workspace when one does not exist.
- Page content is markdown as returned by the Atlassian API. Very large pages may be truncated by the API — note it in the output when it happens.

## Reference Documents

- `../validate-mcp-connection/SKILL.md` — invoked in Step 1
- `../download-confluence-pages/SKILL.md` — batch counterpart for many pages at once
- `../search-summarize-confluence/SKILL.md` — topic-wide search, download, and summary
