---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "createEpic"
---
# jira.createEpic

Create a new Jira Epic via the create-jira-issues workflow skill. Uses the Epic profile (acceptanceCriteriaMode = inline-description by default since most projects, including AIP, do not expose the AC custom field on Epic; flips to adf-field when the project does expose it). Supports the standard priority field and optional Epic-specific custom fields (Epic Name, target start/end dates, theme).

## Parameter Specifications

- **`projectKey`** (string) - *Optional*
  - Jira project key the epic should be created in (e.g., 'AIP', 'PCG'). When omitted, the workflow falls back to top-level defaultProjectKey in .ai/jira.config.json. If neither is set, the workflow halts with DefaultProjectKeyMissingError.

- **`summary`** (string) - **Required**
  - Epic title / summary (also serves as the Epic Name in modern Jira)

- **`description`** (string) - *Optional*
  - Epic description in markdown format

- **`acceptanceCriteria`** (string) - *Optional*
  - Acceptance criteria as a comma-separated or newline-separated list. Default mode appends them as a `## Acceptance Criteria` section in the description (inline-description); when the project exposes the AC custom field on Epic, the workflow sets it via a separate ADF API call instead.

- **`labels`** (string) - *Optional*
  - Comma-separated labels to apply

- **`priority`** (string) - *Optional*
  - Priority name as defined in the target Jira instance (e.g. 'High', 'Medium', 'Low', or 'Highest'/'Lowest' where the project defines them). Sent as the standard priority field in object form: {"name": "<priority>"}. Omit to let the project default apply. Names are instance-specific and passed through unchanged; an unknown name returns FIELD_VALIDATION_FAILED.

- **`epicName`** (string) - *Optional*
  - Separate Epic Name field, when the consuming Jira project keeps Epic Name distinct from summary

- **`targetStartDate`** (string) - *Optional*
  - Target start date in YYYY-MM-DD format

- **`targetEndDate`** (string) - *Optional*
  - Target end date in YYYY-MM-DD format

- **`theme`** (string) - *Optional*
  - Epic theme value, when the consuming project defines themes

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `projectKey` (optional) - Jira project key the epic should be created in (e.g., 'AIP', 'PCG'). When omitted, the workflow falls back to top-level defaultProjectKey in .ai/jira.config.json. If neither is set, the workflow halts with DefaultProjectKeyMissingError.
   - Parameter 2: `summary` (required) - Epic title / summary (also serves as the Epic Name in modern Jira)
   - Parameter 3: `description` (optional) - Epic description in markdown format
   - Parameter 4: `acceptanceCriteria` (optional) - Acceptance criteria as a comma-separated or newline-separated list. Default mode appends them as a `## Acceptance Criteria` section in the description (inline-description); when the project exposes the AC custom field on Epic, the workflow sets it via a separate ADF API call instead.
   - Parameter 5: `labels` (optional) - Comma-separated labels to apply
   - Parameter 6: `priority` (optional) - Priority name as defined in the target Jira instance (e.g. 'High', 'Medium', 'Low', or 'Highest'/'Lowest' where the project defines them). Sent as the standard priority field in object form: {"name": "<priority>"}. Omit to let the project default apply. Names are instance-specific and passed through unchanged; an unknown name returns FIELD_VALIDATION_FAILED.
   - Parameter 7: `epicName` (optional) - Separate Epic Name field, when the consuming Jira project keeps Epic Name distinct from summary
   - Parameter 8: `targetStartDate` (optional) - Target start date in YYYY-MM-DD format
   - Parameter 9: `targetEndDate` (optional) - Target end date in YYYY-MM-DD format
   - Parameter 10: `theme` (optional) - Epic theme value, when the consuming project defines themes

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.createEpic value1 value2`
- Named parameters: `/jira.createEpic param1=value1 param2=value2`
- Mixed format: `/jira.createEpic value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Created Jira epic details

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `issueKey` (string) - **Required** - Created issue key
- `summary` (string) - **Required** - 
- `issueType` (string) - **Required** - 
- `url` (string) - *Optional* - Jira issue URL
## Error Handling

### ConnectionError



**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 
- `details` (string) - 

### CreationError



**Properties:**

- `code` (string) (values: ["CREATION_FAILED"]) - 
- `message` (string) - 
- `details` (string) - 

### FieldValidationError



**Properties:**

- `code` (string) (values: ["FIELD_VALIDATION_FAILED"]) - 
- `message` (string) - 
- `field` (string) - 
- `details` (string) - 

### ConfigInvalidError

