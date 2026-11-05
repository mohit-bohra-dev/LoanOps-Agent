# Feature Specification: Web UI Process Pipeline

**Feature Branch**: `feat/web-ui-process-pipeline`  
**Created**: 2026-11-05  
**Status**: Draft  
**Input**: User description: "Build a pipeline that reads each application's web front-end project (for example the CoreComponents web app) and recovers the screens, how users move between them, and which backend operations each screen uses, so the platform has real multi-step process knowledge instead of one unverified draft."

### Problem Today (user-observable)

- The platform can find a single backend operation that sounds like the question, but it does not know which operation usually comes **before or after** another in real work.
- The only process knowledge available is a small, unreviewed draft extracted from written procedures; most steps have no link to an operation a user could actually call.
- The web front-ends that people really use every day (screens, menus, forms) are registered as part of each application but are **never read**, so their built-in sequence of work is invisible to the assistant.
- Multi-step questions ("what do I need before this?", "what else is related to this operation?") therefore get a single-operation answer or a wrong guess.

### Users

- **Platform engineers**: register applications, run extraction, fix gaps.
- **Process reviewers (operations / servicing subject experts)**: confirm that a recovered screen flow reflects how the work is really done.
- **Assistant users (care, ops, analysts, engineers)**: ask multi-step questions and expect related operations to be surfaced, with sources.
- **Product owners**: judge coverage and decide which applications to onboard next.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See an application's screens and what each one uses (Priority: P1)

As a platform engineer, I want to run the pipeline for a registered application and get a list of its screens, how they link to each other, and which backend operations each screen uses, so that the application's real workflow becomes visible instead of guessed.

**Why this priority**: Everything else (review, gaps, assistant answers) depends on having the recovered screens and their backend usage. This is the foundation and a viable MVP on its own as a report.

**Independent Test**: Register one application that has a front-end project. Run the pipeline against a known commit. Confirm the output lists known screens, shows at least one navigation link between two screens, and lists the backend operations used by a screen known to call one.

**Acceptance Scenarios**:

1. **Given** an application with a registered front-end project, **When** I run the pipeline, **Then** I get one entry per discovered screen with a route or address, a human-readable label, and the source file it came from.
2. **Given** a screen that links to another screen (menu item, link, or button), **When** the pipeline finishes, **Then** the link appears as an ordered connection between the two screens.
3. **Given** a screen that triggers a backend operation, **When** the pipeline finishes, **Then** that operation is listed for the screen and marked as either "matched to a known operation" or "unmatched".
4. **Given** the front-end project uses a technology the pipeline cannot read, **When** I run the pipeline, **Then** I am told clearly which parts were skipped and why, rather than getting an empty result.

---

### User Story 2 - Review and approve recovered flows (Priority: P1)

As a process reviewer, I want every recovered flow to start as a proposal that I can approve or reject, with the evidence shown, so that the assistant never treats an unverified guess as fact.

**Why this priority**: The platform's existing rule is that process knowledge is advisory and starts unreviewed. Without review, results cannot be trusted for any answer.

**Independent Test**: Take the output from Story 1, open one proposed flow, approve it and reject another. Confirm the decision, reviewer, and time are recorded and the rejected flow is excluded from any later use.

**Acceptance Scenarios**:

1. **Given** newly extracted flows, **When** I list them, **Then** each shows status "pending review" and the source evidence (application, commit, file, lines).
2. **Given** a pending flow, **When** I approve it, **Then** its status changes to approved and the approval is attributed to me with a timestamp.
3. **Given** an approved flow, **When** the application's source changes in a way that affects that flow, **Then** the flow becomes "needs re-approval" until reviewed again.
4. **Given** a rejected flow, **When** extraction runs again on unchanged source, **Then** the rejection is remembered and the flow is not re-proposed as new.

---

### User Story 3 - See what the pipeline could not resolve (Priority: P2)

As a platform engineer, I want a clear list of gaps (screens with no detected backend use, backend calls that match no known operation, unsupported parts), so that I know what to fix before relying on the results.

**Why this priority**: Gaps decide whether the data is good enough. It is useful immediately but not required for the first report.

**Independent Test**: Run on a project known to contain one backend call that matches no catalog entry. Confirm that call appears in the gap list with its source location.

**Acceptance Scenarios**:

1. **Given** a screen calls something that matches no known operation, **When** the run finishes, **Then** the gap list names the screen, the unmatched call, and where it was found.
2. **Given** a known operation that no screen uses, **When** I request coverage, **Then** it is listed as "not seen in any screen" (informational, not an error).
3. **Given** I fix the cause of a gap and re-run, **When** the run finishes, **Then** the gap no longer appears.

