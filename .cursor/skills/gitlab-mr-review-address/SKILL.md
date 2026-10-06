---
name: gitlab-mr-review-address
description: Retrieve, track, and systematically address GitLab merge request review comments. Persists progress via the review-tracker TypeScript CLI under .ai/gitlab/review/{branch}-{mr_iid}/ — never edit tracking JSON by hand. Use when the user wants to address MR feedback, respond to review comments, or resolve reviewer suggestions.
promp:
  package: "gitlab"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "mr-review-address"
---

# MR Review Address

Systematically retrieve, evaluate, and address every review comment on a GitLab merge request. Progress is stored locally under `.ai/gitlab/review/` using **only** the `review-tracker.ts` CLI — **do not** read, write, or edit any tracking JSON files directly.

## Prerequisites

- A working **GitLab backend** with write access — either the GitLab MCP server (`GITLAB_READ_ONLY_MODE=false`, `api`-scoped token in `.env`) **or** an authenticated `glab` CLI (`api`-scoped token). See the `gitlab-backend` skill.
- The working directory must be a Git repository with a GitLab remote
- Node.js available; run the tracker with `npx tsx` from the repo root (or any cwd — paths below are relative to cwd)

## GitLab Backend

Before Phase 1, resolve the backend via the `gitlab-backend` skill (or use the `backend` value passed in by the caller): `"mcp"` (preferred) or `"glab"` (fallback). Every GitLab call below has both forms — pick the one for the resolved backend using the `gitlab-backend` **Operation Map**:

| This skill needs to… | MCP | glab |
|---|---|---|
| Find the open MR for a branch | `list_merge_requests` (`state=opened`, `source_branch=...`) | `glab mr list --source-branch <branch> --state opened` |
| List all discussions on the MR | `list_merge_request_discussions` | `glab api "projects/<id>/merge_requests/<iid>/discussions?per_page=100"` |
| Reply to a discussion thread | `create_merge_request_discussion_note` | `glab api -X POST "projects/<id>/merge_requests/<iid>/discussions/<discussion_id>/notes" -f body="..."` |
| Add a general MR note | `create_merge_request_note` | `glab mr note <iid> -m "..."` |

If neither backend is available, **stop** and return a `BackendUnavailableError` (run `/gitlab.setup`). The local `review-tracker.ts` CLI is backend-independent and used identically in both modes.

## Tracker CLI

**Path (use `{packageRoot}` as the directory containing this package’s `promp.json`, e.g. `.ai/packages/gitlab` after install):**

```text
npx tsx {packageRoot}/skills/mr-review-address/scripts/review-tracker.ts
```

**Review session directory:** After Phase 1, you know `sanitized_branch` and `mr_iid`. Define:

```text
{reviewRoot} = .ai/gitlab/review/{sanitized_branch}-{mr_iid}/
```

Run all tracker commands with **current working directory = repository root** so `{reviewRoot}` resolves correctly.

See **Scripts Reference** at the end for every subcommand, stdin shapes, and stdout.

---

## Instructions

Follow these phases **in order**. Do not skip phases or proceed to the next until the current one is fully complete.

---

### Phase 1: Resolve MR Identity

Determine which merge request to work with.

1. If `mr_iid` is provided, use it directly (still resolve `source_branch` from the MR via MCP if needed)
2. If not provided, detect the current branch with `git rev-parse --abbrev-ref HEAD` and look up the open MR for that branch (via the resolved backend):
   - Resolve the project ID from `git remote get-url origin` (parse `namespace/project` from the URL)
   - MCP: call `list_merge_requests` with `state=opened` and `source_branch={current_branch}`. glab: `glab mr list --source-branch {current_branch} --state opened`
   - If multiple MRs exist, pick the one targeting the repository default branch
3. If no MR is found, **stop and report** — there is no MR to review

Store the resolved `project_id`, `mr_iid`, and `source_branch` for all subsequent steps. Derive the **review directory name**:

```text
{sanitized_branch}-{mr_iid}
```

Sanitize the branch name by replacing `/` with `-` (e.g., `feature/dev/add-logging` → `feature-dev-add-logging`). The session path is:

```text
{reviewRoot} = .ai/gitlab/review/{sanitized_branch}-{mr_iid}/
```

---

### Phase 2: Fetch All Review Comments