The .ai/jira.config.json file exists but failed schema validation. The workflow halts before attempting to create or update an issue. Run the verify-jira-config skill to see violations.

**Properties:**

- `code` (string) (values: ["CONFIG_INVALID"]) - 
- `message` (string) - 
- `configPath` (string) - Absolute path to the offending config file
- `details` (array) - Per-violation findings from schema validation

### BootstrapFailedError

The configure-jira skill reported success but the freshly-written .ai/jira.config.json could not be loaded or validated on the follow-up load-jira-config call. Indicates an unexpected discrepancy between write and read.

**Properties:**

- `code` (string) (values: ["BOOTSTRAP_FAILED"]) - 
- `message` (string) - 
- `configPath` (string) - Absolute path the configure-jira skill reported writing
- `details` (string) - Why the post-write load failed (parse error, schema violation, missing file)

### ProjectNotInConfigError

The .ai/jira.config.json file exists and is valid, but has no entry under config.projects for the requested project key. The workflow halts and the calling agent should offer to bootstrap the missing project via the configure-jira skill with projectKey=<requested>.

**Properties:**

- `code` (string) (values: ["PROJECT_NOT_IN_CONFIG"]) - 
- `message` (string) - 
- `requestedProjectKey` (string) - The project key the workflow attempted to resolve
- `availableProjectKeys` (array) - Project keys currently configured in the file
- `configPath` (string) - Absolute path to the loaded config file

### DefaultProjectKeyMissingError

The .ai/jira.config.json file is valid but the workflow could not resolve a project key — the calling prompt did not supply a projectKey parameter and config.defaultProjectKey is unset. The workflow halts; the user must either supply projectKey explicitly or run the configure-jira skill to set defaultProjectKey.

**Properties:**

- `code` (string) (values: ["DEFAULT_PROJECT_KEY_MISSING"]) - 
- `message` (string) - 
- `availableProjectKeys` (array) - Project keys configured in the file (the user can pick one to pass as projectKey)
- `configPath` (string) - Absolute path to the loaded config file

## Prompt Content

# Create Jira Epic

Create a new Epic issue in Jira. Thin dispatcher around the `create-jira-issues` workflow skill. Epics group related Stories, Tasks, and Bugs under a higher-level initiative or capability theme.

## Parameters

- **{{projectKey}}** (string, optional): Jira project key the epic should be created in (e.g., `AIP`, `PCG`). When omitted, the workflow falls back to top-level `defaultProjectKey` in `.ai/jira.config.json`. If neither is set, the workflow halts with `DefaultProjectKeyMissingError`.
- **{{summary}}** (string, required): Epic title / summary (also serves as the Epic Name in modern Jira)
- **{{description}}** (string, optional): Epic description in markdown format
  - Recommended sections: Overview, User Problem, Key Features, Success Metrics, Dependencies
- **{{acceptanceCriteria}}** (string, optional): High-level epic-completion acceptance criteria as a comma-separated or newline-separated list. By default the workflow appends these to the description (`inline-description` mode); when the project exposes the AC custom field on Epic, the workflow sets it via a separate ADF API call instead.
- **{{labels}}** (string, optional): Comma-separated labels to apply (e.g., initiative or theme keys like `pitcrew`, `phase-2`)
- **{{priority}}** (string, optional): Priority name as defined in the target Jira instance (e.g. `High`, `Medium`, `Low`, or `Highest`/`Lowest` where the project defines them). Sent as the standard `priority` field in object form — `{"name": "<priority>"}`. Omit to let the project's default apply. Names are **instance-specific and passed through unchanged**; an unknown name comes back as `FieldValidationError`.
- **{{epicName}}** (string, optional): Separate Epic Name field, when the consuming Jira project keeps Epic Name distinct from `summary`. Maps to `{{epicNameFieldId}}`
- **{{targetStartDate}}** (string, optional): Target start date in `YYYY-MM-DD` format. Maps to `{{epicStartDateFieldId}}`
- **{{targetEndDate}}** (string, optional): Target end date in `YYYY-MM-DD` format. Maps to `{{epicEndDateFieldId}}`
- **{{theme}}** (string, optional): Epic theme value, when the consuming project defines themes. Maps to `{{epicThemeFieldId}}`

The four Epic-specific parameters (`epicName`, `targetStartDate`, `targetEndDate`, `theme`) are optional and only meaningful when the consuming team has configured the corresponding placeholders. See the `create-jira-issues` skill's `jira-field-mappings` reference (Epic-Specific Fields) for the full list. `priority` is different — it is a **standard** Jira field (see Standard Jira Fields in the same reference), so it needs no field-id configuration.

