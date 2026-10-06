---
promp:
  package: "gitlab"
  version: "1.3.1"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "openMR"
---
# gitlab.openMR

Create a GitLab merge request from the current branch or a specified branch with auto-generated title and description

## Parameter Specifications

- **`branch`** (string) - *Optional*
  - Source branch containing your changes (defaults to current Git branch)

- **`targetBranch`** (string) - *Optional*
  - Target branch to merge into (defaults to repository default branch)

- **`title`** (string) - *Optional*
  - Merge request title (auto-generated from commits if not provided)

- **`description`** (string) - *Optional*
  - Merge request description body in markdown (auto-generated if not provided)

- **`draft`** (boolean) - *Optional*
  - Whether to create the MR as a draft

- **`project_id`** (string) - *Optional*
  - GitLab project ID (numeric) or full path (e.g., 'cet/ai/promp'). Auto-detected from Git remote if not provided.

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `branch` (optional) - Source branch containing your changes (defaults to current Git branch)
   - Parameter 2: `targetBranch` (optional) - Target branch to merge into (defaults to repository default branch)
   - Parameter 3: `title` (optional) - Merge request title (auto-generated from commits if not provided)
   - Parameter 4: `description` (optional) - Merge request description body in markdown (auto-generated if not provided)
   - Parameter 5: `draft` (optional) - Whether to create the MR as a draft
   - Parameter 6: `project_id` (optional) - GitLab project ID (numeric) or full path (e.g., 'cet/ai/promp'). Auto-detected from Git remote if not provided.

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/gitlab.openMR value1 value2`
- Named parameters: `/gitlab.openMR param1=value1 param2=value2`
- Mixed format: `/gitlab.openMR value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Created merge request details

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the MR was created successfully
- `mr_iid` (number) - **Required** - The merge request IID (human-readable number)
- `mr_url` (string) - **Required** - Direct URL to the merge request in GitLab
- `title` (string) - **Required** - The MR title
- `source_branch` (string) - **Required** - The source branch
- `target_branch` (string) - **Required** - The target branch
- `draft` (boolean) - *Optional* - Whether the MR was created as a draft
## Error Handling

### BackendUnavailableError

Error when neither the GitLab MCP server nor an authenticated glab CLI is available

**Properties:**

- `code` (string) (values: ["BACKEND_UNAVAILABLE"]) - 
- `message` (string) - 
- `remediation` (string) - 

### ProjectNotFoundError

Error when GitLab project cannot be identified

**Properties:**

- `code` (string) (values: ["PROJECT_NOT_FOUND"]) - 
- `message` (string) - 

### AuthenticationError

Error when GitLab authentication fails or token lacks write permissions

**Properties:**

- `code` (string) (values: ["AUTHENTICATION_FAILED"]) - 
- `message` (string) - 
- `tokenInstructions` (string) - 

### SameBranchError

Error when source and target branches are the same

**Properties:**

- `code` (string) (values: ["SAME_BRANCH"]) - 
- `message` (string) - 
- `branch` (string) - 

### NoCommitsError

Error when no commits exist between source and target branches

**Properties:**

- `code` (string) (values: ["NO_COMMITS"]) - 
- `message` (string) - 
- `source_branch` (string) - 
- `target_branch` (string) - 

### MRCreationFailedError

Error when the API call to create the MR fails

**Properties:**

- `code` (string) (values: ["MR_CREATION_FAILED"]) - 
- `message` (string) - 
- `details` (string) - 

## Prompt Content

# Open GitLab Merge Request

Create a GitLab merge request from the current branch or a specified branch, with an auto-generated or user-provided title and description.

## Overview

This prompt automates the creation of GitLab merge requests. It:
- Detects the current project and branch from the local Git repository
- Analyzes commit history to generate a meaningful MR title and description
- Creates the merge request via the resolved GitLab backend (MCP server or `glab` CLI)
- Returns the MR URL for easy access

## Prerequisites

A working **GitLab backend** — either the GitLab MCP server (preferred) **or** an authenticated `glab` CLI. Step 0 resolves this automatically; if neither is available it returns setup guidance (run `/gitlab.setup`).

