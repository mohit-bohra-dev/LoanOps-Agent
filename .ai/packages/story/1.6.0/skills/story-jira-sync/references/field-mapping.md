# Story ⇄ Jira Field Mapping

How `[name].story.md` content maps onto the three syncable Jira fields, how to
extract and normalize each one, and how the per-field diff decides what enters
the delta. The story layer does this extraction and comparison; the values are
then handed to `{{skill:jira.create-jira-issues}}` / `{{skill:jira.update-jira-issues}}`
with `profileName: Story`.

## The Mapping

| Jira field (jira skill input) | Story source | Notes |
|---|---|---|
| `summary` | Story title — the feature name / headline | One line. Strip leading `#` and surrounding whitespace. |
| `description` | The story narrative: user stories (P1/P2/P3), requirements (FR/NFR), success criteria, out-of-scope | Markdown body. Exclude the AC section (it has its own field) and any design/plan cross-link boilerplate. |
| `acceptanceCriteria` | The story's acceptance-criteria list | A list of discrete bullet items. Comma- or newline-separated when passed to the jira skill, which parses it into bullets. |

Only these three fields are story-owned content. `labels`, `projectKey`,
`transition`, `assignee`, and `parentKey` are operational inputs, not
story-derived content — pass them when the sync or lifecycle step needs them, not
as part of the content diff. `parentKey` (the parent **Epic** link) is owned by
the `story-epic-linking` skill: when the story records a parent epic, the sync
resolves it to the epic's issue key and rides it along on the `createStory` /
update call, but the parent is not part of the summary/description/AC diff.

## Extracting Each Field

### summary

Take the story's primary title. If the story uses a top-level `# Heading`, use
its text. Trim markdown markers and whitespace so the value is a clean single
line — Jira summaries are plain text, not markdown.

### description

Assemble the descriptive body from the story sections that describe WHAT/WHY:
the user stories, functional/non-functional requirements, success criteria, and
out-of-scope notes. Keep it markdown (the jira skill accepts markdown and handles
the markdown→ADF conversion).

Do **not** fold acceptance criteria into the description — AC has a dedicated
field and a dedicated merge mode. Duplicating AC into the description produces
drift between the two fields on the next sync.

### acceptanceCriteria

Collect the AC bullets as discrete items, one criterion per item. Normalize
before diffing:

- Strip list markers (`-`, `*`, `1.`), leading/trailing whitespace.
- Preserve the criterion text exactly otherwise — wording is the identity of a
  bullet for diff purposes.

Pass the items to the jira skill as a comma- or newline-separated list; jira's
acceptance-criteria handling builds the ADF.

## The Per-Field Diff

For each mapped field, compare the **local (parsed story)** value against the
**remote (retrieved baseline)** value and assign one verdict:

| Verdict | Condition | Enters delta? |
|---|---|---|
| `unchanged` | Local equals remote (after normalization) | No |
| `changed` | Local differs from remote; remote shows no independent edit | Yes — push local |
| `conflict` | Local differs **and** remote also changed away from the last-synced value | Yes, but **only after confirmation** — see `conflict-handling.md` |

Normalization before comparison avoids false deltas: trim whitespace, collapse
trailing newlines, and ignore pure markdown-rendering differences (e.g. `-` vs
`*` bullet markers) that Jira's ADF round-trip introduces.

### Acceptance-criteria diff (item-level)

AC is a **list**, so diff it item by item rather than as one blob:

| Item state | Meaning | Action |
|---|---|---|
| Added | In local, not in remote | New bullet — include in the AC delta |
| Unchanged | In both, same text | Leave as-is |
| Removed | In remote, not in local | The story dropped it |
| Edited | Same intent, different wording | Treat as a removed+added pair unless clearly a minor reword |

The item-level result drives the [merge-mode choice](#choosing-acmergemode).

## Choosing acMergeMode

The AC diff determines whether the sync should `append` or `replace`:

| AC diff result | `acMergeMode` | Why |
|---|---|---|
| Only **additions** (no removals/edits) | `append` | Add new bullets; preserve existing ones a teammate may have refined in Jira |
| Any **removal or edit** the story is authoritative for | `replace` | Append cannot delete or rewrite an existing bullet; replace makes the story's full list win |
| Routine sync, ambiguous | `append` | Safer default — never silently destroys Jira-side wording |

`append` is the story default because it is non-destructive. Reach for `replace`
only when a deletion or rewrite must propagate and the story owns the complete
AC list. Because `replace` overwrites the whole field, confirm with the user
when the removal would erase Jira-side bullets that are not in the local story
(this is a conflict — see `conflict-handling.md`).

## Putting It Together

A typical subsequent sync produces a delta object like:

```text
delta = {
  summary:            changed   → push new value
  description:        unchanged → omit from the update call
  acceptanceCriteria: +1 added  → push list with acMergeMode="append"
}
```

Translated to the call: `{{skill:jira.update-jira-issues}}` with
`profileName: Story`, `issueKey`, the new `summary`, the AC list, and
`acMergeMode="append"` — `description` is omitted because it did not change.