Retrieve every discussion thread on the MR (via the resolved backend).

1. List all discussions for the project ID and MR IID — MCP: `list_merge_request_discussions`; glab: `glab api "projects/<id>/merge_requests/<iid>/discussions?per_page=100"`
2. For each discussion, extract:
   - `discussion_id` — the thread identifier
   - `note_id` — the individual note identifier
   - `author` — who wrote the comment
   - `body` — the comment text
   - `resolved` — whether the thread is already resolved
   - `position` (if present) — file path, old/new line numbers, diff ref
   - `created_at` — timestamp
3. Filter out:
   - System-generated notes (status changes, label additions, etc.)
   - Notes authored by the current user (your own comments)
   - Already-resolved threads (unless `includeResolved` is true)
4. Group the remaining comments by file path (use `"general"` for comments not attached to a specific file/line) for your own reasoning — tracking files are created in Phase 3 via the CLI only.

---

### Phase 3: Initialize Tracking Metadata

**Do not create or edit JSON files manually.** Initialize tracking with the tracker:

1. Build an **InitPayload** JSON object with:
   - `project_id`, `mr_iid`, `mr_url` (web URL of the MR), `branch` (exact source branch string from Git / MR)
   - `comments`: array of objects, each with at least `discussion_id`, `author`, `body`, and optionally `note_id`, `file`, `old_line`, `new_line`, `code_context`, `resolved_on_gitlab`

2. From the repository root, pipe the JSON to stdin:

```bash
echo '<InitPayload JSON>' | npx tsx {packageRoot}/skills/mr-review-address/scripts/review-tracker.ts init
```

3. Read stdout. It confirms the session path and prints `--- review-state ---` followed by JSON. **Capture `{reviewRoot}`** from the line `reviewRoot (use for other commands): <absolute or relative path>` or construct it as `.ai/gitlab/review/{sanitized_branch}-{mr_iid}/`.

If a previous run left a directory at the same `{reviewRoot}`, the tracker **archives** it to `{reviewRoot}-previous-<timestamp>` before writing fresh state.

---

### Phase 4: Address Each Comment

Process every pending comment one at a time.

#### Step 4a: Get the next comment (tracker)

```bash
npx tsx {packageRoot}/skills/mr-review-address/scripts/review-tracker.ts get-pending {reviewRoot}
```

Stdout includes `--- pending ---` and JSON `{ "pending": <comment> | null }`. If `pending` is `null`, skip to Phase 5 (or run `status` to confirm).

#### Step 4b: Read the relevant code

- If the comment references a file and line, read that region of the file in the repo (at least 20 lines of context)
- If the comment includes a code suggestion, capture the suggested change

#### Step 4c: Evaluate the comment

| Category | Condition |
|---|---|
| **Reviewer is correct** | The suggestion fixes a real bug, improves quality, or aligns with project standards |
| **Better alternative exists** | The reviewer identified a real issue, but a different fix is superior |
| **Current code is correct** | The existing implementation is intentional and the concern is explained by context |

#### Step 4d: Take action and record via tracker (no manual JSON edits)

**If the reviewer is correct — implement their suggestion:**

1. Apply the change in the codebase
2. Pipe an **AddressPayload** to the tracker (stdin JSON):

```json
{
  "disposition": "agree_implemented",
  "response": "<text you will post on GitLab>",
  "changes_made": "<brief file:line summary or null>"
}
```

```bash
echo '<AddressPayload JSON>' | npx tsx {packageRoot}/skills/mr-review-address/scripts/review-tracker.ts address-comment {reviewRoot} <discussion_id>
```

3. Reply on the GitLab discussion thread with the same `response` text (use `create_merge_request_discussion_note` or equivalent)

**If a better alternative exists:**

1. Implement the alternative
2. Use `address-comment` with `disposition`: `"better_alternative"` and fill `response` / `changes_made`
3. Reply on GitLab

**If the current code is correct:**

1. Do **not** change the code
2. Use `address-comment` with `disposition`: `"disagree_defended"`, `changes_made`: `null`
3. Reply on GitLab with the reasoning

**Edge cases (e.g. deleted file, N/A):** use `disposition`: `"not_applicable"` and explain in `response`.

Counters (`addressed` / `pending` in session state) are updated **inside** `address-comment` — do not edit `review-state.json` yourself.

#### Step 4e: Present progress

