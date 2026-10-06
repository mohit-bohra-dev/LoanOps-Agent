---
name: load-jira-config
description: Locates and parses the per-team `.ai/jira.config.json` file for the consuming repo, validates it against the package schema, and returns either a flat single-project view (resolved from the caller's `projectKey` input or `defaultProjectKey`) or the full multi-project config. Read-only filesystem skill — no MCP calls. Use as the second step of every Jira create or update workflow, after MCP validation, so the workflow can resolve `{{*FieldId}}` placeholders deterministically against the right project's settings.
---

# Load Jira Config

Loads the consuming repo's `jira.config.json`, validates it against the package's JSON Schema, and returns a structured response that workflow skills consume to resolve field-ID placeholders and supply per-team defaults. The config is multi-project: a single file can hold entries for several Jira projects (`AIP`, `PCG`, ...). This skill resolves the active project and returns a flat single-project view by default, so downstream workflow code can read `config.fieldIds.channel` exactly as before.

## When to Use

Call this skill as the second step (after `validate-mcp-connection`) of any workflow that creates or updates Jira issues, and as the first step of any drift-detection workflow. It is also called by the `configure-jira` skill to fetch the full config for merging.

This skill never modifies the config file. It only reads.

## Prerequisites

None. This skill operates purely on the filesystem and does not require MCP connectivity. It is intentionally separated from `validate-mcp-connection` so callers that only need the static config (e.g., schema-only previews) can invoke it cheaply.

## Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `projectKey` | string | no | Jira project key (e.g., `"AIP"`). When provided, the skill returns a *flat single-project view* (`{ projectKey, site, fieldIds, defaults, issueTypeOverrides, customExtras }`) for that project. When omitted, the skill resolves to `config.defaultProjectKey` and returns a flat single-project view for that. To bypass project resolution and get the entire multi-project config (e.g., for `configure-jira` or `verify-jira-config` iteration), set `mode: "full"` instead. |
| `mode` | string | no | One of `"resolved"` (default — return flat single-project view) or `"full"` (return entire multi-project config without resolving a project). When `mode: "full"`, the `projectKey` input is ignored. |

## Instructions

### Step 1: Locate the Config File

Search for `jira.config.json` in this order. **Stop at the first match.** Do not merge multiple files.

1. `<workspace_root>/.ai/jira.config.json` — primary location, repo-committed by convention
2. `<cwd>/.ai/jira.config.json` — when the agent's cwd is a sub-package of a monorepo
3. Walk up from `<cwd>` to the nearest ancestor containing `.ai/jira.config.json`, stopping at the workspace root

Where:

- `<workspace_root>` is the topmost directory of the user's project (the directory shown in the IDE's terminal cwd at session start).
- `<cwd>` is the agent's current working directory at the moment this skill is invoked.

If no file is found after exhausting the search, return the structured `not-found` response (Output Contract) — **do not error**. Workflow skills handle this gracefully by offering to bootstrap via `configure-jira` or falling back to inline prompting.

See `references/lookup-paths.md` for the full search-order rationale.

### Step 2: Read and Parse JSON

Read the located file and parse as JSON.

**Parse failure handling:**

- If `JSON.parse` fails (malformed JSON), return the structured `invalid` response with `error.code = "PARSE_ERROR"` and the parser's offset/message. Do not attempt recovery.
- If the file is unreadable (permissions, IO error), return `error.code = "READ_ERROR"` with the IO message.

### Step 3: Validate Against Schema

Validate the parsed object against `references/jira.config.schema.json` (JSON Schema draft 2020-12).

The validation step is conceptual — the agent does not need a JSON Schema engine in the loop. Instead:

