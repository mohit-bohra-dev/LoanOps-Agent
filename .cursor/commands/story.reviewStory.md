---
promp:
  package: "story"
  version: "1.6.0"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  prompt: "reviewStory"
---
# story.reviewStory

Review a [name].story.md against the standard eight-dimension rubric, ground it with cross-review analysis via the arbor search package, write a review write-up under .ai/working/, and return the write-up path, an overall score, and a pass/fail verdict. Read-only — never edits the story

## Parameter Specifications

- **`storyPath`** (string) - **Required**
  - Path to the [name].story.md to review

- **`formatContract`** (string) - *Optional*
  - The format the story must conform to — a template path or an inline section-contract (e.g. a caller's story-format rule). When omitted, graded against the package default and story-authoring

- **`outputDir`** (string) - *Optional*
  - Where to write the review write-up. Default .ai/working/story-reviews
  - Default: `.ai/working/story-reviews`

- **`iteration`** (number) - *Optional*
  - The review pass number in a cycle (1, 2, ...), recorded in the write-up header
  - Default: `1`

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
   - Parameter 1: `storyPath` (required) - Path to the [name].story.md to review
   - Parameter 2: `formatContract` (optional) - The format the story must conform to — a template path or an inline section-contract (e.g. a caller's story-format rule). When omitted, graded against the package default and story-authoring
   - Parameter 3: `outputDir` (optional) [default: .ai/working/story-reviews] - Where to write the review write-up. Default .ai/working/story-reviews
   - Parameter 4: `iteration` (optional) [default: 1] - The review pass number in a cycle (1, 2, ...), recorded in the write-up header

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/story.reviewStory value1 value2`
- Named parameters: `/story.reviewStory param1=value1 param2=value2`
- Mixed format: `/story.reviewStory value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

The review verdict

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - 
- `reviewPath` (string) - **Required** - Path to the saved review write-up
- `score` (number) - **Required** - Overall score, 1.0-5.0 (mean of the eight dimensions)
- `verdict` (string) - **Required** - 
- `iteration` (number) - *Optional* - 
- `mustFixCount` (number) - *Optional* - Count of open CRITICAL + HIGH findings
- `summary` (string) - *Optional* - 
## Error Handling

### StoryNotFoundError

No readable story file exists at storyPath

**Properties:**

- `code` (string) (values: ["STORY_NOT_FOUND"]) - 
- `message` (string) - 
- `storyPath` (string) - 

## Prompt Content

# Review Story

Review a `[name].story.md` against the standard rubric, ground it with arbor cross-review analysis, and produce a written verdict — a saved review write-up plus an overall score and a pass/fail.

## Parameters

- **{{storyPath}}** (string, required): Path to the `[name].story.md` to review.
- **{{formatContract}}** (string, optional): The format the story must conform to — a template path or an inline section-contract (e.g. a caller's story-format rule). When omitted, the story is graded against the package's `story.md.template` and `story-authoring`.
- **{{outputDir}}** (string, optional): Where to write the review. Default `.ai/working/story-reviews`.
- **{{iteration}}** (number, optional): The review pass number in a cycle (1, 2, …), recorded in the write-up header. Default `1`.

## Instructions

Load **@./.cursor\skills\story-story-review\SKILL.md** and execute its Invocation Contract with these inputs:

| Parameter | Skill input |
|---|---|
| `{{storyPath}}` | `storyPath` |
| `{{formatContract}}` | `formatContract` |
| `{{outputDir}}` | `outputDir` |
| `{{iteration}}` | `iteration` |

The skill owns the eight-dimension rubric, the 1–5 scoring, the overall-score and pass/fail rules, the cross-review method (via **@./.cursor\skills\arbor-kb-search\SKILL.md**, best-effort), the write-up format, and the error catalogue. It grades against **@./.cursor\skills\story-story-authoring\SKILL.md** and the supplied `{{formatContract}}`.

This prompt performs the review inline. For an author → review → revise cycle in a fresh context, hand off to the **@./.cursor\agents\story-reviewer.md** agent instead — same rubric, same write-up.

## Response Format

```json
{
  "success": true,
  "reviewPath": ".ai/working/story-reviews/payment-retries.review.md",
  "score": 4.2,
  "verdict": "pass",
  "iteration": 1,
  "mustFixCount": 0,
  "summary": "The story is well-formed and independently testable; one MEDIUM polish item on edge-case coverage."
}
```

**Field descriptions:**

- `success`: Whether the review was produced.
- `reviewPath`: Path to the saved review write-up.
- `score`: Overall score, 1.0–5.0 (mean of the eight dimensions).
- `verdict`: `pass` or `fail` per the rubric's rule.
- `iteration`: The review pass number.
- `mustFixCount`: Count of open CRITICAL + HIGH findings (the must-fix set).
- `summary`: One-line verdict rationale.

## Error Handling

Return the error and stop. See `story-review` (Invocation Contract → Errors) for the full detail and recovery.

- **StoryNotFoundError** (`STORY_NOT_FOUND`) — no readable story file exists at `{{storyPath}}`; carries `storyPath`.

An unavailable arbor source is **not** an error — the review notes the limitation and grades cross-story coherence from sibling stories on disk.

## Notes

- **Review only — never edits the story.** The write-up is the deliverable; use `reviseStory` (or hand the `reviewPath` to the `story-author` subagent) to act on a fail.
- **Isolated handoff.** The `story-reviewer` agent is the fresh-context alternative to this prompt.