- For the **MCP server**: configured in Cursor with `GITLAB_PERSONAL_ACCESS_TOKEN` set, token with `api` scope (write access), and `GITLAB_READ_ONLY_MODE=false`.
- For the **glab CLI**: `glab` installed and authenticated (`glab auth login --hostname gitlab.pnmac.com`) with a token that has `api` scope.
- Access to the target GitLab project.

## Parameters

- **{{branch}}** (string, optional): The source branch containing your changes
  - Default: current Git branch
- **{{targetBranch}}** (string, optional): The branch to merge into
  - Default: repository default branch (usually `main` or `master`)
- **{{title}}** (string, optional): MR title
  - Default: auto-generated from commit messages
- **{{description}}** (string, optional): MR description body (markdown supported)
  - Default: auto-generated from commit diff summary
- **{{draft}}** (boolean, optional): Whether to create the MR as a draft
  - Default: false
- **{{project_id}}** (string, optional): GitLab project ID or full path (e.g., `cet/ai/promp`)
  - Default: auto-detected from Git remote

## Instructions

### Step 0: Resolve GitLab Backend

#### Actions
- [ ] Load the `gitlab-backend` skill (`skills/gitlab-backend/SKILL.md`) and run its **Backend Resolution** procedure.
- [ ] Set `backend` to `"mcp"` (preferred) or `"glab"` (fallback).
- [ ] Use the skill's **Operation Map** for every GitLab call in the steps below — the MCP tool when `backend = "mcp"`, the `glab` command when `backend = "glab"`.

#### Outputs
- **backend**: `"mcp"` or `"glab"`

**CRITICAL STOP CONDITION**: If neither backend is available, **IMMEDIATELY RETURN** the `BackendUnavailableError` and **STOP**. Do not attempt any GitLab operation.
```json
{
  "code": "BACKEND_UNAVAILABLE",
  "message": "No GitLab backend available. Configure the GitLab MCP server or install and authenticate the glab CLI.",
  "remediation": "Run /gitlab.setup to configure a backend."
}
```

---

### Step 1: Resolve Project Identity

#### Inputs
- **project_id** (from parameters, optional)

#### Actions

**Scenario A: project_id is provided**
- [ ] Store the provided project_id for subsequent steps

**Scenario B: project_id is not provided**
- [ ] Verify current directory is a Git repository
- [ ] Run `git remote get-url origin` to get the remote URL
- [ ] Parse the project path from the remote URL:
  - SSH: `git@gitlab.pnmac.com:cet/ai/promp.git` → `cet/ai/promp`
  - HTTPS: `https://gitlab.pnmac.com/cet/ai/promp.git` → `cet/ai/promp`
- [ ] Store the extracted path as project_id

#### Outputs
- **project_id**: Resolved project ID or path
- **lookup_method**: How the project was identified (`provided` or `from_git`)

#### Validation
- [ ] **project_id** is not empty
- [ ] Project path matches expected format (e.g., `namespace/project`)

**CRITICAL STOP CONDITION**: If project cannot be determined, **IMMEDIATELY RETURN** error:
```json
{
  "code": "PROJECT_NOT_FOUND",
  "message": "Unable to determine GitLab project. Provide project_id or run from a Git repository with a GitLab remote."
}
```

---

### Step 2: Determine Branches

#### Inputs
- **branch** (from parameters, optional)
- **targetBranch** (from parameters, optional)
- **project_id** (from Step 1)

#### Actions
- [ ] If **branch** is not provided, run `git rev-parse --abbrev-ref HEAD` to get the current branch
- [ ] If **targetBranch** is not provided, retrieve the project's default branch via the resolved backend:
  - MCP: call `mcp_gitlab_get_project` with the project_id
  - glab: `glab api projects/<url-encoded-path>` (read `default_branch`)
  - Use the project's `default_branch` value (typically `main` or `master`)
- [ ] Verify the source branch is not the same as the target branch
- [ ] Verify the source branch has been pushed to the remote:
  - Run `git rev-parse --verify origin/{{branch}}` to check if the remote tracking branch exists
  - If the branch has not been pushed, push it: `git push -u origin {{branch}}`

#### Outputs
- **source_branch**: The branch containing changes
- **target_branch**: The branch to merge into
- **default_branch**: The project's default branch

