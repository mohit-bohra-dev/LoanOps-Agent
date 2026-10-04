---
name: search-jira
description: >-
  Federated search entry point for the Atlassian source. Accepts arbor's
  SearchQuery envelope, runs a single CQL query over Confluence via the Atlassian
  MCP, and returns ranked, cited results in arbor's normalized SearchResultSet /
  RankedResult shape — lightweight retrieval (titles + short excerpts), not a
  download-and-summarize research pass. Never throws: connection, auth, and CQL
  failures come back as a soft error on the envelope so a federated search
  degrades gracefully. Use when a caller needs ranked, cited Atlassian hits to
  ground an answer, or when arbor federates into the `jira-confluence` source.
  For downloaded pages plus a categorized written summary, use
  `search-summarize-confluence` instead.
---

# Search Jira (Atlassian Search Source)

The Atlassian package's **search source**: one query in, a ranked and cited `SearchResultSet` out. It is the artifact the `jira-confluence` arbor source resolves to, and it is directly callable by any agent that needs grounded Atlassian context.

This skill searches **Confluence** content. Retrieving a single Jira issue by key is `retrieve-jira`; batch-pulling issues by JQL is `download-jiras`.

## When to Use

- An agent needs ranked, cited Atlassian excerpts to ground an answer
- A federated search (`arbor`) is fanning out to the `jira-confluence` source
- A caller wants fast retrieval — titles and excerpts — without writing files

Do **not** use this for deep research. When the caller wants every relevant page downloaded and a categorized summary written to disk, use `search-summarize-confluence`.

## Prerequisites

- Atlassian MCP server configured and OAuth completed. When it is not, this skill returns a soft `CONNECTION_FAILED` envelope rather than failing the caller.

## Inputs

The input is arbor's `SearchQuery` envelope. No `paramMap` is needed — this skill consumes the envelope natively.

| Input | Type | Required | Description |
|---|---|---|---|
| `query` | string | yes | The search text (e.g., `"incident escalation policy"`). |
| `limit` | number | no | Maximum results to return. Default `10`, minimum `1`. |
| `type` | string | no | Content-type filter. Honored when it is `page` or `blogpost`; otherwise ignored. |
| `filters.spaces` | string[] | no | Confluence space keys to restrict to (e.g., `["ENG", "OPS"]`). |
| `filters.dateRange` | string | no | CQL date clause (e.g., `lastModified > -90d`). |
| `timeoutMs` | number | no | Soft time budget. On exhaustion return what is available with `partial: true`. |

The top-level native names `specificSpaces` and `dateRange` are also tolerated as a convenience; read whichever form the caller supplied.

## Workflow

### Step 1: Validate the Connection (Soft)

Invoke `validate-mcp-connection` to obtain `cloudId` and the site base URL (needed to build result URLs).

On failure **do not throw.** Return a degraded envelope immediately and stop:

```json
{ "source": "jira-confluence", "query": "<query>", "count": 0, "partial": true, "error": { "code": "CONNECTION_FAILED", "message": "Atlassian MCP not authenticated; skipped Confluence source." }, "results": [] }
```

### Step 2: Build One CQL Query

Compose a single query — this is retrieval, not a multi-pass research flow:

- Base: `(text ~ '{query}' OR title ~ '{query}')`
- Space filter when `filters.spaces` / `specificSpaces` is provided: `AND space.key IN ('SPACE1','SPACE2')`
- Date filter when `filters.dateRange` / `dateRange` is provided: `AND {dateRange}`
- Type filter when `type` is `page` or `blogpost`: `AND type = '{type}'`
- Sort: `ORDER BY lastModified DESC`

Escape single quotes in `{query}` so the CQL stays valid.

### Step 3: Run the Search

Call `mcp_atlassian_searchConfluenceUsingCql` with `cloudId` and the constructed `cql`, requesting up to `limit` results. Page once if needed to reach `limit`; do not exhaust all pages.