---

### User Story 4 - Related steps appear in assistant answers (Priority: P2)

As an assistant user asking a multi-step question, I want the assistant to also surface the operations that come right before or after the one it found, using only approved flows, so that I get the full picture instead of a single call.

**Why this priority**: This is the end-user payoff, but it depends on Stories 1 and 2 and must stay off until data quality is proven.

**Independent Test**: With one approved flow loaded and the capability turned on, ask a question whose best direct match is the middle of that flow. Confirm the answer references the neighbouring operations and cites where that knowledge came from. Turn the capability off and confirm answers return to the previous behaviour.

**Acceptance Scenarios**:

1. **Given** an approved flow containing the operation the assistant found, **When** the capability is on, **Then** the next and previous operations in the flow are offered as "related steps" after the direct matches.
2. **Given** only pending or rejected flows exist, **When** the capability is on, **Then** no related steps are offered.
3. **Given** the capability is off, **When** the same question is asked, **Then** the answer is identical to today's behaviour.
4. **Given** related steps are shown, **When** I read the answer, **Then** each related step shows it came from an approved application flow, not from live data.

---

### User Story 5 - Keep results fresh as applications change (Priority: P3)

As a platform engineer, I want to re-run the pipeline when an application changes and have unchanged applications skipped, so that results stay current without wasted work.

**Why this priority**: Important for long-term trust but not needed to prove value.

**Independent Test**: Run twice on the same commit and confirm the second run reports "no change". Change one screen's link in a test copy and confirm only that screen's flow is flagged as changed.

**Acceptance Scenarios**:

1. **Given** an application whose source has not changed since the last run, **When** I run the pipeline, **Then** it reports no change and does no extraction work.
2. **Given** a changed screen, **When** I run the pipeline, **Then** only affected flows are updated and flagged for re-review.

---

### Edge Cases

- What happens when two screens are reachable from the same menu on every page (shared navigation)? Are flows duplicated or merged?
- How does the pipeline treat screens reachable only after sign-in, or only for certain roles?
- What if a screen reaches the backend through a generic helper so the specific operation cannot be determined?
- How are screens that are generated at run time (data-driven menus, lazy-loaded routes) handled?
- What if navigation forms a loop (screen A to B to A)?
- What happens when the same operation is used by many screens in unrelated flows?
- How does the pipeline behave when the repository is private, unreachable, or the checkout is partial?
- What if a screen is hidden behind a feature toggle and may not exist in production?
- How should pages in shared libraries used by several applications be attributed?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Platform engineers MUST be able to declare, per registered application, which front-end project(s) belong to it.
- **FR-002**: System MUST extract, for each declared front-end project, the screens with their address, a human-readable label, and the source location.
- **FR-003**: System MUST extract navigation links between screens (menus, links, buttons that move the user) and preserve their order where order is defined by the source.
- **FR-004**: System MUST identify, for each screen, the backend operations it uses and mark each as matched or unmatched against the platform's known operations.
- **FR-005**: Every extracted fact MUST carry provenance: application, commit, file, and line range, plus a confidence level.
- **FR-006**: All extracted flows MUST start in a "pending review" state and MUST NOT be used by the assistant until approved.
- **FR-007**: Reviewers MUST be able to list, approve, and reject flows, and each decision MUST record who decided and when.
- **FR-008**: System MUST mark an approved flow "needs re-approval" when the underlying source changes in a way that affects it, and MUST remember rejections across re-runs on unchanged source.
- **FR-009**: System MUST produce a gap report listing unmatched backend calls, screens with no detected backend use, and unsupported technologies or files.
- **FR-010**: System MUST report clearly when a front-end technology is unsupported instead of returning an empty or partial result silently.
- **FR-011**: A re-run on unchanged source MUST be a no-op that reports no change.
- **FR-012**: Recovered flow knowledge MUST remain advisory: it MUST NOT grant, deny, or alter which operations may be called.
- **FR-013**: When the related-steps capability is enabled, System MUST offer neighbouring operations from **approved** flows only, clearly labelled as coming from application flows.
- **FR-014**: The related-steps capability MUST be off by default and, when off, MUST leave current assistant behaviour unchanged.
- **FR-015**: System MUST NOT capture personal or customer data; only structural information about screens, links, and operation names is recorded.
- **FR-016**: System MUST work from a local copy of the source with no cloud credentials and without running the application.

