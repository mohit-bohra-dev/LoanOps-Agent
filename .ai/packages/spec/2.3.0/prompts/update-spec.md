# Update Technical Specification

Update existing spec artifacts from a description of changes, routing each change to the artifacts it touches and keeping them consistent.

## Parameters

- **{{featureName}}** (string, optional): Name of the spec to update
  - Must match an existing spec directory under `.ai/specs/`
  - If omitted, ask the user (and list available specs when in a specs directory)
  - Example: "payment-retries"

- **{{changes}}** (string, optional): Description of the changes to make
  - May be high-level or detailed; may describe multiple changes
  - If omitted or unclear, ask what changed and why
  - Example: "Add a P2 story for retry backoff; update the retry algorithm and timeline"

- **{{artifact}}** (string, optional): Restrict the update to one artifact
  - One of: `story`, `spec`, `plan`, `readme`, `all`
  - `readme` is the merged `README.md` (overview + executive summary)
  - When omitted, the skill's routing matrix derives the affected artifacts
  - When `all`, every artifact needed to keep the spec consistent is updated

## Instructions

Load **{{skill:spec-artifact-model}}** and execute its Invocation Contract in `update` mode with the inputs below. The skill owns spec location, change routing, the per-artifact edit authorities, the cross-artifact consistency checks, the Jira re-sync offer, and the error catalogue — do not re-derive any of it here.

| Prompt parameter | Skill input | Notes |
|---|---|---|
| — | `mode` | `update` — the distinguishing input; this prompt is the update entry point |
| `{{featureName}}` | `featureName` | Ask the user when absent |
| `{{changes}}` | `changes` | Ask what changed and why when absent or ambiguous |
| `{{artifact}}` | `artifact` | Omit to let the routing matrix decide |

The skill routes each change to **{{skill:story.story-authoring}}** (`mode: revise`, local stories only), **{{skill:technical-spec-authoring}}**, **{{skill:spec-plan-format}}**, or its own README standards. Surface the skill's result as this prompt's output, and relay its errors verbatim.

## Response Format

```json
{
  "success": true,
  "featureName": "payment-retries",
  "filesUpdated": [
    ".ai/specs/payment-retries/payment-retries.story.md",
    ".ai/specs/payment-retries/payment-retries.spec.md"
  ],
  "changesSummary": "Added a P2 backoff story and the corresponding retry-backoff algorithm to the spec."
}
```

`filesUpdated` lists only the artifacts actually changed; `changesSummary` is one to two sentences on what changed and why.

## Error Handling

On any error, stop and return the structured error. Conditions and recovery are in the skill's Errors table.

- **`SPEC_NOT_FOUND`** — no directory exists at `.ai/specs/{{featureName}}`.
- **`INVALID_ARTIFACT`** — `artifact` is not one of `story`, `spec`, `plan`, `readme`, `all`.
