# Create GitLab Project

Create a new GitLab project (repository) in a target group/namespace and return its details.

## Overview

This prompt creates a new GitLab project so other flows (for example, an `arbor` knowledge-base package) can provision repositories on demand. It:
- Resolves a GitLab backend (MCP server preferred, `glab` CLI fallback)
- Resolves the target group/namespace, defaulting to a configurable namespace when none is provided
- Preflights for an existing project at the target path to avoid collisions
- Creates the project via the resolved backend with the requested visibility and README option
- Returns the new project's id, path, clone URLs, and web URL

## Prerequisites

A working **GitLab backend** — either the GitLab MCP server (preferred) **or** an authenticated `glab` CLI. Step 0 resolves this automatically; if neither is available it returns setup guidance (run `/gitlab.setup`).

- For the **MCP server**: configured in Cursor with `GITLAB_PERSONAL_ACCESS_TOKEN` set, token with `api` scope (write access), and `GITLAB_READ_ONLY_MODE=false`. The package's MCP server is `@zereight/mcp-gitlab`.
- For the **glab CLI**: `glab` installed and authenticated (`glab auth login --hostname gitlab.pnmac.com`) with a token that has `api` scope.
- Write access to the target group/namespace.

## Parameters

- **{{name}}** (string, required): Project name / slug for the new repository
  - Must not be empty
  - Example: `my-kb`
- **{{group}}** (string, optional): Target group full path
  - Default: a configurable default namespace; if none is configured, the current user's personal namespace
  - Example: `ai-platform-services/knowledge-bases`
- **{{description}}** (string, optional): Project description
  - Default: none (empty description)
- **{{visibility}}** (string, optional): Project visibility level
  - Must be one of: `private`, `internal`, `public`
  - Default: `private`
- **{{initializeReadme}}** (boolean, optional): Initialize the repository with a README
  - Default: `false`

## Instructions

### Step 0: Resolve GitLab Backend

#### Actions
- [ ] Load the `gitlab-backend` skill (`skills/gitlab-backend/SKILL.md`) and run its **Backend Resolution** procedure.
- [ ] Set `backend` to `"mcp"` (preferred) or `"glab"` (fallback).
- [ ] Use the resolved backend for every GitLab call in the steps below — the MCP tool when `backend = "mcp"`, the `glab` command when `backend = "glab"`.

#### Outputs
- **backend**: `"mcp"` or `"glab"`

**Note**: Project creation and group lookup are not in the `gitlab-backend` skill's Operation Map. The MCP and glab forms for those operations are documented inline in the steps below, using the skill's `glab api` REST fallback convention (URL-encode project/group path slashes — `cet/ai/promp` → `cet%2Fai%2Fpromp`).

**CRITICAL STOP CONDITION**: If neither backend is available, **IMMEDIATELY RETURN** the `BackendUnavailableError` and **STOP**. Do not attempt any GitLab operation.
```json
{
  "code": "BACKEND_UNAVAILABLE",
  "message": "No GitLab backend available. Configure the GitLab MCP server or install and authenticate the glab CLI.",
  "remediation": "Run /gitlab.setup to configure a backend."
}
```

---

### Step 1: Resolve Target Namespace/Group

#### Inputs
- **group** (from parameters, optional)
- **backend** (from Step 0)

#### Actions

**Scenario A: group is provided**
- [ ] Store the provided **group** full path as the target namespace.

**Scenario B: group is not provided**
- [ ] Use the configured default namespace if one is set for the workspace.
- [ ] If no default is configured, resolve the current user's personal namespace:
  - MCP: call the GitLab MCP server's current-user tool (e.g. `get_current_user`) and use the returned `username` as the namespace.
  - glab: run `glab api user` and use the returned `username` as the namespace.

