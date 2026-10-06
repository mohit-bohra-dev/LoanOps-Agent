---
promp:
  package: "git"
  version: "1.6.1"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "push"
---
# git.push

Push the current branch to the remote origin, failing immediately if the remote has diverged

## Parameter Specifications

- **`verificationMode`** (string) - *Optional*
  - Controls git hook verification behavior for the push
  - Default: `full`

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `verificationMode` (optional) [default: full] - Controls git hook verification behavior for the push

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/git.push value1 value2`
- Named parameters: `/git.push param1=value1 param2=value2`
- Mixed format: `/git.push value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of the push operation

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the operation completed successfully
- `branch` (string) - **Required** - The branch name that was pushed to
- `commitHash` (string) - **Required** - The commit SHA that was pushed
## Error Handling

### RemoteChangesError

Error when push is rejected because the remote has commits not present locally

**Properties:**

- `code` (string) (values: ["REMOTE_CHANGES_EXIST"]) - 
- `message` (string) - 
- `branch` (string) - The branch that was being pushed to
- `commitHash` (string) - The local commit hash that failed to push
- `pushOutput` (string) - The output from the rejected push command

### PushHookError

Error when push hook fails (not retried)

**Properties:**

- `code` (string) (values: ["PUSH_HOOK_FAILED"]) - 
- `message` (string) - 
- `hookOutput` (string) - The output from the failed push hook
- `commitHash` (string) - The commit hash that was created (commit succeeded but push failed)

### NetworkError

Error when network connectivity issues prevent push

**Properties:**

- `code` (string) (values: ["NETWORK_ERROR"]) - 
- `message` (string) - 
- `commitHash` (string) - The commit hash that was created (commit succeeded but push failed)

### AuthenticationError

Error when authentication fails for remote repository

**Properties:**

- `code` (string) (values: ["AUTHENTICATION_FAILED"]) - 
- `message` (string) - 
- `remote` (string) - The remote URL that failed authentication

### ProtectedBranchError

Error when pushing to a protected branch without permissions

**Properties:**

- `code` (string) (values: ["PROTECTED_BRANCH"]) - 
- `message` (string) - 
- `branch` (string) - The protected branch name
- `requiredPermissions` (array) - List of required permissions

## Prompt Content

# Push

Push the current branch to the remote origin.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\git-push\SKILL.md using the Read tool. That skill contains the complete push workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to push from memory or improvise the workflow. The skill is the sole source of truth.

Execute the entire workflow defined in the skill, including all steps, validation, error handling, and response formatting.