After each `address-comment`, stdout includes updated `review-state` and a progress line. Briefly report to the user: discussion id, disposition, action, remaining count (from stdout or `status`).

Repeat from Step 4a until `get-pending` returns `{ "pending": null }`.

---

### Phase 5: Final Verification

1. Run:

```bash
npx tsx {packageRoot}/skills/mr-review-address/scripts/review-tracker.ts check-all-addressed {reviewRoot}
```

- Exit code **0** means every comment has `status: "addressed"`. Stdout includes a `--- check ---` JSON block.
- Exit code **1** means some threads are still pending — return to Phase 4 for the listed `pendingDiscussionIds`.

2. When `check-all-addressed` succeeds, mark the session complete:

```bash
npx tsx {packageRoot}/skills/mr-review-address/scripts/review-tracker.ts complete {reviewRoot}
```

3. Run the project linter/type checker if available.

4. Present a final summary (MR URL, totals, disposition breakdown — you may use `status` or `list-comments` for a last look if helpful).

---

## Replying to GitLab Discussions

Use the form matching the resolved backend:

- **Inline/diff threads:**
  - MCP: `create_merge_request_discussion_note` using `discussion_id`
  - glab: `glab api -X POST "projects/<id>/merge_requests/<iid>/discussions/<discussion_id>/notes" -f body="<reply>"`
- **General MR notes:**
  - MCP: `create_merge_request_note` with MR IID
  - glab: `glab mr note <iid> -m "<reply>"`

Keep replies concise and professional.

---

## Resuming a Previous Session

1. Construct `{reviewRoot}` for the MR (same branch + `mr_iid` rule as Phase 1).

2. Load session state **only via the tracker**:

```bash
npx tsx {packageRoot}/skills/mr-review-address/scripts/review-tracker.ts get-state {reviewRoot}
```

3. If `status` in the printed JSON is `"in_progress"`, get the next pending comment:

```bash
npx tsx {packageRoot}/skills/mr-review-address/scripts/review-tracker.ts get-pending {reviewRoot}
```

4. Continue Phase 4 from Step 4b (or 4a if you prefer always calling `get-pending` first).

Do **not** open `review-state.json` or `comments/*.json` in the editor for edits — use the CLI only.

---

## Edge Cases

- **Deleted file:** `not_applicable` + reply on GitLab
- **Stale line / comment:** re-read current file; then address or defend
- **Question only:** explain in `response`; disposition often `disagree_defended` (context only)
- **Nitpick:** implement or defend; use the same `address-comment` flow
- **Multiple points in one thread:** one discussion thread → one tracked file; address all points in your GitLab reply and one `address-comment` for that `discussion_id`

---

## Scripts Reference

All commands: `npx tsx {packageRoot}/skills/mr-review-address/scripts/review-tracker.ts <command> ...`

Run `npx tsx .../review-tracker.ts --help` for a short built-in summary.

| Command | Arguments | Stdin | Stdout / behavior |
|---|---|---|---|
| `init` | none | **InitPayload** JSON | Creates `{reviewRoot}`, writes state + comment files; archives old dir if present. Prints paths and `review-state`. |
| `get-state` | `{reviewRoot}` | none | Prints `review-state` JSON. |
| `list-comments` | `{reviewRoot}` | none | Table of comments + progress line. |
| `get-comment` | `{reviewRoot}` `<discussion_id>` | none | One comment JSON. |
| `get-pending` | `{reviewRoot}` | none | `{ "pending": <comment object> \| null }`. |
| `address-comment` | `{reviewRoot}` `<discussion_id>` | **AddressPayload** JSON | Updates comment + counters; prints updated records. |
| `complete` | `{reviewRoot}` | none | Sets session `status` to `complete`. |
| `check-all-addressed` | `{reviewRoot}` | none | Prints check JSON; **exit 1** if any comment not addressed. |
| `status` | `{reviewRoot}` | none | Human-readable summary + disposition counts. |

**InitPayload (stdin for `init`):** `project_id`, `mr_iid`, `mr_url`, `branch`, `comments[]` with per-comment fields as in Phase 3.

**AddressPayload (stdin for `address-comment`):** `disposition` (`agree_implemented` \| `better_alternative` \| `disagree_defended` \| `not_applicable`), `response` (string), `changes_made` (string \| null).