- Confirm the top-level shape: `projects` is required and is an object; `site`, `defaultProjectKey`, `$schema` are optional. No other top-level keys allowed.
- Confirm every key in `projects` matches `^[A-Z][A-Z0-9_]+$`.
- For each project entry, confirm the four sub-objects (`fieldIds`, `defaults`, `issueTypeOverrides`, `customExtras`) when present have the expected shapes:
  - Every `fieldIds.*` value is either `null` or a string matching `^customfield_\d+$`.
  - Every `defaults.*` value is either `null` or a string.
  - Every `issueTypeOverrides.<Type>.acceptanceCriteriaMode` is one of `adf-field`, `inline-description`, `none`.
  - Every `customExtras.*` value matches `^customfield_\d+$`.
- Confirm `site.cloudId` (when present) is a UUID and `site.url` (when present) is a URL.
- Confirm `defaultProjectKey` (when present and non-null) matches `^[A-Z][A-Z0-9_]+$` AND is a key that exists in `projects`.

On any violation, return the `invalid` response with `error.code = "SCHEMA_VIOLATION"` and a `details` array listing each violation as `{ path, message }`.

### Step 4: Resolve and Return

Branch on `mode`:

#### `mode = "full"` (or any time the caller wants the entire multi-project config)

Return the **full-config success** response (see Output Contract) with the parsed `config` object exactly as written. Per-project entries are normalized so missing optional sub-objects (`fieldIds`, `defaults`, `issueTypeOverrides`, `customExtras`) are materialized as `{}`. Top-level `site` is materialized as `{}` if absent. **Do not** materialize `defaultProjectKey` if absent — leave it `null` or omitted.

#### `mode = "resolved"` (default)

Resolve the active project key, then return a flat single-project view:

1. **Determine the active project key:**
   - If the `projectKey` input is provided, use that.
   - Else if `config.defaultProjectKey` is set (non-null, non-empty), use that.
   - Else return the `default-project-key-missing` response (no project key supplied and no default to fall back to).
2. **Look up the project entry:**
   - If `config.projects[<activeProjectKey>]` exists, build the flat view (next bullet) and return the **flat-view success** response.
   - If it does not exist, return the `project-not-in-config` response with the list of available project keys (`Object.keys(config.projects)`) so the caller can present the gap to the user.
3. **Build the flat view** by merging the resolved project entry with the top-level `site`:
   - `projectKey` — the active project key
   - `site` — copy of top-level `config.site` (or `{}` if absent)
   - `fieldIds` — `config.projects[<key>].fieldIds` (or `{}`)
   - `defaults` — `config.projects[<key>].defaults` (or `{}`)
   - `issueTypeOverrides` — `config.projects[<key>].issueTypeOverrides` (or `{}`)
   - `customExtras` — `config.projects[<key>].customExtras` (or `{}`)

The flat view exactly matches the shape the workflow skills consumed before multi-project support was added — `config.fieldIds.channel`, `config.defaults.workStream`, etc. — so downstream code does not need to know multi-project exists.

**Backward compatibility:** Downstream skills (`create-jira-issues`, `update-jira-issues`, `set-acceptance-criteria`, etc.) keep the exact same `config.*` access paths they used before. The only change required of a workflow caller is to **resolve the active project key and pass it as the `projectKey` input** when invoking this skill. No other read sites need rewriting.

## Output Contract

The skill's output is one of six shapes. The discriminator is the pair `(found, valid)` plus an optional `error.code`.

### Flat-view success (`mode = "resolved"`, project resolved successfully)

```json
{
  "found": true,
  "valid": true,
  "mode": "resolved",
  "configPath": "/abs/path/to/.ai/jira.config.json",
  "config": {
    "projectKey": "AIP",
    "site": { "url": "https://pennymac.atlassian.net", "cloudId": "..." },
    "fieldIds": { "channel": "customfield_10253", "...": "..." },
    "defaults": { "workStream": "AI Platform Services", "...": "..." },
    "issueTypeOverrides": { "Epic": { "acceptanceCriteriaMode": "inline-description" } },
    "customExtras": { "tShirtSize": "customfield_10190" }
  }
}
```

### Full-config success (`mode = "full"`)

