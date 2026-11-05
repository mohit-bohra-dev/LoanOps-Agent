# Feature Specification: Eval Improvement Platform

**Feature Branch**: `feat/eval-improvement-platform`  
**Created**: 2026-11-03  
**Status**: Draft  
**Input**: User description: "Evolve MCP and AI Agent evaluation into an Enterprise AI Evaluation & Improvement Platform — Test, Observe, Review, Discover, Diagnose, Improve, Validate — with error analysis before automated judges; Observe/Evaluate/Learn portal IA; workflow and data model before thick UI."

### Problem Today (user-observable)

- Teams can run layered evaluation suites and see pass/fail, but cannot systematically inspect what the assistant did, why it failed, or which knowledge pipeline caused the miss.
- Feedback on answers (thumbs, comments, failure reasons) is not captured into a durable review workflow that feeds the Golden Dataset.
- Recurring failures are rediscovered by vibe check instead of being categorized, counted, and turned into regression cases.
- Product, QA, and engineering do not share one improvement loop that proves a fix actually helped.

### Users

- **Platform engineers**: instrument runs, fix tools/prompts/retrieval, ship regression gates.
- **QA / evaluation owners**: review traces, label failures, promote cases, track agreement.
- **Product managers**: prioritize failure categories by frequency and severity; judge release readiness.
- **Compliance (later)**: high-stakes review rubrics and auditability of promotions.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inspect a complete agent turn (Priority: P1)

As a platform engineer or QA reviewer, I want to open a single assistant turn and see the user request, tool timeline (including inputs and results), retrieved evidence, final answer, and citations, so that I can understand what actually happened without guessing.

**Why this priority**: Error analysis is impossible without complete, inspectable behavior. This is the Observe foundation for every later story.

**Independent Test**: Produce or load one completed turn with known tools and answer. Open it in the evaluation experience. Confirm query, timeline, results, answer, and citations are all visible (or clearly linked to the observability store).

**Acceptance Scenarios**:

1. **Given** a completed assistant turn exists, **When** I open it in Observe, **Then** I see the user request and final answer side by side with citations.
2. **Given** the turn called tools, **When** I expand the timeline, **Then** each step shows tool name, inputs, result (or a clear redacted/unavailable marker), and whether it failed.
3. **Given** the turn is stored in the observability system of record, **When** I choose “open externally,” **Then** I reach the same turn in that system without losing the identifier.

---

### User Story 2 - Review with failure categories (Priority: P1)

As a QA reviewer or PM, I want to mark a turn good or bad, assign a primary failure category and severity, name the responsible component, and leave a comment, so that failures become countable and actionable instead of free-text noise.

**Why this priority**: Categorization turns inspection into a prioritized backlog. Must ship with Observe feedback, not after elaborate dashboards.

**Independent Test**: Submit feedback on a known-bad turn with category `incorrect_answer`, severity `major`, and a comment. Confirm another reviewer can find that label on the same turn.

**Acceptance Scenarios**:

1. **Given** an open turn under review, **When** I mark it bad and choose a primary failure category from the controlled list, **Then** the label is saved with my identity and timestamp.
2. **Given** I select severity and root component, **When** I save, **Then** those fields appear on the review record and can be filtered later.
3. **Given** multiple categories apply, **When** I save, **Then** I can attach secondary categories while one primary remains required for aggregation.
4. **Given** I highlight an incorrect sentence in the answer, **When** I save, **Then** the review retains that highlight reference for later readers.

---

### User Story 3 - Promote reviewed failures into Golden candidates (Priority: P1)

As an evaluation owner, I want an approved review to become a Golden Dataset candidate that still requires human approval before it becomes an official regression case, so that production failures stop recurring without silently polluting the official set.

**Why this priority**: Closes the improvement loop; without promotion, review work dies in comments.

**Independent Test**: Approve a reviewed fail; confirm a candidate case appears for PR/approval and is not treated as official until approved through the existing governance path.

**Acceptance Scenarios**:

