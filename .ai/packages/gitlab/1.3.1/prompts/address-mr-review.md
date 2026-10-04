# Address MR Review

Retrieve, evaluate, and systematically address all review comments on a GitLab merge request.

## Overview

This prompt kicks off the MR review addressing workflow. It delegates all logic to the `mr-review-address` skill, which handles fetching comments, **persisting progress only through the `review-tracker.ts` CLI** under `.ai/gitlab/review/{branch}-{mr_iid}/`, evaluating each comment, making code changes or defending the current implementation, and replying on GitLab. Each MR gets its own tracking subdirectory, so multiple reviews can be in progress simultaneously.

## Prerequisites

- A working **GitLab backend** with write access — either the GitLab MCP server (`GITLAB_READ_ONLY_MODE=false`, `api`-scoped token) **or** an authenticated `glab` CLI (`glab auth login` with an `api`-scoped token). Step 1 resolves this; if neither is available, run `/gitlab.setup`.
- Working directory is a Git repository with a GitLab remote
- An open merge request on the current branch (or provide `mr_iid` explicitly)

## Parameters

- **{{mr_iid}}** (number, optional): The merge request IID to address reviews for
  - If not provided, auto-detected from the current branch's open MR
- **{{project_id}}** (string, optional): GitLab project ID or full path (e.g., `cet/ai/promp`)
  - If not provided, auto-detected from the Git remote
- **{{includeResolved}}** (boolean, optional): Whether to re-process already-resolved threads
  - Default: false

## Instructions

### Step 0: Resolve GitLab Backend

Load the `gitlab-backend` skill (`skills/gitlab-backend/SKILL.md`) and run its **Backend Resolution** procedure. Set `backend` to `"mcp"` (preferred) or `"glab"` (fallback). The `mr-review-address` skill uses the **Operation Map** to choose MCP tools or `glab` commands for listing discussions and posting replies.

**CRITICAL STOP CONDITION**: If neither backend is available, **IMMEDIATELY RETURN** a `BackendUnavailableError` and **STOP**:
```json
{
  "code": "BACKEND_UNAVAILABLE",
  "message": "No GitLab backend available. Configure the GitLab MCP server or install and authenticate the glab CLI.",
  "remediation": "Run /gitlab.setup to configure a backend."
}
```

### Step 1: Load the Skill

Read the `mr-review-address` skill file and follow its instructions completely. The skill is the authoritative source for the full review workflow. Pass the resolved `backend` to the skill.

**Skill location:** `skills/mr-review-address/SKILL.md` (relative to this package)

### Step 2: Execute the Skill

Pass all provided parameters to the skill workflow:

- `mr_iid` → Phase 1 (MR identity resolution)
- `project_id` → Phase 1 (MR identity resolution)
- `includeResolved` → Phase 2 (comment filtering)

Follow every phase in the skill sequentially:

1. **Phase 1** — Resolve MR identity
2. **Phase 2** — Fetch all review comments
3. **Phase 3** — Initialize tracking metadata in `.ai/gitlab/review/{branch}-{mr_iid}/`
4. **Phase 4** — Address each comment (evaluate, implement/defend, reply on GitLab)
5. **Phase 5** — Final verification sweep

### Step 3: Return Results

After the skill completes, return the structured result.

## Response Format

### Success Response

```json
{
  "success": true,
  "mr_iid": 42,
  "mr_url": "https://gitlab.pnmac.com/cet/ai/promp/-/merge_requests/42",
  "total_comments": 8,
  "addressed": 8,
  "dispositions": {
    "agree_implemented": 3,
    "better_alternative": 2,
    "disagree_defended": 3
  },
  "files_modified": ["src/api/handler.ts", "src/utils/validator.ts"],
  "tracking_directory": ".ai/gitlab/review/feature-dev-add-logging-42/"
}
```

## Error Handling

### BackendUnavailableError

Returned when neither the GitLab MCP server nor an authenticated `glab` CLI is available.

```json
{
  "code": "BACKEND_UNAVAILABLE",
  "message": "No GitLab backend available. Configure the GitLab MCP server or install and authenticate the glab CLI.",
  "remediation": "Run /gitlab.setup to configure a backend."
}
```

### NoMRFoundError

Returned when no open merge request is found for the current branch.

```json
{
  "code": "NO_MR_FOUND",
  "message": "No open merge request found for branch 'feature/my-branch'. Create one first with /gitlab.openMR or provide mr_iid explicitly."
}
```

### NoCommentsError

Returned when the MR has no unresolved review comments.

```json
{
  "code": "NO_COMMENTS",
  "message": "No unresolved review comments found on MR !42. Nothing to address."
}
```

### AuthenticationError

Returned when GitLab authentication fails or token lacks write permissions.

```json
{
  "code": "AUTHENTICATION_FAILED",
  "message": "GitLab authentication failed or insufficient permissions",
  "tokenInstructions": "Ensure your token has 'api' scope and GITLAB_READ_ONLY_MODE is set to false."
}
```

## Examples

### Example 1: Address reviews on current branch's MR

**Scenario:** You're on branch `feature/add-logging` and a reviewer has left comments on your MR.

**Input:**

```json
{}
```

**Output:**

```json
{
  "success": true,
  "mr_iid": 42,
  "mr_url": "https://gitlab.pnmac.com/cet/ai/promp/-/merge_requests/42",
  "total_comments": 5,
  "addressed": 5,
  "dispositions": {
    "agree_implemented": 2,
    "better_alternative": 1,
    "disagree_defended": 2
  },
  "files_modified": ["src/api/handler.ts"],
  "tracking_directory": ".ai/gitlab/review/feature-add-logging-42/"
}
```

### Example 2: Address reviews on a specific MR

**Input:**

```json
{
  "mr_iid": 99,
  "project_id": "cet/ai/promp"
}
```

**Output:**

```json
{
  "success": true,
  "mr_iid": 99,
  "mr_url": "https://gitlab.pnmac.com/cet/ai/promp/-/merge_requests/99",
  "total_comments": 12,
  "addressed": 12,
  "dispositions": {
    "agree_implemented": 7,
    "better_alternative": 3,
    "disagree_defended": 2
  },
  "files_modified": ["src/service.ts", "src/config.ts", "tests/service.test.ts"],
  "tracking_directory": ".ai/gitlab/review/feature-dev-refactor-config-99/"
}
```

### Example 3: No MR found

**Input:**

```json
{}
```

**Error Output:**

```json
{
  "code": "NO_MR_FOUND",
  "message": "No open merge request found for branch 'main'. Create one first with /gitlab.openMR or provide mr_iid explicitly."
}
```

## Notes

- Review progress is tracked in `.ai/gitlab/review/{branch}-{mr_iid}/`. Add `.ai/gitlab/review/` to `.gitignore` to avoid committing tracking metadata. Multiple MRs can be tracked simultaneously in separate subdirectories.
- If the process is interrupted, re-running the command will resume from where it left off (pending comments are picked up automatically from the MR's subdirectory).
- The skill evaluates each comment independently — it does not batch changes. This ensures each reviewer comment gets a targeted response.
- After completion, you should commit the code changes and push to update the MR. The GitLab replies are posted immediately as each comment is addressed.

