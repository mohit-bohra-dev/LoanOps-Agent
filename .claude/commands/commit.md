---
description: Stage files and generate a conventional commit message
allowed-tools: Bash(git status), Bash(git diff), Bash(git diff --cached), Bash(git add *)
---

## Step 1 — Show current status

Run `git status` to show the user what is modified, staged, and untracked.

Then ask the user:
> "Which files would you like to stage? (e.g. `.` for all, or specific paths)"

Wait for their response. Then run `git add <their answer>`.

## Step 2 — Generate commit message

Run `git diff --cached` to analyze what is now staged.

Generate a commit message following the **project's exact commit pattern**:

```
<type>(<scope>): <subject>

[optional body — one concise sentence explaining why, not what]
```

### Types
`feat` | `fix` | `docs` | `style` | `refactor` | `test` | `chore`

### Scope rules
- Single scope: `feat(web):`, `feat(api):`, `fix(api):`, `chore:`
- Multiple areas: comma-separate → `feat(api, web):`, `fix(api, web):`
- Module-level: `feat(copilot):`, `feat(auth):`, `fix(web):`

### Subject rules
- Present tense, imperative mood, ≤72 chars for the first line
- Do NOT capitalize the first word after the colon
- Do NOT end with a period

### Examples from this repo
```
feat(copilot): add VAD-driven auto-transcription with live interim text
fix(api, web): resolve Copilot flush handling issues and improve user feedback
fix(api): enhance dotenv loading and STT provider handling
feat(web): finalize System Design frontend implementation with routing and UI components
feat(api): implement System Design Simulator module with backend scaffolding and PII security
chore: update documentation with extended-scope task tracker
```

Output **only** the commit message, nothing else. $ARGUMENTS
