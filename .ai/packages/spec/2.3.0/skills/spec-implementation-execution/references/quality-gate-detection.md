# Quality-Gate Detection

How the spec-execution agent chooses and runs quality gates after implementing a
scoped unit. Read this before running gates. `<repo>` below is the path to the
repository being worked on.

**aidev is optional and runtime-detected.** Never assume `@pennymac/aidev` is
installed. Run the detection algorithm every time and act on whichever tier is
the first available. spec must work in repos that have never heard of aidev.

## Detection Algorithm (ordered)

Evaluate in this order and stop at the first tier that applies:

```text
1. PROJECT CONFIG:  test -f <repo>/.ai/project.json
                    AND it parses as JSON with version === 1
2. CLI RESOLVABLE:  command -v aidev
                    OR test -x <repo>/node_modules/.bin/aidev
                    OR npx @pennymac/aidev --version   (exit 0)
3. CONFIRM (opt.):  aidev workflow list -p <repo>      (exit 0 → CLI + config wired)
4. FALLBACK:        detect <repo>/package.json scripts (test, lint, typecheck, build)
5. SKIP:            no runnable gates → record a noted assumption in the deliverable
```

**`aidev_present` = (step 1 AND step 2).** Both the valid `.ai/project.json`
*and* a resolvable CLI must exist. Do **not** treat the presence of the `aidev`
promp package (rules/skills installed) as sufficient on its own — without the
CLI and `project.json`, gates cannot run via aidev.

Tier selection from the algorithm:

- `aidev_present` → **Tier 1** (aidev).
- not present, but `package.json` scripts exist → **Tier 2** (repo scripts).
- neither → **Tier 3** (skip-with-note).

Prefer the local `node_modules/.bin/aidev` over a global install when both
resolve — the global CLI can drift from the version the repo expects.

## Invocation Strategy

| Situation | aidev present | Action |
|-----------|---------------|--------|
| Inspect before running | Yes | `aidev workflow list -p <repo>` — log which steps will run |
| Run gates | Yes | `aidev workflow run -p <repo>` — single command; replaces any per-tool npm chain |
| A workflow step fails | Yes | Follow aidev triage (below): run the matching `aidev … find-*` command and load the matching skill, fix at the source, re-run |
| Bootstrap (CLI resolves, no `.ai/project.json`) | CLI only | Do **not** auto-init. Record a recommendation to run `/aidev.setupWorkflow` or `aidev init`; fall through to Tier 2 for this pass |
| aidev absent | No | Tier 2: run detected `package.json` scripts; record which ran and that aidev was unavailable |
| No gates runnable | — | Tier 3: skip with an explicit noted assumption; recommend `promp i aidev` + `/aidev.setupWorkflow` |

Prefer calling `aidev workflow run` directly over `npm run dev-workflow` — the
npm script is only a thin delegate and may be customized incorrectly.

The workflow runs its configured steps in a fixed order (duplication → lint →
format → typecheck → build → deadCode → audit → test → cdkNag → validate),
skips steps not configured in `.ai/project.json`, and is fail-fast (the first
non-zero step aborts).

## aidev Triage (Tier 1 failure handling)

Only when `aidev_present`. On a failed `aidev workflow run` step, load aidev's
own triage rule and the skill for the failing category — opportunistically,
because they exist only when aidev is installed:

- Load **`{{rule:aidev.workflowTriage}}`** for the failure → triage-command →
  skill mapping.
- Run the structured triage command for the failed step and load the matching
  skill:

| Failed step | Triage command | Skill |
|-------------|----------------|-------|
| duplication | `aidev code find-duplication --sort=priority` | `{{skill:aidev.code-duplication}}` |
| lint | `aidev code find-lint-issues --min-severity=error` | `{{skill:aidev.linting}}` |
| format | `aidev code find-format-issues` | `{{skill:aidev.code-formatting}}` |
| typecheck | `aidev code find-type-errors --groupBy=file` | `{{skill:aidev.typechecking}}` |
| build | `aidev code find-build-errors --emit-blocking-only` | `{{skill:aidev.typechecking}}` |
| deadCode | `aidev code find-dead-code --groupBy=file` | `{{skill:aidev.dead-code}}` |
| audit | `aidev dependencies audit --format=json` | `{{skill:aidev.dependency-audit}}` |
| test | `aidev tests find-failures --sort=duration` | `{{skill:aidev.test-debugging}}` |
| cdkNag / validate | parse the tool's stderr (no structured adapter) | — |

Do **not** reference aidev's readiness/onboarding prompts (`analyzeReadiness`,
`fillGaps`) during execution — they are not gate runners. The only aidev prompt
worth surfacing is `/aidev.setupWorkflow`, and only as the bootstrap suggestion
above.

If a gate failure cannot be fixed on-scope, it becomes a blocking question or an
error per the return contract — never a disabled check, a lowered threshold, or
a skipped test.

## Tier 2 — Repo `package.json` Scripts (fallback)

When aidev is absent, fall back to the repo's own scripts. Detect which of these
exist in `<repo>/package.json` `scripts` and run the available ones in
dependency order (do not assume a fixed set of names — use what the repo
defines):

| Concern | Common script names |
|---------|---------------------|
| tests | `test`, `test-coverage` |
| lint | `lint`, `lint:check` |
| typecheck | `type-check`, `typecheck`, `tsc` |
| build | `build` |

Order: tests/lint/typecheck before build is a reasonable default; adjust to the
repo's conventions. Run only scripts that exist; skipping an absent script is
expected. Fix failures at the source, then re-run. Record which scripts were
invoked and that aidev was not available.

This tier is the parameterized, repo-detected successor to the old hard-coded
`npm run test` / `lint:check` / `type-check` / `build` chain — the script names
are discovered, not assumed.

## Tier 3 — Skip With a Noted Assumption

When neither aidev nor usable `package.json` scripts are present, skip automated
gates and **record a noted assumption** in the deliverable: state that gates
were skipped because none were runnable, list what you checked, and recommend
establishing gates (`promp i aidev` + `/aidev.setupWorkflow`, or adding
`package.json` scripts). Skipping must be explicit and visible — never silent.
