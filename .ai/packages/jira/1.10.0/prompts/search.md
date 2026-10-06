# Search

Run one CQL query over Confluence and return ranked, cited results in arbor's normalized `SearchResultSet` envelope.

## Parameters

- **{{query}}** (string, required): The search text
  - Example: `incident escalation policy`
- **{{limit}}** (number, optional): Maximum number of results to return
  - Default: `10`
  - Min: 1
- **{{type}}** (string, optional): Content-type filter; honored when it is `page` or `blogpost`, otherwise ignored
- **{{filters}}** (object, optional): Source-specific filters
  - `spaces` (array): Confluence space keys to restrict to (e.g. `["ENG", "OPS"]`)
  - `dateRange` (string): CQL date clause (e.g. `lastModified > -90d`)
- **{{timeoutMs}}** (number, optional): Soft time budget; return what is available with `partial: true` if exceeded

The `spaces` / `dateRange` values are read from the `filters` envelope; the top-level native names `specificSpaces` and `dateRange` are also tolerated.

## Instructions

Load `{{skill:jira.search-jira}}` and execute it with these inputs.

| Skill input | Value |
|---|---|
| `query` | `{{query}}` |
| `limit` | `{{limit}}` (default `10`) |
| `type` | `{{type}}` (only if provided — honored for `page` / `blogpost`) |
| `filters.spaces` | `{{filters}}.spaces` (only if provided) |
| `filters.dateRange` | `{{filters}}.dateRange` (only if provided) |
| `timeoutMs` | `{{timeoutMs}}` (only if provided) |

The skill validates the MCP connection, builds one CQL query from the inputs sorted `ORDER BY lastModified DESC`, runs it, maps each match to a `RankedResult` with a source-relative score, and returns the envelope.

**Soft failure:** the skill never throws for connection, auth, search, or empty-result conditions. It always returns a `SearchResultSet`; problems are reported via `error` + `partial` so a calling federation keeps working.

Return the skill's response unchanged.

## Response Format

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

Required fields: `source`, `query`, `count`, `results`. An empty `results` array means no matches — not an error. `partial` is `true` when results were truncated or the source was skipped by a soft error.

## Error Handling

Both conditions are returned **as a `SearchResultSet` with a soft `error`**, never thrown:

- `CONNECTION_FAILED` — Atlassian MCP not configured, OAuth expired, or network failure
- `SEARCH_FAILED` — CQL syntax or API error on the search call

```json
{ "source": "jira-confluence", "query": "rate limiting", "count": 0, "partial": true, "error": { "code": "SEARCH_FAILED", "message": "CQL search failed: text ~ 'rate limiting' AND bad_field = 'x'" }, "results": [] }
```