- [ ] Verify the target namespace exists and is accessible via the resolved backend:
  - MCP: call the GitLab MCP server's namespace/group lookup tool (e.g. `get_namespace` / `get_group`) with the namespace full path. A successful response with an `id` confirms access.
  - glab: run `glab api groups/<url-encoded-group-path>` (URL-encode slashes). A `200` with `id` and `full_path` confirms access; a `404`/`401` means the group is missing or inaccessible.
  - (Skip this check when the namespace is the current user's personal namespace resolved in Scenario B.)

#### Outputs
- **namespace**: The resolved target group/namespace full path
- **namespace_id**: The numeric namespace id (when returned by the lookup; used by the REST create fallback)
- **resolution_method**: How the namespace was determined (`provided` or `default`)

#### Validation
- [ ] **namespace** is not empty
- [ ] The namespace exists and is accessible (when a group was provided or a default group is configured)

**CRITICAL STOP CONDITION**: If the target group/namespace does not exist or is not accessible, **IMMEDIATELY RETURN** the `GroupNotFoundError` and **STOP**:
```json
{
  "code": "GROUP_NOT_FOUND",
  "message": "Target group or namespace does not exist or is not accessible.",
  "group": "ai-platform-services/knowledge-bases"
}
```

---

### Step 2: Check for Existing Project

#### Inputs
- **name** (from parameters)
- **namespace** (from Step 1)
- **backend** (from Step 0)

#### Actions
- [ ] Construct the candidate path: `{namespace}/{name}`.
- [ ] Check whether a project already exists at that path via the resolved backend:
  - MCP: call the GitLab MCP server's `get_project` tool with the full path `{namespace}/{name}`. A successful response means the project already exists.
  - glab: run `glab api projects/<url-encoded-namespace-and-name>` (URL-encode the slashes, e.g. `ai-platform-services%2Fknowledge-bases%2Fmy-kb`). A `200` means the project exists; a `404` means the path is free.

#### Outputs
- **project_exists**: Boolean indicating whether a project already exists at the candidate path
- **candidate_path**: The `{namespace}/{name}` path that was checked

#### Validation
- [ ] **project_exists** is `false`

**CRITICAL STOP CONDITION**: If a project already exists at the candidate path, **IMMEDIATELY RETURN** the `ProjectExistsError` and **STOP**. Do not attempt creation.
```json
{
  "code": "PROJECT_EXISTS",
  "message": "A project with that name already exists in the target group.",
  "path_with_namespace": "ai-platform-services/knowledge-bases/my-kb"
}
```

---

### Step 3: Create the Project

#### Inputs
- **name** (from parameters)
- **namespace** (from Step 1)
- **namespace_id** (from Step 1, when available)
- **description** (from parameters, optional)
- **visibility** (from parameters, optional — default `private`)
- **initializeReadme** (from parameters, optional — default `false`)
- **backend** (from Step 0)

#### Actions

Create the project via the resolved backend.

**If `backend = "mcp"`:**
- [ ] Call the GitLab MCP server's `create_project` tool (or the server's equivalent `create_repository` tool) with:
  ```yaml
  name: "{name}"
  namespace_id: {namespace_id}        # or pass the namespace full path if the tool accepts it
  description: "{description}"
  visibility: "{visibility}"          # private | internal | public
  initialize_with_readme: {initializeReadme}
  ```

**If `backend = "glab"`:**
- [ ] Run:
  ```bash
  glab repo create "{namespace}/{name}" \
    --description "{description}" \
    {visibility flag: --private | --internal | --public} \
    {initializeReadme ? "--readme" : ""}
  ```
  (`glab repo create <name> --group {namespace}` is equivalent. Omit `--description` when none is provided.)
- [ ] If a field is not exposed by `glab repo create`, fall back to the REST API per the `gitlab-backend` skill's command map:
  ```bash
  glab api -X POST projects \
    -f name="{name}" \
    -f namespace_id="{namespace_id}" \
    -f description="{description}" \
    -f visibility="{visibility}" \
    -f initialize_with_readme={initializeReadme}
  ```

- [ ] Parse the created project's `id`, `path_with_namespace`, `web_url`, `default_branch`, `ssh_url_to_repo`, and `http_url_to_repo` from the response. (For `glab repo create`, the created project URL is printed on success; run `glab api projects/<url-encoded-path>` to read the full structured fields.)
- [ ] Verify the project was created successfully.

#### Outputs
- **project_id**: The numeric GitLab project id
- **path_with_namespace**: The full path of the created project (e.g. `ai-platform-services/knowledge-bases/my-kb`)
- **web_url**: The web URL of the created project
- **default_branch**: The project's default branch (may be null when `initializeReadme` is `false`)
- **ssh_url_to_repo**: The SSH clone URL
- **http_url_to_repo**: The HTTPS clone URL

#### Validation
- [ ] The create call returned successfully (no errors)
- [ ] **project_id** is a positive integer
- [ ] **path_with_namespace** is not empty
- [ ] **web_url** is a valid HTTPS URL

**Retry Logic**: If the API call fails with a network error, retry up to 3 times with exponential backoff.

**CRITICAL STOP CONDITION**: If the create call returns a `401`/`403`, **IMMEDIATELY RETURN** the `AuthenticationError` and **STOP**:
```json
{
  "code": "AUTHENTICATION_FAILED",
  "message": "GitLab authentication failed or insufficient permissions",
  "tokenInstructions": "Ensure your token has 'api' scope (not just 'read_api') and GITLAB_READ_ONLY_MODE is set to false."
}
```

**CRITICAL STOP CONDITION**: If creation fails for any other reason after retries, **IMMEDIATELY RETURN** the `CreationFailedError` and **STOP**:
```json
{
  "code": "CREATION_FAILED",
  "message": "Failed to create the GitLab project.",
  "details": "[error details from API response]"
}
```

---

### Step 4: Present Results

#### Inputs
- All outputs from Steps 1-3

#### Actions
- [ ] Format a summary of the created project.
- [ ] Display the web URL prominently so the user can click through.

#### Output Format

```markdown
## Project Created

**Project:** {path_with_namespace}
**ID:** {project_id}
**Visibility:** {visibility}
**Default Branch:** {default_branch}
**SSH:** {ssh_url_to_repo}
**HTTPS:** {http_url_to_repo}

**URL:** {web_url}
```

---

## Response Format

This prompt returns a structured JSON object describing the created project.

### Success Response

