---
name: create-jira-issues
description: >-
  Drives the end-to-end create workflow for Jira stories, tasks, bugs,
  sub-tasks, and epics via the Atlassian MCP server. Loads an issue-type
  profile, assembles required + optional fields, asks user permission,
  creates the issue, dispatches acceptance-criteria handling, and verifies
  the result. Use whenever a prompt or agent needs to create a Jira issue
  of any supported type.
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  skill: "create-jira-issues"
---

# Create Jira Issues

End-to-end create workflow for any supported Jira issue type. Loads an issue-type profile, assembles fields, gets explicit user approval, calls the Atlassian MCP, dispatches acceptance-criteria handling based on the profile, and verifies the result.

## When to Use

- Creating a new Jira Story, Task, Bug, Sub-task, or Epic
- Building tickets from requirements, specs, or conversation context
- Batch-creating multiple related issues (e.g., sub-tasks from a plan)

For updates to existing issues, use the `update-jira-issues` skill instead. For just the ADF acceptance-criteria pattern, use the `set-acceptance-criteria` skill.

## Prerequisites

- Atlassian MCP server reachable (use `validate-mcp-connection` first)
- Project key and per-team custom field IDs configured in the consumer's promp parameters

## Inputs

| Input | Type | Required | Description |
|---|---|---|---|
| `profileName` | enum | yes | One of `Story`, `Task`, `Bug`, `Sub-task`, `Epic` |
| `projectKey` | string | no | Jira project key the issue should be created in (e.g., `AIP`, `PCG`). When omitted, Step 2.0 falls back to `config.defaultProjectKey`. If neither is set, the workflow halts with `DefaultProjectKeyMissingError`. |
| `summary` | string | yes | Issue title |
| `description` | string (markdown) | no | Issue description |
| `acceptanceCriteria` | string or string[] | no | List of acceptance criteria (comma-separated string or array) |
| `labels` | string or string[] | no | Labels (comma-separated string or array) |
| `priority` | string | no | Priority name as it appears in the target Jira instance (e.g. `"High"`, `"Highest"`). Sent as the standard `priority` field in object form. Values are instance-specific and are **not** translated by this skill — pass a name the project actually defines. |
| `storyPoints` | number | no | Numeric estimate for estimable types (`Story` / `Task` / `Bug`). Written to `config.fieldIds.storyPoints` as a **bare number**, not an option object. Rejected for `Sub-task`. Projects often validate on it before an issue may leave `Backlog`, so setting it at create time avoids a follow-up edit. |
| `parentKey` | string | conditional | Required when `profileName = Sub-task`. Optional when `profileName = Story` (or `Task`) to link the issue under a parent **Epic** (the Epic Link / parent relationship); e.g., `"PROJ-123"` |
| `environment` | string | conditional | Required when `profileName = Bug`; default `"PRD"` |
| `severity` | string | conditional | Required when `profileName = Bug`; default `"Sev 2"` |
| `testPhase` | string | conditional | Required when `profileName = Bug`; default `"Production"` |
| `responsibleTeam` | string | conditional | Required when `profileName = Bug`; default `"Pennymac"` |
| `epicExtras` | object | no | Optional per-team Epic fields (see Epic profile in `references/issue-type-requirements.md`) |

## Workflow

### Step 1: Validate MCP Connection

Invoke the `validate-mcp-connection` skill.

- Capture `cloudId` from the response.

**CRITICAL STOP CONDITION:** If validation fails after 2 retries, return a `ConnectionError` and stop.

### Step 2: Load Jira Config

This package is **multi-project**: `.ai/jira.config.json` can hold entries for multiple Jira projects. Resolve the active project key first, then load the config scoped to that project.

**2.0 — Resolve the active project key (BEFORE invoking `load-jira-config`):**

1. If the calling prompt supplied a `projectKey` parameter, use that as `activeProjectKey`.
2. Otherwise leave `activeProjectKey = undefined` and let `load-jira-config` fall back to the top-level `defaultProjectKey` in `.ai/jira.config.json` (handled in Step 2.1).

**2.1 — Invoke `load-jira-config`** with `mode = "resolved"` and `projectKey = activeProjectKey` (omit the input if undefined). The skill returns one of five resolved-mode response shapes — branch on the response and continue:

