# Revise Story

Apply a described change to an existing `[name].story.md`, keeping it consistent and technology-agnostic, then optionally offer a Jira re-sync.

## Parameters

- **{{storyPath}}** (string, required): Path to the existing `[name].story.md` to revise.
- **{{changes}}** (string, optional): Description of what is changing and why. If missing or unclear, ask the user before editing.
- **{{template}}** (string, optional): Path to a template file **or** an inline section-contract describing the story format to conform to (overrides the package default). Lets a caller keep its own format.
- **{{offerSync}}** (boolean, optional): Whether to offer a Jira re-sync after editing. Default `true`.

## Instructions

Load **{{skill:story-authoring}}** and execute its Invocation Contract with `mode: revise` and these inputs:

| Parameter | Skill input |
|---|---|
| — | `mode` = `revise` |
| `{{storyPath}}` | `storyPath` |
| `{{changes}}` | `changes` |
| `{{template}}` | `template` |
| `{{offerSync}}` | `offerSync` |

The skill owns the authoring standards, the numbered procedure, ID stability, the `[NEEDS CLARIFICATION]` convention, and the error catalogue. It loads **{{skill:story-source-model}}** for story-source detection and the recorded issue key, and offers **{{skill:story-jira-sync}}** for the re-sync.

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
