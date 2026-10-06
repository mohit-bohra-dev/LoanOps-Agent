# GitLab Pipeline Log Retrieval Prompt

## Purpose
This prompt guides you through retrieving pipeline status and job logs for the latest commit in a GitLab repository using the resolved GitLab backend (the GitLab MCP server, or the `glab` CLI as a fallback). This is useful for investigating CI/CD failures and understanding deployment issues.

## Prerequisites
A working **GitLab backend** — either the GitLab MCP server (preferred) **or** an authenticated `glab` CLI. Step 0 resolves this automatically; if neither is available it returns setup guidance (run `/gitlab.setup`).

- For the **MCP server**: configured in Cursor with a GitLab Personal Access Token (`GITLAB_PERSONAL_ACCESS_TOKEN`), token with `api` or `read_api` scope.
- For the **glab CLI**: `glab` installed and authenticated (`glab auth login --hostname gitlab.pnmac.com`).
- Access to the target GitLab project.

## Top Level Inputs

### Optional Inputs (All are optional - will auto-detect from current directory if not provided)
- **project_id**: The GitLab project ID (numeric) or full path (e.g., "cet/ai/promp")
  - If not provided, will be looked up from **repo_name** or **repo_url**
- **repo_name**: The repository name (e.g., "promp") to look up the project
  - Used to find the project ID if **project_id** is not provided
- **repo_url**: The full repository URL (e.g., "git@gitlab.pnmac.com:cet/ai/promp.git")
  - Used to extract project path and look up project ID
- **commit_sha**: The commit SHA to investigate
  - If not provided, will use the latest commit from local Git repository
- **branch_name**: The branch name to check
  - If not provided, will use current branch from local Git repository
- **max_retries**: Maximum number of retry attempts for API calls (defaults to 3)

### Auto-Detection Behavior
If none of the project identifiers are provided:
1. Check if current working directory is a Git repository
2. Extract remote URL from Git configuration
3. Parse project path from remote URL
4. Use project path to look up project ID via GitLab API

### Input Validation
Before proceeding with any steps, validate the inputs:

- [ ] At least one of: **project_id**, **repo_name**, **repo_url**, or valid Git repository in current directory
- [ ] If **project_id** is provided, it's either a numeric ID or a valid project path format
- [ ] If **repo_url** is provided, it follows valid Git URL format
- [ ] **branch_name** (if provided) follows valid Git branch naming conventions
- [ ] **max_retries** is a positive integer between 1 and 5

**CRITICAL STOP CONDITION**: If no way to identify the project exists (no inputs provided and not in a Git repository), **IMMEDIATELY RETURN** an error message and **DO NOT PROCEED** with any retrieval steps.

---

## Retrieval Steps

### Step 0a: Resolve GitLab Backend

#### Actions
- [ ] Load the `gitlab-backend` skill (`skills/gitlab-backend/SKILL.md`) and run its **Backend Resolution** procedure.
- [ ] Set `backend` to `"mcp"` (preferred) or `"glab"` (fallback).
- [ ] For every GitLab call in the steps below, use the skill's **Operation Map**:
  - `mcp_gitlab_get_project` → `glab api projects/<url-encoded-path>`
  - `mcp_gitlab_execute_graphql` → `glab api graphql -f query='...'`
  - `mcp_gitlab_get_pipeline_job_output` → `glab ci trace <job_id>` (or `glab api projects/<id>/jobs/<job_id>/trace`)

**CRITICAL STOP CONDITION**: If neither backend is available, **IMMEDIATELY RETURN** a `BackendUnavailableError` and **STOP**:
```json
{
  "code": "BACKEND_UNAVAILABLE",
  "message": "No GitLab backend available. Configure the GitLab MCP server or install and authenticate the glab CLI.",
  "remediation": "Run /gitlab.setup to configure a backend."
}
```

---

### Step 0: Determine Project ID (if not provided)

#### Inputs
- **project_id** (from top level inputs, optional)
- **repo_name** (from top level inputs, optional)
- **repo_url** (from top level inputs, optional)

#### Actions

**Scenario A: project_id is already provided**
- [ ] Skip this step and proceed to Step 1
- [ ] Store the provided project_id for subsequent steps

**Scenario B: repo_url is provided**
- [ ] Parse the project path from the URL
  - For SSH URLs: `git@gitlab.pnmac.com:cet/ai/promp.git` → `cet/ai/promp`
  - For HTTPS URLs: `https://gitlab.pnmac.com/cet/ai/promp.git` → `cet/ai/promp`