| `load-jira-config` response | Behavior |
|---|---|
| `found = true, valid = true` (no `error` field) | The response's `config` is the **flat single-project view**: `config.projectKey`, `config.site`, `config.fieldIds`, `config.defaults`, `config.issueTypeOverrides`, `config.customExtras`. Set `config = response.config` and continue to Step 3. The placeholder `{{projectKey}}` resolves to `config.projectKey` from this point onward. |
| `found = true, valid = false` | **Halt with `ConfigInvalidError`.** Surface `response.error.message` and the per-violation `details`, and instruct the user to run the `verify-jira-config` skill to inspect drift. Do not attempt creation against an invalid config. |
| `found = false` | **Offer to bootstrap the config via `configure-jira`** — see Step 2a below. |
| `error.code = "PROJECT_NOT_IN_CONFIG"` | The config exists but has no entry for `activeProjectKey`. **Offer to bootstrap that one project via `configure-jira` with `projectKey = <activeProjectKey>`** — see Step 2a below. The user prompt and fallback table are the same as the `not-found` branch, with the surfaced message tailored to "no entry for project X" instead of "no config file found". |
| `error.code = "DEFAULT_PROJECT_KEY_MISSING"` | The config exists but the user did not supply `projectKey` and `config.defaultProjectKey` is unset. **Halt this workflow** and ask the user to either (a) re-invoke the calling prompt with `projectKey=<one of response.error.availableProjectKeys>`, or (b) run `configure-jira` to set `defaultProjectKey`. Do not fall back to inline prompts — without a project key the workflow has no way to choose the right field IDs. |

The remainder of this skill is written assuming `config` is populated. Wherever a `{{*FieldId}}` placeholder appears in Step 4, resolve it via the **Config Resolution Reference** at the bottom of this skill. When `config = null` (after Step 2a fallback), prompt the user inline for each value the assembled payload would otherwise need.

#### Step 2a: Conditionally Bootstrap via `configure-jira` (when `found = false` or `error.code = "PROJECT_NOT_IN_CONFIG"`)

When `load-jira-config` returns `found = false` or `error.code = "PROJECT_NOT_IN_CONFIG"`, ask the user before chaining into a configuration flow. Pick the message that matches the response:

**If `found = false`:**

