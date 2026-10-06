# Change Routing Matrix

How a described change becomes a set of artifacts to edit, which authority owns each
edit, and what must stay consistent afterwards. Read this when running the
`mode: update` contract in the parent `SKILL.md`.

The matrix **routes**; the skills (and the story package) **author**. Deciding which
artifacts a change touches is this document's job; deciding what goes inside a section
belongs to the matching authority in [Edit Authorities](#edit-authorities).

## Deriving `targetArtifacts`

When the caller passed an `artifact` value, scope to it (`all` = every artifact) and skip
the matrix. Otherwise derive the target set from the nature of the change:

| Change type | Primary artifact | Ripples to |
|---|---|---|
| User stories, requirements, success criteria, edge cases, scope | `[featureName].story.md` | `README.md` (overview/summary); `[featureName].spec.md` if the mechanism changes |
| Architecture, data model, algorithm, API, technical decision | `[featureName].spec.md` | `[featureName].plan.md` (if approach/tasks change); `README.md` (architecture summary) |
| New feature or requirement (end-to-end) | `[featureName].story.md` + `[featureName].spec.md` + `[featureName].plan.md` | `README.md` |
| Implementation phases, tasks, or todo content | `[featureName].plan.md` | `README.md` (status) |
| Timeline or effort estimates | `[featureName].plan.md` (timeline + phase durations) | `README.md` (implementation overview/status) |
| Implementation progress (todo `status`) | `[featureName].plan.md` (todo status in frontmatter) | `README.md` (status when a phase completes) |
| Overview, status, navigation, or metadata | `README.md` | — |
| Correction or clarification | the artifact that owns the content | cross-references only |

A change may match more than one row — union the primary artifacts and their ripples.

## Edit Authorities

For each artifact in `targetArtifacts`, read it, edit in place, and follow its authority
for section-level decisions:

| Artifact | Authority | Notes |
|---|---|---|
| `[featureName].story.md` | `{{skill:story.story-authoring}}` (`mode: revise`) | **Local stories only.** Pass `storyPath` (the local story file), `changes` (the story-affecting change), and `offerSync: false`. The story package owns the WHAT/WHY standards. |
| `[featureName].spec.md` | `{{skill:technical-spec-authoring}}` | The HOW layer; the depth bar applies to every edited section. |
| `[featureName].plan.md` | `{{skill:spec-plan-format}}` | Edit todos and the matching body sections; **keep todo IDs stable**. |
| `README.md` | the parent `SKILL.md` | The README role: front door, navigation, and the absorbed executive summary. |

**External stories are edited at the source.** When the story source is an external file
or a Jira issue, do not create or edit a local story file — change the source, then
re-sync. Detect the source per the parent `SKILL.md` (Story Source).

## Preserving Existing Content

- Add and amend rather than wholesale replace.
- Never rename a legacy spec's files in place, and never recreate a removed `SUMMARY.md`.
- Keep the `{{#if storyPath}} … {{else}} … {{/if}}` rendering intact in any artifact that
  still carries it.

## Cross-Artifact Consistency

After editing, verify the artifacts still tell one story:

- [ ] Apply the ripples from the matrix — a story change flows into
      `[featureName].spec.md`, `[featureName].plan.md`, and `README.md`.
- [ ] Update cross-references and relative links per the parent `SKILL.md` cross-link rules.
- [ ] Confirm no contradictions across `README.md`, `[featureName].story.md`,
      `[featureName].spec.md`, and `[featureName].plan.md` — the same scope, the same file
      set, the same status.
- [ ] Confirm requirement IDs cited in the spec/plan still exist in the story after the edit.

An inconsistency found here is part of the same update — fix it before returning, rather
than reporting a partial success.

## Worked Example

**Change:** "Add a P2 user story for exponential backoff between retries, and reflect the
new backoff behavior in the design and plan." No `artifact` passed.

1. **Route** — the change matches the *user stories* row and the *architecture/algorithm*
   row: primaries `[featureName].story.md` and `[featureName].spec.md`; ripples pull in
   `[featureName].plan.md` and `README.md`. `targetArtifacts = { story, spec, plan, readme }`.
2. **Apply** — story via `{{skill:story.story-authoring}}` (`mode: revise`, `offerSync: false`);
   the backoff algorithm (pseudocode + complexity) via `{{skill:technical-spec-authoring}}`;
   a new `p4-*` todo group via `{{skill:spec-plan-format}}`; the README summary per the
   parent skill.
3. **Consistency** — the new `FR-` ID the story added is cited in the spec section that
   implements it, and the README's status line matches the plan's new phase count.
