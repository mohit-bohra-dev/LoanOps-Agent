# story

Author and review user stories, link them to a parent epic and to sibling dependencies, sync them to Jira, and drive their tracker lifecycle — workflow **state**, **assignment**, and **estimate**.

The `story` package owns everything about a `[name].story.md` (the WHAT/WHY of a unit of work) and its life in a tracker: authoring, review, linking to a parent epic and to sibling dependencies, delta-syncing to Jira, and driving the tracker lifecycle (state, assignment, estimate).

Two consumption surfaces, for two different callers:

| Caller | Surface | Why |
|---|---|---|
| A person, in chat | The `/story.*` slash commands | Each prompt is a thin entry point that loads the skill carrying the procedure. |
| Another package (e.g. `spec`, `nexus`) | The **skills**, referenced as `skill:story.<skill-name>` | `story` is normally installed as a *transitive* dependency, for which the promp CLI emits skills and agents but no command files. Each skill that backs a prompt publishes an **Invocation Contract** (Inputs / Returns / Errors) so a caller can invoke it without reading the prompt. |

## Why use this?

Stop hand-writing inconsistent stories and manually juggling their Jira issues. This package turns a one-line feature description into a well-formed, reviewed user story and keeps it in lockstep with the tracker — so your backlog stays trustworthy and your team spends time building, not bookkeeping.

