# Issue Type Requirements

Per-type profiles consumed by the `create-jira-issues` and `update-jira-issues` workflow skills. Each profile defines the required and optional fields, the `acceptanceCriteriaMode` the workflow uses to dispatch AC handling, and a working `createJiraIssue` example.

## Per-Team Configuration Overrides

The workflow skills resolve every `{{*FieldId}}` placeholder below from the consuming repo's `.ai/jira.config.json` at runtime (see [`load-jira-config/SKILL.md`](../../load-jira-config/SKILL.md)). When the file is missing, the workflow falls back to inline-prompting for each value. When `config.fieldIds.<name>` is `null`, the workflow omits that key from the payload entirely — useful for projects that don't expose a given field on a given issue type.

The default `acceptanceCriteriaMode` per profile below can be overridden per-issue-type via `config.issueTypeOverrides[<Type>].acceptanceCriteriaMode` (`adf-field` | `inline-description` | `none`). The workflow also force-flips the effective mode to `inline-description` whenever `config.fieldIds.acceptanceCriteria` is `null`, regardless of the profile default.

See [`packages/jira/skills/create-jira-issues/SKILL.md`](../SKILL.md) → "Config Resolution Reference" for the complete placeholder → config-path mapping.

## Profile Schema

Every profile in this document defines:

- `issueTypeName` -- Exact API value passed to `createJiraIssue` (e.g., `"Story"`, `"Epic"`)
- `requiredFields` -- Field IDs the project enforces; creation fails if any are missing
- `recommendedFields` -- Optional fields that improve quality
- `acceptanceCriteriaMode` -- One of:
  - `adf-field` -- AC is set on `{{acceptanceCriteriaFieldId}}` as ADF JSON in a separate API call after creation (Story, Task, Sub-task)
  - `inline-description` -- AC is appended into the description before creation (Bug and Epic, since the AC custom field is unavailable for those types in many projects including AIP)
  - `none` -- AC is not supported for this type
- `specialFieldHandling` -- Notes on type-specific quirks (parent for Sub-task, bug-specific fields for Bug, etc.)

## Field Requirements Matrix


| Field                                                  | Story        | Task         | Bug                  | Sub-task                      | Epic                                                                       |
| ------------------------------------------------------ | ------------ | ------------ | -------------------- | ----------------------------- | -------------------------------------------------------------------------- |
| Summary                                                | **Required** | **Required** | **Required**         | **Required**                  | **Required**                                                               |
| Description                                            | Recommended  | Recommended  | **Required**         | Recommended                   | **Required**                                                               |
| Channel (`{{channelFieldId}}`)                         | **Required** | **Required** | **Required**         | **Required**                  | Optional (project-dependent)                                               |
| Work-Stream (`{{workStreamFieldId}}`)                  | **Required** | **Required** | **Required**         | **Required**                  | **Required**                                                               |
| Teams (`{{teamsFieldId}}`)                             | **Required** | **Required** | **Required**         | **Required**                  | **Required**                                                               |
| Acceptance Criteria (`{{acceptanceCriteriaFieldId}}`)  | Recommended  | Optional     | **Not available**    | Optional                      | **Not available** (project-dependent; see AC Mode Fallback)                |
| Labels                                                 | Optional     | Optional     | Optional             | **Required** (tracking label) | Optional                                                                   |
| Parent (Epic Link)                                     | Optional     | Optional     | N/A                  | **Required**                  | N/A                                                                        |
| Environment (`{{bugEnvironmentFieldId}}`)              | N/A          | N/A          | **Required**         | N/A                           | N/A                                                                        |
| Severity (`{{bugSeverityFieldId}}`)                    | N/A          | N/A          | **Required**         | N/A                           | N/A                                                                        |
| Test Phase (`{{bugTestPhaseFieldId}}`)                 | N/A          | N/A          | **Required**         | N/A                           | N/A                                                                        |
| Responsible Dev Team (`{{bugResponsibleTeamFieldId}}`) | N/A          | N/A          | **Required**         | N/A                           | N/A                                                                        |
| AC Mode                                                | `adf-field`  | `adf-field`  | `inline-description` | `adf-field`                   | `inline-description` (default; `adf-field` when project exposes the field) |


## Story Creation

