# Review Story

Review a `[name].story.md` against the standard rubric, ground it with arbor cross-review analysis, and produce a written verdict — a saved review write-up plus an overall score and a pass/fail.

## Parameters

- **{{storyPath}}** (string, required): Path to the `[name].story.md` to review.
- **{{formatContract}}** (string, optional): The format the story must conform to — a template path or an inline section-contract (e.g. a caller's story-format rule). When omitted, the story is graded against the package's `story.md.template` and `story-authoring`.
- **{{outputDir}}** (string, optional): Where to write the review. Default `.ai/working/story-reviews`.
- **{{iteration}}** (number, optional): The review pass number in a cycle (1, 2, …), recorded in the write-up header. Default `1`.

## Instructions

Load **{{skill:story-review}}** and execute its Invocation Contract with these inputs:

| Parameter | Skill input |
|---|---|
| `{{storyPath}}` | `storyPath` |
| `{{formatContract}}` | `formatContract` |
| `{{outputDir}}` | `outputDir` |
| `{{iteration}}` | `iteration` |

The skill owns the eight-dimension rubric, the 1–5 scoring, the overall-score and pass/fail rules, the cross-review method (via **{{skill:arbor.kb-search}}**, best-effort), the write-up format, and the error catalogue. It grades against **{{skill:story-authoring}}** and the supplied `{{formatContract}}`.

This prompt performs the review inline. For an author → review → revise cycle in a fresh context, hand off to the **{{agent:story-reviewer}}** agent instead — same rubric, same write-up.

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
