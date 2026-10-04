# Create Branch

Create and switch to a new Git branch, with support for the standard feature branch naming convention.

## Overview

This prompt creates a new Git branch and checks it out. It supports two modes:

1. **Direct branch name** - Create a branch with an exact name you provide
2. **Feature branch** - Create a branch following the `feature/[environment]/[feature-name]` convention, with environment defaulting to `dev`

## Prerequisites

- Current directory must be a Git repository

## Parameters

- **{{branchName}}** (string, optional): The full branch name to create
  - If provided, creates the branch with this exact name
  - If not provided, the prompt will construct a feature branch name from the other parameters

- **{{featureName}}** (string, optional): The feature name in kebab-case for a feature branch
  - Used to construct `feature/[environment]/[featureName]`
  - Required if `branchName` is not provided
  - Example: `add-user-auth`, `fix-login-redirect`

- **{{environment}}** (string, optional): The target environment for a feature branch
  - Must be one of: `dev`, `dev2`, `qa`, `qa2`, `stg`, `prod`
  - Default: `dev`
  - Only used when constructing a feature branch (i.e., when `branchName` is not provided)

- **{{baseBranch}}** (string, optional): The branch to create the new branch from
  - Default: current branch
  - Example: `main`, `develop`

- **{{push}}** (boolean, optional): Whether to push the new branch to the remote and set upstream tracking
  - Default: false

## Instructions

### Step 1: Validate Inputs and Determine Branch Name

#### Inputs
- **branchName** (from parameters, optional)
- **featureName** (from parameters, optional)
- **environment** (from parameters, optional, default: `dev`)

#### Actions

**Scenario A: branchName is provided**
- [ ] Use the provided `branchName` as-is
- [ ] Validate it follows Git branch naming rules (no spaces, no `..`, no trailing `.lock`, no control characters)

**Scenario B: branchName is not provided, featureName is provided**
- [ ] Validate `environment` is one of: `dev`, `dev2`, `qa`, `qa2`, `stg`, `prod`
- [ ] Validate `featureName` is kebab-case (lowercase, hyphens, no spaces)
- [ ] Construct branch name: `feature/{environment}/{featureName}`

**Scenario C: neither branchName nor featureName is provided**
- [ ] Ask the user what the branch should be called
- [ ] If the user describes a feature, construct a feature branch name using `feature/dev/{derived-kebab-case-name}`
- [ ] If the user gives an exact name, use it as-is

#### Outputs
- **resolved_branch_name**: The final branch name to create
- **is_feature_branch**: Whether it follows the feature branch convention

#### Validation
- [ ] **resolved_branch_name** is not empty
- [ ] **resolved_branch_name** does not already exist locally (check with `git branch --list`)
- [ ] Branch name follows Git naming rules

**CRITICAL STOP CONDITION**: If the branch already exists, **IMMEDIATELY RETURN** error:
```json
{
  "code": "BRANCH_EXISTS",
  "message": "Branch already exists",
  "branch": "{resolved_branch_name}",
  "suggestion": "Use 'git checkout {resolved_branch_name}' to switch to it, or choose a different name."
}
```

**CRITICAL STOP CONDITION**: If `environment` is not a valid value, **IMMEDIATELY RETURN** error:
```json
{
  "code": "INVALID_ENVIRONMENT",
  "message": "Invalid environment specified",
  "environment": "{environment}",
  "validEnvironments": ["dev", "dev2", "qa", "qa2", "stg", "prod"]
}
```

---

### Step 2: Prepare Base Branch

#### Inputs
- **baseBranch** (from parameters, optional)

#### Actions
- [ ] If **baseBranch** is provided, verify it exists: `git branch --list {baseBranch}` or `git rev-parse --verify {baseBranch}`
- [ ] If **baseBranch** is not provided, use the current branch (no extra action needed)

#### Outputs
- **base**: The branch to create from (provided value or current branch)

#### Validation
- [ ] **base** branch exists

**CRITICAL STOP CONDITION**: If the specified base branch does not exist, **IMMEDIATELY RETURN** error:
```json
{
  "code": "BASE_BRANCH_NOT_FOUND",
  "message": "Base branch does not exist",
  "branch": "{baseBranch}"
}
```

---

### Step 3: Create and Checkout the Branch

#### Inputs
- **resolved_branch_name** (from Step 1)
- **base** (from Step 2)

#### Actions
- [ ] If a **baseBranch** was explicitly provided:
  - Run `git checkout -b {resolved_branch_name} {base}`
