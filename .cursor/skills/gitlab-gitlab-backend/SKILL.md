---
name: gitlab-gitlab-backend
description: Resolve which GitLab backend to use (GitLab MCP server or the glab CLI) and map every GitLab operation in this package to the resolved backend. Use at the start of any GitLab operation (open MR, pipeline log retrieval, MR review) to detect availability, prefer MCP, fall back to glab, or stop with setup guidance when neither is available.
promp:
  package: "gitlab"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "gitlab-backend"
---

# GitLab Backend Resolution

Resolve which backend to use for GitLab operations, then route every operation through it. The package supports two backends:

1. **GitLab MCP server** (`gitlab`) — preferred when its tools are available.
2. **glab CLI** — fallback when the MCP server is not configured but `glab` is installed and authenticated.

If neither is available, stop and return setup guidance (see **Setup Guidance** below).

## Backend Resolution (run first, every time)

Run this resolution **before** any GitLab operation. The result is a single value: `backend = "mcp" | "glab"`, or a stop condition.

### Step 1: Check for the GitLab MCP server

- [ ] Determine whether the GitLab MCP tools are available in your current tool set (tools named `mcp_gitlab_*`, e.g. `mcp_gitlab_get_project`, or the equivalent `create_merge_request` / `list_merge_request_discussions` tools provided by the `gitlab` MCP server).
- [ ] If those tools are present, set `backend = "mcp"` and **stop resolving** — use MCP for all operations.

### Step 2: Check for the glab CLI

Only if the MCP server is **not** available:

- [ ] Run `command -v glab` to confirm the binary is installed.
- [ ] Run `glab auth status` to confirm it is authenticated to the GitLab host (`gitlab.pnmac.com`).
- [ ] If both succeed, set `backend = "glab"` — use glab for all operations.

### Step 3: Neither available — stop

If the MCP server is not available **and** glab is missing or unauthenticated:

- [ ] **IMMEDIATELY RETURN** a `BackendUnavailableError` (see **Setup Guidance**) and **do not proceed** with the operation.

```json
{
  "code": "BACKEND_UNAVAILABLE",
  "message": "No GitLab backend available. Configure the GitLab MCP server or install and authenticate the glab CLI.",
  "remediation": "Run /gitlab.setup to configure a backend, or see the setup steps below."
}
```

## Preference Order

- **MCP is preferred.** When the MCP server is available, use it even if glab is also installed. The MCP server exposes richer structured tools (GraphQL, complete job-log retrieval, discussion threading).
- **glab is the fallback.** Use it only when the MCP server cannot be found.

This matches the package contract: "if the MCP server cannot be found, use glab."

## Operation Map

Every GitLab operation this package performs has both an MCP form and a glab form. Use the row for your resolved `backend`. For glab, prefer the dedicated subcommand; use `glab api` (REST) or `glab api graphql` for operations without a dedicated subcommand. See `references/glab-command-map.md` for full syntax, flags, and output notes.

| Operation | MCP backend | glab backend |
|---|---|---|
| Get project / verify access / default branch | `mcp_gitlab_get_project` | `glab api projects/:id` (URL-encode the path) |
| Pipelines for a commit SHA | `mcp_gitlab_execute_graphql` (pipelines by `sha`) | `glab api graphql` with the same query, or `glab ci list` |
| Pipeline / job detail | `mcp_gitlab_execute_graphql` | `glab ci view <pipeline_id>` |
| Complete job log | `mcp_gitlab_get_pipeline_job_output` | `glab ci trace <job_id|job_name>` |
| Create merge request | `create_merge_request` | `glab mr create` |
| List merge requests (by branch/state) | `list_merge_requests` | `glab mr list` |
| View a merge request | `get_merge_request` | `glab mr view <iid>` |
| List MR discussions | `list_merge_request_discussions` | `glab api projects/:id/merge_requests/:iid/discussions` |
| Reply to a discussion thread | `create_merge_request_discussion_note` | `glab api -X POST projects/:id/merge_requests/:iid/discussions/:discussion_id/notes -f body=...` |
| Add a general MR note | `create_merge_request_note` | `glab mr note <iid> -m "..."` |

When the glab form for an operation is unclear, fall back to `glab api` against the corresponding GitLab REST endpoint — `glab api` automatically uses the authenticated host and token.

## Setup Guidance

When `backend` resolution stops (neither available), return guidance that offers two paths. Prefer pointing the user at the `/gitlab.setup` prompt, which automates this.

**Option A — GitLab MCP server (preferred):**
1. Create a GitLab Personal Access Token at `https://gitlab.pnmac.com/-/profile/personal_access_tokens` with `api` scope (`read_api` is sufficient for read-only pipeline retrieval).
2. Add `GITLAB_PERSONAL_ACCESS_TOKEN=<token>` to a `.env` file in your workspace root.
3. Ensure the `gitlab` MCP server is configured (it ships in this package's `promp.json`). Restart Cursor to load it.

**Option B — glab CLI (fallback):**
1. Install glab — macOS: `brew install glab`. Other platforms: see `https://gitlab.com/gitlab-org/cli/-/releases`.
2. Authenticate: `glab auth login --hostname gitlab.pnmac.com` and follow the prompts (paste a token with `api` scope).
3. Verify: `glab auth status` and `glab ci list`.

**Or run the automated setup:**

```text
/gitlab.setup
```

## Notes

- Resolution is per-operation, not cached: re-run it at the start of each prompt or skill phase that touches GitLab.
- Write operations (create MR, reply to discussions) require `api` scope on the token (not `read_api`). For MCP, `GITLAB_READ_ONLY_MODE` must be `false`.
- glab uses its own stored credentials from `glab auth login`; it does not read `GITLAB_PERSONAL_ACCESS_TOKEN` from `.env`.