- Zero matches is **not** an error — return `count: 0`, empty `results`, `error: null`.
- On a CQL or API error, return a degraded envelope with `error.code = "SEARCH_FAILED"` and `partial: true`, including the failing CQL in the message.
- On `timeoutMs` exhaustion, return what is available with `partial: true`.

### Step 4: Map Matches to `RankedResult`

For each match, in the recency order CQL returned, build a `RankedResult`. The field-by-field mapping and the source-relative scoring formula are documented in {{file:../confluence-search-source/SKILL.md}} (Step 4); the shape is:

- `source` — always `"jira-confluence"`
- `ref` — the Confluence page id
- `url` — `{siteBaseUrl}/wiki/spaces/{spaceKey}/pages/{pageId}`, or the link from the search result when present
- `type` — the content type (`page` / `blogpost`)
- `title` — the page title
- `matchedSections` — a single `{ "heading": "Excerpt", "excerpt": "…" }` from the result's excerpt or highlight text (whitespace collapsed, markup stripped, ~280 chars). Falls back to the title when no excerpt is available.
- `citation` — `Confluence › {spaceKey} › {title}`
- `score` — a **source-relative** rank score assigned by position; not comparable across sources

Truncate to `limit`.

### Step 5: Return the Envelope

Return the assembled `SearchResultSet`. Set `partial: true` when results were cut short by `timeoutMs` or paging; otherwise `false`. Keep `error: null` on success.

## Output Contract

### Success Response

```json
{
  "source": "jira-confluence",
  "query": "incident escalation policy",
  "count": 1,
  "partial": false,
  "error": null,
  "results": [
    {
      "source": "jira-confluence",
      "ref": "123456",
      "url": "https://acme.atlassian.net/wiki/spaces/ENG/pages/123456",
      "type": "page",
      "title": "On-Call Escalation Runbook",
      "score": 20,
      "matchedSections": [ { "heading": "Excerpt", "excerpt": "Page the secondary on-call if the primary does not ack within 5 minutes…" } ],
      "citation": "Confluence › ENG › On-Call Escalation Runbook"
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `source` | Always `"jira-confluence"` |
| `query` | The query that was searched |
| `count` | Number of entries in `results` |
| `partial` | `true` when results were truncated or the source was skipped by a soft error |
| `error` | `null` on success, or `{ code, message }` when the source could not run |
| `results` | Ranked `RankedResult`s. Empty means no matches — not an error. |

`source`, `query`, `count`, and `results` are always present.

### Errors

Every condition below is returned **as a `SearchResultSet` with a soft `error`** — this skill does not throw, so a federation that includes it keeps working with this group degraded.

| Code | When |
|---|---|
| `CONNECTION_FAILED` | Atlassian MCP not configured, OAuth expired, or network failure (Step 1) |
| `SEARCH_FAILED` | CQL syntax or API error on the search call (Step 3) |

```json
{ "source": "jira-confluence", "query": "rate limiting", "count": 0, "partial": true, "error": { "code": "SEARCH_FAILED", "message": "CQL search failed: text ~ 'rate limiting' AND bad_field = 'x'" }, "results": [] }
```

## Registering as an Arbor Source

The source entry in a repo's `.kbs/.arbor.json`:

```json
{ "id": "jira-confluence", "kind": "skill", "skill": "jira.search-jira", "enabled": true }
```

Adding it through arbor's `source-registry` skill (preset `jira-confluence`) writes the entry for you.

## Notes

- One CQL query, ranked excerpts, no per-page fan-out. Keeping it fast is the point of the source contract.
- Scores are source-relative and are not comparable to other arbor sources' scores; arbor presents results grouped by source.
- Read-only: this skill never downloads pages or writes files.

## Reference Documents

- {{file:../confluence-search-source/SKILL.md}} — the retrieval mechanics this skill executes: CQL construction, result mapping, and the source-relative scoring formula
- {{file:../search-summarize-confluence/SKILL.md}} — the heavyweight counterpart when downloads and a written summary are wanted
- `../validate-mcp-connection/SKILL.md` — invoked in Step 1