1. **Given** a reviewed bad turn with category and comment, **When** I promote it, **Then** a candidate case is created that references the source turn.
2. **Given** a candidate exists, **When** it has not been approved, **Then** it does not count as an official Golden case for release gates.
3. **Given** a candidate is approved through governance, **When** regression evaluation runs, **Then** that scenario can fail the suite if the old bug returns.

---

### User Story 4 - See evaluation health, not only a single run (Priority: P1)

As a PM or engineer, I want a clear health view of MCP, tool selection, arguments, trajectory, outcomes, robustness, operations, and governance results over recent runs, so that I know whether we are getting better or worse.

**Why this priority**: Arize-style Evaluate question; prevents shipping on vibes after one green run.

**Independent Test**: With at least two recorded evaluation runs (or fixture reports), open Evaluate and confirm pass/fail (or score) per layer and a comparison to the prior run.

**Acceptance Scenarios**:

1. **Given** recent offline evaluation results exist, **When** I open Evaluate, **Then** I see status for each evaluation layer the platform supports.
2. **Given** production operation scores are separated from offline scores, **When** I switch views, **Then** I do not mix the two score families on one undifferentiated chart.
3. **Given** a release is proposed, **When** I open the release gate panel, **Then** I see whether required layer checks and recent human review coverage meet the agreed bar.

---

### User Story 5 - Attribute failure to a knowledge or agent stage (Priority: P2)

As an engineer, I want failures diagnosed against capability search, API search, policy retrieval, graph-assisted retrieval, orchestration, and final generation, so that I fix the right pipeline instead of rewriting prompts blindly.

**Why this priority**: Highest leverage after basic review; depends on traces and stage scores existing.

**Independent Test**: Run a case known to fail retrieval (wrong document) versus one that retrieves correctly but answers wrong. Confirm stage attribution differs.

**Acceptance Scenarios**:

1. **Given** a turn with stage scores, **When** capability or API search missed the expected item, **Then** the diagnosis points at that retrieval stage rather than only “bad answer.”
2. **Given** retrieval was correct but the answer contradicts tool text, **When** diagnosis runs, **Then** the primary component is generation (or equivalent).
3. **Given** engineering-code search is not yet on the assistant path, **When** I view stages, **Then** that stage is absent or marked not applicable — not falsely failing.

---

### User Story 6 - Signal inbox of what matters (Priority: P2)

As a busy reviewer, I want a ranked inbox of sampled production failures, operation breaches, and unlabeled high-risk turns, so that I do not scroll an endless unprioritized trace list.

**Why this priority**: Makes human review sustainable; Arize “Signal” pattern.

**Independent Test**: Seed several fails with different severities/frequencies. Confirm the inbox ranks higher severity×frequency first and links into review.

**Acceptance Scenarios**:

1. **Given** sampled failures and operation breaches exist, **When** I open Signal, **Then** items are ranked by severity and frequency (or an equivalent explicit ranking rule).
2. **Given** an inbox item, **When** I open it, **Then** I land in the review workbench for that turn.
3. **Given** an item is reviewed, **When** I return to Signal, **Then** it is marked reviewed or leaves the default queue per policy.

---

### User Story 7 - Multi-reviewer agreement and adjudication (Priority: P2)

As an evaluation owner, I want two independent reviewers and a clear path when they disagree, so that ambiguous labels do not silently enter the Golden Dataset.

**Why this priority**: Required before trusting automated judges at scale.

**Independent Test**: Two reviewers label the same turn differently; confirm it enters adjudication and cannot promote until resolved.

**Acceptance Scenarios**:

1. **Given** two reviewers label the same turn, **When** labels agree, **Then** agreement metrics update and promotion may proceed under policy.
2. **Given** labels disagree, **When** either attempts promotion, **Then** the case is blocked pending adjudication.
3. **Given** an adjudicator resolves the disagreement, **When** resolution is saved, **Then** the official label is the adjudicated one.

---