Stories represent user-facing features or capabilities.

### Profile

- `issueTypeName`: `"Story"`
- `acceptanceCriteriaMode`: `adf-field`

### Required Fields

- `summary` -- Concise title
- `description` -- Feature description (markdown)
- Channel, Work-Stream, Teams -- Organizational custom fields

### Recommended Fields

- Acceptance Criteria (`{{acceptanceCriteriaFieldId}}`) -- In ADF format (see `adf-format-guide.md`)
- Labels -- Relevant categorization tags

### Optional Parent (Epic Link)

A Story may be linked under a parent **Epic** at create or update time via the `parentKey` input (the issue key of the Epic). On modern Jira Cloud this is the standard `parent` field (`{"key": parentKey}`); on legacy company-managed projects it is the **Epic Link** custom field, resolved from `config.fieldIds.epicLink` when present. Only one of the two is sent. Omit `parentKey` to leave the story unparented. The same handling applies to `Task`.

### Working Example

```json
{
  "cloudId": "{{cloudId}}",
  "projectKey": "{{projectKey}}",
  "issueTypeName": "Story",
  "summary": "Implement user notification preferences",
  "description": "As a user, I want to configure my notification preferences so that I only receive relevant alerts.\n\n## Context\nUsers currently receive all notifications with no way to filter them.\n\n## Scope\n- Email notification toggle\n- Push notification toggle\n- Per-category preferences",
  "additional_fields": {
    "{{channelFieldId}}": [{"value": "{{channel}}"}],
    "{{workStreamFieldId}}": {"value": "{{workStream}}"},
    "{{teamsFieldId}}": [{"value": "{{team}}"}],
    "labels": ["notifications", "user-preferences"]
  }
}
```

### Post-Creation: Set Acceptance Criteria

Update in a **separate API call** using ADF format:

```json
{
  "cloudId": "{{cloudId}}",
  "issueIdOrKey": "CREATED-KEY",
  "additional_fields": {
    "{{acceptanceCriteriaFieldId}}": {
      "type": "doc",
      "version": 1,
      "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "I know this is done when:"}]},
        {"type": "bulletList", "content": [
          {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "User can toggle email notifications on/off"}]}]},
          {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "User can toggle push notifications on/off"}]}]},
          {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Preferences persist across sessions"}]}]}
        ]}
      ]
    }
  }
}
```

## Task Creation

Tasks represent technical work, maintenance, or non-feature work.

### Profile

- `issueTypeName`: `"Task"`
- `acceptanceCriteriaMode`: `adf-field`

### Required Fields

- `summary` -- Concise title
- Channel, Work-Stream, Teams -- Organizational custom fields

### Recommended Fields

- `description` -- Task details (markdown)
- Labels -- Relevant categorization tags

### Working Example

```json
{
  "cloudId": "{{cloudId}}",
  "projectKey": "{{projectKey}}",
  "issueTypeName": "Task",
  "summary": "Upgrade database driver to v3.2",
  "description": "Upgrade the PostgreSQL driver from v2.8 to v3.2 to resolve connection pooling issues and support new TLS requirements.",
  "additional_fields": {
    "{{channelFieldId}}": [{"value": "{{channel}}"}],
    "{{workStreamFieldId}}": {"value": "{{workStream}}"},
    "{{teamsFieldId}}": [{"value": "{{team}}"}],
    "labels": ["tech-debt", "database"]
  }
}
```

## Bug Creation

Bugs represent defects, regressions, or unexpected behavior. Bugs have the most required fields.

### Profile

- `issueTypeName`: `"Bug"`
- `acceptanceCriteriaMode`: `inline-description` (AC field not available; AC merged into description)

### Required Fields

- `summary` -- Concise bug title
- `description` -- Bug details including repro steps (**include AC here** since the AC field is not available for bugs)
- Channel, Work-Stream, Teams -- Organizational custom fields
- Environment (`{{bugEnvironmentFieldId}}`) -- Where the bug was found
- Severity (`{{bugSeverityFieldId}}`) -- Impact level
- Test Phase (`{{bugTestPhaseFieldId}}`) -- Testing stage where discovered
- Responsible Dev Team (`{{bugResponsibleTeamFieldId}}`) -- Team responsible for the fix

### Bug Description Strategy