- [ ] Otherwise:
  - Run `git checkout -b {resolved_branch_name}`
- [ ] Verify the checkout succeeded by running `git branch --show-current`

#### Outputs
- **checkout_success**: Whether the branch was created and checked out
- **current_branch**: The current branch after the operation

#### Validation
- [ ] **current_branch** equals **resolved_branch_name**

---

### Step 4: Push to Remote (Optional)

#### Inputs
- **push** (from parameters, optional, default: false)
- **resolved_branch_name** (from Step 1)

#### Actions
- [ ] Skip this step if **push** is false
- [ ] Run `git push -u origin {resolved_branch_name}` to push and set upstream tracking

#### Outputs
- **pushed**: Whether the branch was pushed to the remote
- **tracking_branch**: The upstream tracking branch (e.g., `origin/{resolved_branch_name}`)

---

### Step 5: Present Results

#### Actions
- [ ] Display the created branch name
- [ ] If it's a feature branch, highlight the environment

#### Output Format

```markdown
## Branch Created

**Branch:** {resolved_branch_name}
**Based on:** {base}
**Pushed:** {pushed ? "Yes (tracking origin/" + resolved_branch_name + ")" : "No (local only)"}
```

## Error Handling

### BranchExistsError

```json
{
  "code": "BRANCH_EXISTS",
  "message": "Branch already exists",
  "branch": "feature/dev/add-auth",
  "suggestion": "Use 'git checkout feature/dev/add-auth' to switch to it, or choose a different name."
}
```

### InvalidEnvironmentError

```json
{
  "code": "INVALID_ENVIRONMENT",
  "message": "Invalid environment specified",
  "environment": "staging",
  "validEnvironments": ["dev", "dev2", "qa", "qa2", "stg", "prod"]
}
```

### BaseBranchNotFoundError

```json
{
  "code": "BASE_BRANCH_NOT_FOUND",
  "message": "Base branch does not exist",
  "branch": "develop"
}
```

### InvalidBranchNameError

```json
{
  "code": "INVALID_BRANCH_NAME",
  "message": "Branch name contains invalid characters",
  "branch": "my branch name",
  "requirements": [
    "No spaces",
    "No '..' sequences",
    "Cannot end with '.lock'",
    "No control characters"
  ]
}
```

## Examples

### Example 1: Create a feature branch (default environment)

**Scenario:** Create a feature branch for adding authentication, defaulting to `dev` environment.

**Input:**
```json
{
  "featureName": "add-user-auth"
}
```

**Output:**
```json
{
  "success": true,
  "branch": "feature/dev/add-user-auth",
  "baseBranch": "main",
  "isFeatureBranch": true,
  "environment": "dev",
  "pushed": false
}
```

### Example 2: Create a feature branch for a specific environment

**Scenario:** Create a feature branch targeting the QA environment.

**Input:**
```json
{
  "featureName": "fix-payment-flow",
  "environment": "qa"
}
```

**Output:**
```json
{
  "success": true,
  "branch": "feature/qa/fix-payment-flow",
  "baseBranch": "main",
  "isFeatureBranch": true,
  "environment": "qa",
  "pushed": false
}
```

### Example 3: Create a branch with an exact name

**Scenario:** Create a branch with a specific name that doesn't follow the feature convention.

**Input:**
```json
{
  "branchName": "hotfix/critical-security-patch"
}
```

**Output:**
```json
{
  "success": true,
  "branch": "hotfix/critical-security-patch",
  "baseBranch": "main",
  "isFeatureBranch": false,
  "pushed": false
}
```

### Example 4: Create and push a feature branch from a specific base

**Scenario:** Create a feature branch from `develop` and push it immediately.

**Input:**
```json
{
  "featureName": "redesign-dashboard",
  "environment": "dev2",
  "baseBranch": "develop",
  "push": true
}
```

**Output:**
```json
{
  "success": true,
  "branch": "feature/dev2/redesign-dashboard",
  "baseBranch": "develop",
  "isFeatureBranch": true,
  "environment": "dev2",
  "pushed": true
}
```

## Notes

- When neither `branchName` nor `featureName` is provided, the prompt will ask the user interactively.
- Feature branch names are always constructed as `feature/{environment}/{featureName}`.
- The default environment is `dev` -- most new feature work starts there.
- The `branchName` parameter takes precedence; if provided, `featureName` and `environment` are ignored.
- Branch names are validated against Git's naming rules before creation.