### User Story 8 - Prove a fix improved quality (Priority: P2)

As a PM or engineer, I want to record an improvement cycle (top failure, hypothesis, change reference, baseline vs after evaluation) and see whether regressions appeared, so that “we fixed it” is evidence-based.

**Why this priority**: Learn loop; Arize “will this fix make things better?”

**Independent Test**: Create a cycle with baseline and post run identifiers; confirm the UI shows improved, unchanged, or regressed for the targeted failure category.

**Acceptance Scenarios**:

1. **Given** a baseline evaluation run and a later run after a change, **When** I open the improvement cycle, **Then** I see the targeted failure category rate before and after.
2. **Given** a new failure appears after the change, **When** the cycle is viewed, **Then** regression is clearly indicated.
3. **Given** no post run is linked yet, **When** I view the cycle, **Then** status shows awaiting validation — not success.

---

### User Story 9 - Observe / Evaluate / Learn navigation (Priority: P1)

As any portal user, I want the evaluation portal organized into Observe, Evaluate, and Learn areas that answer “what happened,” “are we better or worse,” and “did our fix help,” so that Engineers, PMs, and QA share one mental model.

**Why this priority**: Product IA; cheap to ship as navigation even while screens are thin.

**Independent Test**: Open the portal shell; confirm three top-level areas with the intended questions; thin Phase 1 content still routes correctly.

**Acceptance Scenarios**:

1. **Given** I open the evaluation portal, **When** I look at primary navigation, **Then** I see Observe, Evaluate, and Learn.
2. **Given** I am in Observe, **When** I follow a turn into review, **Then** Learn/promote actions remain reachable without leaving the turn context.
3. **Given** Phase 1 is thin, **When** a Learn screen is not fully built, **Then** I see an honest “coming soon / use governance CLI” state rather than a fake dashboard.

---

### User Story 10 - Experiment compare before shipping prompt or model changes (Priority: P3)

As an engineer, I want to compare two evaluation runs on the same scenario set (for example two prompts or models) and see which cases flipped, so that I do not deploy a change that only “feels” better.

**Why this priority**: Valuable after the core loop; Phase 3.

**Independent Test**: Two runs on the same case set with at least one flipped case; compare view lists the flip.

**Acceptance Scenarios**:

1. **Given** two runs share the same case identifiers, **When** I compare them, **Then** I see counts of newly passing, newly failing, and unchanged cases.
2. **Given** a case newly fails, **When** I open it, **Then** I can jump to Observe for that turn.

---

### User Story 11 - Suggested actions and advisory Eval Copilot (Priority: P3)

As an engineer, I want suggested next actions on a failure cluster (for example missing capability, stale policy, new assertion) that never auto-apply to production, so that diagnosis speeds up without bypassing human approval.

**Why this priority**: Advanced; must not precede human review discipline.

**Independent Test**: Open a cluster with known missing-API pattern; confirm a suggestion appears and applying it requires an explicit human-approved change path (for example a PR), never a silent write to live tools or auth.

**Acceptance Scenarios**:

1. **Given** a failure cluster has a recognizable pattern, **When** I view suggested actions, **Then** I see human-readable recommendations tied to the category.
2. **Given** a suggestion exists, **When** I attempt to apply it, **Then** the system does not mutate production auth, tools, or prompts without a human-approved change process.
3. **Given** Eval Copilot answers a question about failure rates, **When** it proposes a fix, **Then** the proposal is advisory and cited to the underlying review or score data.

---

### Edge Cases

