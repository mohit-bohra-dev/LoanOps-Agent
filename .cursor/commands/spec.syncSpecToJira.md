---
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "syncSpecToJira"
---
# spec.syncSpecToJira

Delta-sync a spec's story to its Jira issue — create on first sync, push only the changed fields on every sync after. Thin entry point that loads the spec-jira-sync skill, which delegates to the story package's story-jira-sync skill

## Parameter Specifications

- **`featureName`** (string) - *Optional*
  - The spec whose story to sync

- **`storySource`** (string) - *Optional*
  - Story file path OR Jira issue key (auto-detected). When an issue key, the existing issue is updated, never re-created

- **`projectKey`** (string) - *Optional*
  - Target Jira project for a first-sync create. When omitted, the jira config's default project is used

## Instructions

You are executing a Promp package prompt. Follow these steps:

0. **Resolve package location (required first tool call):** Run this shell command before any other tool and use the returned `packageDir` as the package root for every artifact path in this file:

```bash
promp ensure-package spec --json --project-path "D:\Users\v-mbohra\Documents\Projects\LoanOps-Agent"
```

- `packageDir` is the extracted package directory. Use it for every skill, prompt, or template path below.
- If `success` is `false` and no `packageDir` is returned, the package could not be found or installed. Run `promp install spec` or `promp install -g spec` and retry.
- Do **not** search other workspace roots for package files — always use the path returned by this command.

1. **Parse the user input** to extract parameters:
   - Parameter 1: `featureName` (optional) - The spec whose story to sync
   - Parameter 2: `storySource` (optional) - Story file path OR Jira issue key (auto-detected). When an issue key, the existing issue is updated, never re-created
   - Parameter 3: `projectKey` (optional) - Target Jira project for a first-sync create. When omitted, the jira config's default project is used

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/spec.syncSpecToJira value1 value2`
- Named parameters: `/spec.syncSpecToJira param1=value1 param2=value2`
- Mixed format: `/spec.syncSpecToJira value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of syncing the spec story to Jira

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the sync completed (including a clean no-op when nothing changed)
- `featureName` (string) - **Required** - The spec that was synced
- `issueKey` (string) - **Required** - The created or updated Jira issue key
- `fieldsChanged` (array) - **Required** - Fields actually pushed (summary, description, acceptanceCriteria, transition). Empty when the story already matched Jira
- `conflictReport` (unknown) - *Optional* - Object describing surfaced divergences and their resolution, or null when there were no conflicts
## Error Handling

### SpecNotFoundError

Error when the spec directory or story file cannot be located

**Properties:**

- `code` (string) (values: ["SPEC_NOT_FOUND"]) - 
- `message` (string) - 
- `featureName` (string) - 

### ConnectionError

Surfaced from the jira skills when the Atlassian MCP server is not connected or authenticated

**Properties:**

- `code` (string) (values: ["CONNECTION_FAILED"]) - 
- `message` (string) - 

### IssueNotFoundError

Surfaced from the jira skills when the issue key does not exist

**Properties:**

- `code` (string) (values: ["ISSUE_NOT_FOUND"]) - 
- `message` (string) - 
- `issueKey` (string) - 

## Prompt Content

# Sync Spec Story to Jira

Delta-sync a spec's story to its Jira issue — create on first sync, push only the changed fields on every sync after.

## Parameters

- **{{featureName}}** (string, optional): The spec whose story to sync.
  - Locates the spec at `.ai/specs/{{featureName}}/` and its `{{featureName}}.story.md`.
  - Example: `payment-retries`

- **{{storySource}}** (string, optional): The sync target — **either** a story file path **or** a Jira issue key, auto-detected by shape. When it is an issue key, the existing issue is **updated**, never re-created.
  - Examples: `PAY-512`, `./payment-retries.story.md`

- **{{projectKey}}** (string, optional): Target Jira project for a first-sync create. When omitted, the jira config's default project is used.

At least one of `featureName` or `storySource` is needed to locate the work. If neither is provided, ask the user which spec to sync before proceeding.

## Instructions

Load **@./.cursor\skills\spec-spec-jira-sync\SKILL.md** and execute its Invocation Contract with the inputs below. The skill owns story-file resolution, the delegation to **@./.cursor\skills\story-story-jira-sync\SKILL.md**, the result mapping, and the error relay — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| `{{featureName}}` | `featureName` | Locates `.ai/specs/{{featureName}}/{{featureName}}.story.md` |
| `{{storySource}}` | `storySource` | Passed through; the story package auto-detects path vs. issue key |
| `{{projectKey}}` | `projectKey` | Passed through for a first-sync create |

The delta-sync method, acceptance-criteria merge mode, conflict surfacing, and issue-key recording all live in the **story** package. Surface its permission prompts and conflict confirmations to the user as-is, and relay its errors verbatim.

## Response Format

```json
{
  "success": true,
  "featureName": "payment-retries",
  "issueKey": "PAY-512",
  "fieldsChanged": ["summary", "acceptanceCriteria"],
  "conflictReport": null
}
```

An empty `fieldsChanged` with `success: true` is a clean no-op sync — the story already matched Jira. `conflictReport` is `null` when there were no divergences.

## Error Handling

`SPEC_NOT_FOUND` is raised by this layer; every other code is relayed verbatim from the story package (which relays the jira skills). Conditions and recovery are in the skill's Errors table.

- **`SPEC_NOT_FOUND`** — the spec or its `[featureName].story.md` cannot be located, and no `storySource` resolves to syncable content.
- **`STORY_NOT_FOUND`** — the story file could not be located.
- **`CONNECTION_FAILED`** — the Atlassian MCP server is not connected or authenticated.
- **`ISSUE_NOT_FOUND`** — the issue key does not exist.
- **`CONFIG_INVALID`** / **`PROJECT_NOT_IN_CONFIG`** / **`DEFAULT_PROJECT_KEY_MISSING`** — jira config problems; point the user at `@./.cursor\skills\jira-configure-jira\SKILL.md` or `@./.cursor\skills\jira-verify-jira-config\SKILL.md`.