- [ ] Use the extracted project path as the project_id
- [ ] Verify the project exists by calling `mcp_gitlab_get_project` with the path

**Scenario C: repo_name is provided**
- [ ] Use GitLab API to search for projects matching the repo name
- [ ] Call `mcp_gitlab_get_project` with the repo name to see if it matches directly
- [ ] If direct match fails, search using pattern matching (e.g., `*/repo_name`)
- [ ] If multiple matches found, select the most recently active one (check `last_activity_at`)
- [ ] If no matches found, return error indicating project not found
- [ ] Store the found project ID and full project path for subsequent steps

**Search Strategy:**
1. Try exact match: `repo_name`
2. Try with common namespaces: `cet/ai/{repo_name}`, `cet/{repo_name}`
3. Use GitLab search API if MCP provides search functionality

**Scenario D: No project identifiers provided**
- [ ] Check if current working directory is a Git repository
- [ ] Run `git remote get-url origin` to get remote URL
- [ ] Parse project path from the remote URL (same as Scenario B)
- [ ] Use the extracted project path as the project_id
- [ ] Verify the project exists by calling `mcp_gitlab_get_project`

#### Parsing Examples

**SSH URL Format:**
```bash
git@gitlab.pnmac.com:cet/ai/promp.git
Extract: cet/ai/promp
```

**HTTPS URL Format:**
```text
https://gitlab.pnmac.com/cet/ai/promp.git
Extract: cet/ai/promp
```

**Git Command:**
```bash
git remote get-url origin
# Output: git@gitlab.pnmac.com:cet/ai/promp.git
```

#### Outputs
- **project_id**: String containing the project ID (numeric) or project path (e.g., "cet/ai/promp")
- **project_path**: String containing the full project path with namespace
- **lookup_method**: String indicating how project_id was determined ("provided", "from_url", "from_name", "from_git")
- **project_verified**: Boolean indicating if project exists in GitLab

#### Validation
- [ ] **project_id** is not empty
- [ ] **project_verified** is true (project exists in GitLab)
- [ ] **project_path** matches expected format (namespace/project)

**Retry Logic**: If project lookup fails, retry up to **max_retries** times with exponential backoff.

**CRITICAL STOP CONDITION**: If project cannot be identified or verified after retries, **IMMEDIATELY RETURN** an error:
```text
Unable to determine GitLab project. Please provide one of:
1. project_id (numeric ID or full path)
2. repo_url (full Git repository URL)
3. repo_name (repository name to search)
Or ensure you are in a Git repository with a GitLab remote configured.
```

---

### Step 1: Get Latest Commit Information

#### Inputs
- **project_id** (from Step 0)
- **branch_name** (from top level inputs, optional)
- **commit_sha** (from top level inputs, optional)

#### Actions

**Scenario A: commit_sha is provided**
- [ ] Verify the commit SHA is a valid 40-character hex string
- [ ] Store the commit SHA for subsequent steps
- [ ] Optionally retrieve commit message for reference

**Scenario B: commit_sha is not provided**
- [ ] Check if current directory is a Git repository
- [ ] Run `git log -1 --format="%H %s"` to get latest commit SHA and message
- [ ] Run `git rev-parse --abbrev-ref HEAD` to get current branch name (if not provided)
- [ ] Store the commit SHA for subsequent steps
- [ ] Store the commit message for reference
- [ ] Verify the commit SHA is a valid 40-character hex string

#### Outputs
- **commit_sha**: String containing the full 40-character commit SHA
- **commit_message**: String containing the commit message
- **current_branch**: String containing the branch name
- **retrieval_status**: Boolean indicating if commit info was retrieved successfully

#### Validation
- [ ] **commit_sha** is exactly 40 characters and contains only hex characters (0-9, a-f)
- [ ] **commit_message** is not empty
- [ ] **current_branch** is not empty
- [ ] **retrieval_status** is true

**Retry Logic**: If validation fails, retry git commands up to **max_retries** times.

**CRITICAL STOP CONDITION**: If validation still fails after retries, **IMMEDIATELY RETURN** an error indicating inability to retrieve commit information and **STOP ALL RETRIEVAL**.

---

### Step 2: Verify GitLab Project Access

#### Inputs
- **project_id** (from top level inputs)

