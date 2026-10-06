# Remove Submodule

Remove a submodule and clean up its git metadata.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load {{skill:git-submodule}} using the Read tool. That skill contains the complete submodule workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to remove a submodule from memory or improvise the workflow. The skill is the sole source of truth.

## Parameters

- **{{path}}** (string, required): The submodule path to remove.

## Instructions

Execute the skill's **Remove Workflow** using the parameter above, including all steps, validation, error handling, and response formatting. Return the Remove success JSON (with the `cleanedPaths` list) on success, or the appropriate error JSON (`SubmoduleNotFoundError`, `RemoveFailedError`) on failure.
