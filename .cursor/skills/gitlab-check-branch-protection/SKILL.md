---
name: gitlab-check-branch-protection
description: Determine whether the current user can push directly to a given branch (typically `main`) of a GitLab project, or whether changes must go through a merge request. Read-only. Use before pushing or publishing — e.g. in a createProject or arbor publish flow — to decide push-vs-MR.
promp:
  package: "gitlab"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.161"
  skill: "check-branch-protection"
---

# Check Branch Protection

Decide whether the current user can push directly to a branch (typically `main`) of a GitLab project, or whether changes must go through a merge request. This skill performs **only read operations** — it never modifies protection settings, never pushes, and never opens an MR. It returns a small structured result the caller uses to choose between pushing and opening an MR.

## Prerequisites

- A working **GitLab backend** — the GitLab MCP server (preferred) **or** an authenticated `glab` CLI. See the `gitlab-backend` skill. A **read-only** token (`read_api` scope) is sufficient because every operation here is read-only. For MCP, `GITLAB_READ_ONLY_MODE=true` is fine.
- For the `glab` fallback, run from inside the Git repo (or pass `--repo <namespace/project>`).

## Inputs

- **`project_id`** (required): numeric GitLab project id (e.g. `1234`) **or** the full project path (e.g. `cet/ai/promp`). For REST calls, URL-encode the slashes in a path (`cet/ai/promp` → `cet%2Fai%2Fpromp`). A numeric id needs no encoding.
- **`branch`** (optional): the branch to evaluate. Default `main`.

## Structured Result

Return exactly this object:

```json
{
  "branch": "main",
  "protected": true,
  "canPush": false,
  "recommendation": "open-mr",
  "reason": "main is protected; only Maintainer+ may push and the current user is a Developer."
}
```

- `recommendation` is `"push"` when `canPush` is `true`, otherwise `"open-mr"`.
- `reason` is a short, human-readable explanation of the decision.

## GitLab Backend

Before Phase 1, resolve the backend via the `gitlab-backend` skill (or use the `backend` value passed in by the caller): `"mcp"` (preferred) or `"glab"` (fallback). If neither is available, **stop** and return the exact `BackendUnavailableError`:

```json
{
  "code": "BACKEND_UNAVAILABLE",
  "message": "No GitLab backend available. Configure the GitLab MCP server or install and authenticate the glab CLI.",
  "remediation": "Run /gitlab.setup to configure a backend, or see the setup steps below."
}
```

The `gitlab-backend` **Operation Map** does not include protected-branch or current-user operations, so this skill documents the operations it needs inline. Pick the column for the resolved `backend`. For glab, use the dedicated subcommand where one exists, otherwise `glab api` (REST) — it injects the authenticated host and token automatically.

| This skill needs to… | MCP | glab |
|---|---|---|
| Get current user (identity + access) | the `get_current_user` tool if available, else fall back to `mcp_gitlab_execute_graphql` for `currentUser` | `glab api user` |
| Get project + caller's access level | `mcp_gitlab_get_project` | `glab api projects/<url-encoded-id>` (read `permissions.project_access.access_level` and `permissions.group_access.access_level`) |
| List protected branches | the `list_protected_branches` tool if available, else fall back to `mcp_gitlab_execute_graphql`/REST | `glab api "projects/<id>/protected_branches?per_page=100"` |
| Get a single protected branch | the `get_protected_branch` tool if available, else fall back to `mcp_gitlab_execute_graphql`/REST | `glab api "projects/<id>/protected_branches/<branch>"` |

## Instructions

Follow these phases **in order**. Do not skip a phase or proceed before the current one is complete.

### Phase 1: Resolve backend

Resolve the backend via the `gitlab-backend` skill (or the caller-supplied `backend`). If neither MCP nor glab is available, **immediately return** the `BackendUnavailableError` above and stop.

### Phase 2: Resolve project id

