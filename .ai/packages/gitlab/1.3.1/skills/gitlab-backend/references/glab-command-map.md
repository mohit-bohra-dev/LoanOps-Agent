# glab CLI Command Map

Concrete `glab` command syntax for every GitLab operation this package performs. Use this when `backend = "glab"` (see `../SKILL.md`).

General rules:
- `glab` uses the host and credentials from `glab auth login`. Run commands from inside the Git repo so the project is auto-detected, or pass `--repo <namespace/project>`.
- For operations without a dedicated subcommand, use `glab api <endpoint>` (REST) or `glab api graphql -f query=...` (GraphQL). `glab api` injects the authenticated host and token automatically.
- When passing a project path as a REST path segment (`projects/:id`), URL-encode the slashes: `cet/ai/promp` → `cet%2Fai%2Fpromp`. A numeric project ID needs no encoding.

---

## Project

### Get project / verify access / default branch

```bash
glab api projects/cet%2Fai%2Fpromp
```

**Output:** JSON with `id`, `path_with_namespace`, `default_branch`, `web_url`, `visibility`, `permissions`. A non-zero exit or `404`/`401` indicates the project is missing or the token lacks access.

---

## Pipelines & Jobs

### List pipelines (optionally by branch / status)

```bash
glab ci list --branch main --status failed --limit 20
```

**Output:** Table with pipeline ID, ref, status, and timestamps.

### Pipelines for a specific commit SHA (GraphQL)

```bash
glab api graphql -f query='
query {
  project(fullPath: "cet/ai/promp") {
    pipelines(sha: "<commit_sha>", first: 5) {
      nodes {
        id iid sha status
        detailedStatus { text label group }
        createdAt finishedAt duration ref
        jobs { nodes { name status stage { name } duration } }
      }
    }
  }
}'
```

This is the glab equivalent of the MCP `mcp_gitlab_execute_graphql` call. Output is the same GraphQL JSON.

Alternative (REST, by SHA without GraphQL):

```bash
glab api "projects/cet%2Fai%2Fpromp/pipelines?sha=<commit_sha>"
```

### View a pipeline and its job tree

```bash
glab ci view <pipeline_id>
```

**Output:** Pipeline status, ref, SHA, duration, and the full job tree with names, statuses, and durations.

### Retrieve a complete job log

```bash
glab ci trace <job_id>
# or by job name on the current pipeline:
glab ci trace <job_name>
```

**Output:** Full job log (stdout/stderr). This is the glab equivalent of `mcp_gitlab_get_pipeline_job_output`. Pipe through `tail`/`grep` for large logs. For pagination by exact endpoint, use:

```bash
glab api "projects/cet%2Fai%2Fpromp/jobs/<job_id>/trace"
```

---

## Merge Requests

### Create a merge request

```bash
glab mr create \
  --source-branch "<source_branch>" \
  --target-branch "<target_branch>" \
  --title "<title>" \
  --description "<markdown body>" \
  --yes
```

Flags:
- `--draft` — create as a draft MR.
- `--push` — push the source branch before creating (or push manually first with `git push -u origin <branch>`).
- `--yes` — skip interactive prompts (required for non-interactive use).
- `--repo <namespace/project>` — when not inside the repo.

**Output:** The created MR URL on the last line. Parse the IID from the URL (`.../-/merge_requests/<iid>`). If an MR already exists for the same source/target, glab exits non-zero with a message — treat as `MR_CREATION_FAILED`.

### List merge requests (find the MR for a branch)

```bash
glab mr list --source-branch "<branch>" --state opened
```

**Output:** Table with MR IID, title, author, branches, state. Use to resolve `mr_iid` from a branch.

### View a merge request

```bash
glab mr view <iid>
```

**Output:** Title, description, state, author, source/target branches, diff stats, approvals, web URL.

---

## MR Review Discussions

glab has no dedicated subcommand for threaded discussion replies, so use `glab api` against the REST discussions endpoints. `:id` is the URL-encoded project path, `:iid` is the MR IID.

### List all discussions on an MR

```bash
glab api "projects/cet%2Fai%2Fpromp/merge_requests/<iid>/discussions?per_page=100"
```

**Output:** JSON array of discussions. Each has `id` (discussion_id) and `notes[]` with `id` (note_id), `author`, `body`, `resolved`, `system`, `created_at`, and `position` (file/line for diff notes). Filter out `system: true` notes and notes authored by the current user, exactly as with the MCP form.

### Reply to a specific discussion thread (inline/diff thread)

```bash
glab api -X POST \
  "projects/cet%2Fai%2Fpromp/merge_requests/<iid>/discussions/<discussion_id>/notes" \
  -f body="<reply text>"
```

This is the glab equivalent of `create_merge_request_discussion_note`.

### Add a general note to an MR (not tied to a thread)

```bash
glab mr note <iid> -m "<note text>"
```

Equivalent to `create_merge_request_note`.

### Resolve a discussion thread (optional)

```bash
glab api -X PUT \
  "projects/cet%2Fai%2Fpromp/merge_requests/<iid>/discussions/<discussion_id>?resolved=true"
```

---

## Authentication & Diagnostics

```bash
glab auth status                          # confirm authenticated host + token scope
glab auth login --hostname gitlab.pnmac.com   # (re)authenticate
glab api user                             # whoami — confirms the token works
```

A `401`/`403` from any `glab api` call means the token is missing, expired, or lacks `api` scope. Surface this as an `AUTHENTICATION_FAILED` error with instructions to re-run `glab auth login`.
