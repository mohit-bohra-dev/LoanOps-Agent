# Git Branching Structure

## Feature Branches

Feature branches follow the format:

```text
feature/[environment]/[feature-name]
```

### Environment Values

The environment segment must be one of:

| Environment | Purpose |
|-------------|---------|
| `dev`       | Primary development environment |
| `dev2`      | Secondary development environment |
| `qa`        | Primary QA/testing environment |
| `qa2`       | Secondary QA/testing environment |
| `stg`       | Staging / pre-production environment |
| `prod`      | Production environment |

### Branch Naming

The feature name segment should be kebab-case (lowercase with hyphens).

**Examples:**

```text
feature/dev/add-user-authentication
feature/qa/fix-payment-processing
feature/stg/update-dashboard-layout
feature/prod/hotfix-login-redirect
feature/dev2/refactor-api-client
feature/qa2/add-integration-tests
```

### Patterns

When creating or referencing branches, always use this structure:

```text
feature/{environment}/{feature-name}
```

Where `{environment}` is one of: `dev`, `dev2`, `qa`, `qa2`, `stg`, `prod`.

When creating new branches (e.g., via `git checkout -b`), default to `feature/dev/{feature-name}` unless the user specifies a different environment.