- What happens when tool results are redacted or truncated — can review still proceed?
- What if a turn has no tools (refusal / small talk) — how is Observe rendered?
- What if two reviewers use different departments’ rubrics on the same turn?
- What if a candidate’s source turn is later deleted from the observability store?
- What if offline and production score names collide in the UI?
- What if severity is set without a primary category?
- What if Engineering KG / code search is not on the assistant path — how is that stage shown?
- What if sampled production volume is too low for meaningful Signal ranking?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to inspect a complete assistant turn including request, tool timeline with inputs/results (or explicit unavailability), answer, and citations.
- **FR-002**: Users MUST be able to submit binary good/bad feedback on a turn with reviewer identity.
- **FR-003**: Users MUST assign a primary failure category from a controlled vocabulary when marking a turn bad.
- **FR-004**: Users MUST be able to assign severity (`blocker` | `major` | `minor`) and a root component when reviewing a failure.
- **FR-005**: Users MUST be able to attach optional secondary failure categories and free-text comments.
- **FR-006**: Users MUST be able to reference highlighted answer spans or timeline steps on a review.
- **FR-007**: Users MUST be able to promote an adjudicated (or policy-approved) review into a Golden Dataset candidate that references the source turn.
- **FR-008**: Candidates MUST NOT become official Golden cases without explicit human approval through governance.
- **FR-009**: The portal MUST expose Observe, Evaluate, and Learn as primary navigation areas.
- **FR-010**: Evaluate MUST show recent health for the platform’s evaluation layers and keep production operation scores visually separate from offline evaluation scores.
- **FR-011**: The system MUST support stage-level diagnosis for capability search, API search, policy retrieval, graph-assisted retrieval (when used), orchestration, and final generation.
- **FR-012**: Signal MUST present a ranked inbox of high-value review targets (sampled fails, operation breaches, unlabeled high-risk turns).
- **FR-013**: The system MUST support at least two independent reviewers and block Golden promotion on unresolved disagreement.
- **FR-014**: Users MUST be able to create and view an improvement cycle linking a failure focus, change reference, baseline evaluation, and post-change evaluation.
- **FR-015**: Users MUST be able to compare two evaluation runs on the same scenario set and see newly passing and newly failing cases (P3).
- **FR-016**: Suggested actions and Eval Copilot MUST be advisory only and MUST NOT auto-apply production changes (P3).
- **FR-017**: Reviewers MUST be able to open the same turn in the observability system of record via a stable identifier.
- **FR-018**: Failure taxonomy v1 MUST include: wrong API selected, missing API, incorrect arguments, missing policy context, incorrect answer, unauthorized access, unnecessary tool calls, hallucination, SOP violation, unhandled tool error, and other.
- **FR-019**: Error analysis and human categorization MUST be usable before the product relies on automated LLM judges for those categories.
- **FR-020**: Release gate view MUST surface whether required evaluation checks and recent human review coverage meet the agreed bar.

### Non-Functional Requirements

- **NFR-001**: The platform MUST remain usable with a local-first evaluation store when cloud observability credentials are absent.
- **NFR-002**: Official evaluation pass thresholds MUST NOT be lowered to make new workflows look green.
- **NFR-003**: Authentication and authorization for tools MUST remain enforced server-side; the portal MUST NOT become a bypass.
- **NFR-004**: Review and promotion actions MUST be attributable (who, when) for audit.
- **NFR-005**: The product MUST NOT require a second primary evaluation database alongside the chosen observability/eval store.
- **NFR-006**: PII and secrets in traces MUST be redacted or omitted per existing safety policy before display or export.
- **NFR-007**: Offline evaluation scores and production operation scores MUST remain separable for dashboards and gates.
- **NFR-008**: Portal Phase 1 MAY be thin (links + forms) provided Stories 1–4 and 9 remain demonstrable.

### Key Entities *(business meaning)*

- **Agent turn / trace**: One user request and the assistant’s full behavior for that request.
- **Timeline step**: A tool or retrieval action within a turn.
- **Review label**: A human judgment on a turn (good/bad, categories, severity, comments).
- **Failure category**: Controlled reason a bad turn failed.
- **Root component**: Which part of the system is primarily responsible (retrieval family, orchestration, generation, security, etc.).
- **Golden candidate**: A proposed regression case not yet official.
- **Official Golden case**: An approved regression scenario that can fail releases.
- **Evaluation run**: A scored execution of a scenario set at a point in time.
- **Stage score**: Quality signal for one pipeline stage on a turn or case.
- **Signal item**: A prioritized work item for human review.
- **Improvement cycle**: A tracked attempt to fix a top failure and re-validate.
- **Adjudication**: Resolution of reviewer disagreement.

