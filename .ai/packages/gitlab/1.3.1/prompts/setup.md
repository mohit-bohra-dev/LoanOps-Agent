# Set Up GitLab Backend

Detect, install, and authenticate a working GitLab backend (the GitLab MCP server or the `glab` CLI) so the other GitLab prompts can run.

## Overview

The GitLab prompts in this package work through one of two backends:

- **GitLab MCP server** (preferred) — richer structured tools, configured via `promp.json` and a `.env` token.
- **glab CLI** (fallback) — used when the MCP server is not configured.

This prompt checks what is already available and guides you through configuring whichever backend you choose. It is **guided**: it runs detection automatically, but asks for confirmation before any command that installs software or changes credentials.

## Parameters

- **{{backend}}** (string, optional): Which backend to set up — `mcp`, `glab`, or `auto`
  - Default: `auto` (detect what's present; if neither, recommend glab as the fastest path)
- **{{hostname}}** (string, optional): GitLab host for glab auth
  - Default: `gitlab.pnmac.com`

## Instructions

### Step 1: Detect current state

#### Actions
- [ ] Check whether the GitLab MCP tools are available in your current tool set (`mcp_gitlab_*` / `create_merge_request` etc.).
- [ ] Check the glab CLI:
  - Run `command -v glab` to see if it is installed.
  - If installed, run `glab auth status` to see if it is authenticated to **{{hostname}}**.

#### Outputs
- **mcp_available**: Whether the GitLab MCP server tools are present
- **glab_installed**: Whether the `glab` binary is on PATH
- **glab_authenticated**: Whether `glab auth status` reports an authenticated session for **{{hostname}}**

#### Report
Summarize the detected state to the user before doing anything, e.g.:

```markdown
## GitLab Backend Status
- GitLab MCP server: <available | not configured>
- glab CLI installed: <yes | no>
- glab authenticated (<hostname>): <yes | no>
```

**STOP CONDITION (already working):** If `mcp_available` is true, **or** `glab_installed` and `glab_authenticated` are both true, report that a working backend already exists and return success without making changes (unless the user explicitly asked to set up the other backend via **{{backend}}**).

---

### Step 2: Choose the backend to configure

#### Actions
- [ ] If **{{backend}}** is `mcp` or `glab`, use that.
- [ ] If **{{backend}}** is `auto` and nothing is configured, recommend **glab** (fastest, no Cursor restart) but offer the MCP option. Ask the user which they want before proceeding.

---

### Step 3a: Configure the glab CLI

Only if the chosen backend is `glab`.

#### Actions

**Install (if `glab_installed` is false):**
- [ ] Detect the OS.
- [ ] On macOS, propose: `brew install glab`. **Ask the user to confirm before running it.**
- [ ] On Linux/other, do **not** auto-install — point the user to `https://gitlab.com/gitlab-org/cli/-/releases` and the package manager for their distro, then wait for them to install.
- [ ] After install, re-run `command -v glab` to confirm.

**Authenticate (if `glab_authenticated` is false):**
- [ ] Explain that authentication is interactive and needs a Personal Access Token with `api` scope (create at `https://{{hostname}}/-/profile/personal_access_tokens`).
- [ ] Propose: `glab auth login --hostname {{hostname}}`. **Ask the user to confirm before running it**, and let them complete the interactive prompts.
- [ ] Verify with `glab auth status` and `glab api user`.

#### Validation
- [ ] `command -v glab` succeeds.
- [ ] `glab auth status` reports authenticated for **{{hostname}}**.

---

### Step 3b: Configure the GitLab MCP server

Only if the chosen backend is `mcp`.

#### Actions
- [ ] Confirm the `gitlab` MCP server is declared in the active `promp.json` (it ships with this package). If the package is installed, it is.
- [ ] Guide the user to create a Personal Access Token at `https://{{hostname}}/-/profile/personal_access_tokens`:
  - `api` scope for write operations (open MR, reply to reviews), or `read_api` for read-only pipeline retrieval.
- [ ] Help add `GITLAB_PERSONAL_ACCESS_TOKEN=<token>` to a `.env` file in the workspace root. **Confirm with the user before writing to `.env`**, and ensure `.env` is in `.gitignore`:
  - Check: `grep "\.env" .gitignore` — if absent, propose `echo ".env" >> .gitignore`.
- [ ] Tell the user to **restart Cursor** so the MCP server loads with the new environment.

#### Validation
- [ ] `.env` contains `GITLAB_PERSONAL_ACCESS_TOKEN`.
- [ ] `.env` is gitignored.
- [ ] User has been told to restart Cursor (MCP availability can only be confirmed after restart).

---

### Step 4: Confirm and report

#### Actions
- [ ] Re-run the Step 1 detection for the configured backend (for MCP, note it requires a restart to verify).
- [ ] Return a structured result.

## Response Format

```json
{
  "success": true,
  "backend_configured": "glab",
  "mcp_available": false,
  "glab_installed": true,
  "glab_authenticated": true,
  "next_steps": "glab is ready. Run /gitlab.openMR, /gitlab.pipelineLogRetrieval, or /gitlab.addressMRReview."
}
```

## Error Handling

### InstallFailedError

Returned when installing glab fails.

```json
{
  "code": "INSTALL_FAILED",
  "message": "Failed to install glab",
  "details": "<error output>",
  "remediation": "Install manually from https://gitlab.com/gitlab-org/cli/-/releases, then re-run /gitlab.setup."
}
```

### AuthFailedError

Returned when glab authentication does not succeed.

```json
{
  "code": "AUTH_FAILED",
  "message": "glab authentication did not complete",
  "remediation": "Re-run: glab auth login --hostname gitlab.pnmac.com with a token that has 'api' scope."
}
```

## Examples

### Example 1: Nothing configured, set up glab

**Input:**
```json
{}
```

**Output:**
```json
{
  "success": true,
  "backend_configured": "glab",
  "mcp_available": false,
  "glab_installed": true,
  "glab_authenticated": true,
  "next_steps": "glab is ready. Run /gitlab.openMR."
}
```

### Example 2: Backend already working

**Input:**
```json
{}
```

**Output:**
```json
{
  "success": true,
  "backend_configured": "mcp",
  "mcp_available": true,
  "glab_installed": false,
  "glab_authenticated": false,
  "next_steps": "GitLab MCP server already available. No setup needed."
}
```

### Example 3: Explicitly set up the MCP server

**Input:**
```json
{ "backend": "mcp" }
```

**Output:**
```json
{
  "success": true,
  "backend_configured": "mcp",
  "mcp_available": false,
  "glab_installed": false,
  "glab_authenticated": false,
  "next_steps": "Token added to .env. Restart Cursor to load the GitLab MCP server."
}
```

## Notes

- This prompt never runs install or credential commands without explicit user confirmation.
- glab stores its own credentials from `glab auth login`; it does not read `GITLAB_PERSONAL_ACCESS_TOKEN` from `.env`. The two backends are configured independently.
- MCP availability cannot be verified until Cursor is restarted, so after MCP setup this prompt reports `mcp_available: false` with a restart instruction rather than a false positive.
- For the detection logic and operation mapping used by the other prompts, see the `gitlab-backend` skill.
