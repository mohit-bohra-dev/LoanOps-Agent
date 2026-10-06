---
promp:
  package: "story"
  version: "1.6.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "reviseStory"
---
# story.reviseStory

Apply a described change to an existing [name].story.md in place, preserving stable IDs and the WHAT/WHY boundary, then optionally offer a Jira re-sync

## Parameter Specifications

- **`storyPath`** (string) - **Required**
  - Path to the existing [name].story.md to revise

- **`changes`** (string) - *Optional*
  - Description of what is changing and why

- **`template`** (string) - *Optional*
  - Optional path to a template file OR an inline section-contract describing the story format to conform to (overrides the package default). Lets a caller keep its own format.

- **`offerSync`** (boolean) - *Optional*
  - Whether to offer a Jira re-sync after editing
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
   - Parameter 1: `storyPath` (required) - Path to the existing [name].story.md to revise
   - Parameter 2: `changes` (optional) - Description of what is changing and why
   - Parameter 3: `template` (optional) - Optional path to a template file OR an inline section-contract describing the story format to conform to (overrides the package default). Lets a caller keep its own format.
   - Parameter 4: `offerSync` (optional) [default: true] - Whether to offer a Jira re-sync after editing

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/story.reviseStory value1 value2`
- Named parameters: `/story.reviseStory param1=value1 param2=value2`
- Mixed format: `/story.reviseStory value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Details about the story revision

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `storyPath` (string) - **Required** - 
- `changesSummary` (string) - *Optional* - 
## Error Handling

### StoryNotFoundError

No readable story file exists at storyPath

**Properties:**

- `code` (string) (values: ["STORY_NOT_FOUND"]) - 
- `message` (string) - 
- `storyPath` (string) - 

## Prompt Content

# Revise Story

Apply a described change to an existing `[name].story.md`, keeping it consistent and technology-agnostic, then optionally offer a Jira re-sync.

## Parameters

- **{{storyPath}}** (string, required): Path to the existing `[name].story.md` to revise.
- **{{changes}}** (string, optional): Description of what is changing and why. If missing or unclear, ask the user before editing.
- **{{template}}** (string, optional): Path to a template file **or** an inline section-contract describing the story format to conform to (overrides the package default). Lets a caller keep its own format.
- **{{offerSync}}** (boolean, optional): Whether to offer a Jira re-sync after editing. Default `true`.

## Instructions

Load **@./.cursor\skills\story-story-authoring\SKILL.md** and execute its Invocation Contract with `mode: revise` and these inputs:

| Parameter | Skill input |
|---|---|
| — | `mode` = `revise` |
| `{{storyPath}}` | `storyPath` |
| `{{changes}}` | `changes` |
| `{{template}}` | `template` |
| `{{offerSync}}` | `offerSync` |

The skill owns the authoring standards, the numbered procedure, ID stability, the `[NEEDS CLARIFICATION]` convention, and the error catalogue. It loads **@./.cursor\skills\story-story-source-model\SKILL.md** for story-source detection and the recorded issue key, and offers **@./.cursor\skills\story-story-jira-sync\SKILL.md** for the re-sync.

## Response Format

```json
{
  "success": true,
  "storyPath": "./payment-retries.story.md",
  "changesSummary": "Added a P2 backoff user story and SC-006; clarified the retry-limit edge case."
}
```

**Field descriptions:**

- `success` (boolean): Whether the revision was applied.
- `storyPath` (string): Path to the revised story file.
- `changesSummary` (string): One- to two-sentence summary of what changed and why.

## Error Handling

Return the error and stop. See `story-authoring` (Invocation Contract → Errors) for the full detail and recovery.

- **StoryNotFoundError** (`STORY_NOT_FOUND`) — no readable story file exists at `{{storyPath}}`; carries `storyPath`. Check the path, or use `createStory`.

## Notes

- **Edit, don't re-author.** Preserve existing content and stable IDs; this is the counterpart to `createStory`.
- **Re-sync is offered, never automatic.** The push surfaces Jira-side conflicts before overwriting.

