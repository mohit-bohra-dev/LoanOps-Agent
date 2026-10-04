# GitLab CI/CD Prompts

AI-powered prompts and skills for GitLab CI/CD pipeline analysis, merge request automation, and MR review management. Works through a **dual backend**: the GitLab MCP server (preferred) or the `glab` CLI as a fallback.

## Why use this?

Chasing red pipelines through the GitLab UI and hand-managing merge requests breaks your flow and pulls you out of the editor. This package brings pipeline debugging and the full MR lifecycle into your assistant, working with whatever GitLab access you already have.

- **Debug failures without leaving your editor** — `pipelineLogRetrieval` pulls the latest commit's pipeline status and failed-job logs and analyzes them, so you skip the UI click-through hunt.
- **Open MRs in one command** — `openMR` creates a merge request from your branch with an auto-generated title and description, including a branch-protection check so you know when a direct push isn't allowed.
- **Systematically clear review comments** — `addressMRReview` retrieves every review comment, evaluates each, and works through them with local progress tracking so nothing gets missed.
- **Works with what you have** — a dual backend uses the GitLab MCP server when available and falls back to the authenticated `glab` CLI, with a preflight that routes you to `/gitlab.setup` if neither is configured.
- **Guided one-command setup** — `/gitlab.setup` detects, installs, and authenticates a backend for you, so you're not wrestling with tokens and scopes by hand.
- **Automates project creation** — `createProject` spins up a new GitLab repository in a target group and returns its IDs and URLs, ready to clone.

## Overview

This package provides prompts and skills for interacting with GitLab pipelines, CI/CD workflows, and merge requests. It includes tools for retrieving pipeline status, analyzing failed jobs, debugging deployment issues, creating merge requests, and systematically addressing MR review comments.

Every prompt runs a **backend-resolution preflight**: it uses the GitLab MCP server if available, otherwise falls back to an authenticated `glab` CLI. If neither is configured, it stops and points you to `/gitlab.setup`.

## Quick Start

Not sure what you have configured? Run:

```text
/gitlab.setup
```