#### Validation
- [ ] **source_branch** is not empty
- [ ] **target_branch** is not empty
- [ ] **source_branch** !== **target_branch**
- [ ] Source branch exists on the remote

**CRITICAL STOP CONDITION**: If source and target branches are identical, **IMMEDIATELY RETURN** error:
```json
{
  "code": "SAME_BRANCH",
  "message": "Source branch and target branch are the same. Cannot create a merge request.",
  "branch": "{{branch}}"
}
```

---

### Step 3: Analyze Commits and Generate MR Content

#### Inputs
- **source_branch** (from Step 2)
- **target_branch** (from Step 2)
- **title** (from parameters, optional)
- **description** (from parameters, optional)

#### Actions
- [ ] Run `git log origin/{{target_branch}}..HEAD --oneline` to get the list of commits
- [ ] Run `git diff origin/{{target_branch}}..HEAD --stat` to get a summary of changed files

**If title is not provided:**
- [ ] Analyze commit messages to generate a concise, descriptive MR title
- [ ] If there is a single commit, use its message as the title
- [ ] If there are multiple commits, synthesize a summary title that captures the overall change
- [ ] Follow conventional commit format if commits use it (e.g., `feat:`, `fix:`, `chore:`)

**If description is not provided:**
- [ ] Generate a description that includes:
  - A brief summary of what the MR accomplishes
  - A list of changes (derived from commit messages)
  - Files changed summary

**Template for auto-generated description:**
```markdown
## Summary

[Brief summary of the overall change]

## Changes

[List of commit messages as bullet points]

## Files Changed

[Summary of files modified/added/deleted from git diff --stat]
```

#### Outputs
- **mr_title**: Final MR title (provided or generated)
- **mr_description**: Final MR description (provided or generated)
- **commit_count**: Number of commits in the MR
- **files_changed**: Number of files changed

#### Validation
- [ ] **mr_title** is not empty and under 255 characters
- [ ] **mr_description** is not empty
- [ ] **commit_count** is at least 1

**CRITICAL STOP CONDITION**: If there are no commits between source and target branch, **IMMEDIATELY RETURN** error:
```json
{
  "code": "NO_COMMITS",
  "message": "No commits found between the source and target branches. Nothing to merge.",
  "source_branch": "{{branch}}",
  "target_branch": "{{targetBranch}}"
}
```

---

### Step 4: Create the Merge Request

#### Inputs
- **project_id** (from Step 1)
- **source_branch** (from Step 2)
- **target_branch** (from Step 2)
- **mr_title** (from Step 3)
- **mr_description** (from Step 3)
- **draft** (from parameters, optional)

#### Actions

Create the MR via the resolved backend.

**If `backend = "mcp"`:**
- [ ] Call the `create_merge_request` MCP tool with:
  ```yaml
  project_id: "{project_id}"
  title: "{mr_title}"
  description: "{mr_description}"
  source_branch: "{source_branch}"
  target_branch: "{target_branch}"
  draft: {draft}
  ```