```json
{
  "found": true,
  "valid": true,
  "mode": "full",
  "configPath": "/abs/path/to/.ai/jira.config.json",
  "config": {
    "site": { "url": "...", "cloudId": "..." },
    "defaultProjectKey": "AIP",
    "projects": {
      "AIP": { "fieldIds": {...}, "defaults": {...}, "issueTypeOverrides": {...}, "customExtras": {...} },
      "PCG": { "fieldIds": {...}, "defaults": {...}, "issueTypeOverrides": {...}, "customExtras": {...} }
    }
  }
}
```

### Not Found (`found = false`)

The config file does not exist on disk anywhere in the search path. Independent of `mode`.

```json
{
  "found": false,
  "valid": null,
  "searchedPaths": [
    "/abs/workspace/.ai/jira.config.json",
    "/abs/cwd/.ai/jira.config.json"
  ],
  "hint": "Run the configure-jira skill to generate a project-scoped config file."
}
```

### Invalid (`found = true, valid = false`)

The file exists but failed parsing or schema validation. Independent of `mode`.

```json
{
  "found": true,
  "valid": false,
  "configPath": "/abs/path",
  "error": {
    "code": "PARSE_ERROR" | "SCHEMA_VIOLATION" | "READ_ERROR",
    "message": "<short human-readable summary>",
    "details": [
      { "path": "projects.AIP.fieldIds.channel", "message": "must match pattern ^customfield_\\d+$" }
    ]
  }
}
```

### Project Not In Config (`mode = "resolved"`, key resolved but missing from `projects`)

The file is found, valid, and a project key was resolved (from input or `defaultProjectKey`), but no entry exists for that key under `config.projects`.

```json
{
  "found": true,
  "valid": true,
  "mode": "resolved",
  "configPath": "/abs/path",
  "error": {
    "code": "PROJECT_NOT_IN_CONFIG",
    "message": "Project 'PCG' is not configured in .ai/jira.config.json",
    "requestedProjectKey": "PCG",
    "availableProjectKeys": ["AIP"],
    "hint": "Run the configure-jira skill with projectKey=PCG to add an entry, or use one of the available project keys."
  }
}
```

### Default Project Key Missing (`mode = "resolved"`, no key supplied and no default in config)

The file is found and valid, but the caller did not supply a `projectKey` and the file does not set `defaultProjectKey`. The skill cannot pick a project deterministically.

```json
{
  "found": true,
  "valid": true,
  "mode": "resolved",
  "configPath": "/abs/path",
  "error": {
    "code": "DEFAULT_PROJECT_KEY_MISSING",
    "message": "No projectKey supplied and config.defaultProjectKey is not set",
    "availableProjectKeys": ["AIP", "PCG"],
    "hint": "Supply a projectKey input, or set defaultProjectKey in .ai/jira.config.json (run the configure-jira skill to set it)."
  }
}
```

## Error Handling

This skill never throws to the caller. Every failure mode is encoded in the structured response so workflow consumers can branch deterministically:

| Caller behavior | Trigger |
|---|---|
| Use `config` (flat or full as requested) | `found = true, valid = true`, no `error` field |
| Halt with a clear error and point user at `verify-jira-config` | `found = true, valid = false` (`PARSE_ERROR` / `SCHEMA_VIOLATION` / `READ_ERROR`) |
| Offer to bootstrap via `configure-jira` (Step 2a in workflow skills), else fall back to inline prompts | `found = false` |
| Offer to bootstrap **the missing project** via `configure-jira` with `projectKey = <requested>`, else fall back to inline prompts | `error.code = "PROJECT_NOT_IN_CONFIG"` |
| Surface to the user — they need to pass `projectKey` explicitly, run `configure-jira` to set `defaultProjectKey`, or pick from `availableProjectKeys` | `error.code = "DEFAULT_PROJECT_KEY_MISSING"` |

## Reference

- `references/jira.config.schema.json` — JSON Schema (draft 2020-12) for the config file
- `references/lookup-paths.md` — Search order rationale and edge cases