This detects, installs (guided), and authenticates a backend for you. See [Backends](#backends) for details.

## Backends

| Backend | When used | Setup |
|---|---|---|
| GitLab MCP server | Preferred — used whenever its tools are available | `.env` token + `promp.json` (ships with this package), restart Cursor |
| `glab` CLI | Fallback — used when the MCP server is not configured | `brew install glab` + `glab auth login --hostname gitlab.pnmac.com` |

The detection logic and the full MCP→glab operation map live in the `gitlab-backend` skill (`skills/gitlab-backend/SKILL.md`).

## Prerequisites

You need **one** working backend (the MCP server *or* an authenticated `glab` CLI). `/gitlab.setup` configures either one. The sections below cover both.

### GitLab CLI (glab) — fallback backend

1. **Install glab:**
   ```bash
   # macOS
   brew install glab
   # Other platforms: https://gitlab.com/gitlab-org/cli/-/releases
   ```
2. **Authenticate** (paste a token with `api` scope when prompted):
   ```bash
   glab auth login --hostname gitlab.pnmac.com
   ```
3. **Verify:**
   ```bash
   glab auth status
   glab ci list
   ```

Note: `glab` stores its own credentials from `glab auth login` and does **not** read `GITLAB_PERSONAL_ACCESS_TOKEN` from `.env`.

### GitLab Personal Access Token (MCP backend)

The GitLab MCP backend authenticates with the GitLab API using a Personal Access Token in `.env`. Follow these steps to generate one (skip if you use the `glab` CLI backend):

1. **Navigate to GitLab Settings:**
   - Go to [https://gitlab.pnmac.com/-/profile/personal_access_tokens](https://gitlab.pnmac.com/-/profile/personal_access_tokens)
   - Or: Click your profile picture → **Preferences** → **Access Tokens** (left sidebar)

2. **Create a new token:**
   - **Token name**: `Cursor AI - GitLab MCP` (or any descriptive name)
   - **Expiration date**: Set according to your security policy (recommended: 90 days)
   - **Select scopes**:
     - ✅ `api` - Full API access (read/write)
     - OR
     - ✅ `read_api` - Read-only API access (if you only need to read pipeline data)

3. **Create the token:**
   - Click **Create personal access token**
   - **IMPORTANT**: Copy the token immediately - you won't be able to see it again!

4. **Add token to .env file:**
   - Create a `.env` file in the root of your project (if it doesn't exist)
   - Add the following line:
     ```bash
     GITLAB_PERSONAL_ACCESS_TOKEN=your_token_here
     ```
   - Replace `your_token_here` with your actual token

5. **Secure your .env file:**
   - **IMPORTANT**: Ensure `.env` is added to your `.gitignore` file to prevent committing sensitive tokens
   - Check if `.env` is already in `.gitignore`:
     ```bash
     grep "\.env" .gitignore
     ```
   - If not found, add it:
     ```bash
     echo ".env" >> .gitignore
     ```
   - Verify the file is ignored:
     ```bash
     git status --ignored
     ```

### Environment Configuration

The package uses a `.env` file at the project root for configuration. See the `.env.example` file for reference.

Required environment variable:
- `GITLAB_PERSONAL_ACCESS_TOKEN` - Your GitLab personal access token

### MCP Server

This package includes MCP (Model Context Protocol) server configuration for GitLab integration. The MCP server is automatically configured in the `promp.json` file and provides:

- Project information retrieval
- Pipeline status queries via GraphQL
- Job log retrieval
- Automatic authentication using environment variables

## Installation

```bash
promp install gitlab --save
```

Or manually copy this package to your `.ai/packages/` directory.

## Prompts

### `setup`

Detect, install, and authenticate a GitLab backend (MCP server or `glab` CLI). Guided — asks before any install or credential change.

**Command:**
```text
/gitlab.setup
```

**Usage:**

1. **Auto (detect and configure the fastest path):**
   ```text
   /gitlab.setup
   ```
2. **Set up a specific backend:**
   ```text
   /gitlab.setup backend=glab
   /gitlab.setup backend=mcp
   ```

**Parameters:**
- `backend` (string, optional): `mcp`, `glab`, or `auto` (default: `auto`)
- `hostname` (string, optional): GitLab host for glab auth (default: `gitlab.pnmac.com`)

**See:** [prompts/setup.md](./prompts/setup.md)

### Pipeline Log Retrieval

Retrieve and analyze GitLab pipeline status and job logs for debugging CI/CD failures.

**Command:**
```text
/gitlab.pipelineLogRetrieval
```

**Usage:**

1. **Auto-detect from current directory** (no parameters needed):
   ```text
   /gitlab.pipelineLogRetrieval
   ```
   - Automatically detects project from Git remote
   - Uses latest commit from current branch
   - Retrieves and displays pipeline status

2. **Explicit project ID:**
   ```text
   /gitlab.pipelineLogRetrieval project_id=13466
   ```

3. **With repository URL:**
   ```text
   /gitlab.pipelineLogRetrieval repo_url=git@gitlab.pnmac.com:cet/ai/promp.git
   ```

4. **Specific commit:**
   ```text
   /gitlab.pipelineLogRetrieval commit_sha=34f286db5be6bc7ba76cb5d41cb9250293844732
   ```

**Parameters:**
- `project_id` (string, optional): GitLab project ID or full path (e.g., "cet/ai/promp")
- `repo_name` (string, optional): Repository name to search for
- `repo_url` (string, optional): Full Git repository URL
- `commit_sha` (string, optional): Specific commit SHA to analyze
- `branch_name` (string, optional): Branch name to check
- `max_retries` (number, optional): Maximum API retry attempts (default: 3)

**Features:**
- ✅ Auto-detects project from Git repository
- ✅ Retrieves latest commit automatically
- ✅ Shows pipeline status and job breakdown
- ✅ Analyzes failed jobs with error summaries
- ✅ Provides direct URLs for investigation
- ✅ Handles network errors with retry logic
- ✅ Supports GraphQL queries for efficient data retrieval
- ✅ Retrieves complete job logs (not just summaries)

**Output:**

The prompt generates a comprehensive report including:
- Pipeline status (SUCCESS, FAILED, RUNNING, etc.)
- Commit information
- Job breakdown by status (successful, failed, skipped)
- Failed job analysis with error messages
- Direct links to pipeline and job logs
- Actionable next steps for debugging

**Example Output:**

```markdown
## Pipeline Status for Latest Commit

**Commit:** 34f286db5be6bc7ba76cb5d41cb9250293844732
**Message:** feat: add S3 bucket logging configuration
**Branch:** main
**Pipeline ID:** #4930910
**Status:** ❌ FAILED
**Duration:** 5m 32s
**Started:** 2026-02-02 10:15:23 PST
**Finished:** 2026-02-02 10:20:55 PST

### Pipeline Jobs Breakdown:

#### ✅ Successful Jobs:
1. **build** (build stage) - 45s
2. **test** (test stage) - 120s

#### ❌ Failed Jobs:
- **cdk-deploy** (deploy stage) - Failed after 187s

#### ⏭️ Skipped Jobs:
- **cleanup** (cleanup stage)

### Failed Job Analysis:

**Primary Failed Job:** cdk-deploy
**Stage:** deploy
**Duration:** 187s

**Error Summary:**
- CREATE_FAILED: PNMAC::S3BucketAccessLogging::Hook
- Resource handler returned message: "Hook failed..."
- Stack: PrompStack

**Job URL:** https://gitlab.pnmac.com/cet/ai/promp/-/jobs/56789

### Next Steps:
1. Review the complete logs at: https://gitlab.pnmac.com/cet/ai/promp/-/jobs/56789
2. Check if the failure is environment-specific
3. Review recent changes that might have caused the failure
4. Verify all required environment variables and secrets are configured
5. Check for any service dependencies that might be down

**Pipeline URL:** https://gitlab.pnmac.com/cet/ai/promp/-/pipelines/4930910
```

### `openMR`

Create a GitLab merge request from the current branch or a specified branch with auto-generated title and description.

**Command:**
```text
/gitlab.openMR
```

**Usage:**

1. **Create MR from current branch** (no parameters needed):
   ```text
   /gitlab.openMR
   ```
   - Auto-detects project from Git remote
   - Uses current branch as source
   - Auto-generates title and description from commits
   - Targets the repository's default branch

2. **Create MR from a specific branch:**
   ```text
   /gitlab.openMR branch=feature/new-ui
   ```

3. **Create a draft MR:**
   ```text
   /gitlab.openMR draft=true
   ```

4. **Create MR with custom title and target branch:**
   ```text
   /gitlab.openMR title="feat: add user authentication" targetBranch=develop
   ```

**Parameters:**
- `branch` (string, optional): Source branch with changes (default: current branch)
- `targetBranch` (string, optional): Branch to merge into (default: repository default branch)
- `title` (string, optional): MR title (auto-generated from commits if not provided)
- `description` (string, optional): MR description in markdown (auto-generated if not provided)
- `draft` (boolean, optional): Create as draft MR (default: false)
- `project_id` (string, optional): GitLab project ID or full path

**Features:**
- Auto-detects project from Git repository
- Auto-generates MR title from commit messages
- Auto-generates MR description with change summary
- Pushes branch to remote if not already pushed
- Supports draft merge requests
- Returns direct URL to the created MR

**Returns:** MR IID, URL, title, source/target branches, and draft status.

**Note:** Requires `api` scope on your GitLab token (not just `read_api`) and `GITLAB_READ_ONLY_MODE` set to `false`.

**See:** [prompts/open-mr.md](./prompts/open-mr.md)

### `addressMRReview`

Retrieve, evaluate, and systematically address all review comments on a GitLab merge request. Tracks progress locally in `.ai/gitlab/review/` so nothing is missed and interrupted sessions can be resumed.

**Command:**
```text
/gitlab.addressMRReview
```

**Usage:**

1. **Address reviews on current branch's MR** (no parameters needed):
   ```text
   /gitlab.addressMRReview
   ```
   - Auto-detects the open MR for the current branch
   - Fetches all unresolved review comments
   - Evaluates each comment and takes appropriate action
   - Replies on GitLab with the resolution

2. **Address reviews on a specific MR:**
   ```text
   /gitlab.addressMRReview mr_iid=42
   ```

3. **Include already-resolved threads:**
   ```text
   /gitlab.addressMRReview includeResolved=true
   ```

**Parameters:**
- `mr_iid` (number, optional): MR IID to address reviews for (default: auto-detected from current branch)
- `project_id` (string, optional): GitLab project ID or full path (default: auto-detected from Git remote)
- `includeResolved` (boolean, optional): Re-process already-resolved threads (default: false)

**How it works:**

For each review comment, the agent evaluates and takes one of three actions:

| Scenario | Action | GitLab Reply |
|---|---|---|
| Reviewer is correct | Implements the suggested change | Confirms the suggestion was applied |
| Better alternative exists | Implements a superior fix | Explains the alternative approach and why |
| Current code is correct | No code changes | Provides reasoning for why the code should stay |

**Progress tracking:**

Each MR gets its own subdirectory under `.ai/gitlab/review/`, named `{sanitized_branch}-{mr_iid}` (e.g., `feature-dev-add-logging-42`). State is written and read **only** via the TypeScript CLI `skills/mr-review-address/scripts/review-tracker.ts` (see the skill) — agents must not edit JSON files by hand. The tracker stores session state and per-discussion records under that directory.

Multiple MRs can be tracked simultaneously. If interrupted, re-running resumes using the same CLI (`get-state`, `get-pending`).

**Returns:** Summary with total comments, dispositions breakdown, files modified, and tracking directory path.

**Note:** Requires `api` scope on your GitLab token and `GITLAB_READ_ONLY_MODE` set to `false`.

**See:** [prompts/address-mr-review.md](./prompts/address-mr-review.md)

### `createProject`

Create a new GitLab project (repository) in a target group/namespace and return its details (id, path, clone URLs, web URL). Resolves a backend automatically (MCP server preferred, `glab` CLI fallback).

**Command:**
```text
/gitlab.createProject
```

**Usage:**

1. **Create a private project in the default namespace:**
   ```text
   /gitlab.createProject name=my-kb
   ```

2. **Create an internal project in a specific group, initialized with a README:**
   ```text
   /gitlab.createProject name=team-docs group=ai-platform-services/knowledge-bases visibility=internal initializeReadme=true
   ```

**Parameters:**
- `name` (string, required): Project name / slug
- `group` (string, optional): Target group full path (e.g., `ai-platform-services/knowledge-bases`). Default: a configurable namespace, or the current user's personal namespace if unset.
- `description` (string, optional): Project description
- `visibility` (string, optional): `private`, `internal`, or `public` (default: `private`)
- `initializeReadme` (boolean, optional): Initialize the repository with a README (default: `false`)

**Returns:** Created project id, `path_with_namespace`, web URL, default branch, and SSH/HTTPS clone URLs.

**Note:** Requires `api` scope on your GitLab token (not just `read_api`) and, for the MCP backend, `GITLAB_READ_ONLY_MODE` set to `false`. You must have write access to the target group/namespace.

**See:** [prompts/create-project.md](./prompts/create-project.md)

---

## Skills

### `gitlab-backend`

Resolves which backend to use for GitLab operations and maps each operation to the right tool. Prefers the MCP server, falls back to the `glab` CLI, and stops with setup guidance when neither is available. Used by every prompt's Step 0 preflight.

**Capabilities:**
- Detects GitLab MCP tool availability, then probes `glab` install + auth status
- Provides the MCP→glab operation map (project lookup, pipelines, job logs, MR create, MR list/view, discussions, replies)
- Emits `BackendUnavailableError` with setup guidance when no backend is found

**See:** [skills/gitlab-backend/SKILL.md](./skills/gitlab-backend/SKILL.md) · [references/glab-command-map.md](./skills/gitlab-backend/references/glab-command-map.md)

### `mr-review-address`

Core workflow skill for retrieving, tracking, and addressing GitLab MR review comments. This skill contains the full five-phase process: MR identity resolution, comment fetching, metadata initialization, comment-by-comment evaluation and action, and final verification.

**Capabilities:**
- Fetches all discussion threads from a GitLab MR via MCP
- Persists tracking metadata via `scripts/review-tracker.ts` (init, address-comment, check-all-addressed, complete, etc.)
- Evaluates each comment against the codebase context
- Implements changes, defends code, or proposes alternatives as appropriate
- Replies to reviewers on GitLab with resolution details
- Supports resuming interrupted sessions

**See:** [skills/mr-review-address/SKILL.md](./skills/mr-review-address/SKILL.md) · [scripts/review-tracker.ts](./skills/mr-review-address/scripts/review-tracker.ts)

### `check-branch-protection`

Read-only skill that decides whether the current user can push directly to a branch (typically `main`) of a GitLab project, or whether changes must go through a merge request. Used by the `createProject` flow's callers and external publish flows to choose push-vs-MR.

**Capabilities:**
- Resolves the backend via the `gitlab-backend` skill (MCP preferred, `glab` fallback)
- Queries the project's protected branches (handling exact and wildcard rules) and the caller's access level
- Returns a small structured result `{ branch, protected, canPush, recommendation, reason }` where `recommendation` is `"push"` or `"open-mr"`
- Read-only — never changes protection settings or pushes; `read_api` scope is sufficient

**See:** [skills/check-branch-protection/SKILL.md](./skills/check-branch-protection/SKILL.md)

---

## MCP Server Configuration

The GitLab MCP server is the **preferred** backend. When it is not configured, the prompts fall back to the `glab` CLI (see [Backends](#backends)). This package includes automatic MCP server configuration for GitLab. The server is configured with:

- **Server Name:** `gitlab`
- **Command:** `npx @zereight/mcp-gitlab`
- **Environment:** Loads from `.env` file in workspace root
- **Configuration:**
  - `GITLAB_API_URL`: https://gitlab.pnmac.com/api/v4
  - `GITLAB_READ_ONLY_MODE`: true (safe mode)
  - `USE_PIPELINE`: true (enables pipeline tools)

The MCP server provides the following tools:
- `mcp_gitlab_get_project` - Retrieve project information
- `mcp_gitlab_execute_graphql` - Execute GraphQL queries
- `mcp_gitlab_get_pipeline_job_output` - Retrieve complete job logs

## Troubleshooting

### "No GitLab backend available" (`BACKEND_UNAVAILABLE`)

**Cause:** Neither the GitLab MCP server nor an authenticated `glab` CLI was found.

**Solution:**
1. Run `/gitlab.setup` to configure a backend automatically, or
2. **MCP:** set `GITLAB_PERSONAL_ACCESS_TOKEN` in `.env` and restart Cursor, or
3. **glab:** `brew install glab` then `glab auth login --hostname gitlab.pnmac.com` and verify with `glab auth status`.

### "401 Unauthorized" Error

**Cause:** GitLab token is not set, expired, or lacks required permissions

**Solution:**
1. Verify `GITLAB_PERSONAL_ACCESS_TOKEN` in `.env` file
2. Check token hasn't expired in GitLab settings
3. Verify token has `api` or `read_api` scope
4. Restart Cursor to reload environment variables

### "Unable to determine GitLab project"

**Cause:** No project identifiers provided and not in a Git repository

**Solution:**
1. Provide `project_id` explicitly
2. Provide `repo_url` parameter
3. Run the prompt from within a Git repository with GitLab remote

### "No pipelines found for commit"

**Cause:** Pipeline hasn't been triggered or commit not pushed

**Solution:**
1. Verify commit exists on GitLab: `git log origin/{branch}`
2. Check if CI/CD is enabled for the project
3. Verify `.gitlab-ci.yml` exists and is valid
4. Ensure commit was pushed: `git push origin {branch}`

## Development

To add new prompts to this package:

1. Create a markdown file in `prompts/` directory
2. Add the prompt definition to `promp.json`
3. Update this README with usage instructions
4. Test the prompt locally
5. Update CHANGELOG.md

## Version History

See [CHANGELOG.md](./CHANGELOG.md) for detailed version history.

## License

MIT

## Author

Pennymac AI Platform
