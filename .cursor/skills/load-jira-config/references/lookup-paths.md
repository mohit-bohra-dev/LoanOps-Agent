# Config File Lookup Paths

The `load-jira-config` skill searches for `jira.config.json` in this order and stops at the first match.

## Search Order

| # | Path | Rationale |
|---|---|---|
| 1 | `<workspace_root>/.ai/jira.config.json` | Primary, repo-committed location. The `.ai/` directory is the established home for project-scoped configuration in this ecosystem (e.g., `.ai/audit-allowlist.json`, `.ai/specs/`, `.ai/packages/`). Most invocations resolve here. |
| 2 | `<cwd>/.ai/jira.config.json` | Supports monorepo layouts where the user has cd'd into a sub-package that owns its own Jira project (different teams, different field IDs). |
| 3 | Walk up from `<cwd>` to nearest ancestor with `.ai/jira.config.json`, stopping at `<workspace_root>` | Catches the case where the user is several directories deep in a monorepo and the config lives at an intermediate level. |

`<workspace_root>` is the topmost directory of the user's project (the IDE's session-start cwd).
`<cwd>` is the agent's current working directory at the moment this skill is invoked.

## Why Stop at First Match (Don't Merge)

A merge strategy (combine workspace-root config with sub-package overrides) sounds appealing but creates a subtle problem: drift detection (`verify-jira-config`) becomes ambiguous because there's no single config to verify against the live Jira schema. First-match wins keeps the model simple and `verify-jira-config` deterministic.

If a monorepo needs per-sub-package configs, place a `.ai/jira.config.json` at each sub-package root; the search will pick the closest one based on the agent's cwd.

## Why Not User-Level

Per-user configs (e.g., `~/.cursor/jira.config.json`) were considered and rejected because:

1. Field IDs are properties of the **project**, not the **user**. Two engineers on the same Jira project share the same field IDs.
2. Defaults like `defaults.team` may differ per user, but those are easier to override at prompt-invocation time than to merge from multiple config sources.
3. User-level config introduces "works on my machine" failure modes for shared automation.

## Edge Cases

| Case | Behavior |
|---|---|
| File exists but is empty | Return `valid = false`, `error.code = "PARSE_ERROR"` |
| File is a directory | Return `valid = false`, `error.code = "READ_ERROR"` |
| File contains `{}` | Return `valid = false`, `error.code = "SCHEMA_VIOLATION"` (because `fieldIds` is required) |
| File contains valid JSON but unknown top-level keys | Return `valid = false`, `error.code = "SCHEMA_VIOLATION"` (schema sets `additionalProperties: false`) |
| Multiple `.ai/jira.config.json` files exist along the search path | First match wins; later matches are ignored. The skill reports the resolved `configPath` so the user can disambiguate if needed. |
| `<workspace_root>` cannot be determined | Skip step 1, start with step 2. |

## What This Skill Does NOT Do

- Does not write or modify `jira.config.json` (that's `configure-jira`)
- Does not call any MCP tool (use `verify-jira-config` for drift detection)
- Does not attempt to migrate older config formats (none exist yet)
- Does not auto-create the config when missing (returns `found = false` so the caller can decide whether to prompt the user)
