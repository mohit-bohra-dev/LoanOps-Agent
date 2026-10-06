# Field Mapping Heuristics

Discovery rules consumed by `configure-jira` Steps 6 and 7. All matching is case-insensitive and tolerates hyphen / space variants.

## Step 6 — Logical Name to Live Field Name

Match each logical name against the `name` of every deduplicated custom field discovered on the project.

| Logical name (`fieldIds.<key>`) | Live field name candidates |
|---|---|
| `acceptanceCriteria` | `Acceptance Criteria` |
| `channel` | `Channel` |
| `workStream` | `Work-Stream`, `Work Stream` |
| `teams` | `Teams` |
| `storyPoints` | `Story Points`, `Story point estimate` |
| `bugEnvironment` | `Environment` |
| `bugSeverity` | `Severity` |
| `bugTestPhase` | `Test Phase` |
| `bugResponsibleTeam` | `Responsible Dev Team`, `Responsible Development Team` |
| `epicName` | `Epic Name` |
| `epicStartDate` | `Target Start`, `Start Date` |
| `epicEndDate` | `Target End`, `End Date` |
| `epicTheme` | `Theme` |

**Story Points tie-break.** When a project exposes both `Story Points` and `Story point estimate`, prefer the exact `Story Points` match. The latter is the team-managed variant and is usually the unused one; picking it writes points to a field no board reads.

**No match.** Set the key to `null` rather than omitting it — the schema requires every key to be present, and `null` is how the config expresses "this project does not expose that field."

**Unmatched required fields.** A custom field that is `required = true` on some issue type but matches no logical name is a `customExtras` candidate. Collect these and offer them to the user in Step 9, keyed by camelCase logical name.

## Step 7 — AC Mode Detection

For each discovered issue type:

1. The type's **live AC capability** is whether its field list includes the AC custom field ID resolved in Step 6.
2. The **detected mode** is `adf-field` when the AC field is present, `inline-description` when it is not.
3. Compare the detected mode against the package default for that type, documented in `../../create-jira-issues/references/issue-type-requirements.md`.
4. Emit `issueTypeOverrides[<type>].acceptanceCriteriaMode` **only when the detected mode differs from the package default.**

A project whose types all match the package defaults produces no AC overrides at all — that is the expected outcome, not a discovery failure.

## Step 7 — Channel Requirement Detection

For each discovered issue type, check whether the Channel field ID from Step 6 appears in that type's required fields.

Package defaults to compare against:

| Issue type | Package default for Channel |
|---|---|
| Story | required |
| Task | required |
| Bug | required |
| Sub-task | required |
| Epic | project-dependent |

Emit `issueTypeOverrides[<type>].channelRequired` only on divergence:

- `false` — the package default is "required" but Channel is not required on the live type
- `true` — the package default is "optional" but Channel is required on the live type

## Override Emission Rules

- An override entry holds only the keys that diverge. Never emit an empty object.
- `acceptanceCriteriaMode` is `adf-field` or `inline-description`.
- `channelRequired` is `true` or `false`.
- Types absent from the project produce no override entry.