#### Actions
- [ ] Call `mcp_gitlab_get_project` with the project_id
- [ ] Verify the API call succeeds without authentication errors
- [ ] Extract key project information:
  - Project name
  - Project path with namespace
  - Default branch
  - Project visibility
  - Web URL

#### Outputs
- **project_name**: String containing the project name
- **project_path**: String containing the full project path (namespace/project)
- **default_branch**: String containing the default branch name
- **project_url**: String containing the project web URL
- **access_verified**: Boolean indicating successful project access

#### Validation
- [ ] **access_verified** is true (no 401 or 403 errors)
- [ ] **project_name** is not empty
- [ ] **project_path** matches the expected format
- [ ] **project_url** is a valid HTTPS URL

**Retry Logic**: If access fails with network errors, retry up to **max_retries** times with exponential backoff.

**CRITICAL STOP CONDITION**: If access fails with 401 Unauthorized or 403 Forbidden after retries, **IMMEDIATELY RETURN** an error indicating:
```text
GitLab authentication failed. Please verify:
1. GITLAB_TOKEN environment variable is set
2. Token has not expired
3. Token has 'api' or 'read_api' scope
4. You have access to project: {project_id}
```

---

### Step 3: Retrieve Pipeline Status for Commit

#### Inputs
- **project_path** (from Step 2)
- **commit_sha** (from Step 1)

#### Actions
- [ ] Execute GraphQL query to retrieve pipeline information:
  - Query the `project` with `fullPath: "{project_path}"`
  - Filter `pipelines` by `sha: "{commit_sha}"`
  - Request first 5 pipelines to handle multiple pipeline runs
  - Retrieve pipeline fields: id, iid, status, detailedStatus, createdAt, updatedAt, finishedAt, duration, ref
  - Retrieve job fields: name, status, stage, duration, createdAt, finishedAt
- [ ] Parse the GraphQL response
- [ ] Extract pipeline and job information
- [ ] Calculate total pipeline duration and status

#### GraphQL Query Template
```graphql
query {
  project(fullPath: "{project_path}") {
    name
    pipelines(sha: "{commit_sha}", first: 5) {
      nodes {
        id
        iid
        sha
        status
        detailedStatus {
          text
          label
          icon
          group
        }
        createdAt
        updatedAt
        finishedAt
        duration
        ref
        jobs {
          nodes {
            name
            status
            stage {
              name
            }
            duration
            createdAt
            finishedAt
          }
        }
      }
    }
  }
}
```

#### Outputs
- **pipeline_id**: String containing the pipeline ID (e.g., "gid://gitlab/Ci::Pipeline/4930910")
- **pipeline_iid**: String containing the pipeline IID (human-readable number)
- **pipeline_status**: String containing the pipeline status (SUCCESS, FAILED, RUNNING, etc.)
- **pipeline_duration**: Number indicating total pipeline duration in seconds
- **pipeline_started_at**: String containing ISO timestamp when pipeline started
- **pipeline_finished_at**: String containing ISO timestamp when pipeline finished (null if running)
- **jobs**: Array of job objects containing name, status, stage, duration
- **failed_jobs**: Array of job objects that have FAILED status
- **successful_jobs**: Array of job objects that have SUCCESS status
- **skipped_jobs**: Array of job objects that have SKIPPED status

#### Validation
- [ ] GraphQL query executes without errors
- [ ] At least one pipeline is returned in the response
- [ ] **pipeline_status** is a valid status value
- [ ] **jobs** array is not empty
- [ ] Each job has required fields: name, status, stage
- [ ] **failed_jobs**, **successful_jobs**, and **skipped_jobs** are correctly categorized

**Retry Logic**: If GraphQL query fails, retry up to **max_retries** times.

**CRITICAL STOP CONDITION**: If no pipelines are found for the commit after retries, **IMMEDIATELY RETURN** an error:
```text
No pipelines found for commit {commit_sha} on branch {branch_name}.
This could mean:
1. Pipeline has not been triggered yet
2. Commit was not pushed to GitLab
3. CI/CD is not configured for this project
```

---

### Step 4: Identify Failed Jobs

#### Inputs
- **failed_jobs** (from Step 3)
- **pipeline_iid** (from Step 3)

#### Actions
- [ ] Filter the jobs array to identify all jobs with FAILED status
- [ ] For each failed job:
  - Extract job name
  - Extract job stage
  - Extract job duration
  - Calculate job web path: `/cet/ai/promp/-/jobs/{job_id}`
- [ ] Sort failed jobs by stage order (to identify which stage failed first)
- [ ] Determine the primary failure (earliest failed job in pipeline execution)

