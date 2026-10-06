---
promp:
  package: "jira"
  version: "1.10.0"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "createBug"
---
# jira.createBug

Create a new Jira Bug with all required bug-specific fields (Environment, Severity, Test Phase, Responsible Team) and AC embedded in description

## Parameter Specifications

- **`projectKey`** (string) - *Optional*
  - Jira project key the bug should be created in (e.g., 'AIP', 'PCG'). When omitted, the workflow falls back to top-level defaultProjectKey in .ai/jira.config.json. If neither is set, the workflow halts with DefaultProjectKeyMissingError.

- **`summary`** (string) - **Required**
  - Bug title / summary

- **`description`** (string) - *Optional*
  - Bug description in markdown (include repro steps, expected/actual behavior)

- **`acceptanceCriteria`** (string) - *Optional*
  - Acceptance criteria (appended to description since AC field unavailable for Bugs)

- **`environment`** (string) - *Optional*
  - Environment where bug was found (e.g., PRD, QA, DEV, STG)
  - Default: `PRD`

- **`severity`** (string) - *Optional*
  - Bug severity level (Sev 1, Sev 2, Sev 3, TBD)
  - Default: `Sev 2`

- **`testPhase`** (string) - *Optional*
  - Testing phase where bug was discovered (QA, UAT, SIT, E2E, Production)
  - Default: `Production`

- **`responsibleTeam`** (string) - *Optional*
  - Development team responsible for the fix
  - Default: `Pennymac`

- **`labels`** (string) - *Optional*
  - Comma-separated labels to apply to the bug

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `projectKey` (optional) - Jira project key the bug should be created in (e.g., 'AIP', 'PCG'). When omitted, the workflow falls back to top-level defaultProjectKey in .ai/jira.config.json. If neither is set, the workflow halts with DefaultProjectKeyMissingError.
   - Parameter 2: `summary` (required) - Bug title / summary
   - Parameter 3: `description` (optional) - Bug description in markdown (include repro steps, expected/actual behavior)
   - Parameter 4: `acceptanceCriteria` (optional) - Acceptance criteria (appended to description since AC field unavailable for Bugs)
   - Parameter 5: `environment` (optional) [default: PRD] - Environment where bug was found (e.g., PRD, QA, DEV, STG)
   - Parameter 6: `severity` (optional) [default: Sev 2] - Bug severity level (Sev 1, Sev 2, Sev 3, TBD)
   - Parameter 7: `testPhase` (optional) [default: Production] - Testing phase where bug was discovered (QA, UAT, SIT, E2E, Production)
   - Parameter 8: `responsibleTeam` (optional) [default: Pennymac] - Development team responsible for the fix
   - Parameter 9: `labels` (optional) - Comma-separated labels to apply to the bug

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/jira.createBug value1 value2`
- Named parameters: `/jira.createBug param1=value1 param2=value2`
- Mixed format: `/jira.createBug value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Created Jira bug details

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `issueKey` (string) - **Required** - Created issue key
- `summary` (string) - **Required** - 
- `issueType` (string) - **Required** - 
- `environment` (string) - *Optional* - 
- `severity` (string) - *Optional* - 
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

# Create Jira Bug

Create a new Bug issue in Jira. Thin dispatcher around the `create-jira-issues` workflow skill. Bugs require additional mandatory fields (Environment, Severity, Test Phase, Responsible Dev Team) and the AC custom field is **not available**, so AC is merged into the description.

## Parameters

- **{{projectKey}}** (string, optional): Jira project key the bug should be created in (e.g., `AIP`, `PCG`). When omitted, the workflow falls back to top-level `defaultProjectKey` in `.ai/jira.config.json`. If neither is set, the workflow halts with `DefaultProjectKeyMissingError`.
- **{{summary}}** (string, required): Bug title / summary
- **{{description}}** (string, optional): Bug description in markdown
  - Should include: Summary, Steps to Reproduce, Expected Behavior, Actual Behavior
- **{{acceptanceCriteria}}** (string, optional): Acceptance criteria as a comma-separated or newline-separated list
  - Will be appended to the description (NOT placed in the AC custom field)
- **{{environment}}** (string, optional): Environment where the bug was found. Default: `PRD`
- **{{severity}}** (string, optional): Bug severity level. Default: `Sev 2`
- **{{testPhase}}** (string, optional): Testing phase where bug was discovered. Default: `Production`
- **{{responsibleTeam}}** (string, optional): Development team responsible for the fix. Default: `Pennymac`
- **{{labels}}** (string, optional): Comma-separated labels to apply to the bug

Allowed values for `environment`, `severity`, `testPhase`, and `responsibleTeam` are documented in the skill's `jira-field-mappings` reference (Bug Field Allowed Values).

## Instructions

Load `@./.cursor\skills\create-jira-issues\SKILL.md` and execute it with these inputs.

| Workflow input | Value |
|---|---|
| `profileName` | `Bug` |
| `projectKey` | `{{projectKey}}` (omit to fall back to `config.defaultProjectKey`) |
| `summary` | `{{summary}}` |
| `description` | `{{description}}` |
| `acceptanceCriteria` | `{{acceptanceCriteria}}` (merged into description by the skill, since AC field is unavailable) |
| `labels` | `{{labels}}` |
| `environment` | `{{environment}}` |
| `severity` | `{{severity}}` |
| `testPhase` | `{{testPhase}}` |
| `responsibleTeam` | `{{responsibleTeam}}` |

The Bug profile sets `acceptanceCriteriaMode = inline-description`, so the skill appends a `## Acceptance Criteria` section into the description before creation rather than calling `set-acceptance-criteria`. The four bug-specific custom fields are resolved from `.ai/jira.config.json` and added per the Bug profile in the skill's `issue-type-requirements` reference.

Return the skill's response unchanged.

## Response Format

### Success Response

```json
{
  "success": true,
  "issueKey": "PROJ-123",
  "summary": "Bug summary here",
  "issueType": "Bug",
  "environment": "PRD",
  "severity": "Sev 2",
  "url": "https://pennymac.atlassian.net/browse/PROJ-123"
}
```

## Error Handling

Errors are surfaced as returned by the `create-jira-issues` skill:

- `ConnectionError` (`CONNECTION_FAILED`)
- `CreationError` (`CREATION_FAILED`)
- `FieldValidationError` (`FIELD_VALIDATION_FAILED`) -- common for invalid `environment`, `severity`, `testPhase`, or `responsibleTeam` values; verify against the skill's `jira-field-mappings` reference
- `UserCancelled` (`USER_CANCELLED`)
- `ConfigInvalidError` (`CONFIG_INVALID`) -- `.ai/jira.config.json` failed schema validation; run `@./.cursor\skills\verify-jira-config\SKILL.md` to inspect the drift
- `BootstrapFailedError` (`BOOTSTRAP_FAILED`) -- `configure-jira` reported success but the freshly-written config could not be re-loaded
- `ProjectNotInConfigError` (`PROJECT_NOT_IN_CONFIG`) -- the resolved project key has no entry in `config.projects` and the user declined to bootstrap it
- `DefaultProjectKeyMissingError` (`DEFAULT_PROJECT_KEY_MISSING`) -- neither `projectKey` parameter nor `config.defaultProjectKey` is set

```json
{ "code": "FIELD_VALIDATION_FAILED", "message": "Invalid severity value", "field": "severity", "details": "Must be one of: Sev 1, Sev 2, Sev 3, TBD" }
```