```json
{
  "success": true,
  "project_id": 4821,
  "path_with_namespace": "ai-platform-services/knowledge-bases/my-kb",
  "web_url": "https://gitlab.pnmac.com/ai-platform-services/knowledge-bases/my-kb",
  "default_branch": "main",
  "ssh_url_to_repo": "git@gitlab.pnmac.com:ai-platform-services/knowledge-bases/my-kb.git",
  "http_url_to_repo": "https://gitlab.pnmac.com/ai-platform-services/knowledge-bases/my-kb.git"
}
```

**Field Descriptions:**
- `success`: Whether the project was created successfully (always `true` on success)
- `project_id`: The numeric GitLab project id
- `path_with_namespace`: The full path of the created project
- `web_url`: The web URL of the created project
- `default_branch`: The project's default branch (may be `null` when the repository was created without a README)
- `ssh_url_to_repo`: The SSH clone URL
- `http_url_to_repo`: The HTTPS clone URL

Required fields: `success`, `project_id`, `path_with_namespace`, `web_url`.

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

### GroupNotFoundError

Returned when the target group/namespace does not exist or is not accessible.

```json
{
  "code": "GROUP_NOT_FOUND",
  "message": "Target group or namespace does not exist or is not accessible.",
  "group": "ai-platform-services/knowledge-bases"
}
```

### ProjectExistsError

Returned when a project with that name already exists in the target group.

```json
{
  "code": "PROJECT_EXISTS",
  "message": "A project with that name already exists in the target group.",
  "path_with_namespace": "ai-platform-services/knowledge-bases/my-kb"
}
```

### AuthenticationError

Returned when GitLab authentication fails or the token lacks write permissions.

```json
{
  "code": "AUTHENTICATION_FAILED",
  "message": "GitLab authentication failed or insufficient permissions",
  "tokenInstructions": "Ensure your token has 'api' scope (not just 'read_api') and GITLAB_READ_ONLY_MODE is set to false."
}
```

### CreationFailedError

Returned when the create API call fails for a reason other than authentication.

```json
{
  "code": "CREATION_FAILED",
  "message": "Failed to create the GitLab project.",
  "details": "Path my-kb has already been taken at the namespace level."
}
```

## Examples

### Example 1: Create a project with defaults (minimal)

**Scenario:** Create a private project named `my-kb` in the default namespace.

**Input:**
```json
{
  "name": "my-kb"
}
```

**Output:**
```json
{
  "success": true,
  "project_id": 4821,
  "path_with_namespace": "jsmith/my-kb",
  "web_url": "https://gitlab.pnmac.com/jsmith/my-kb",
  "default_branch": null,
  "ssh_url_to_repo": "git@gitlab.pnmac.com:jsmith/my-kb.git",
  "http_url_to_repo": "https://gitlab.pnmac.com/jsmith/my-kb.git"
}
```

### Example 2: Create an internal project in a group, initialized with a README

**Scenario:** Create an internal project named `team-docs` in the `ai-platform-services/knowledge-bases` group, initialized with a README.

**Input:**
```json
{
  "name": "team-docs",
  "group": "ai-platform-services/knowledge-bases",
  "visibility": "internal",
  "initializeReadme": true
}
```

**Output:**
```json
{
  "success": true,
  "project_id": 4822,
  "path_with_namespace": "ai-platform-services/knowledge-bases/team-docs",
  "web_url": "https://gitlab.pnmac.com/ai-platform-services/knowledge-bases/team-docs",
  "default_branch": "main",
  "ssh_url_to_repo": "git@gitlab.pnmac.com:ai-platform-services/knowledge-bases/team-docs.git",
  "http_url_to_repo": "https://gitlab.pnmac.com/ai-platform-services/knowledge-bases/team-docs.git"
}
```

### Example 3: Project already exists (error case)

**Scenario:** Attempt to create `my-kb` in a group where it already exists.

**Input:**
```json
{
  "name": "my-kb",
  "group": "ai-platform-services/knowledge-bases"
}
```

**Error Output:**
```json
{
  "code": "PROJECT_EXISTS",
  "message": "A project with that name already exists in the target group.",
  "path_with_namespace": "ai-platform-services/knowledge-bases/my-kb"
}
```

## Notes

- This prompt resolves a backend in Step 0: the GitLab MCP server is preferred, and the `glab` CLI is used as a fallback when the MCP server is not configured. If neither is available, run `/gitlab.setup`.
- Project creation and group lookup are not in the `gitlab-backend` skill's Operation Map; their MCP and glab forms are documented inline in the steps above, using the skill's `glab api` REST fallback (URL-encode path slashes, e.g. `ai-platform-services/knowledge-bases` → `ai-platform-services%2Fknowledge-bases`).
- Your GitLab token (MCP `.env` token, or the token used for `glab auth login`) must have `api` scope (full access). The `read_api` scope is insufficient for creating projects.
- For MCP: `GITLAB_READ_ONLY_MODE` must be `false` for project creation. If the server is in read-only mode, the create tool will not be available.
- Default visibility is `private`. Set `visibility` to `internal` or `public` explicitly when broader access is required.
- When `initializeReadme` is `false`, the project is created empty and `default_branch` may be `null` until the first push.
