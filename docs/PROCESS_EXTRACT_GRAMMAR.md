# Process extract grammar (ADR-028)

Detector: `process_rules` version `1.0.0`.

Anything not matching a pattern below becomes a `needs_review` item.
Never invent branch destinations or missing content from lossy exports.

## Supported patterns

### Header
- Procedure id: `DP\d+-[A-Za-z]+\d+\.v\d+`
- Effective / revised date: `Effective Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})` or `Date Revised:\s*(\d{1,2}/\d{1,2}/\d{2,4})`

### Sections
Fixed headings (case-insensitive, optional `**`):
`Purpose`, `Scope`, `Procedures`, `Monitoring and Reporting`, `Training`,
`Authority`, `Related Policies and Procedures`, `Related Policies`,
`Document Maintenance`, `Job Aid`.

### Hub topics
Markdown links inside a cell or section labeled `Topics`:
`[Title](/wiki/spaces/.../pages/{id}...)` or absolute pennymac.atlassian.net URLs.

### Ordered steps
Numbered list under `Procedures` / `Job Aid`:
`^\d+\.\s+(.+)$`

Nested bullets under a step:
`^[-*]\s+(.+)$` (indent depth tracked).

### Decisions and branches
1. Bullet `If yes` / `If no` / `If yes,` / `If no,` → decision with labels `Yes` / `No`.
2. Line `^(If|When)\s+(.+?),\s*(.+)$` → decision; guard = clause before comma; action = after.
3. `continue to the next step` → transition to following ordinal step.
4. Terminal phrases (from maps): `Stop here`, `not EFTA sensitive`, `Stop.` → `stepKind=end`.
5. `wait until ... then ...` / `wait until ... and analyze` → `needs_review` (action+jump).
6. Lines containing `do it anyway` / `Important:` with override language → `transitionKind=override` + `needs_review`.

### Thresholds
- `(\d+)\s+calendar\s+days?` → unit `calendar_days`
- `(\d+)\s+business\s+days?` → unit `business_days`
- `(\d+)\s+days?` (no calendar/business) → unit `days_unspecified`
- `(?:>=|≥)\s*(\d+)\s+months?` or `(\d+)\s+months?` → unit `months`

Keep exact matched text in `thresholdText`. No silent unit conversion.

### Gazetteers (approved maps)
- Systems → `usesSystem`
- Regulations → `governedBy`
- Phrase → operation key → candidate `CapabilityLink` (`linkStatus=unverified`)

### Provenance
Each node: `sourceSection`, `sourceOrdinal`, page id, version, content hash.
Labels only — no SOP quotes in graph output.

### Source completeness
- If Confluence `lossyConversion` or `lostFeatures` non-empty → `lossy_unverified`
- Else → `complete_unverified`
- Only a human sets `verified_complete`