> No `.ai/jira.config.json` was found at any of the searched paths: `<response.searchedPaths>`.
> Would you like me to run **`configure-jira`** now to discover the project's field IDs and write a config? [Y/n]
> (If you decline, I'll fall back to asking for each field inline for this one invocation.)

**If `error.code = "PROJECT_NOT_IN_CONFIG"`:**

> `.ai/jira.config.json` exists but has no entry for project **`<response.error.requestedProjectKey>`**. The configured projects are: `<response.error.availableProjectKeys>`.
> Would you like me to run **`configure-jira` with `projectKey = <response.error.requestedProjectKey>`** now to add an entry for this project? [Y/n]
> (If you decline, I'll fall back to asking for each field inline for this one invocation.)

Branch on the user's answer:

| User answer | Behavior |
|---|---|
| **Yes** (default) | Invoke the **`configure-jira`** skill. Pass `projectKey` when known (always pass it for the `PROJECT_NOT_IN_CONFIG` branch — use `response.error.requestedProjectKey`). `configure-jira` will discover issue types, map field IDs, capture defaults, present a JSON preview, and gate the write behind its own permission step; it will **merge** the new project entry into any existing `config.projects` map. After it returns, branch on its outcome (next table). |
| **No** | Set `config = null` and fall back to today's inline-prompt behavior. Each subsequent `{{*FieldId}}` and default reference must be resolved by asking the user (or a calling prompt) for the value. Surface a one-line hint: `Tip: Run configure-jira anytime to add this project to .ai/jira.config.json so future invocations don't have to ask.` Continue to Step 3. |

After `configure-jira` returns, branch on its response:

| `configure-jira` outcome | Behavior |
|---|---|
| `success = true` | **Re-invoke `load-jira-config`** with the same `projectKey = activeProjectKey` to pick up the freshly-written entry. Expect `found = true, valid = true` (no `error`) on the second invocation. Set `config = response.config` (the flat single-project view) and continue to Step 3. If the second `load-jira-config` returns `found = false`, `valid = false`, or `error.code = "PROJECT_NOT_IN_CONFIG"`, halt with `BootstrapFailedError` (this indicates the write reported success but the entry is unreadable, invalid, or missing for the requested project). |
| `code = USER_CANCELLED` (the user declined the overwrite confirmation, declined the write preview, or aborted mid-flow) | Set `config = null` and fall back to inline-prompt behavior, exactly as if the user had answered "No" above. Continue to Step 3. |
| Any other error code (`CONNECTION_FAILED`, `INVALID_PROJECT_KEY`, `PROJECT_NOT_FOUND`, `WRITE_FAILED`) | **Halt this workflow** and surface the error to the user. The underlying problem (no MCP access, invalid project key, write permissions, etc.) will recur if the workflow proceeds. Do not fall back to inline prompts — the user needs to resolve the configure-jira error before retrying creation. |

Invoke `@./.cursor\skills\configure-jira\SKILL.md` directly, supplying the optional `projectKey` input when it is known so the skill can skip its own project-key dialog.

### Step 3: Load the Issue-Type Profile

Read @./.cursor\skills\create-jira-issues\references\issue-type-requirements.md and locate the section matching `profileName`. Each profile defines:

- `issueTypeName` -- exact API value (`Story`, `Task`, `Bug`, `Sub-task`, `Epic`)
- `requiredFields` -- field IDs the project enforces
- `recommendedFields` -- nice-to-have additions
- `acceptanceCriteriaMode` -- one of:
  - `adf-field` -- AC goes into `{{acceptanceCriteriaFieldId}}` as ADF JSON in a **separate** API call after creation
  - `inline-description` -- AC is appended into the description before creation (Bug pattern; AC field unavailable)
  - `none` -- AC is not supported for this type
- `specialFieldHandling` -- e.g., `parent` (Sub-task), `bug-specific` (Bug), `epic-specific` (Epic)

If `profileName` does not match any documented profile, return a `FieldValidationError` and stop.

### Step 4: Assemble the Field Payload

Build the `additional_fields` object using the profile + user inputs. Refer to @./.cursor\skills\create-jira-issues\references\jira-field-mappings.md for the format-type rules (single-select object vs multi-select array, etc.).

**Resolve every `{{*FieldId}}` placeholder via `config`** (see the Config Resolution Reference below). When `config.fieldIds.<name>` is `null`, the project does not expose that field for this issue type — **omit the key from the payload** rather than sending `null`. When `config = null` (no config file found), prompt the user for each field ID inline as a fallback.

**Always include (required for every type):**

```json
{
  "<config.fieldIds.channel>":    [{"value": "<config.defaults.channel>"}],
  "<config.fieldIds.workStream>": {"value": "<config.defaults.workStream>"},
  "<config.fieldIds.teams>":      [{"value": "<config.defaults.team>"}]
}
```

User-provided inputs override `config.defaults.*`. If `config.fieldIds.channel` is `null` or `config.issueTypeOverrides[profileName].channelRequired` is `false`, omit Channel from the payload.

**Profile-specific additions:**

- **Bug:** add `<config.fieldIds.bugEnvironment>`, `<config.fieldIds.bugSeverity>`, `<config.fieldIds.bugTestPhase>`, `<config.fieldIds.bugResponsibleTeam>` from inputs (fall back to `config.defaults.bugEnvironment` / `bugSeverity` / `bugTestPhase` / `bugResponsibleTeam` when the input is absent)
- **Sub-task:** add `parent: {"key": parentKey}` and ensure `labels` includes `<config.defaults.subtaskTrackingLabel>`
- **Story / Task (optional parent Epic):** when `parentKey` is provided, link the issue to its parent Epic. On modern Jira Cloud the parent relationship is the standard `parent` field — add `parent: {"key": parentKey}`. When the consuming project uses the legacy company-managed **Epic Link** custom field instead, set `<config.fieldIds.epicLink>: parentKey` (resolved from config); omit when `config.fieldIds.epicLink` is `null` and fall back to `parent`. Only one of the two is sent.
- **Epic:** merge any per-team `epicExtras` fields, mapped through `config.fieldIds.epicName` / `epicStartDate` / `epicEndDate` / `epicTheme` (see Epic profile in `references/issue-type-requirements.md` for the supported placeholders in this package)
- **Labels:** if provided, parse to an array of strings and set `labels`
- **Priority:** if provided, set `priority: {"name": "<priority>"}` per the Standard Jira Fields table in `references/jira-field-mappings.md`. This is a standard field, not a custom one — no field-id resolution is involved. Omit the key entirely when the input is absent so the project's own default applies. Priority **names are instance-specific** (some projects use Highest/High/Medium/Low/Lowest, others only High/Medium/Low): pass the value through unchanged and let Jira reject an unknown name as `FieldValidationError`. If the create call fails specifically on `priority` because the project does not expose it on this issue type, report the field as skipped rather than failing the whole create.

**Acceptance-criteria handling at this step:**

The effective AC mode for this issue type is `config.issueTypeOverrides[profileName].acceptanceCriteriaMode` if set, otherwise the profile's documented `acceptanceCriteriaMode`. If `config.fieldIds.acceptanceCriteria` is `null`, force the mode to `inline-description` regardless of the profile (the project does not expose an AC custom field for this type).

- If `acceptanceCriteriaMode = inline-description` AND `acceptanceCriteria` was provided, append the AC section to `description` before creation:

```markdown
{{description}}

## Acceptance Criteria
I know this is done when:
- criterion 1
- criterion 2
```

- If `acceptanceCriteriaMode = adf-field`, do **not** modify the description. AC will be applied in Step 7.

### Step 5: Ask Permission

Present the assembled creation request to the user with a type-aware preview. Example:

```text
I'd like to create the following Jira {{issueTypeName}}:

**Project:** {{projectKey}}
**Summary:** <summary>
**Description:** <preview>
[type-specific fields here, e.g. for Bug: Environment / Severity / Test Phase / Responsible Team]
[for Sub-task: Parent issue]
**Labels:** <labels or "(none)">
**Acceptance Criteria:** <list or "(none)">

Shall I proceed?
```

**Wait for explicit user approval before proceeding.**

If the user declines, return a `UserCancelled` outcome (not an error) and stop.

### Step 6: Create the Issue

Call `mcp_atlassian_createJiraIssue`. The active project key was resolved in Step 2 — read it directly from `config.projectKey` (set by `load-jira-config` when `mode = "resolved"` succeeds). When `config = null` (Step 2a fallback), `projectKey` was passed in by the calling prompt or must be prompted from the user inline.

```json
{
  "cloudId": "{{cloudId}}",
  "projectKey": "<config.projectKey>",
  "issueTypeName": "<profile.issueTypeName>",
  "summary": "<summary>",
  "description": "<description (with inline-description AC merged if applicable)>",
  "additional_fields": { /* assembled in Step 4 */ }
}
```

Refer to @./.cursor\skills\create-jira-issues\references\mcp-tool-usage.md for full per-type request bodies and known quirks.

Extract the created issue key from the response. Capture it as `issueKey`.

**CRITICAL STOP CONDITION:** If creation fails, return a `CreationError` (or `FieldValidationError` if the failure is a field-level rejection) and stop.

### Step 7: Set Acceptance Criteria (Conditional)

Only if the effective `acceptanceCriteriaMode = adf-field` (see Step 4) AND `acceptanceCriteria` was provided:

- Invoke the `set-acceptance-criteria` skill with **all four** required inputs:
  - `cloudId` (from Step 1)
  - `issueKey` (from Step 6)
  - `acceptanceCriteria` (the user-supplied AC list)
  - `acceptanceCriteriaFieldId` = **`config.fieldIds.acceptanceCriteria`** (resolved by THIS skill before delegating; the called skill does not load config itself)
- This MUST be a separate API call from the description -- combining markdown and ADF in one call fails.

If the effective mode is `inline-description` or `none`, skip this step.

### Step 8: Verify and Report

- Call `mcp_atlassian_getJiraIssue` with `cloudId` and `issueKey`.
- Confirm summary, type, and key custom fields are set as expected.
- Build the issue URL (typically `https://<site>/browse/<issueKey>`) and report success.

## Output Contract

### Success Response

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "summary": "<summary>",
  "issueType": "<profile.issueTypeName>",
  "url": "https://<site>/browse/PROJ-123"
}
```

For Bug, include `environment` and `severity` echo fields. For Sub-task, include the `parentKey`.

### Error Responses

| Code | When |
|---|---|
| `CONNECTION_FAILED` | MCP connection or auth failed |
| `FIELD_VALIDATION_FAILED` | Required field missing, invalid value, or unknown profile |
| `CREATION_FAILED` | `createJiraIssue` returned an unrecoverable error |
| `USER_CANCELLED` | User declined the proposed creation |

```json
{ "code": "<error code>", "message": "...", "field": "...", "details": "..." }
```

## Quick Reference: Field Format Types

| Format | Syntax | Used By |
|--------|--------|---------|
| Single-select | `{"value": "Option"}` | Work-Stream, Environment, Severity, Test Phase, Responsible Dev Team |
| Multi-select | `[{"value": "Option"}]` | Channel, Teams |
| Plain text | `"text content"` | Summary, Description |
| ADF JSON | `{"type": "doc", ...}` | Acceptance Criteria |
| Array of strings | `["label1", "label2"]` | Labels |
| Object with key | `{"key": "PROJ-123"}` | Parent (sub-tasks) |

## Error Recovery

| Error | Cause | Fix |
|-------|-------|-----|
| "Failed to convert markdown to adf" | Mixed markdown + ADF in one call | Step 7 is a separate call -- never combine description + AC |
| "Field cannot be set" | Missing required field | Re-check the profile in `references/issue-type-requirements.md` |
| "Bad Request" | Invalid field value | Verify against the allowed values in `references/jira-field-mappings.md` |
| MCP timeout | Large payload or connection issue | Retry with smaller payload |

## Config Resolution Reference

This table maps the `{{*FieldId}}` placeholders that historically appeared inline in this skill to the paths Step 2's `config` object exposes. When `config = null` (no `.ai/jira.config.json` found), the workflow falls back to inline prompting for each value.

| Placeholder (legacy) | Resolved from `config` |
|---|---|
| `{{acceptanceCriteriaFieldId}}` | `config.fieldIds.acceptanceCriteria` |
| `{{channelFieldId}}` | `config.fieldIds.channel` |
| `{{workStreamFieldId}}` | `config.fieldIds.workStream` |
| `{{teamsFieldId}}` | `config.fieldIds.teams` |
| `{{storyPointsFieldId}}` | `config.fieldIds.storyPoints` |
| `{{bugEnvironmentFieldId}}` | `config.fieldIds.bugEnvironment` |
| `{{bugSeverityFieldId}}` | `config.fieldIds.bugSeverity` |
| `{{bugTestPhaseFieldId}}` | `config.fieldIds.bugTestPhase` |
| `{{bugResponsibleTeamFieldId}}` | `config.fieldIds.bugResponsibleTeam` |
| `{{epicNameFieldId}}` | `config.fieldIds.epicName` |
| `{{epicStartDateFieldId}}` | `config.fieldIds.epicStartDate` |
| `{{epicEndDateFieldId}}` | `config.fieldIds.epicEndDate` |
| `{{epicThemeFieldId}}` | `config.fieldIds.epicTheme` |
| `{{channel}}` (default value) | `config.defaults.channel` |
| `{{workStream}}` (default value) | `config.defaults.workStream` |
| `{{team}}` (default value) | `config.defaults.team` |
| `{{subtaskTrackingLabel}}` | `config.defaults.subtaskTrackingLabel` |
| `{{projectKey}}` | `config.projectKey` (resolved by `load-jira-config` in Step 2 from the `projectKey` input or top-level `defaultProjectKey`) |

**Rules:**

- A field ID resolved to `null` from `config` means the project does not expose that field for this issue type — **omit the key from the payload entirely**, never send `null`.
- A default resolved to `null` means the team has no default — **prompt the user inline** for the value when it's required.
- `config.issueTypeOverrides[profileName].acceptanceCriteriaMode` overrides the profile's documented AC mode when present.
- `config.issueTypeOverrides[profileName].channelRequired = false` means Channel is not required for this issue type and can be omitted even if `config.fieldIds.channel` is non-null.

## Reference Documents

### In-skill references

- @./.cursor\skills\create-jira-issues\references\jira-field-mappings.md -- Complete field ID reference with custom field mappings and format types
- @./.cursor\skills\create-jira-issues\references\issue-type-requirements.md -- Per-type profiles (Story/Task/Bug/Sub-task/Epic) with required/optional fields and working examples
- @./.cursor\skills\create-jira-issues\references\adf-format-guide.md -- Atlassian Document Format patterns for acceptance criteria and rich text
- @./.cursor\skills\create-jira-issues\references\mcp-tool-usage.md -- MCP tool calling patterns, working examples, and known quirks

### Related skills

- `validate-mcp-connection` (`../validate-mcp-connection/SKILL.md`) -- Invoked in Step 1 to obtain `cloudId` and confirm Atlassian MCP availability
- `load-jira-config` (`../load-jira-config/SKILL.md`) -- Invoked in Step 2; documents the config object shape consumed throughout this workflow
- `configure-jira` (`../configure-jira/SKILL.md`) -- Invoked in Step 2a to bootstrap or repair the project's `.ai/jira.config.json` entry
- `verify-jira-config` (`../verify-jira-config/SKILL.md`) -- Read-only drift check the user runs when Step 2 halts with `ConfigInvalidError`
- `set-acceptance-criteria` (`../set-acceptance-criteria/SKILL.md`) -- Invoked in Step 7 to apply ADF acceptance criteria via `editJiraIssue` for `adf-field` profiles
