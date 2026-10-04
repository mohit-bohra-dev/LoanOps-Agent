---
promp:
  package: "spec"
  version: "2.3.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "createSpec"
---
# spec.createSpec

Create a new spec directory and its skills-backed artifacts for a feature, optionally sourcing the story from a file or a Jira issue

## Parameter Specifications

- **`featureName`** (string) - *Optional*
  - Name of the feature in kebab-case (e.g., 'package-version-cleanup')

- **`description`** (string) - *Optional*
  - Brief description of what the feature does

- **`storySource`** (string) - *Optional*
  - Story file path OR Jira issue key (auto-detected). When provided, the spec references this external story instead of generating a local [featureName].story.md

- **`specDirectory`** (string) - *Optional*
  - Directory where spec should be created (defaults to .ai/specs/<featureName>)

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
   - Parameter 1: `featureName` (optional) - Name of the feature in kebab-case (e.g., 'package-version-cleanup')
   - Parameter 2: `description` (optional) - Brief description of what the feature does
   - Parameter 3: `storySource` (optional) - Story file path OR Jira issue key (auto-detected). When provided, the spec references this external story instead of generating a local [featureName].story.md
   - Parameter 4: `specDirectory` (optional) - Directory where spec should be created (defaults to .ai/specs/<featureName>)

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/spec.createSpec value1 value2`
- Named parameters: `/spec.createSpec param1=value1 param2=value2`
- Mixed format: `/spec.createSpec value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Details about the created specification

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the spec was created successfully
- `featureName` (string) - **Required** - Name of the feature
- `specPath` (string) - **Required** - Path to the spec directory
- `storySource` (string,null) - *Optional* - The external story path or Jira issue key, or null when a local story was generated
- `filesCreated` (array) - **Required** - List of files that were created
## Error Handling

### SpecExistsError

Error when a spec with the same name already exists

**Properties:**

- `code` (string) (values: ["SPEC_EXISTS"]) - 
- `message` (string) - 
- `existingSpecPath` (string) - 

### StoryNotFoundError

Error when the story source cannot be resolved (missing file or Jira issue)

**Properties:**

- `code` (string) (values: ["STORY_NOT_FOUND"]) - 
- `message` (string) - 
- `storySource` (string) - 

### InvalidNameError

Error when feature name is invalid

**Properties:**

- `code` (string) (values: ["INVALID_NAME"]) - 
- `message` (string) - 
- `providedName` (string) - 

## Prompt Content

# Create Technical Specification

Create a new spec directory and its skills-backed artifacts for a feature, optionally sourcing the story from a file or a Jira issue.

## Parameters

- **{{featureName}}** (string, optional): Feature name in kebab-case (e.g. `package-version-cleanup`).
  - Lowercase letters, digits, and hyphens only; must start with a letter.
  - Names the spec directory and the `[featureName].*` artifact files.
  - If not provided, ask the user for it.

- **{{description}}** (string, optional): One-line description of what the feature does and the problem it solves.
  - If not provided, ask the user for it.

- **{{storySource}}** (string, optional): Where the story comes from — a story **file path** OR a Jira **issue key**. Auto-detected by shape.
  - A value matching `^[A-Z][A-Z0-9]+-\d+$` (e.g. `ABC-123`) is a Jira issue key.
  - A value containing `/`, `\`, `.`, or a file extension is a file path. When ambiguous, treat it as a path.
  - When absent, a local `[featureName].story.md` is generated.

- **{{specDirectory}}** (string, optional): Directory for the spec.
  - Defaults to `.ai/specs/{{featureName}}`.

## Instructions

Load **@./.cursor\skills\spec-spec-artifact-model\SKILL.md** and execute its Invocation Contract in `create` mode with the inputs below. The skill owns validation, story-source resolution, template rendering, the Jira-sync offer, and the error catalogue — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| — | `mode` | `create` — the distinguishing input; this prompt is the create entry point |
| `{{featureName}}` | `featureName` | Ask the user when absent |
| `{{description}}` | `description` | Ask the user when absent |
| `{{storySource}}` | `storySource` | Omit for a local story |
| `{{specDirectory}}` | `specDirectory` | Defaults to `.ai/specs/{{featureName}}` |

The skill loads **@./.cursor\skills\spec-technical-spec-authoring\SKILL.md** and **@./.cursor\skills\spec-spec-plan-format\SKILL.md** for the spec and plan it renders, and delegates story content to **@./.cursor\skills\story-story-authoring\SKILL.md** (`mode: create`). Surface the skill's result as this prompt's output, and relay its errors verbatim.

## Response Format

```json
{
  "success": true,
  "featureName": "package-version-cleanup",
  "specPath": ".ai/specs/package-version-cleanup",
  "storySource": null,
  "filesCreated": [
    ".ai/specs/package-version-cleanup/README.md",
    ".ai/specs/package-version-cleanup/package-version-cleanup.story.md",
    ".ai/specs/package-version-cleanup/package-version-cleanup.spec.md",
    ".ai/specs/package-version-cleanup/package-version-cleanup.plan.md"
  ]
}
```

`storySource` is the provided path/key, or `null` when a local story was generated. `filesCreated` omits `[featureName].story.md` whenever `storySource` is set.

## Error Handling

On any error, stop and return the structured error — never leave a partial spec reported as success. Conditions and recovery are in the skill's Errors tables.

- **`INVALID_NAME`** — `featureName` is not kebab-case.
- **`SPEC_EXISTS`** — the target directory already exists.
- **`STORY_NOT_FOUND`** — `storySource` cannot be resolved.

