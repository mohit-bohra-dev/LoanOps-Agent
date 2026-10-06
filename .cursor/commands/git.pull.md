---
promp:
  package: "git"
  version: "1.6.1"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "pull"
---
# git.pull

Pull latest remote changes using a stash-based rebase workflow that safely preserves local work-in-progress

## Parameter Specifications

No parameters required.

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - No parameters required for this prompt

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/git.pull value1 value2`
- Named parameters: `/git.pull param1=value1 param2=value2`
- Mixed format: `/git.pull value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of the pull operation

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the operation completed successfully
- `branch` (string) - **Required** - The current branch name
- `newCommitsPulled` (boolean) - **Required** - Whether new commits were fetched from remote
- `stashUsed` (boolean) - **Required** - Whether local changes were stashed and restored
- `mergeConflictsResolved` (boolean) - **Required** - Whether stash pop conflicts were encountered and auto-resolved
- `resolvedFiles` (array) - *Optional* - List of files where merge conflicts were resolved
## Error Handling

### StashError

Error when git stash fails

**Properties:**

- `code` (string) (values: ["STASH_FAILED"]) - 
- `message` (string) - 
- `stashOutput` (string) - The output from the failed stash command

### PullError

Error when git pull --rebase fails

**Properties:**

- `code` (string) (values: ["PULL_FAILED"]) - 
- `message` (string) - 
- `pullOutput` (string) - The output from the failed pull command
- `recoverySteps` (array) - Suggested recovery steps

### StashPopConflictError

Error when stash pop produces merge conflicts too complex to auto-resolve

**Properties:**

- `code` (string) (values: ["STASH_POP_CONFLICT"]) - 
- `message` (string) - 
- `conflictedFiles` (array) - List of files with unresolved conflicts
- `localChanges` (string) - Description of stashed local changes
- `remoteChanges` (string) - Description of newly pulled remote changes
- `clarificationNeeded` (string) - Specific questions that need user input to resolve

### NetworkError

Error when network connectivity issues prevent pull

**Properties:**

- `code` (string) (values: ["NETWORK_ERROR"]) - 
- `message` (string) - 

### AuthenticationError

Error when authentication fails for remote repository

**Properties:**

- `code` (string) (values: ["AUTHENTICATION_FAILED"]) - 
- `message` (string) - 
- `remote` (string) - The remote URL that failed authentication

### RebaseError

Error when rebase fails during pull due to corrupted repository state

**Properties:**

- `code` (string) (values: ["REBASE_FAILED"]) - 
- `message` (string) - 
- `rebaseOutput` (string) - The output from the failed rebase operation
- `recoverySteps` (array) - Suggested recovery steps

## Prompt Content

# Pull with Rebase

Pull the latest remote changes using a stash-based rebase workflow that safely preserves local work.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\git-pull\SKILL.md using the Read tool. That skill contains the complete pull workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to pull from memory or improvise the workflow. The skill is the sole source of truth.

Execute the entire workflow defined in the skill, including all steps, validation, error handling, and response formatting.

