---
name: story-source-model
description: >-
  Where a story comes from and how it is identified: story-source detection (a
  local `[name].story.md` file path vs a Jira issue key, by shape), the
  `[name].story.md` naming convention, and recording a created/synced Jira issue
  key back into the story so future syncs update instead of re-creating. Use when
  resolving a story source before authoring or syncing, deciding whether a value
  is a file path or an issue key, or persisting the issue key after a first sync.
---

# Story Source Model

A story is identified by a single **story source** value that is either a local
story file or a tracker issue. This skill defines how to tell them apart, what a
local story file is named, and how to remember the Jira issue once one exists so
the story and issue stay linked across syncs.

## When to Use

- Resolving a story source before authoring (`createStory`), revising
  (`reviseStory`), or syncing (`syncStoryToJira`)
- Deciding whether a provided value is a filesystem path or a Jira issue key
- Recording the issue key back after a first-sync create

## Story Source: Local File or Jira Issue

A story can come from three places. Detect which by the **shape** of the provided
story-source value:

| Value shape | Example | Outcome |
|---|---|---|
| Absent | — | A new local `[name].story.md` is authored from the template. |
| Filesystem path | `./stories/auth.md`, `.ai/specs/auth/auth.story.md` | An existing local story file. Read it for content; sync diffs against it. |
| Jira issue key | `ABC-123`, `PROJ-4567` | The story already lives in Jira. Fetch it via the jira package; an issue already exists. |

**Detection heuristic:** an issue key matches an uppercase project key, a hyphen,
and digits (`^[A-Z][A-Z0-9]+-\d+$`) and contains no path separators or extension.
Anything containing `/`, `\`, `.`, or a file extension is a path. When ambiguous,
treat it as a path.

This is the single canonical heuristic — callers and the `story-jira-sync` skill
defer to it rather than re-deriving the rule.

## Story File Naming

| Rule | Detail |
|---|---|
| Suffix | A local story file is named `[name].story.md`, where `[name]` is the kebab-case unit-of-work name (e.g. `payment-retries.story.md`). |
| Findability | The `[name].` prefix makes the story `@`-mentionable alongside sibling artifacts (a spec's `[name].spec.md`, `[name].plan.md`). |
| Location | The story lives wherever its caller places it — commonly a spec directory under `.ai/specs/<name>/`, but the story package does not mandate a location; the caller supplies the path. |

## Recording the Key Back

After a first-sync create, the story must remember its issue so future syncs
**update** instead of creating a duplicate. Write the returned `issueKey` back:

- The story's **frontmatter** (e.g. a `jira:` key), and/or
- A **status table** the caller maintains (for a spec, the README status row /
  link).

A story whose source was a file path but has a recorded issue key syncs as an
update on the next run. Without the recorded key, the next sync would create a
duplicate issue.

When the story is part of a larger artifact set (e.g. a spec), the caller may
record the key in its own index in addition to the story frontmatter; the story
frontmatter is the minimum that keeps the story self-describing.

## Recording the Parent Epic

A story may belong under a parent **epic**. Record the parent in the story's
frontmatter (an `epic:` / `parent:` key) as **either** a relative
`[name].epic.md` path **or** the epic's Jira issue key (or both). This is the
local side of the link; the Jira side (the Epic Link / parent field) is pushed via
`{{skill:jira.*}}` `parentKey`. The detection, epic-file→issue-key resolution,
policies, and conflict surfacing live in the `story-epic-linking` skill — this
model only governs that the parent reference is recorded alongside the story's own
identity. The parent-epic value follows the **same shape heuristic** as a story
source: an issue key matches `^[A-Z][A-Z0-9]+-\d+$`; anything with `/`, `\`, `.`,
or a file extension is a path.

## External Stories and Local Generation

When the story source is a **Jira issue key** or a **path to an existing external
file**, do not generate a new local `[name].story.md` — the story already exists.
Reference it and read it for content. Generate a local story only when no source
is provided.

Callers that render conditional artifact links (for example a spec's templates
that gate on `{{#if storyPath}}`) use this same local-vs-external distinction:
the `{{else}}` branch links a local `./[name].story.md`; the `{{#if storyPath}}`
branch links the external file or Jira issue and notes the story is maintained
externally.
