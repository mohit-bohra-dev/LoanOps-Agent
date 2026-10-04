---
promp:
  package: "story"
  version: "1.6.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "createStory"
---
# story.createStory

Author a new [name].story.md (WHAT/WHY) from a feature description and optionally offer a first Jira sync

## Parameter Specifications

- **`name`** (string) - *Optional*
  - Kebab-case name for the unit of work (e.g. 'payment-retries'); names the [name].story.md file

- **`description`** (string) - *Optional*
  - One-line description of what the feature does and the problem it solves

- **`storyPath`** (string) - *Optional*
  - Where to write the story file. A directory (file created as <dir>/[name].story.md) or a full file path. Defaults to ./[name].story.md

- **`parentEpic`** (string) - *Optional*
  - Optional parent epic to link the story under — a local [name].epic.md path OR an epic Jira issue key. Recorded in the story and applied on first Jira sync (via jira.createStory parentKey).

- **`template`** (string) - *Optional*
  - Optional path to a template file OR an inline section-contract that overrides the package's default story.md.template. Lets a caller (e.g. nexus) supply its own story format while reusing this prompt's authoring + sync. When omitted, the package's default template is used.

- **`offerSync`** (boolean) - *Optional*
  - Whether to offer a first Jira sync after authoring (offered, never run automatically)
  - Default: `true`

## Instructions

You are executing a Promp package prompt. Follow these steps:

0. **Resolve package location (required first tool call):** Run this shell command before any other tool and use the returned `packageDir` as the package root for every artifact path in this file:

```bash
promp ensure-package story --json --project-path "D:\Users\v-mbohra\Documents\Projects\LoanOps-Agent"
```

- `packageDir` is the extracted package directory. Use it for every skill, prompt, or template path below.
- If `success` is `false` and no `packageDir` is returned, the package could not be found or installed. Run `promp install story` or `promp install -g story` and retry.
- Do **not** search other workspace roots for package files — always use the path returned by this command.

1. **Parse the user input** to extract parameters:
   - Parameter 1: `name` (optional) - Kebab-case name for the unit of work (e.g. 'payment-retries'); names the [name].story.md file
   - Parameter 2: `description` (optional) - One-line description of what the feature does and the problem it solves
   - Parameter 3: `storyPath` (optional) - Where to write the story file. A directory (file created as <dir>/[name].story.md) or a full file path. Defaults to ./[name].story.md
   - Parameter 4: `parentEpic` (optional) - Optional parent epic to link the story under — a local [name].epic.md path OR an epic Jira issue key. Recorded in the story and applied on first Jira sync (via jira.createStory parentKey).
   - Parameter 5: `template` (optional) - Optional path to a template file OR an inline section-contract that overrides the package's default story.md.template. Lets a caller (e.g. nexus) supply its own story format while reusing this prompt's authoring + sync. When omitted, the package's default template is used.
   - Parameter 6: `offerSync` (optional) [default: true] - Whether to offer a first Jira sync after authoring (offered, never run automatically)

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/story.createStory value1 value2`
- Named parameters: `/story.createStory param1=value1 param2=value2`
- Mixed format: `/story.createStory value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Details about the created story

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `name` (string) - **Required** - 
- `storyPath` (string) - **Required** - Path to the created story file
- `filesCreated` (array) - **Required** - 
## Error Handling

### InvalidNameError

The name is not kebab-case

**Properties:**

- `code` (string) (values: ["INVALID_NAME"]) - 
- `message` (string) - 
- `providedName` (string) - 

### StoryExistsError

A story file already exists at the resolved path

**Properties:**

- `code` (string) (values: ["STORY_EXISTS"]) - 
- `message` (string) - 
- `storyPath` (string) - 

## Prompt Content

# Create Story

Author a new `[name].story.md` — the WHAT/WHY of a unit of work — from a feature description, and optionally offer a first Jira sync.

## Parameters

- **{{name}}** (string, optional): Kebab-case name for the unit of work (e.g. `payment-retries`). Names the `[name].story.md` file. If not provided, ask the user.
- **{{description}}** (string, optional): One-line description of what the feature does and the problem it solves. If not provided, ask the user.
- **{{storyPath}}** (string, optional): Where to write the story file. May be a directory (the file is created as `<dir>/[name].story.md`) or a full file path. Defaults to `./[name].story.md`.
- **{{parentEpic}}** (string, optional): Parent epic to link the story under — a local `[name].epic.md` path **or** an epic Jira issue key. Recorded in the story and applied on first Jira sync.
- **{{template}}** (string, optional): Path to a template file **or** an inline section-contract that overrides the package's default `story.md.template`. Lets a caller (e.g. `nexus`) supply its own story format while reusing this package's authoring + sync. When omitted, the package default is used.
- **{{offerSync}}** (boolean, optional): Whether to offer a first Jira sync after authoring. Default `true`. Offered as an option — never run automatically.

## Instructions

Load **@./.cursor\skills\story-story-authoring\SKILL.md** and execute its Invocation Contract with `mode: create` and these inputs:

| Parameter | Skill input |
|---|---|
| — | `mode` = `create` |
| `{{name}}` | `name` |
| `{{description}}` | `description` |
| `{{storyPath}}` | `storyPath` |
| `{{parentEpic}}` | `parentEpic` |
| `{{template}}` | `template` |
| `{{offerSync}}` | `offerSync` |

The skill owns the authoring standards, the numbered procedure, and the error catalogue. It loads **@./.cursor\skills\story-story-source-model\SKILL.md** for path resolution and naming, **@./.cursor\skills\story-story-epic-linking\SKILL.md** when `{{parentEpic}}` is given, and offers **@./.cursor\skills\story-story-jira-sync\SKILL.md** for the first sync.

## Response Format

```json
{
  "success": true,
  "name": "payment-retries",
  "storyPath": "./payment-retries.story.md",
  "filesCreated": ["./payment-retries.story.md"]
}
```

**Field descriptions:**

- `success` (boolean): Whether the story was created.
- `name` (string): The kebab-case name.
- `storyPath` (string): Path to the created story file.
- `filesCreated` (array of string): Paths of the files created.

## Error Handling

Return the error and stop. See `story-authoring` (Invocation Contract → Errors) for the full detail and recovery.

- **InvalidNameError** (`INVALID_NAME`) — `{{name}}` is not kebab-case; carries `providedName`.
- **StoryExistsError** (`STORY_EXISTS`) — a story already exists at the resolved path; carries `storyPath`. Use `reviseStory` to edit it.

## Notes

- **Story is WHAT/WHY only.** Technical design belongs elsewhere; keep this file technology-agnostic per `story-authoring`.
- **Format is pluggable.** A caller can supply its own story format via `template`; the authoring judgment in `story-authoring` still applies.
- **Parent epic is recorded, pushed on sync.** When `parentEpic` is given it is recorded locally now and applied to Jira on the first sync. Use `linkStoryToEpic` to set/verify/clear the parent later.
- **Sync is offered, never automatic.** A first sync records the issue key back into the story so future syncs update instead of re-creating.