#### Outputs
- **failed_job_count**: Number indicating total failed jobs
- **primary_failed_job**: Object containing details of the earliest failed job
- **primary_job_name**: String containing the name of the primary failed job
- **primary_job_stage**: String containing the stage of the primary failed job
- **primary_job_id**: String containing the job ID (extracted from GraphQL response)
- **primary_job_url**: String containing the full web URL to view the job

#### Validation
- [ ] If pipeline status is FAILED, **failed_job_count** is greater than 0
- [ ] **primary_failed_job** is correctly identified
- [ ] **primary_job_url** is a valid HTTPS URL
- [ ] All failed job details are complete and accurate

**Special Cases**:
- If no jobs failed but pipeline status is FAILED, this indicates a pipeline-level failure (not job-level)
- If multiple jobs failed in parallel, identify the one with the earliest startedAt timestamp

---

### Step 5: Retrieve Failed Job Logs

#### Inputs
- **project_id** (from top level inputs)
- **primary_job_id** (from Step 4, extracted from GraphQL response or job path)

#### Actions
- [ ] Use `mcp_gitlab_get_pipeline_job_output` tool to retrieve the complete job log
- [ ] Provide project_id and job_id to the tool
- [ ] Optionally use `limit` and `offset` parameters to retrieve specific portions of the log
- [ ] Parse the raw log output to identify:
  - Error messages
  - Exit codes
  - Failed commands
  - Stack traces (if present)
  - CloudFormation events (if CDK deployment)
- [ ] Clean up ANSI color codes and escape sequences from the log

#### Tool Call Template
```typescript
mcp_gitlab_get_pipeline_job_output({
  project_id: "{project_id}",
  job_id: "{job_id}",
  limit: 1000,  // Optional: max lines from end of log (default: 1000)
  offset: 0     // Optional: lines to skip from end (default: 0)
})
```

#### Outputs
- **job_log_raw**: String containing the complete raw job log output
- **job_log_cleaned**: String with ANSI codes removed for readability
- **error_messages**: Array of strings containing identified error messages
- **exit_code**: Number indicating the job exit code (if identifiable)
- **failed_command**: String containing the command that failed (if identifiable)
- **cloudformation_errors**: Array of CloudFormation resource failures (if applicable)
- **log_retrieval_status**: Boolean indicating if logs were successfully retrieved

#### Validation
- [ ] Tool call executes without errors
- [ ] **job_log_raw** is not null or empty
- [ ] At least one error indicator is found in the log
- [ ] **log_retrieval_status** is true
- [ ] Log contains relevant failure information

#### Parsing Guidelines

**For CDK/CloudFormation Deployments:**
- Look for lines containing `CREATE_FAILED`, `UPDATE_FAILED`, `DELETE_FAILED`
- Extract resource types and logical IDs from CloudFormation events
- Identify hook failures (e.g., `PNMAC::S3BucketAccessLogging::Hook`)
- Capture stack traces showing the CDK construct source locations

**For General Job Failures:**
- Look for lines starting with `ERROR:`, `FATAL:`, or `FAILED`
- Identify exit codes from lines like `command terminated with exit code X`
- Extract command that failed from execution logs
- Capture any exception stack traces

**Retry Logic**: If tool call fails, retry up to **max_retries** times.

**ADVANTAGES of this tool:**
- ✅ Returns complete job log, not just a summary
- ✅ Simple one-line tool call
- ✅ No need for GraphQL query construction
- ✅ Supports pagination with limit/offset for large logs
- ✅ Raw text output is easier to parse than HTML

---

### Step 6: Format and Present Results

#### Inputs
- All outputs from Steps 1-5

#### Actions
- [ ] Compile a comprehensive summary report
- [ ] Format the pipeline status in a readable format
- [ ] Organize jobs by status (successful, failed, skipped)
- [ ] Present failed job details prominently
- [ ] Include actionable next steps for investigation
- [ ] Provide direct URLs for deeper investigation

#### Output Format

