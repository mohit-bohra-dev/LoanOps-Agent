---
name: spec-artifact-model
description: >-
  The spec artifact model: the required file set under
  `.ai/specs/<featureName>/`, the `[featureName].X.md` naming convention,
  what each artifact is for and who reads it, the WHAT/WHY (story) vs HOW
  (spec) boundary, cross-link rules between artifacts, story-source detection
  (local file path vs Jira issue key), and how the spec templates map to
  artifacts. Use when creating, updating, executing, or reviewing any spec
  artifact, or when deciding which file holds which content or how artifacts
  reference each other.
---

# Spec Artifact Model

A spec is a directory of cooperating markdown files, not a single document. This skill defines the file set, the naming convention, what each file is for, how the files link to each other, and where the story comes from. Detailed authoring standards live in sibling skills — this skill defines the *shape*, not the prose inside each artifact.

## When to Use

- Creating a new spec, or adding/renaming artifacts in an existing one
- Deciding which artifact a piece of content belongs in
- Writing or fixing cross-references between spec files
- Resolving a story source (local file vs Jira issue) before generating a spec
- Filling the spec templates (see `references/template-index.md`)

## The Artifact Set

A spec lives in `.ai/specs/<featureName>/` and contains exactly these files:

| Artifact | Required | Role |
|---|---|---|
| `README.md` | Yes | Front door + navigation. **Absorbs the executive summary** — there is no separate summary file. |
| `[featureName].story.md` | Yes¹ | User stories and requirements — **WHAT and WHY**. |
| `[featureName].spec.md` | Yes | Technical design — **HOW**. |
| `[featureName].plan.md` | Yes | Cursor-format implementation plan with trackable todos. |
| `[featureName].review.md` | Optional | Implementation review output. Created by the review flow on first run; may not exist yet. |

