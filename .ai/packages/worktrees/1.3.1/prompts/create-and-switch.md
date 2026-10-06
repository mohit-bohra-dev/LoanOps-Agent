# Create and Switch Worktree

Create a new git worktree (optionally on a new feature branch), run its setup hooks, and switch the active workspace to it.

> **PREREQUISITE — YOU MUST DO THIS FIRST**
>
> Before performing any actions, you MUST read and load {{skill:create-and-switch-worktree}} using the Read tool. That skill contains the complete create-then-switch workflow — every step, validation rule, error handler, and response format. Do NOT proceed until you have read the skill file in full. Do NOT attempt to create or switch worktrees from memory or improvise the workflow. The skill is the sole source of truth.

Branch options (pass at most one):

- **{{newBranch}}** — create a new feature branch in the worktree (uses the detached-HEAD-first technique with rollback). Follow the `feature/{environment}/{feature-name}` convention where applicable.
- **{{branch}}** — check out an existing branch, tag, or commit.
- (none) — create a new branch named after the worktree directory.

Execute the entire workflow defined in the skill, including all steps, validation, error handling, and response formatting. The switch step is best-effort: a failed switch never invalidates a successfully created worktree.
