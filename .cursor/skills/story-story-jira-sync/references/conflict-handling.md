# Conflict Surfacing & Resolution

The story is the source of truth, but the sync must **not** silently overwrite
work done on the Jira side. When the diff shows Jira has diverged, the agent
stops, shows the divergence, and gets the user's decision before pushing. This
file defines what counts as a conflict, how to present it, and how each user
choice resolves.

## What Counts as a Conflict

Not every difference is a conflict. Distinguish three cases per field (the diff
verdicts come from `field-mapping.md`):

| Case | Local | Remote (Jira) | Treatment |
|---|---|---|---|
| Clean push | Changed | Matches the last-synced value (no independent Jira edit) | **Not a conflict.** The story moved forward; Jira is behind. Push the delta. |
| Conflict | Changed | Also changed away from the last-synced value | **Conflict.** Both sides edited the same field. Surface and confirm. |
| Destructive replace | AC removal/edit | Remote has bullets the local list would erase | **Conflict.** A `replace` would delete Jira-side bullets. Surface and confirm. |

If you cannot determine the last-synced value (e.g. no sync metadata recorded),
treat **any** field where local and remote both differ from each other as a
potential conflict and surface it — err toward asking, not overwriting.

## The Resolution Flow

1. **Detect.** During the per-field diff (delta-sync step 3), flag every field
   whose verdict is `conflict` per the table above.
2. **Halt the push.** Do not call `{{skill:jira.update-jira-issues}}` yet. A conflict
   on any field pauses the whole sync — you resolve before mutating Jira.
3. **Surface the divergence** field by field (format below). Show local, remote,
   and what the push would do.
4. **Ask for a decision** per conflicted field, or once for the whole set if the
   user prefers a blanket choice.
5. **Apply the decision** (resolve below), then push only the fields the user
   approved.
6. **Record** the outcome with the key (see `{{skill:story-source-model}}`,
   "Recording the Key") so the next sync has a fresh last-synced baseline.

## Presenting a Conflict

For each conflicted field show three things: the local (story) value, the remote
(Jira) value, and the action the push would take. Keep it scannable.

```text
Conflict on "summary"
  Local (story.md): "Retry failed payments with exponential backoff"
  Remote (Jira):    "Retry failed payments (backoff + jitter)"
  Push would:       overwrite Jira with the local value

Conflict on "acceptanceCriteria"
  Local adds:       "Retries stop after 24h"
  Remote has (not in local): "Backoff includes jitter"   ← would be erased by replace
  Push would:       replace the AC field, removing the jitter bullet
```

State plainly that the story is the source of truth, so the default action is to
push local — but that you are confirming because Jira changed too.

## User Choices

Offer three resolutions. Map the user's answer to a concrete action:

| Choice | Action |
|---|---|
| **Confirm / overwrite** | Push the local value for that field (the story wins). For AC, prefer keeping Jira-only bullets by switching to `acMergeMode="append"` when the only issue was additions; use `replace` only if the user explicitly wants Jira-side bullets removed. |
| **Skip** | Leave that field as-is in Jira; exclude it from the jira update call. The story and Jira stay divergent on that field by the user's choice. |
| **Abort** | Cancel the sync entirely. Push nothing. Report the conflicts so the user can reconcile the story manually first. |

Default, if the user gives no per-field instruction and the divergence is
additive-only, is the non-destructive path: `append`, preserving Jira's bullets.
Never default to a destructive `replace` without explicit confirmation.

## Acceptance-Criteria Conflicts Specifically

AC is the field most likely to conflict because two people often refine criteria
independently. The merge mode is the lever:

- **Additions only** → `append` resolves it cleanly with no data loss; usually no
  confirmation needed unless other fields conflict.
- **Local removed or rewrote a bullet that still exists in Jira** → `replace`
  would erase the Jira version. This is always a conflict — surface the specific
  bullets that would disappear and confirm before using `replace`.

When the user confirms a `replace`, pass the story's full AC list with
`acMergeMode="replace"`. When they prefer to keep Jira's wording, switch to
`append` (or skip the AC field).

## After Resolution

Once conflicts are resolved and the approved delta is pushed:

- Re-fetch or trust the jira update result as the new baseline.
- Update the recorded issue key / sync marker in the story so the next diff
  compares against the post-sync state, not the stale pre-conflict value.
- If the user chose **skip** on a field, note in the sync report that the story
  and Jira remain intentionally divergent there.
