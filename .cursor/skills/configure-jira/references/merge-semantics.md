# Merge Semantics

How `configure-jira` combines a freshly-discovered project entry with whatever `.ai/jira.config.json` already holds. Consumed by Steps 2 and 9.

`.ai/jira.config.json` is a **multi-project** file: one `site`, one `defaultProjectKey`, and a `projects` map keyed by Jira project key. Each invocation of `configure-jira` touches exactly one entry in that map and must leave every other entry byte-identical.

## Merge Modes

| Mode | Trigger | Effect |
|---|---|---|
| `create-file` | No config file found at any search path | Build a fresh envelope containing only this project |
| `add` | Config exists, `projectKey` is not in `projects` | Insert the new entry alongside the existing ones |
| `replace` | Config exists, `projectKey` is already in `projects` | Overwrite that one entry; requires confirmation unless `force = true` |

Only `replace` prompts for confirmation before discovery. `add` never does — adding a project cannot destroy anything.

## Envelope Construction

### `create-file`

```json
{
  "$schema": "./skills/load-jira-config/references/jira.config.schema.json",
  "site": { "url": "<detectedSiteUrl>", "cloudId": "<cloudId>" },
  "defaultProjectKey": "<projectKey>",
  "projects": { "<projectKey>": { "fieldIds": {}, "defaults": {}, "issueTypeOverrides": {}, "customExtras": {} } }
}
```

The single project becomes `defaultProjectKey` because it is the only candidate.

### `add` and `replace`

Shallow-clone `existingConfig`, then set `mergedConfig.projects[projectKey]` to the new entry. Everything else is preserved verbatim:

- Every other key in `existingConfig.projects` — untouched
- `existingConfig.site` — preserved when present and non-empty. Do not overwrite an explicit site value with an auto-detected one unless they match.
- `existingConfig.$schema` — preserved when already set.
- `existingConfig.defaultProjectKey` — see below.

## `defaultProjectKey` Stickiness

`defaultProjectKey` is set **once**, when the file is first created. Re-pointing it silently would re-target every workflow that omits an explicit `projectKey`, which is a far larger change than adding a project.

| Situation | Behavior |
|---|---|
| Already set to any value | Leave it exactly as-is, even when adding a new project |
| Missing or null, and the merge leaves exactly one project | Set it to `projectKey` |
| Missing or null, and the merge leaves multiple projects | Leave it null and surface in the preview: `Tip: defaultProjectKey is unset. Workflow skills will require a projectKey input until you set it (you can hand-edit the file or re-run configure-jira).` |

Changing an already-set `defaultProjectKey` is a hand-edit. There is no flow for it.

## Post-Merge Validation

Before previewing, confirm:

- `previewConfig` parses as valid JSON
- `previewConfig.$schema` is set
- `previewConfig.site.url` and `previewConfig.site.cloudId` are non-empty strings
- `previewConfig.projects[projectKey]` deep-equals the assembled entry
- `previewConfig.projects` contains every key from `existingProjectKeys` — no entry silently dropped
- `previewConfig.defaultProjectKey` is null or a key present in `previewConfig.projects`

After writing, read the file back and re-assert the last three.

## Worked Scenarios

### First-time configuration

No config file. `replaceMode = "create-file"`, `existingProjectKeys = []`. Discovery resolves 10 of 13 fields for `AIP`; Epic diverges from the package AC default so one override is emitted. A fresh envelope is written with `defaultProjectKey = "AIP"`.

Response: `replaceMode: "create-file"`, `projectsAfterWrite: ["AIP"]`.

### Adding a second project

The file already holds `projects.AIP` with `defaultProjectKey = "AIP"`. Configuring `PCG` gives `replaceMode = "add"` and no confirmation prompt. The merge preserves `projects.AIP` and leaves `defaultProjectKey = "AIP"` untouched, so no unset-default tip appears.

Response: `replaceMode: "add"`, `projectsAfterWrite: ["AIP", "PCG"]`.

### Replacing an existing entry

`AIP` is already configured and an admin has renamed the Channel field. Re-running with `projectKey = AIP` and `force = false` prompts: *"An entry for project 'AIP' already exists in /Users/me/proj/.ai/jira.config.json. Replace just this entry (other projects: PCG will be preserved)? [y/N]"*. On `y`, discovery re-runs and only `projects.AIP` is overwritten; `projects.PCG` and `defaultProjectKey` survive.

Response: `replaceMode: "replace"`, `projectsAfterWrite: ["AIP", "PCG"]`.

### Declined replacement

Same setup, user answers `N`. Return `{ "code": "USER_CANCELLED", "message": "User declined to replace existing project entry", "step": "Step 2", "projectKey": "AIP" }`. Nothing is discovered and the file is untouched.

### Existing config is invalid

The loader returns `found = true, valid = false` — for example a hand-edited file that still carries the pre-multi-project top-level `fieldIds`. Halt in Step 2 with `CONFIG_INVALID`, surfacing the violation paths:

```json
{
  "code": "CONFIG_INVALID",
  "message": "Existing .ai/jira.config.json failed schema validation; fix or replace it before re-running",
  "details": [
    { "path": "fieldIds", "message": "additional property at top level (multi-project shape requires `projects.<KEY>.fieldIds` instead)" }
  ]
}
```

Merging into an invalid file would produce a file that is still invalid while looking freshly written.