```markdown
## Pipeline Status for Latest Commit

**Commit:** {commit_sha}
**Message:** {commit_message}
**Branch:** {current_branch}
**Pipeline ID:** #{pipeline_iid}
**Status:** {status_emoji} {pipeline_status}
**Duration:** {duration} (formatted)
**Started:** {pipeline_started_at} (formatted)
**Finished:** {pipeline_finished_at} (formatted)

### Pipeline Jobs Breakdown:

#### ✅ Successful Jobs:
1. **{job_name}** ({stage_name} stage) - {duration}s
2. ...

#### ❌ Failed Jobs:
- **{job_name}** ({stage_name} stage) - Failed after {duration}s

#### ⏭️ Skipped Jobs:
- **{job_name}** ({stage_name} stage)
- ...

### Failed Job Analysis:

**Primary Failed Job:** {primary_job_name}
**Stage:** {primary_job_stage}
**Duration:** {duration}s

**Error Summary:**
{parsed error messages from logs}

**Job URL:** {primary_job_url}

### Next Steps:
1. Review the complete logs at: {primary_job_url}
2. Check if the failure is environment-specific
3. Review recent changes that might have caused the failure
4. Verify all required environment variables and secrets are configured
5. Check for any service dependencies that might be down

**Pipeline URL:** {project_url}/-/pipelines/{pipeline_iid}
```

#### Validation
- [ ] All placeholders are replaced with actual values
- [ ] URLs are valid and clickable
- [ ] Status emojis are correctly applied (✅ for success, ❌ for failure, ⏭️ for skipped)
- [ ] Durations are formatted in human-readable format (e.g., "3m 28s" instead of "208")
- [ ] Timestamps are formatted in a readable timezone

---

## Error Handling Throughout Process

### Network Errors
If any GitLab API call fails due to network issues:
1. Log the specific error message
2. Wait for exponential backoff period (1s, 2s, 4s)
3. Retry the operation up to **max_retries** times
4. If all retries fail, return a network error message

### Authentication Errors (401, 403)
If authentication fails at any step:
1. **IMMEDIATELY STOP** all API calls
2. Return clear error message about token configuration
3. Provide specific instructions for fixing authentication

### Not Found Errors (404)
If project or pipeline is not found:
1. Verify the project_id is correct
2. Verify the commit exists in the remote repository
3. Return helpful error message with suggestions

### GraphQL Errors
If GraphQL query returns errors in the response:
1. Log the specific GraphQL error message
2. Check if it's a schema mismatch (field doesn't exist)
3. Attempt to modify the query to remove problematic fields
4. Retry with simplified query
5. If still failing, return the GraphQL error details

---

## Cleanup Instructions

**ALWAYS PERFORM CLEANUP** regardless of success or failure:
- [ ] Clear any temporary variables or data structures
- [ ] Log the completion status
- [ ] If logs were downloaded to temporary files, remove them
- [ ] Close any open file handles or network connections

---

## Expected Success Criteria

A successful retrieval is confirmed when:
- [ ] Pipeline status is retrieved and displayed
- [ ] All jobs are categorized by status
- [ ] Failed jobs (if any) are identified with details
- [ ] Job logs for failed jobs are retrieved or access URLs are provided
- [ ] A formatted summary report is presented
- [ ] Direct URLs are provided for deeper investigation

---

## Common Issues and Troubleshooting

### Issue: "401 Unauthorized" Error
**Cause:** GitLab token is not set, expired, or lacks required permissions
**Solution:**
1. Verify GITLAB_TOKEN environment variable: `echo $GITLAB_TOKEN`
2. Check token hasn't expired in GitLab settings
3. Verify token has `api` or `read_api` scope
4. Restart Cursor to reload environment variables

### Issue: "Unable to determine GitLab project"
**Cause:** No project identifiers provided and not in a Git repository
**Solution:**
1. Provide project_id explicitly: `project_id: 13466` or `project_id: "cet/ai/promp"`
2. Provide repo_url: `repo_url: "git@gitlab.pnmac.com:cet/ai/promp.git"`
3. Provide repo_name: `repo_name: "promp"`
4. Run the prompt from within a Git repository with GitLab remote configured

### Issue: "No pipelines found for commit"
**Cause:** Pipeline hasn't been triggered or commit not pushed
**Solution:**
1. Verify commit exists on GitLab: `git log origin/{branch} | grep {commit_sha}`
2. Check if CI/CD is enabled for the project
3. Verify .gitlab-ci.yml exists and is valid
4. Check if pipeline was manually cancelled or skipped
5. Ensure commit was pushed: `git push origin {branch}`

### Issue: "GraphQL field doesn't exist" Error
**Cause:** GitLab version doesn't support certain GraphQL fields
**Solution:**
1. Simplify the GraphQL query to use only core fields
2. Check GitLab version and GraphQL schema documentation
3. Remove advanced fields like trace or detailedStatus if not supported

