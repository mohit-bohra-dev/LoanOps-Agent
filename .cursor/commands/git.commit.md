---
promp:
  package: "git"
  version: "1.6.1"
  environment: "development"
  prompVersion: "1.0.1-beta.83"
  prompt: "commit"
---
# git.commit

Commit staged changes with an AI-generated message, with automatic pre-commit hook failure handling

## Parameter Specifications

- **`verificationMode`** (string) - *Optional*
  - Controls git hook verification behavior for the commit
  - Default: `full`

## Instructions

You are executing a Promp package prompt. Follow these steps:

1. **Parse the user input** to extract parameters:
   - Parameter 1: `verificationMode` (optional) [default: full] - Controls git hook verification behavior for the commit

2. **Replace parameter placeholders** in the prompt content below:
   - Parameters use the format `{{parameterName}}` in the prompt
   - Replace each placeholder with the corresponding parsed value
   - If a parameter is optional and not provided, use its default value (if specified)
   - If a required parameter is missing, ask the user to provide it

3. **Execute the prompt** with the replaced parameters

## Usage

When the user invokes this command, they may provide parameters in various ways:
- Space-separated values: `/git.commit value1 value2`
- Named parameters: `/git.commit param1=value1 param2=value2`
- Mixed format: `/git.commit value1 param2=value2`

Parse flexibly and map values to the expected parameters in order for positional arguments.

## Expected Output

Result of the commit operation

**Type:** `object`

**Properties:**

- `success` (boolean) - **Required** - Whether the operation completed successfully
- `commitHash` (string) - **Required** - The Git commit hash (SHA) of the created commit
- `commitMessage` (string) - **Required** - The generated commit message that was used
- `branch` (string) - **Required** - The current branch name
- `filesChanged` (number) - *Optional* - Number of files changed in the commit
- `preCommitFixesApplied` (boolean) - *Optional* - Whether pre-commit hook failures required fixes
- `fixesApplied` (array) - *Optional* - List of fixes that were applied due to pre-commit hooks
## Error Handling

### NoStagedChangesError

Error when there are no staged changes to commit

**Properties:**

- `code` (string) (values: ["NO_STAGED_CHANGES"]) - 
- `message` (string) - 

### PreCommitHookError

Error when pre-commit hook fails and cannot be automatically fixed

**Properties:**

- `code` (string) (values: ["PRE_COMMIT_HOOK_FAILED"]) - 
- `message` (string) - 
- `hookOutput` (string) - The output from the failed pre-commit hook
- `failedChecks` (array) - List of checks that failed

### CommitMessageGenerationError

Error when AI fails to generate a suitable commit message

**Properties:**

- `code` (string) (values: ["COMMIT_MESSAGE_GENERATION_FAILED"]) - 
- `message` (string) - 
- `reason` (string) - Reason why commit message generation failed

## Prompt Content

# Commit

Commit staged changes with an AI-generated commit message, with automatic pre-commit hook failure handling.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load @./.cursor\skills\git-commit\SKILL.md using the Read tool. That skill contains the complete commit workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to commit from memory or improvise the workflow. The skill is the sole source of truth.

Execute the entire workflow defined in the skill, including all steps, validation, error handling, and response formatting.