### Controlled Failure Taxonomy (v1) — user-facing labels

| Category key (stable) | User-facing meaning | Typical root component |
|---|---|---|
| `wrong_api_selected` | Wrong API/operation chosen | Capability / API retrieval |
| `missing_api` | Needed API/capability absent | Capability catalog / API index |
| `incorrect_arguments` | Tool inputs wrong | Agent planning |
| `missing_policy_context` | Needed policy/SOP not retrieved | Policy retrieval |
| `incorrect_answer` | Final answer factually wrong vs evidence | Generation |
| `unauthorized_access` | AuthZ/security violation | MCP security |
| `unnecessary_tool_calls` | Wasteful or inappropriate tools | Orchestration |
| `hallucination` | Claims not supported by evidence | Generation |
| `sop_violation` | Violates stated policy/SOP | Generation / policy retrieval |
| `tool_error_unhandled` | Tool failed and agent mishandled it | Orchestration / MCP |
| `other` | Does not fit above | Unknown |

Severity: `blocker`, `major`, `minor`.

---

## Success Criteria *(mandatory)*

- **SC-001**: Reviewers can complete labeled error analysis on a batch of approximately 100 turns without leaving the Observe/Review path for basic fields (good/bad, primary category, severity, comment).
- **SC-002**: At least one production or sampled failure path is demonstrably promoted to a Golden candidate with source-turn linkage in a pilot.
- **SC-003**: Evaluate view answers “better or worse” for supported layers across at least two consecutive runs.
- **SC-004**: For a seeded retrieval-miss versus generation-miss pair, stage diagnosis attributes different primary components.
- **SC-005**: Unresolved dual-reviewer disagreement blocks Golden promotion in the pilot workflow.
- **SC-006**: An improvement cycle can show improved / unchanged / regressed for a targeted failure category after a deliberate fix.
- **SC-007**: Portal primary nav always presents Observe, Evaluate, and Learn with the three guiding questions visible.
- **SC-008**: No official evaluation threshold is reduced as part of delivering this feature.

---

## Out of Scope

- Replacing the existing nine-layer evaluation methodology with a generic third-party framework as system of record.
- Adopting a second primary observability/eval platform (for example a competing hosted eval cloud) as the store of record for this feature.
- Auto-applying AI-suggested fixes to live tools, auth, or production prompts without human-approved change control.
- Fine-tuning models from review data (may reuse labels later; not this feature’s deliverable).
- Full multi-turn session evaluation UX (listed as later; not required for MVP Stories 1–4).
- Lowering existing Golden evaluation pass thresholds.
- Building a thick native Trace Explorer before the turn data model and feedback path exist (Phase 1 may deep-link).

---

## Dependencies & Constraints

- Builds on the existing layered evaluation suites, Golden Dataset governance, and observability/eval store already chosen by the platform.
- Human review must precede heavy reliance on automated LLM judges for new failure categories (methodology constraint).
- Engineering code-search stage evaluation waits until that capability is on the assistant path.
- Compliance department rubrics may extend taxonomy later without breaking v1 keys.

---

## Security & Privacy

- Trace display and export follow existing PII redaction and secret-handling rules.
- Tool authorization remains server-enforced; portal feedback cannot grant new tool powers.
- Review and promotion audit fields are retained for accountability.

---

## Open Questions

- **OQ-001**: Exact minimum human review coverage % for the release gate panel — [NEEDS CLARIFICATION: product number].
- **OQ-002**: Whether chat UI thumbs in the servicing app write into the same review queue as the portal in Phase 1 — default yes unless product separates them.
- **OQ-003**: Department-specific rubric catalog ownership (QA vs Compliance) for P2 multi-reviewer — [NEEDS CLARIFICATION].