Since the acceptance criteria field is **not available** for Bugs, include AC at the end of the description:

```markdown
## Summary
Brief description of the bug.

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen.

## Actual Behavior
What actually happens.

## Acceptance Criteria
I know this is done when:
- Criterion 1
- Criterion 2
```

### Working Example

```json
{
  "cloudId": "{{cloudId}}",
  "projectKey": "{{projectKey}}",
  "issueTypeName": "Bug",
  "summary": "Login redirect loop on expired session",
  "description": "## Summary\nUsers with expired sessions encounter an infinite redirect loop between /login and /dashboard.\n\n## Steps to Reproduce\n1. Log in and wait for session to expire (30 min)\n2. Navigate to /dashboard\n3. Observe redirect loop\n\n## Expected Behavior\nUser is redirected to /login once and can re-authenticate.\n\n## Actual Behavior\nBrowser enters redirect loop until timeout.\n\n## Acceptance Criteria\nI know this is done when:\n- Expired sessions redirect to /login exactly once\n- User can re-authenticate successfully\n- No redirect loops under any session state",
  "additional_fields": {
    "{{bugEnvironmentFieldId}}": {"value": "PRD"},
    "{{bugSeverityFieldId}}": {"value": "Sev 2"},
    "{{bugTestPhaseFieldId}}": {"value": "Production"},
    "{{bugResponsibleTeamFieldId}}": {"value": "Pennymac"},
    "{{channelFieldId}}": [{"value": "{{channel}}"}],
    "{{workStreamFieldId}}": {"value": "{{workStream}}"},
    "{{teamsFieldId}}": [{"value": "{{team}}"}],
    "labels": ["bug", "authentication"]
  }
}
```

### Common Bug Field Combinations

**Production issue:**

```json
"{{bugEnvironmentFieldId}}": {"value": "PRD"},
"{{bugSeverityFieldId}}": {"value": "Sev 2"},
"{{bugTestPhaseFieldId}}": {"value": "Production"},
"{{bugResponsibleTeamFieldId}}": {"value": "Pennymac"}
```

**QA-found issue:**

```json
"{{bugEnvironmentFieldId}}": {"value": "QA"},
"{{bugSeverityFieldId}}": {"value": "Sev 2"},
"{{bugTestPhaseFieldId}}": {"value": "QA"},
"{{bugResponsibleTeamFieldId}}": {"value": "Pennymac"}
```

**Development issue:**

```json
"{{bugEnvironmentFieldId}}": {"value": "DEV"},
"{{bugSeverityFieldId}}": {"value": "Sev 3"},
"{{bugTestPhaseFieldId}}": {"value": "QA"},
"{{bugResponsibleTeamFieldId}}": {"value": "Pennymac"}
```

## Sub-task Creation

Sub-tasks break a parent story or task into implementable units.

### Profile

- `issueTypeName`: `"Sub-task"`
- `acceptanceCriteriaMode`: `adf-field`
- `specialFieldHandling`: `parent` required in object form `{"key": "PARENT-KEY"}`; `labels` must include `{{subtaskTrackingLabel}}`

### Required Fields

- `summary` -- Concise sub-task title
- `parent` -- Parent issue key in object format
- Channel, Work-Stream, Teams -- Organizational custom fields
- Labels -- Must include tracking label `{{subtaskTrackingLabel}}`

### Critical Rules

- Parent field **MUST** use object format: `{"key": "PARENT-KEY"}` (not a plain string)
- All sub-tasks **MUST** include the `{{subtaskTrackingLabel}}` label
- Sub-tasks do not require sizing/story points
- After creation, transition sub-tasks to "To Do" status

### Working Example

```json
{
  "cloudId": "{{cloudId}}",
  "projectKey": "{{projectKey}}",
  "summary": "Implement email notification toggle API endpoint",
  "issueTypeName": "Sub-task",
  "description": "Create the REST endpoint for toggling email notification preferences.\n\n- POST /api/v1/users/{id}/preferences/notifications/email\n- Request body: { enabled: boolean }\n- Returns updated preference state",
  "additional_fields": {
    "parent": {"key": "{{projectKey}}-1234"},
    "{{channelFieldId}}": [{"value": "{{channel}}"}],
    "{{workStreamFieldId}}": {"value": "{{workStream}}"},
    "{{teamsFieldId}}": [{"value": "{{team}}"}],
    "labels": ["{{subtaskTrackingLabel}}"]
  }
}
```