### Non-Functional Requirements

- **NFR-001**: Extraction for one typical front-end project MUST complete within 10 minutes. [NEEDS CLARIFICATION: confirm target against the largest pilot project]
- **NFR-002**: Results MUST be deterministic: the same source revision produces the same output.
- **NFR-003**: Source access MUST be read-only and no secrets or credentials may appear in outputs, logs, or stored results.
- **NFR-004**: Adding this feature MUST NOT lower any existing evaluation threshold or change existing assistant results when the related-steps capability is off.
- **NFR-005**: Review decisions and extraction runs MUST be auditable after the fact.

### Key Entities *(include if feature involves data)*

- **Screen**: a place a user can be in an application (a page or view); has an address, a label, and a source location; belongs to one application.
- **Navigation link**: a way to move from one screen to another; has an order and a kind (menu, link, button, redirect).
- **Operation use**: the fact that a screen triggers a backend operation; matched to a known operation or marked unmatched; carries evidence and confidence.
- **Flow**: an ordered set of screens and the operations they use, proposed from the navigation links; has a review status and a source-change indicator.
- **Review decision**: an approval or rejection of a flow by a named reviewer at a point in time.
- **Gap**: something the pipeline could not resolve, with a location and a reason.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For the pilot application, at least 90% of detected screen-to-backend calls are matched to a known operation. [NEEDS CLARIFICATION: confirm threshold after the first inventory run]
- **SC-002**: 100% of extracted facts carry provenance (application, commit, file, lines).
- **SC-003**: A reviewer can review and decide on a pilot application's proposed flows in one sitting of under 30 minutes.
- **SC-004**: On a prepared set of multi-step questions, the right neighbouring operation appears in the related steps for at least 70% of questions with the capability on, with no loss on single-lookup questions. [NEEDS CLARIFICATION: confirm target with evaluation owners]
- **SC-005**: With the related-steps capability off, results on the existing evaluation sets are unchanged.
- **SC-006**: A second run on unchanged source reports no change in under 1 minute.

---

## Dependencies & Constraints

### External Dependencies

- Read access to each application's source repository: needed to read its front-end project.
- The platform's existing catalog of known backend operations: needed to match what screens call.
- Human reviewers with process knowledge: needed to approve flows.

### Business Constraints

- Process knowledge stays advisory and starts unreviewed (existing platform rule).
- Existing evaluation thresholds must not be lowered.
- Introducing new configuration settings or a new architecture decision requires explicit approval before build.

---

## Security & Privacy Considerations

### Privacy Considerations

- What user data is collected? None. Only screen addresses, labels, link structure, and operation names.
- How long is data retained? Same retention as other application knowledge; superseded by each new run for a commit.
- Who has access to the data? Same audience as existing application knowledge; review actions are attributed to named reviewers.
- Are there regulatory requirements? No customer data is touched; source access follows existing repository access rules.

---

## Out of Scope

The following are explicitly OUT OF SCOPE for this feature:

- Watching or recording how real users move through the application - this feature reads source structure, not behaviour or analytics.
- Screenshots, visual analysis, or running the application - structural reading only.
- Automated user-interface testing - a different goal.
- Anything that changes data or calls write operations - the platform is read-only.
- Generating flows with a language model - extraction is deterministic; model-assisted investigation is a later, separate decision.
- Re-extracting written procedures - the existing procedure pipeline is unchanged.
- Onboarding every application at once - one pilot application first, then others.

These may be considered for future iterations.

---

## Open Questions

1. **Q**: What technology is each pilot front-end built with, and how does it reach backend operations?  
   **Status**: open - to be answered by the first inventory step before extraction is built.  
   **Answer**: (pending)

2. **Q**: Which application is the pilot, and which flows matter most to reviewers?  
   **Status**: open  
   **Answer**: (pending; candidates are the applications whose registry entries already list a web deployable)

3. **Q**: Where should reviewers do their review first (command line, or a screen in the existing web app)?  
   **Status**: open  
   **Answer**: (pending; the spec assumes command line first, screen later)

4. **Q**: Are some screens only reachable after sign-in or for certain roles, and should flows record that?  
   **Status**: open  
   **Answer**: (pending)

---

## Stakeholders & Reviewers

- **Product Owner**: [NEEDS CLARIFICATION: name]
- **Technical Lead**: [NEEDS CLARIFICATION: name]
- **Other Stakeholders**: process reviewers (servicing / operations), evaluation owners
