# Configure Jira

Generate or update one project entry in `.ai/jira.config.json` by discovering that Jira project's live field configuration and capturing per-team defaults.

## Parameters

- **{{projectKey}}** (string, optional): Jira project key to configure against (e.g., `AIP`). When omitted, the skill asks the user. Each invocation configures exactly one project.
- **{{siteUrl}}** (string, optional): Atlassian site URL (e.g., `https://pennymac.atlassian.net`). When omitted, detected during MCP validation.
- **{{force}}** (boolean, optional): Skip the per-project replace-confirmation prompt when an entry already exists for `{{projectKey}}`. Does **not** suppress the final write-permission prompt. Default: `false`.

## Instructions

Load `{{skill:jira.configure-jira}}` and execute it with these inputs.

| Skill input | Value |
|---|---|
| `projectKey` | `{{projectKey}}` (omit to have the skill ask) |
| `siteUrl` | `{{siteUrl}}` (omit to auto-detect) |
| `force` | `{{force}}` (default `false`) |

The skill validates the MCP connection, loads any existing config in full multi-project mode, decides whether this run adds / replaces / creates the file, discovers the project's issue types and per-type field metadata, maps logical field names to custom field IDs, detects per-type AC and Channel-required postures, captures per-team defaults, previews the merged file, writes it after explicit approval, and sanity-checks the result with a single-project drift report.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "configPath": "/abs/.ai/jira.config.json",
  "projectKey": "AIP",
  "replaceMode": "add",
  "projectsAfterWrite": ["AIP", "PCG"],
  "fieldsResolved": 9,
  "fieldsUnresolved": 3,
  "defaultsConfigured": 5,
  "issueTypesProfiled": ["Story", "Task", "Bug", "Sub-task", "Epic"],
  "driftReport": { "outcome": "no-drift" }
}
```

`replaceMode` is `add`, `replace`, or `create-file`. `projectsAfterWrite` confirms no previously-configured project was dropped during the merge.

## Error Handling

Errors are surfaced as returned by the `configure-jira` skill:

- `ConnectionError` (`CONNECTION_FAILED`) — MCP validation failed, or every per-type discovery call failed
- `ConfigInvalidError` (`CONFIG_INVALID`) — the existing `.ai/jira.config.json` failed schema validation and must be fixed before merging into it
- `InvalidProjectKeyError` (`INVALID_PROJECT_KEY`) — the project key did not match `^[A-Z][A-Z0-9_]+$`
- `ProjectNotFoundError` (`PROJECT_NOT_FOUND`) — the project does not exist or the user lacks access
- `WriteError` (`WRITE_FAILED`) — the config file could not be written or verified
- `UserCancelled` (`USER_CANCELLED`) — the user declined the replace confirmation or the write gate

```json
{ "code": "INVALID_PROJECT_KEY", "message": "Project key must match ^[A-Z][A-Z0-9_]+$", "projectKey": "aip-foo" }
```
