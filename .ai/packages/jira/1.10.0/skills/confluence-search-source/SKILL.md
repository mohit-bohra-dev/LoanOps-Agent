---
name: confluence-search-source
description: Arbor-compatible search source over Confluence. Runs a single CQL query via the Atlassian MCP and maps the top matches to ranked, cited results in arbor's SearchResultSet / RankedResult shape — lightweight retrieval (titles + excerpts), not a download/summarize workflow. Surfaces connection/auth problems as a soft error so a federated search can degrade gracefully. Provides the retrieval mechanics the `search-jira` skill executes.
---

# Confluence Search Source

A **retrieval-shaped** search over Confluence that conforms to arbor's Search Source contract, so `/arbor.search` can federate into it. It runs one CQL query, ranks the matches, and returns short cited excerpts in the normalized envelope. It deliberately does **not** download pages or write a summary — that heavyweight research flow stays in `search-summarize-confluence`.

`search-jira` is the caller-facing entry point for this source and owns the full invocation contract; this skill documents the retrieval mechanics that entry point executes.

## Contract

This skill implements the source side of arbor's Search Source interface. It accepts a `SearchQuery` and returns a `SearchResultSet` whose `results` use the `RankedResult` shape. Operational problems (no MCP, expired OAuth) are returned as a **soft** `error` on the envelope — never thrown — so the calling federation keeps working with this group degraded.

### Input: SearchQuery

| Field | Required | Meaning |
|-------|----------|---------|
| `query` | yes | The search text. |
| `limit` | no | Max results to return (default 10). |
| `type` | no | Optional content-type filter; mapped to Confluence `type` (`page`/`blogpost`) when it is one of those, otherwise ignored. |
| `filters.spaces` | no | Space keys to restrict to (`space.key IN (...)`). |
| `filters.dateRange` | no | CQL date clause (e.g. `lastModified > -90d`). |
| `timeoutMs` | no | Soft budget; return what is available with `partial: true` if exceeded. |

Read `spaces`/`dateRange` from `filters`; also tolerate the top-level native names `specificSpaces` / `dateRange` as a convenience (accept either). Because this prompt consumes the envelope natively, no arbor `paramMap` is needed.

### Output: SearchResultSet

```json
{
  "source": "jira-confluence",
  "query": "<query>",
  "count": 2,
  "partial": false,
  "error": null,
  "results": [ "RankedResult, ..." ]
}
```

Each `RankedResult`:

```json
{
  "source": "jira-confluence",
  "ref": "123456",
  "url": "https://<site>/wiki/spaces/ENG/pages/123456",
  "type": "page",
  "title": "Incident Escalation Policy",
  "score": 14,
  "matchedSections": [ { "heading": "Summary", "excerpt": "Escalate Sev-1 incidents…" } ],
  "citation": "Confluence › ENG › Incident Escalation Policy"
}
```

## Workflow

### Step 1: Validate the connection (soft)

Use the `validate-mcp-connection` skill to obtain the `cloud_id` and site URL.

- On success, keep `cloud_id` and the site base URL (for building result `url`s).
- On failure, **do not throw.** Return immediately with a degraded envelope and stop:

```json
{ "source": "jira-confluence", "query": "<query>", "count": 0, "partial": true, "error": { "code": "CONNECTION_FAILED", "message": "Atlassian MCP not authenticated; skipped Confluence source." }, "results": [] }
```

### Step 2: Build one CQL query

Compose a single query (this is retrieval, not the multi-pass research flow):

- Base: `(text ~ '{query}' OR title ~ '{query}')`
- Space filter when `filters.spaces`/`specificSpaces` provided: `AND space.key IN ('SPACE1','SPACE2')`
- Date filter when `filters.dateRange`/`dateRange` provided: `AND {dateRange}`
- Type filter when `type` is `page` or `blogpost`: `AND type = '{type}'`
- Sort: `ORDER BY lastModified DESC`

Escape single quotes in `{query}` to keep the CQL valid.

### Step 3: Run the search

Call `mcp_atlassian_searchConfluenceUsingCql` with `cloudId` and the constructed `cql`, requesting up to `limit` results (page once if needed to reach `limit`; do not exhaust all pages).

- Zero matches is **not** an error — return `count: 0`, empty `results`, `error: null`.
- If the CQL call errors, return a degraded envelope with `error.code = "SEARCH_FAILED"` and `partial: true` (include the `cqlQuery` in the message).
- If `timeoutMs` is exceeded, return what you have with `partial: true`.

### Step 4: Map matches to RankedResult

For each match (already ordered by recency from CQL), build a `RankedResult`:

- `source`: `"jira-confluence"`.
- `ref`: the Confluence page id.
- `url`: `"{siteBaseUrl}/wiki/spaces/{spaceKey}/pages/{pageId}"` (use the link from the search result when present).
- `type`: the content type (`page` / `blogpost`).
- `title`: the page title.
- `matchedSections`: a single `{ "heading": "Excerpt", "excerpt": "…" }` built from the search result's `excerpt`/highlight text (collapse whitespace, strip markup, ~280 chars). When no excerpt is available, use the page title as the excerpt.
- `citation`: `"Confluence › {spaceKey} › {title}"`.
- `score`: a **source-relative** rank score. Assign by result position so the order is preserved and is comparable only within this group — e.g. `score = max(1, limit*2 - index)` (top hit highest), optionally `+2` when the query appears in the title. Do not attempt to make this comparable to other sources' scores.

Truncate to `limit`.

### Step 5: Return the envelope

Return the assembled `SearchResultSet`. Set `partial: true` if results were truncated by `timeoutMs` or a paging cut; otherwise `false`. Keep `error: null` on success.

## Notes

- This skill is read-only — it never downloads pages or writes files. For a full download + categorized summary, use `search-summarize-confluence`.
- Keep it fast: one CQL query, ranked excerpts, no per-page `getConfluencePage` fan-out.
- Auth and approval for the Atlassian MCP are handled by `validate-mcp-connection`; when unmet this source degrades to a soft `error` rather than failing the caller.