- Accept either a numeric id or a full path.
- For any REST (`glab api`) call, URL-encode slashes in a path: `cet/ai/promp` → `cet%2Fai%2Fpromp`. Numeric ids are used as-is.
- Confirm the project is reachable (the "Get project" operation). Map failures:
  - `404` / not reachable → return `ProjectNotFoundError` (see **Edge Cases**) and stop.
  - `401` / `403` → return `AuthenticationError` (see **Edge Cases**) and stop.

### Phase 3: Fetch protection state

1. List protected branches for the project ("List protected branches" operation). Optionally call "Get a single protected branch" for `branch` directly.
2. Determine whether `branch` matches a protected entry. **Account for wildcard entries** GitLab supports, such as `*` or `main*` — a wildcard `name` whose glob matches `branch` protects it. An exact `name` equal to `branch` also matches.
3. Set `protected`:
   - `protected = true` if any protected-branch entry (exact or wildcard) matches `branch`.
   - `protected = false` otherwise.

### Phase 4: Determine push capability

1. Get the current user and the caller's access level on the project. Read the access level from the project's `permissions.project_access.access_level`, falling back to `permissions.group_access.access_level` (take the higher of the two when both are present).

   **GitLab access-level constants** used below:

   | Level | Value |
   |---|---|
   | No one | `0` |
   | Guest | `10` |
   | Reporter | `20` |
   | Developer | `30` |
   | Maintainer | `40` |
   | Owner | `50` |

2. Decide `canPush`:
   - **If the branch is NOT protected:** `canPush = true` when the caller has at least **Developer** access (`access_level >= 30`); otherwise `false`. (Reporters/Guests cannot push to an unprotected branch.)
   - **If the branch IS protected:** inspect the matching protected branch's `push_access_levels` (and `allowed_to_push` where present). `canPush = true` only when **either**:
     - the caller's `access_level` meets or exceeds the **minimum** `access_level` in `push_access_levels` (e.g. Maintainer = `40`); a `push_access_levels` of `0` means **"No one"** → `canPush = false`; **or**
     - the caller is explicitly listed in `allowed_to_push` (by user id).

### Phase 5: Produce the structured result

- Set `recommendation = "push"` when `canPush` is `true`, else `recommendation = "open-mr"`.
- Write a concise `reason` naming the deciding factor (e.g. `"main is unprotected and the user is a Maintainer"`, or `"main is protected to Maintainer+; user is a Developer"`).
- Return the structured result object.

## Edge Cases

- **Protected with "No one" allowed to push** — `push_access_levels` minimum is `0`. Set `canPush = false`, `recommendation = "open-mr"`, and say so in `reason`.
- **Branch does not exist yet** (brand-new empty project / unborn default branch) — treat as **not-yet-protected**: decide `canPush` per the caller's access level (Developer+ → `true`) and note in `reason` that the branch may not exist yet.
- **Wildcard protected-branch rules** — a `*` or `main*` entry whose glob matches `branch` counts as protecting it; evaluate `push_access_levels` from the matching wildcard entry.
- **Insufficient token scope / `401` / `403`** — surface as an `AuthenticationError` and stop:

```json
{
  "code": "AUTHENTICATION_FAILED",
  "message": "GitLab rejected the request (401/403). The token is missing, expired, or lacks read_api scope.",
  "remediation": "Re-authenticate the backend: for MCP set a read_api-scoped GITLAB_PERSONAL_ACCESS_TOKEN in .env; for glab run glab auth login --hostname gitlab.pnmac.com. Or run /gitlab.setup."
}
```

- **Project not found / no access** — surface as a `ProjectNotFoundError` and stop:

```json
{
  "code": "PROJECT_NOT_FOUND",
  "message": "The project could not be found or is not accessible with the current token.",
  "remediation": "Verify the project_id (numeric id or full path) and that the token has access to it."
}
```

## Notes

- **Read-only.** This skill never changes branch protection and never pushes. It only reads project, user, and protected-branch state.
- **Resolution is per-invocation.** Re-run the backend resolution each time this skill runs — do not cache it across calls — matching the `gitlab-backend` skill's note.
- **`read_api` scope is sufficient.** No write scope is required because all operations are reads.