- **Consistent, high-quality stories every time** — `createStory` and `reviseStory` enforce the same WHAT/WHY standards (prioritized P1/P2/P3 stories, stable FR/NFR/SC IDs, Given/When/Then acceptance criteria), so every story reads the same and nothing slips through as an unstated assumption.
- **Objective review instead of gut-feel sign-off** — `reviewStory` grades a story against an eight-dimension rubric, returns a numeric score and pass/fail verdict, and composes with the author into an automatic author → review → revise loop that raises quality before the work ever starts.
- **Never fights the tracker** — `syncStoryToJira` delta-syncs only the changed fields (create on first sync, update after) and surfaces Jira-side conflicts *before* overwriting, so a local edit never silently clobbers someone else's change.
- **The backlog reflects reality** — `transitionStory`, `assignStory`, and `pointStory` drive all three lifecycle dimensions (workflow state, who's actually doing the work, *and* the estimate a workflow may require), so status boards stay honest without manual clicking.
- **Epics stay connected** — `linkStoryToEpic` records the parent locally and pushes the Epic Link to Jira, with conflict surfacing before re-parenting, keeping rollup reporting intact.
- **Build order shows up on the board** — `linkStoryDependencies` pushes story-to-story dependencies to Jira as native `Blocks` links, so "this can't start until that ships" is visible in the tracker rather than living only in a planning doc.
- **Drops into your own workflows** — every skill publishes an invocation contract other packages can compose against, authoring is format-pluggable via `template`, and isolated-context agents let orchestrators like `nexus` batch-generate and review stories in a fresh context.

## Installation

```bash
promp install story
```

Installs the `jira` dependency (`^1.9.0`) for all Atlassian transport. Every Jira operation goes through a `{{skill:jira.*}}` entry point; this package never talks to Atlassian or the MCP directly. The `^1.9.0` floor adds the `storyPoints` field behind `pointStory`; `jira.link-jira-issues` (used by `linkStoryDependencies`) arrived in `^1.8.0` and the Story↔Epic `parentKey` link behind `linkStoryToEpic` in `^1.7.0`.

## Usage

Invoke prompts with the `/story.<promptName>` prefix. These slash commands exist only when `story` is a **direct** dependency of the consuming repo; when it is installed transitively, compose against the [skills](#skills) instead.

```bash
# Author a new story
/story.createStory name="payment-retries" description="Retry failed payments with exponential backoff"

# Revise an existing story
/story.reviseStory storyPath="./payment-retries.story.md" changes="Add a P2 backoff user story"

# Sync the story to Jira (create on first sync, delta-update after)
/story.syncStoryToJira storyPath="./payment-retries.story.md"

# Transition the story's Jira issue (state)
/story.transitionStory issueKey="PAY-512" status="In Development"

# Check/ensure the story's Jira assignment
/story.assignStory issueKey="PAY-512" policy="ensure-assigned" assignee="me"
/story.pointStory issueKey="PAY-512" points=5 policy="ensure-pointed"

# Link the story under a parent epic (local epic path or epic issue key)
/story.linkStoryToEpic storyPath="./payment-retries.story.md" parentEpic="AIP-100"

# Push story-to-story dependencies to Jira as Blocks links
/story.linkStoryDependencies dependencies='[{"story": "PAY-513", "dependsOn": "PAY-512"}]'
```

## What It Does

| Prompt | Role |
|--------|------|
| `createStory` | Author a new `[name].story.md` from a description; optional first Jira sync |
| `reviseStory` | Apply a described change to an existing story, preserving stable IDs |
| `syncStoryToJira` | Delta-sync the story to Jira (create or update); surface conflicts before overwriting |
| `transitionStory` | Move the story's Jira issue to a target workflow **status** (state) |
| `assignStory` | Check and ensure the story's Jira **assignment** (in addition to state) |
| `pointStory` | Check and ensure the story's Jira **story-point estimate** (persists a value; does not derive one) |
| `linkStoryToEpic` | Set/verify/clear the story's **parent epic** (local epic path or epic issue key); push the Epic Link to Jira |
| `linkStoryDependencies` | Push story-to-story **dependencies** to Jira as native `Blocks` issue links; idempotent, and reports stories that have no Jira issue yet rather than failing the batch |
| `reviewStory` | **Review** a story against the standard rubric with arbor cross-review; write a verdict to `.ai/working/` and return the review path, an overall score, and pass/fail (read-only) |

### The three lifecycle dimensions

A story's tracker lifecycle has three independent dimensions, all driven only through jira skills:

- **State** — the workflow status (`To Do` → `In Development` → `In Review` → `Done`), via `transitionStory`.
- **Assignment** — who the issue is assigned to, via `assignStory`. Assignment is checked **in addition to** state so the tracker reflects who is actually doing the work.
- **Estimate** — the story points the issue carries, via `pointStory`. Checked in addition to the other two because workflows commonly require an estimate before an issue may leave `Backlog`. `pointStory` persists a value; deciding it belongs to the nexus `/nexus.estimateStory` command.

A coordinator typically runs these together at the start of a run: ensure assignment, ensure the estimate, then transition state.

## Skills

| Name | Description |
|------|-------------|
| `story-authoring` | WHAT/WHY standards — P1/P2/P3 stories, FR/NFR/SC ids, Given/When/Then, technology-agnostic boundary |
| `story-jira-sync` | Delta sync (get → diff → push), AC merge mode (`append`/`replace`), conflict handling |
| `story-jira-lifecycle` | State transitions **and** assignment (verify / ensure-assigned / assign policies, conflict surfacing) |
| `story-source-model` | Story-source detection (file path vs issue key), `[name].story.md` naming, recording the issue key + parent epic reference |
| `story-epic-linking` | Parent-epic link — source detection (epic file vs issue key), epic-file→issue-key resolution, verify/ensure-linked/link policies, re-parent conflict surfacing. Covers the parent dimension only; sibling dependencies are `linkStoryDependencies` |
| `story-review` | Review methodology — the eight-dimension grading rubric, 1–5 scoring, overall-score + pass/fail rules, arbor cross-review analysis, and the standard write-up saved under `.ai/working/` |
| `story-dependency-linking` | Sibling-dependency link — the dependency-vs-parent distinction, the `dependsOn` blocks `story` direction rule, issue-key resolution, batching, and idempotency. Covers the dependency dimension only; the parent epic is `story-epic-linking` |

The skills are the package's **cross-package contract**. Each skill that backs a prompt carries an **Invocation Contract** section — an Inputs table, the Returns shape, and the Errors list — so another package can compose against it directly:

| Skill | Invoked by | Distinguishing input |
|---|---|---|
| `story-authoring` | `createStory`, `reviseStory` | `mode` = `create` \| `revise` |
| `story-review` | `reviewStory`, `story-reviewer` agent | — |
| `story-jira-sync` | `syncStoryToJira` | — |
| `story-jira-lifecycle` | `transitionStory`, `assignStory`, `pointStory` | `operation` = `transition` \| `assign` \| `point` |
| `story-epic-linking` | `linkStoryToEpic` | — |
| `story-dependency-linking` | `linkStoryDependencies` | — |

`story-source-model` carries no invocation contract — it is a shared model the other skills load, not an operation.

## Agents

| Name | Role |
|------|------|
| `story-author` | Authors a single `[name].story.md` (create or revise) in an **isolated context** using `story-authoring` — honors a caller-supplied format `template`, records the parent epic, and (in revise mode) can address a review write-up via `reviewPath`. Authoring only (no Jira). Returns a `success`/`questions`/`error` status. |
| `story-reviewer` | **Reviews** a single `[name].story.md` in an **isolated context** using `story-review` — grades the rubric, runs arbor cross-review, writes a verdict to `.ai/working/`, and returns the review path, an overall score, and pass/fail. Read-only w.r.t. the story. |

Both are delegation targets for callers that want authoring/review done in a fresh context (e.g. `nexus` batch generation or an author → review → revise cycle) rather than inline. Hand off with `{{agent:story.story-author}}` / `{{agent:story.story-reviewer}}`.

- **`story-author` contract** (`agents/story-author/AGENT.md`): inputs `mode`, `storyPath`, `name`, `description`/`changes`, `reviewPath` (revise-from-review), `template`, `parentEpic`, `context`; outputs the three-path status. Authoring only — Jira work remains the prompts' job.
- **`story-reviewer` contract** (`agents/story-reviewer/AGENT.md`): inputs `storyPath`, `formatContract`, `outputDir` (default `.ai/working/story-reviews`), `iteration`, `context`; outputs `reviewPath`, `score`, `verdict` (`pass`/`fail`), `mustFixCount`. It writes only the review write-up; it never edits the story.

### The author → review → revise cycle

`story-author` and `story-reviewer` compose into a review loop: author a story, review it, and — if the verdict is `fail` — hand the returned `reviewPath` back to `story-author` (`mode=revise`, `reviewPath=…`) so it addresses the review's **Required Changes**, then review again. `nexus`'s `create-story` runs this cycle; any orchestrator can too. The reviewer grounds cross-review analysis through the `arbor` search package (best-effort — it soft-fails when no sources are wired).

### Format-pluggable authoring

`createStory` and `reviseStory` accept an optional `template` parameter (a path to a template file or an inline section-contract). When supplied, authoring follows the caller's format instead of the package's default `story.md.template` — letting a caller such as `nexus` keep its own strict story format while reusing this package's authoring + Jira sync. When omitted, the package default is used.

## Templates

`templates/story.md.template` is the default rendered by `createStory`. Override it per-call with the `template` parameter.

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `jira` | `^1.9.0` | Story create/update/get, status transitions, **assignment**, **story points**, acceptance criteria, **parent-epic link**, **issue links** — via `{{skill:jira.*}}` |
| `arbor` | `^0.2.0` | **Cross-review analysis** during `reviewStory` — federated search across attached KBs and sources via `{{skill:arbor.kb-search}}` (best-effort; soft-fails when no sources are wired) |

The `^1.9.0` jira floor is required for the **storyPoints** field behind `pointStory`. It also covers the earlier floors this package depends on: `jira.link-jira-issues` for `linkStoryDependencies` (`1.8.0`), the Story↔Epic `parentKey` link behind `linkStoryToEpic` (`1.7.0`), and the **assignee** support `assignStory` uses (`1.5.0`). `arbor` powers the reviewer's cross-story coherence check.

## License

MIT

## Author

Pennymac AI Platform