**If `backend = "glab"`:**
- [ ] Run:
  ```bash
  glab mr create \
    --source-branch "{source_branch}" \
    --target-branch "{target_branch}" \
    --title "{mr_title}" \
    --description "{mr_description}" \
    {draft ? "--draft" : ""} \
    --yes
  ```
  (Use `--repo {project_id}` if not running inside the repo. See the `gitlab-backend` skill's command map.)

- [ ] Parse the response to extract the MR URL and MR IID (for glab, the URL is on the last output line; the IID is the trailing number in `/-/merge_requests/<iid>`)
- [ ] Verify the MR was created successfully

#### Outputs
- **mr_iid**: The merge request IID (human-readable number)
- **mr_url**: The web URL of the created merge request
- **mr_state**: The state of the MR (should be "opened")

#### Validation
- [ ] MCP tool call returned successfully (no errors)
- [ ] **mr_iid** is a positive integer
- [ ] **mr_url** is a valid HTTPS URL
- [ ] **mr_state** is "opened" or "locked"

**Retry Logic**: If the API call fails with a network error, retry up to 3 times with exponential backoff.

**CRITICAL STOP CONDITION**: If the MR creation fails after retries, **IMMEDIATELY RETURN** error:
```json
{
  "code": "MR_CREATION_FAILED",
  "message": "Failed to create merge request",
  "details": "[error details from API response]"
}
```

---

### Step 5: Present Results

#### Inputs
- All outputs from Steps 1-4

#### Actions
- [ ] Format a summary of the created merge request
- [ ] Display the MR URL prominently so the user can click through

#### Output Format

```markdown
## Merge Request Created

**MR:** !{mr_iid}
**Title:** {mr_title}
**Source:** {source_branch} → {target_branch}
**Status:** {draft ? "Draft" : "Open"}
**Commits:** {commit_count}
**Files Changed:** {files_changed}

**URL:** {mr_url}
```

---

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

### ProjectNotFoundError

Returned when the GitLab project cannot be identified.

```json
{
  "code": "PROJECT_NOT_FOUND",
  "message": "Unable to determine GitLab project. Provide project_id or run from a Git repository with a GitLab remote."
}
```

### AuthenticationError

Returned when GitLab authentication fails or token lacks write permissions.

```json
{
  "code": "AUTHENTICATION_FAILED",
  "message": "GitLab authentication failed or insufficient permissions",
  "tokenInstructions": "Ensure your token has 'api' scope (not just 'read_api') and GITLAB_READ_ONLY_MODE is set to false."
}
```

### SameBranchError

Returned when source and target branches are identical.

```json
{
  "code": "SAME_BRANCH",
  "message": "Source branch and target branch are the same.",
  "branch": "main"
}
```

### NoCommitsError

Returned when there are no commits between the source and target branches.

```json
{
  "code": "NO_COMMITS",
  "message": "No commits found between the source and target branches.",
  "source_branch": "feature/my-branch",
  "target_branch": "main"
}
```

### MRCreationFailedError

Returned when the API call to create the MR fails.

```json
{
  "code": "MR_CREATION_FAILED",
  "message": "Failed to create merge request",
  "details": "A merge request for this source/target already exists."
}
```

## Examples

### Example 1: Create MR from current branch (no parameters)

**Scenario:** You are on branch `feature/add-logging` and want to create an MR to `main`.

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
  "title": "feat: add structured logging to API endpoints",
  "source_branch": "feature/add-logging",
  "target_branch": "main",
  "draft": false
}
```

### Example 2: Create a draft MR with a custom title

**Scenario:** Create a draft MR from a specific branch with a custom title.

**Input:**
```json
{
  "branch": "feature/new-ui",
  "title": "WIP: Redesign dashboard layout",
  "draft": true
}
```

**Output:**
```json
{
  "success": true,
  "mr_iid": 43,
  "mr_url": "https://gitlab.pnmac.com/cet/ai/promp/-/merge_requests/43",
  "title": "WIP: Redesign dashboard layout",
  "source_branch": "feature/new-ui",
  "target_branch": "main",
  "draft": true
}
```

### Example 3: Create MR targeting a specific branch

**Scenario:** Create an MR from current branch targeting `develop` instead of the default branch.

**Input:**
```json
{
  "targetBranch": "develop"
}
```

**Output:**
```json
{
  "success": true,
  "mr_iid": 44,
  "mr_url": "https://gitlab.pnmac.com/cet/ai/promp/-/merge_requests/44",
  "title": "fix: resolve race condition in queue processor",
  "source_branch": "fix/queue-race-condition",
  "target_branch": "develop",
  "draft": false
}
```

## Notes

- This prompt resolves a backend in Step 0: the GitLab MCP server is preferred, and the `glab` CLI is used as a fallback when the MCP server is not configured. If neither is available, run `/gitlab.setup`.
- For MCP: `GITLAB_READ_ONLY_MODE` must be `false` for MR creation. If the server is in read-only mode, the `create_merge_request` tool will not be available.
- Your GitLab token (MCP `.env` token, or the token used for `glab auth login`) must have `api` scope (full access). The `read_api` scope is insufficient for creating merge requests.
- If the source branch has not been pushed to the remote, this prompt will push it automatically before creating the MR.
- If an MR already exists for the same source/target branch combination, GitLab will return an error. Check existing MRs first if unsure.
- Auto-generated titles follow conventional commit format when the commits use it.