### Post-Creation: Transition to "To Do"

After creating sub-tasks, transition them so they appear in the backlog:

1. Call `getTransitionsForJiraIssue` on the first sub-task to find available transitions
2. Find the transition ID for "To Do"
3. Call `transitionJiraIssue` for each sub-task with that transition ID

## Epic Creation

Epics group related Stories, Tasks, and Bugs under a higher-level initiative or capability theme.

### Profile

- `issueTypeName`: `"Epic"`
- `acceptanceCriteriaMode`: `inline-description` (default — most projects, including AIP, do **not** expose the AC custom field on Epic, so AC is appended to the description before creation; flip to `adf-field` only when `getJiraIssueTypeMetaWithFields` for Epic returns `{{acceptanceCriteriaFieldId}}`)
- `specialFieldHandling`: optional per-team `epicExtras` may include Epic-specific custom fields when defined by the consuming team (see `jira-field-mappings.md` Epic-Specific Fields section). The base profile uses only the generic required fields.

### Required Fields

- `summary` -- Concise epic title (also serves as the Epic Name in modern Jira)
- `description` -- Full epic body in markdown (overview, user problem, key features, success metrics, dependencies). When `acceptanceCriteriaMode` is `inline-description`, AC is appended here as a final `## Acceptance Criteria` section.
- Work-Stream, Teams -- Organizational custom fields (Channel is optional/project-dependent for Epic — verified absent from required-field set in AIP)

### Recommended Fields

- Acceptance Criteria -- High-level epic-completion criteria. Default delivery mode is inline (appended into description). Only switched to ADF custom field when the project's Epic issue-type metadata exposes that field.
- Labels -- Categorization tags such as initiative or theme keys (e.g., `pitcrew`, `phase-2`)
- Channel (`{{channelFieldId}}`) -- Optional for Epic, required if the team uses Channel for portfolio reporting

### Optional Per-Team Epic Extras

When a consuming team has additional Epic-specific custom fields (target start/end dates, Epic Name as a separate field, theme, etc.), they are passed via the `epicExtras` input and merged into `additional_fields`. The placeholder names follow the same `{{*FieldId}}` convention as Bug-specific fields. See `jira-field-mappings.md` Epic-Specific Fields for the supported placeholders in this package.

### Working Example (inline-description mode — default)

```json
{
  "cloudId": "{{cloudId}}",
  "projectKey": "{{projectKey}}",
  "issueTypeName": "Epic",
  "summary": "AI Portal — Self-Service Onboarding and Visibility",
  "description": "## Overview\nThis epic delivers the AI Portal — the web interface through which engineering teams opt their repositories into PitCrew and watch the platform work.\n\n## User Problem\n...\n\n## Key Features & Functionality\n- Repository opt-in flow\n- Repo Readiness Checklist\n- Live activity dashboard\n\n## Acceptance Criteria\nI know this is done when:\n- Authenticated Technical Lead can opt a repository in without contacting the platform team\n- Activity dashboard displays MRs submitted, MRs merged, and time-to-MR statistics",
  "additional_fields": {
    "{{workStreamFieldId}}": {"value": "{{workStream}}"},
    "{{teamsFieldId}}": [{"value": "{{team}}"}],
    "labels": ["pitcrew", "ai-portal", "phase-2"]
  }
}
```

### Working Example (adf-field mode — when project exposes AC field on Epic)

When the project's Epic issue-type metadata exposes `{{acceptanceCriteriaFieldId}}`, omit the AC section from the description and instead set it via a **separate API call** after creation using the standard ADF pattern (see `adf-format-guide.md`).

### AC Mode Detection

To determine which AC mode to use for a given project, call `getJiraIssueTypeMetaWithFields` with the Epic `issueTypeId` and inspect the returned `fields[]` array:

- If a custom field with the configured `{{acceptanceCriteriaFieldId}}` is present, set `acceptanceCriteriaMode = adf-field`
- Otherwise (e.g., AIP), keep `acceptanceCriteriaMode = inline-description` and merge AC into the description body