### Issue: Job logs show only summary, not full trace (GraphQL)
**Cause:** GraphQL API returns abbreviated trace for performance
**Solution:**
1. Use `mcp_gitlab_get_pipeline_job_output` tool instead of GraphQL trace query
2. This tool returns the complete job log, not just a summary
3. If tool is unavailable, visit the job URL directly in a browser
4. Alternatively, use GitLab REST API: `/api/v4/projects/{id}/jobs/{job_id}/trace`

### Issue: Job log is too large or causes timeouts
**Cause:** Job log exceeds memory or processing limits
**Solution:**
1. Use `limit` parameter to retrieve only last N lines: `limit: 500`
2. Use `offset` parameter to skip earlier log lines: `offset: 100`
3. Retrieve log in chunks if needed (e.g., last 1000 lines, then previous 1000)
4. Focus on the end of the log where errors typically appear

---

## Tool Usage Summary

This prompt uses the following GitLab MCP tools:

1. **mcp_gitlab_get_project**: Retrieves project information and verifies access
   - Can be used with project_id (numeric), full path (namespace/project), or repo name
2. **mcp_gitlab_execute_graphql**: Executes GraphQL queries for pipeline and job data
3. **mcp_gitlab_get_pipeline_job_output**: Retrieves complete job log output

### Additional Tools (if available)
- **mcp_gitlab_search**: Search for projects by name or other criteria
- **mcp_gitlab_list_projects**: List accessible projects with filtering

### Tool Details:

**mcp_gitlab_get_project**
- Purpose: Verify project access and get project metadata
- Required: project_id (numeric ID or full path)
- Returns: Project name, path, URLs, permissions

**mcp_gitlab_execute_graphql**
- Purpose: Query pipeline and job status information
- Required: GraphQL query string
- Optional: variables object for parameterized queries
- Returns: Structured pipeline and job data

**mcp_gitlab_get_pipeline_job_output**
- Purpose: Retrieve complete job log output
- Required: project_id, job_id
- Optional: limit (max lines from end), offset (lines to skip from end)
- Returns: Complete raw job log as plain text
- Advantages: No HTML parsing needed, complete logs, not just summary

### Alternative Backend: glab CLI (when GitLab MCP is unavailable)
When `backend = "glab"` (resolved in Step 0a), use these equivalents — see the `gitlab-backend` skill's command map for full syntax:
- Project / default branch: `glab api projects/<url-encoded-path>`
- Pipelines for a SHA: `glab api graphql -f query='...'` or `glab api "projects/<id>/pipelines?sha=<sha>"`
- Pipeline + job tree: `glab ci view <pipeline_id>`
- Complete job log: `glab ci trace <job_id>` or `glab api "projects/<id>/jobs/<job_id>/trace"`

---

## Example Usage

### Example 1: Auto-detect from current directory
**Scenario:** You're in a Git repository and want to check the latest pipeline status

**Command:**
```text
No inputs required - will auto-detect project from current directory
```

**What happens:**
1. Detects Git remote URL from current directory
2. Extracts project path: `cet/ai/promp`
3. Gets latest commit SHA from `git log`
4. Gets current branch from `git rev-parse --abbrev-ref HEAD`
5. Retrieves and displays pipeline status

### Example 2: Explicit project_id
**Scenario:** You know the project ID and want to check a specific commit

**Inputs:**
- project_id: `13466` or `cet/ai/promp`
- commit_sha: `34f286db5be6bc7ba76cb5d41cb9250293844732`

**What happens:**
1. Uses provided project_id directly
2. Uses provided commit SHA
3. Retrieves and displays pipeline status

### Example 3: Using repo_url
**Scenario:** You have the repository URL but not in a local clone

**Inputs:**
- repo_url: `git@gitlab.pnmac.com:cet/ai/promp.git`

**What happens:**
1. Parses project path from URL: `cet/ai/promp`
2. Looks up project to get project_id
3. Gets latest pipeline for the project
4. Displays pipeline status

### Example 4: Search by repo_name
**Scenario:** You only know the repository name

**Inputs:**
- repo_name: `promp`

**What happens:**
1. Searches GitLab for projects named "promp"
2. Selects most recently active match
3. Gets project_id from search results
4. Retrieves and displays pipeline status

**Expected Output for all scenarios:** A comprehensive report showing pipeline status, all jobs, failed job details, error messages, and direct links for investigation.