¹ The local `[featureName].story.md` is **not** created when the story source is external (a Jira issue or an existing file elsewhere) — see [Story Source](#story-source-local-file-or-jira-issue).

There is **no `SUMMARY.md`**. The executive summary is a section inside `README.md`.

## Artifact Roles

| Artifact | Primary readers | Holds |
|---|---|---|
| `README.md` | Everyone — first file opened | Overview, executive summary (status/version/what-gets-built), document index linking the siblings, getting-started guidance. |
| `[featureName].story.md` | Product, stakeholders, reviewers | Prioritized user stories (P1/P2/P3), functional/non-functional requirements, success criteria, edge cases, out-of-scope. Technology-agnostic. |
| `[featureName].spec.md` | Architects, implementers | Architecture, data models, algorithms, API/function signatures, technical decisions, file structure, testing strategy. Code examples live here. |
| `[featureName].plan.md` | Implementers | Phased, todo-tracked execution plan in Cursor plan format. |
| `[featureName].review.md` | Implementers, reviewers | Requirement/test coverage, health score, findings; the scoped work source for a follow-up execution pass. |

### Story (WHAT/WHY) vs Spec (HOW)

Keep the two separate. The story states user-observable capability and value, technology-agnostic, with no code, schemas, or implementation detail. The spec states the mechanism — architecture, data, algorithms, code. If a passage names a database, an endpoint shape, or a library, it belongs in the spec, not the story.

This is the boundary at a glance. For the full spec-content authoring standards, load `technical-spec-authoring`; for the plan's YAML and todo conventions, load `spec-plan-format`. Story content (WHAT/WHY) is authored by the **story package** via `{{skill:story.story-authoring}}` (`mode: create` / `mode: revise`), which owns those standards — do not author story content from this skill alone.

## File Naming

| Rule | Detail |
|---|---|
| Feature-name prefix | Every artifact **except `README.md`** is prefixed with the kebab-case feature name: `[featureName].story.md`, `[featureName].spec.md`, `[featureName].plan.md`, `[featureName].review.md`. |
| README exception | `README.md` keeps its conventional name (it is the directory's front door). |
| No bare names | Never create `story.md` or `spec.md`. Always prefix. A bare name is wrong even though earlier conventions used it. |
| No summary file | Never create `SUMMARY.md`. The executive summary is a section in `README.md`. |
| Directory | The directory is `<featureName>` (kebab-case), under `.ai/specs/`. |

The prefix exists so artifacts are findable by `@`-mention in Cursor: typing `@my-feature.` surfaces every file for that spec. A bare `spec.md` collides across specs and defeats this.

**Legacy specs:** a spec created under an older convention may contain unprefixed `story.md`/`spec.md` or a `SUMMARY.md`. When working an existing spec, follow its files in place; do not silently rename. When *creating* a new spec, always use the prefixed names above.

## Cross-Link Rules

Artifacts reference each other with **relative links** so the spec is portable:

| From | Links to |
|---|---|
| `README.md` | All siblings: `./[featureName].story.md`, `./[featureName].spec.md`, `./[featureName].plan.md`, and `./[featureName].review.md` when present. |
| `[featureName].spec.md` | Back to the story for requirements context. |
| `[featureName].plan.md` | Back to the story (status table) and to `./[featureName].spec.md` (technical detail). |

Conventions:

- Use the relative form `./[featureName].story.md`, not absolute paths and not bare filenames.
- When the story source is external, the link target changes — see below.
- The link label can be human-readable; the target is the relative path: `[User Stories](./my-feature.story.md)`.

## Story Source: Local File or Jira Issue

A spec's story can come from three places. Detect which by the **shape** of the provided story-source value:

| Value shape | Example | Outcome |
|---|---|---|
| Absent | — | Generate a local `[featureName].story.md` from the story template. |
| Filesystem path | `./stories/auth.md`, `.ai/stories/auth.md` | External file. **Do not** create a local story. Reference the external file; read it for requirements context. |
| Jira issue key | `ABC-123`, `PROJ-4567` | Pull the story from Jira (via the jira package). **Do not** create a local story. Reference the issue; use its content for requirements context. |

**Detection heuristic:** an issue key matches an uppercase project key, a hyphen, and digits (e.g., `^[A-Z][A-Z0-9]+-\d+$`) and contains no path separators or extension. Anything containing `/`, `\`, `.`, or a file extension is a path. When ambiguous, treat it as a path.

This heuristic is the canonical property of the **story package** (`story-source-model`); the spec mirrors it only to render the story-link conditional below. The story package also owns recording the issue key back into the story after a first sync.

**Rendering the conditional.** The templates gate local vs external story rendering with `{{#if storyPath}} … {{else}} … {{/if}}`:

- **`{{else}}` (local):** link to `./[featureName].story.md`.
- **`{{#if storyPath}}` (external):** link to the external location instead — the relative path to the external file, or a link to the Jira issue — and note that the story is maintained externally. The spec, plan, and README all reference the external story rather than a local file.

This conditional must be preserved verbatim in the templates; it is the single switch that turns local story generation on or off.

## Worked Example

Feature `payment-retries`, with **no story source provided** (local story). The spec directory is `.ai/specs/payment-retries/` and contains:

```text
.ai/specs/payment-retries/
├── README.md                      (front door + executive summary)
├── payment-retries.story.md       (WHAT/WHY — generated locally)
├── payment-retries.spec.md        (HOW)
└── payment-retries.plan.md        (Cursor plan + todos)
```

`README.md` links its siblings with relative paths:

```markdown
- [User Stories](./payment-retries.story.md)
- [Technical Specification](./payment-retries.spec.md)
- [Implementation Plan](./payment-retries.plan.md)
```

Now the **same feature with story source `PAY-4821`** (a Jira issue key): no `payment-retries.story.md` is created. The story is pulled from Jira, and `README.md`/`spec.md`/`plan.md` link to the issue and note it is maintained externally — every other file and link stays the same.

## Filling the Templates

Each required artifact is rendered from a template in the package's `templates/` directory. The templates use Handlebars-style `{{placeholder}}` variables and the `{{#if storyPath}}` conditional above.

When generating or updating artifacts, read `references/template-index.md` for: the template→artifact map, the ordered section list for each template (so you fill every required section), and the placeholder-replacement conventions (Title Case vs kebab-case, dates, default version, leaving no `{{…}}` behind). Keep the templates themselves as the source of truth for exact structure.

## Invocation Contract

This skill is the entry point for two lifecycle operations on the artifact set. `mode` is
the distinguishing input and is **required**:

| `mode` | Operation |
|---|---|
| `create` | Scaffold a new spec directory and render its artifacts. |
| `update` | Edit an existing spec's artifacts from a description of changes. |

Both modes apply the naming, cross-link, and story-source rules defined above throughout.
Neither mode authors story *content* — that is the story package's.

### `mode: create`

**Inputs**

| Input | Type | Required | Meaning |
|---|---|---|---|
| `featureName` | string | yes (ask when absent) | Kebab-case feature name: lowercase letters, digits, and hyphens, starting with a letter. Names the directory and the `[featureName].*` artifacts. |
| `description` | string | yes (ask when absent) | One-line description of what the feature does and the problem it solves. |
| `storySource` | string | no | Story **file path** or Jira **issue key**, detected by shape per [Story Source](#story-source-local-file-or-jira-issue). Absent → a local story is generated. |
| `specDirectory` | string | no | Target directory. Defaults to `.ai/specs/<featureName>`. |

When `featureName` or `description` is missing, ask for it — keep that discussion on
WHAT/WHY (user value), not implementation detail.

**Procedure**

1. **Validate.** Confirm `featureName` is kebab-case; if not, return `INVALID_NAME` and
   stop. Resolve the target directory (`specDirectory`, else `.ai/specs/<featureName>`);
   if it already exists, return `SPEC_EXISTS` and stop. **Create no files until both
   checks pass.**
2. **Resolve the story source.** Determine `storyMode` per [Story Source](#story-source-local-file-or-jira-issue):
   - absent → `local`; a `[featureName].story.md` is generated in step 3.
   - Jira issue key → `external`; fetch the issue via `{{skill:jira.retrieve-jira}}`
     (`issueKey`). If it cannot be retrieved, return `STORY_NOT_FOUND` and stop.
   - file path → `external`; verify the file exists and read it. If it does not exist,
     return `STORY_NOT_FOUND` and stop.

   Carry forward `storyMode` and `storyContext` — the requirements basis the other
   artifacts are authored against.
3. **Create the directory and render the artifacts.**
   - When `storyMode = local`, **generate the story first** via
     `{{skill:story.story-authoring}}` (`mode: create`), passing `name: featureName`,
     `description`, `storyPath:` the target spec directory, and `offerSync: false` (step 4
     makes the offer). Never render a story template here — the story package owns the
     story template and its standards.
   - Render the remaining artifacts from `templates/` per `references/template-index.md`:
     `README.md.template` → `README.md`; `spec.md.template` → `[featureName].spec.md`,
     authored per `{{skill:technical-spec-authoring}}` against `storyContext`;
     `plan.md.template` → `[featureName].plan.md`, authored per `{{skill:spec-plan-format}}`.
   - Render the `{{#if storyPath}} … {{else}} … {{/if}}` conditional per `storyMode`, and
     leave **no** `{{…}}` markers behind.
4. **Offer a Jira sync (local story only).** When `storyMode = local`, offer
   `{{skill:spec-jira-sync}}` to create an issue from the new story. Present it as an
   option — never run it automatically, and never block the return on the answer. Skip
   entirely when `storyMode = external`.
5. **Return** the shape below, listing exactly the files created.

**Returns**

```json
{
  "success": true,
  "featureName": "package-version-cleanup",
  "specPath": ".ai/specs/package-version-cleanup",
  "storySource": null,
  "filesCreated": [
    ".ai/specs/package-version-cleanup/README.md",
    ".ai/specs/package-version-cleanup/package-version-cleanup.story.md",
    ".ai/specs/package-version-cleanup/package-version-cleanup.spec.md",
    ".ai/specs/package-version-cleanup/package-version-cleanup.plan.md"
  ]
}
```

`storySource` is the provided path/key, or `null` when a local story was generated.
`filesCreated` omits `[featureName].story.md` whenever `storySource` is set.

**Errors** — on any of these, stop immediately and return the structured error. Never
leave a partial spec behind reported as success.

| Code | When | Recovery to offer |
|---|---|---|
| `INVALID_NAME` | `featureName` has uppercase letters, spaces, or disallowed characters | Convert the name to kebab-case |
| `SPEC_EXISTS` | The target directory already exists | Choose another `featureName`, remove the outdated spec, or run `mode: update` |
| `STORY_NOT_FOUND` | `storySource` is a path that does not exist, or an issue key that cannot be retrieved | Correct the path/key, or omit `storySource` for a local story |

### `mode: update`

**Inputs**

| Input | Type | Required | Meaning |
|---|---|---|---|
| `featureName` | string | yes (ask when absent) | The spec to update; must match an existing directory under `.ai/specs/`. |
| `changes` | string | yes (ask when absent) | Description of the changes. May be high-level or detailed, and may describe several changes at once. |
| `artifact` | string | no | Restrict the update to one artifact: `story`, `spec`, `plan`, `readme`, or `all`. When omitted, the routing matrix derives the targets. |

When `featureName` is missing, ask which spec to update and list the directories under
`.ai/specs/` when they are available. When `changes` is missing or ambiguous, ask **what**
is changing and **why** before editing anything.

**Procedure**

1. **Locate the spec.** Resolve `.ai/specs/<featureName>`; if it does not exist, return
   `SPEC_NOT_FOUND` and stop. Detect the story source (local file, external file, or Jira
   issue key) and record it — when the story is external, never create or edit a local
   story file.
2. **Validate `artifact`** when provided; if it is not one of `story`, `spec`, `plan`,
   `readme`, `all`, return `INVALID_ARTIFACT` and stop.
3. **Route the change** to `targetArtifacts` using `references/change-routing-matrix.md`.
4. **Apply the updates** per the Edit Authorities table in that reference — story content
   via `{{skill:story.story-authoring}}` (`mode: revise`), spec via
   `{{skill:technical-spec-authoring}}`, plan via `{{skill:spec-plan-format}}`, README per
   this skill. Preserve existing content: add and amend rather than replace.
5. **Maintain cross-artifact consistency** using that reference's checklist — ripples,
   cross-links, contradictions, and requirement-ID integrity.
6. **Offer a Jira re-sync.** When the story changed and the spec is (or should be) linked
   to an issue, offer `{{skill:spec-jira-sync}}` so the issue reflects the new story.
   Surface it as a next step; never run it automatically.
7. **Return** the shape below, listing only the files actually changed.

**Returns**

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

`changesSummary` is one to two sentences on what changed and why.

**Errors**

| Code | When | Recovery to offer |
|---|---|---|
| `SPEC_NOT_FOUND` | No directory exists at `.ai/specs/<featureName>` | Check the feature name, or run `mode: create` for a new spec |
| `INVALID_ARTIFACT` | `artifact` is provided but not an allowed value (`summary` is not valid — there is no `SUMMARY.md`) | Pass an allowed value, or omit `artifact` and let the matrix decide |

## Reference Documents

- `references/template-index.md` — Read when generating or updating any spec artifact. Contains the template→artifact mapping, per-template section maps, and placeholder-replacement conventions.
- `references/change-routing-matrix.md` — Read when running `mode: update`. Contains the change→artifact routing matrix, the per-artifact edit authorities, content-preservation rules, and the cross-artifact consistency checklist.