## Instructions

Load `@./.cursor\skills\create-jira-issues\SKILL.md` and execute it with these inputs.


| Workflow input                        | Value                                                               |
| ------------------------------------- | ------------------------------------------------------------------- |
| `profileName`                         | `Epic`                                                              |
| `projectKey`                          | `{{projectKey}}` (omit to fall back to `config.defaultProjectKey`)  |
| `summary`                             | `{{summary}}`                                                       |
| `description`                         | `{{description}}`                                                   |
| `acceptanceCriteria`                  | `{{acceptanceCriteria}}`                                            |
| `labels`                              | `{{labels}}`                                                        |
| `priority`                            | `{{priority}}` (only if provided -- standard field, object form)    |
| `epicExtras.{{epicNameFieldId}}`      | `{{epicName}}` (only if provided)                                   |
| `epicExtras.{{epicStartDateFieldId}}` | `{{targetStartDate}}` (only if provided)                            |
| `epicExtras.{{epicEndDateFieldId}}`   | `{{targetEndDate}}` (only if provided)                              |
| `epicExtras.{{epicThemeFieldId}}`     | `{"value": "{{theme}}"}` (only if provided -- single-select format) |


The Epic profile sets `acceptanceCriteriaMode = inline-description` by default (most projects, including AIP, do not expose the AC custom field on Epic). The skill will:

1. Validate the MCP connection (via `validate-mcp-connection`)
2. Assemble required fields per the Epic profile in the skill's `issue-type-requirements` reference
3. Merge any provided `epicExtras` into `additional_fields`
4. Append the `acceptanceCriteria` list as a `## Acceptance Criteria` section to `description` (inline-description mode)
5. Ask for explicit user approval before creating
6. Call `createJiraIssue`
7. (Adf-field mode only — when the project exposes the AC custom field on Epic) Delegate to the `set-acceptance-criteria` skill in a separate API call
8. Verify with `getJiraIssue` and report

If a consuming project's Jira **does** expose the AC custom field on Epic, the Epic profile's `acceptanceCriteriaMode` is flipped to `adf-field` per the AC Mode Detection note in `issue-type-requirements.md`. No prompt change is required -- the dispatch is handled in the workflow skill.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "summary": "Epic summary here",
  "issueType": "Epic",
  "url": "https://pennymac.atlassian.net/browse/PROJ-123"
}
```

## Error Handling

Errors are surfaced as returned by the `create-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`) -- MCP connection failed
- `CreationError` (`CREATION_FAILED`) -- `createJiraIssue` returned an unrecoverable error
- `FieldValidationError` (`FIELD_VALIDATION_FAILED`) -- a required field was missing, an Epic-specific value was invalid, or the AC field is not available on Epic in this project (consider switching to `inline-description` mode)
- `UserCancelled` (`USER_CANCELLED`) -- the user declined the proposed creation
- `ConfigInvalidError` (`CONFIG_INVALID`) -- `.ai/jira.config.json` failed schema validation; run `@./.cursor\skills\verify-jira-config\SKILL.md` to inspect the drift
- `BootstrapFailedError` (`BOOTSTRAP_FAILED`) -- `configure-jira` reported success but the freshly-written config could not be re-loaded
- `ProjectNotInConfigError` (`PROJECT_NOT_IN_CONFIG`) -- the resolved project key has no entry in `config.projects` and the user declined to bootstrap it
- `DefaultProjectKeyMissingError` (`DEFAULT_PROJECT_KEY_MISSING`) -- neither `projectKey` parameter nor `config.defaultProjectKey` is set

```json
{ "code": "CONNECTION_FAILED", "message": "Unable to connect to Atlassian MCP server", "details": "..." }
```

## Notes

- **Epic Name vs Summary:** Modern Jira projects use `summary` as the Epic Name. Older projects may keep Epic Name as a separate custom field; provide `epicName` when that's the case.
- **AC Field Availability:** The Epic AC field availability varies by Jira project configuration. The default mode is `inline-description` (verified for AIP, where Epic does not expose the AC custom field). If your project exposes `{{acceptanceCriteriaFieldId}}` for Epic, flip the Epic profile's `acceptanceCriteriaMode` to `adf-field` (handled in the `create-jira-issues` skill / `issue-type-requirements.md`).
- **Children:** Linking child Stories / Tasks / Bugs to this Epic is a follow-up step done by setting the parent / Epic Link field on the children, not on the Epic itself.


