# Feature Specification: Enterprise App Scale

**Feature Branch**: `vdd`  
**Created**: 2026-10-08  
**Status**: Draft  
**Input**: User description: "LoanOps (an internal, citation-grounded AI assistant reached from Cursor chat and a web UI) must discover and read data from 30+ enterprise applications reliably, as an enterprise product rather than a proof of concept."

### Problem Today (user-observable)

- Only a handful of applications are reachable. The list of reachable applications is kept by hand in two places, and the two lists drift apart.
- Each added application makes the assistant slower to become ready after a restart. One unreachable application can quietly disappear from search with no warning.
- Live data reads fail as "unauthorized" because a single credential is used for every application. Users cannot tell "this application has not granted access" apart from "the system is broken". In a smoke test on 2026-10-08 the assistant found the correct operations for loan summary, payment schedules, and escrow, but all three live reads came back unauthorized.
- The capability catalog (what exists and which code owns it) and the list of callable operations do not match. Asking for a capability by name sometimes cannot be turned into a call.
- An application's source and its live address are not stored together. Knowing which code owns a capability does not give the address to call, and knowing a live address does not say which source it came from.
- Search quality and speed get worse as the number of operations grows into the thousands.

### Users

- **Internal users**: engineers, product managers, operations staff, and analysts who ask questions through Cursor chat or the web UI.
- **Platform operators**: onboard applications, watch system health, and fix problems.
- **Application-owning teams**: publish their application's operation descriptions and grant (or withhold) access.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register an application once, use it everywhere (Priority: P1)

As a platform operator, I want to register a new enterprise application in one place, so that it becomes discoverable and callable from every assistant surface (Cursor chat, web UI) without me updating any second list.

**Why this priority**: The hand-kept, duplicated application list is the root cause of drift and the main blocker to reaching 30+ applications. Every other story depends on applications actually being onboarded, and a single onboarding path alone already delivers value: more applications become reachable without errors.

**Independent Test**: Register one new sample application in the single registration place. Confirm that, with no other manual step, its operations show up in discovery from both Cursor chat and the web UI and that one of its read-only operations can be called.

**Acceptance Scenarios**:

1. **Given** an application is not registered, **When** an operator registers it once, **Then** its read-only operations become discoverable from every assistant surface after the next catalog refresh, with no second list to edit.
2. **Given** an application is registered, **When** a user asks a question that one of its operations answers, **Then** the assistant can find and call that operation.
3. **Given** an operator retires an application, **When** the next catalog refresh completes, **Then** its operations no longer appear in discovery and cannot be called.
4. **Given** an operator registers an application whose details are incomplete or invalid, **When** they submit it, **Then** they are told what is wrong and other applications are not affected.
5. **Given** an operator registers an application, **When** the registration is saved, **Then** that one record links the application's source and its live address for the chosen environment. A later question can use the source for provenance and the address for a live read, without a second list.

---

### User Story 2 - Find and cite the right operation across 30+ applications (Priority: P1)

As an internal user, I want to ask a question in plain language and have the assistant quickly find the right read-only operation among all registered applications, call it, and cite it, so that I get a grounded answer without knowing which application owns the data.

**Why this priority**: This is the core user value of the product. Without fast, accurate discovery at scale, onboarding more applications makes answers worse, not better.

**Independent Test**: With 30+ sample applications and thousands of sample operations registered, ask a set of benchmark questions with known correct operations. Measure whether the correct operation is in the top results, how long discovery takes, and whether each answer cites the application and operation used.

**Acceptance Scenarios**:

1. **Given** 30+ applications are registered, **When** a user asks for a loan's payment schedule, **Then** the assistant identifies the correct operation and owning application within the discovery latency target.
2. **Given** the assistant answers using live data, **When** the answer is shown, **Then** every factual statement carries a citation naming the application and operation it came from.
3. **Given** two applications expose operations with the same name, **When** the assistant presents or uses either one, **Then** the user can see which application each belongs to and the two are never confused.
4. **Given** no registered operation can answer the question, **When** the user asks it, **Then** the assistant says so plainly and does not make up an answer.

---

### User Story 3 - Fast start and per-application failure isolation (Priority: P1)

As an internal user and as a platform operator, I want the assistant to be ready quickly after a restart and to keep working when some applications are down or misconfigured, so that one bad application never takes down or silently weakens the whole system.

**Why this priority**: At 30+ applications, some will be unavailable at any given moment. If readiness time grows with application count, or one failure silently removes an application from search, the product is not enterprise-grade.

**Independent Test**: Register 30+ sample applications, then make several unreachable or misconfigured. Restart the assistant. Measure time to ready, confirm the healthy applications are discoverable and callable, and confirm the failing applications are reported as failing and not just missing.

**Acceptance Scenarios**:

1. **Given** 30+ applications are registered, **When** the assistant restarts, **Then** it is ready to answer questions within the readiness target, whatever the number of applications.
2. **Given** one application's operation description cannot be fetched, **When** the catalog refreshes, **Then** every other application stays discoverable and the failing application is reported as degraded, not silently dropped.
3. **Given** an application is down at call time, **When** a user's question needs it, **Then** the user is told that application is unavailable right now, and other parts of the answer that do not depend on it are still given.
4. **Given** an application keeps failing, **When** further requests arrive, **Then** the rest of the system's response times are not affected.

---

### User Story 4 - Correct access per application, with clear access errors (Priority: P1)

As an internal user, I want each live read to use the access that fits that application, and to be told clearly when an application has not granted access, so that I can tell "no access to this app" apart from "the system is broken".

**Why this priority**: The 2026-10-08 smoke test showed discovery working but every live read failing as unauthorized. Without per-application access, discovery at scale delivers no live data.

**Independent Test**: Configure two sample applications with different access arrangements and a third with no access granted. Ask questions that need each one. Confirm the first two return data and the third returns a clear message naming the application that lacks access.

**Acceptance Scenarios**:

1. **Given** applications A and B need different access, **When** a user's questions need data from each, **Then** each read uses the access set up for that application and both succeed.
2. **Given** application C has not granted access, **When** a user's question needs C, **Then** the assistant says C has not granted access, and does not report a generic failure.
3. **Given** access to an application has been revoked, **When** the next read is attempted, **Then** the user gets the same clear "no access" message and operators can see that access is no longer working.
4. **Given** the organization later changes how access is obtained (for example, a service identity or acting on behalf of the user), **When** that change is made, **Then** onboarding, discovery, and user-facing behavior do not need to be redesigned.

---

### User Story 5 - Capabilities and callable operations are one thing (Priority: P2)

As an internal user, I want anything I find in the capability catalog by name to be callable (when it is read-only and I am permitted), with provenance showing which application and owning code it comes from, so that the catalog and the callable list never disagree.

**Why this priority**: The mismatch causes confusing dead ends, but users can still get answers through operation search (Story 2), so it comes after the P1 foundation.

**Independent Test**: Pick a sample of capabilities from the catalog. For each read-only, permitted capability, ask for it by name and confirm the assistant can call it and shows its owning application and code.

**Acceptance Scenarios**:

1. **Given** a read-only capability is in the catalog and the user is permitted, **When** the user asks for it by name, **Then** the assistant can call it and shows where it came from.
2. **Given** a capability is in the catalog but is not read-only, **When** the user asks for it, **Then** the assistant explains it cannot be called in this version.
3. **Given** a callable operation has no matching catalog entry, **When** an operator reviews catalog health, **Then** the mismatch is reported.

---

### User Story 6 - Per-application health for operators (Priority: P2)

As a platform operator, I want to see each application's health — whether it is indexed, how fresh its operation description is, and whether access works — so that I can find and fix problems before users report them.

**Why this priority**: Isolation (Story 3) keeps the system working. Visibility is what lets operators restore full coverage. It is valuable but not needed for the first user-facing release.

**Independent Test**: With a mix of healthy, stale, unindexed, and access-failing sample applications, open the health view and confirm each application's state is shown correctly.

**Acceptance Scenarios**:

1. **Given** 30+ applications are registered, **When** an operator views health, **Then** each application shows indexed status, the time its operation description was last refreshed, and whether its access check passes.
2. **Given** an application's operation description has not refreshed within the freshness window, **When** the operator views health, **Then** it is flagged as stale.
3. **Given** an application's access check fails, **When** the operator views health, **Then** the failure says whether access is missing or the application is unreachable.

---

### User Story 7 - Scheduled, incremental catalog refresh (Priority: P2)

As a platform operator, I want the catalog to refresh on a schedule and only reprocess applications whose descriptions changed, so that the catalog stays current without manual reruns and without reprocessing everything.

**Why this priority**: Without it, the catalog goes stale as applications change. Manual refresh is a workable stopgap, so this follows the P1 stories.

**Independent Test**: Run a scheduled refresh with 30+ sample applications where only one has changed. Confirm only that application is reprocessed and its new operations become discoverable.

**Acceptance Scenarios**:

1. **Given** the refresh schedule elapses, **When** no application has changed, **Then** nothing is reprocessed and the catalog stays available.
2. **Given** one application's operation description has changed, **When** the scheduled refresh runs, **Then** only that application is reprocessed, and new or removed operations show up in discovery afterwards.
3. **Given** a refresh fails for one application, **When** the refresh finishes, **Then** that application keeps its last known good catalog entry and is flagged as stale.

---

### User Story 8 - Narrowed and filtered search (Priority: P3)

As an internal user, I want search to narrow to the likely applications first and to let me filter by application or permission, so that results stay relevant as the catalog grows.

**Why this priority**: This improves quality at very large scale. Story 2 already meets the baseline target, so it is a refinement.

**Independent Test**: With thousands of sample operations, run benchmark questions with and without application/permission filters and confirm the filtered results contain only matching applications and that relevance does not drop.

**Acceptance Scenarios**:

1. **Given** a user filters to one application, **When** they search, **Then** only that application's operations are returned.
2. **Given** a user filters by permission level, **When** they search, **Then** only operations they are permitted to call are returned.
3. **Given** no filter is applied, **When** a user searches, **Then** results favor the applications most likely to answer the question.

---

### User Story 9 - Environment separation (Priority: P3)

As a platform operator, I want the same system to run per environment (dev, stage, prod) without mixing applications, catalogs, or access between them, so that test data never leaks into production answers and production is never called from dev.

**Why this priority**: This is needed for enterprise rollout across environments, but the early rollout can run in a single environment.

**Independent Test**: Register the same sample application in two environments with different descriptions. Confirm each environment only discovers and calls its own version.

**Acceptance Scenarios**:

1. **Given** an application is registered in dev and in prod, **When** a user in dev asks a question, **Then** only the dev version is discovered and called.
2. **Given** an application is registered only in stage, **When** a user in prod searches, **Then** it does not appear.
3. **Given** a registration points at a different environment from the one it is registered in, **When** it is registered or refreshed, **Then** the mismatch is rejected or flagged and not silently used.

---

### Edge Cases

- What happens when an application is registered but its operation description is unavailable or invalid?
- What happens when an application's operation description changes between refreshes (operations added, renamed, or removed)?
- What happens to cached results, citations, and discovery when an application is removed or retired?
- How does the system behave when an application is down at the moment a read is attempted?
- What happens when access to an application is revoked between discovery and the call?
- How are two applications that expose operations with the same name told apart in search, calls, and citations?
- What happens when a registration's environment does not match the environment it is used in?
- What happens when a live address is known but no source is registered, or a source is registered but no live address exists for the current environment?
- What happens when a capability in the catalog points to an operation that is not read-only?
- How does the system behave when many applications fail at the same time (for example, a shared network outage)?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a single place to register an enterprise application. That registration MUST be the only source for which applications are discoverable and callable on every assistant surface.
- **FR-002**: System MUST make a newly registered application's read-only operations discoverable without any further manual step beyond registration.
- **FR-003**: System MUST remove a retired application's operations from discovery and calling.
- **FR-004**: Users MUST be able to ask a plain-language question and get the relevant read-only operations from all registered applications, ranked by relevance.
- **FR-005**: System MUST cite the owning application and operation for every factual statement drawn from live data.
- **FR-006**: System MUST tell apart same-named operations from different applications in search results, calls, and citations.
- **FR-007**: System MUST isolate failures per application, so that one application failing to describe its operations or respond does not affect discovery or calls for the others.
- **FR-008**: System MUST report an application that cannot be indexed or reached as degraded, not silently leave it out.
- **FR-009**: System MUST use access appropriate to each application for live reads, set up per application.
- **FR-010**: System MUST tell users clearly, and by name, which application has not granted access, as distinct from the application being unavailable or the system failing.
- **FR-011**: System MUST let the access model be changed without redesigning onboarding, discovery, or user-facing behavior. The access model itself is [NEEDS CLARIFICATION: service identity vs acting on behalf of the user (or a mix per application) — not decided].
- **FR-012**: System MUST make every read-only, permitted capability in the capability catalog callable by name, with provenance (owning application and owning code).
- **FR-013**: System MUST report mismatches between the capability catalog and the callable operations.
- **FR-014**: Operators MUST be able to see, per application, its indexed status, how fresh its operation description is, and whether its access check passes.
- **FR-015**: System MUST refresh the catalog on a schedule [NEEDS CLARIFICATION: refresh frequency not specified — e.g. hourly, daily?] and reprocess only applications whose operation descriptions changed.
- **FR-016**: System MUST keep an application's last known good catalog entry when a refresh for that application fails, and flag it as stale.
- **FR-017**: Users MUST be able to filter discovery by application and by permission level.
- **FR-018**: System MUST narrow discovery to the applications most likely to answer a question before ranking individual operations.
- **FR-019**: System MUST keep applications, catalogs, and access separate per environment (dev, stage, prod) and MUST reject or flag environment mismatches.
- **FR-020**: System MUST only allow read-only operations to be called. Any operation that changes data MUST be refused.
- **FR-021**: System MUST record, for every live read, which application and operation was called, when, and the outcome, for audit.
- **FR-022**: System MUST store, on the single application registration, the link between that application's source and its live address. The live address MUST be allowed to differ by environment. An application MAY have a live address with no source (callable, no code provenance) or a source with no live address in the current environment (known from its source, not callable there). The system MUST NOT invent a source from a live address, or a live address from a source name.

### Non-Functional Requirements

- **NFR-001 (Scale)**: System MUST support at least 30 registered applications and several thousand operations in total without breaking any other requirement.
- **NFR-002 (Readiness)**: System MUST be ready to answer questions within 10 seconds of a restart, and readiness time MUST NOT grow with the number of registered applications. [NEEDS CLARIFICATION: confirm 10-second target]
- **NFR-003 (Discovery latency)**: Operation discovery MUST complete in under 1.5 seconds at the 95th percentile at the scale in NFR-001. [NEEDS CLARIFICATION: confirm 1.5-second p95 target — proposed range was 1–2 s]
- **NFR-004 (Isolation)**: A failure, timeout, or slowdown in any single application MUST NOT degrade discovery or response times for other applications.
- **NFR-005 (Read-only)**: In this version the system MUST NEVER perform an operation that creates, changes, or deletes data in any enterprise application.
- **NFR-006 (Grounding)**: Every factual answer MUST carry a citation to a policy document or to the application and operation it came from.
- **NFR-007 (Local-first)**: The whole capability, including onboarding, discovery, health, and sample reads, MUST run locally with sample data and zero cloud credentials.
- **NFR-008 (Privacy)**: Sample data, test fixtures, and examples MUST NOT contain personal data. Only synthetic data may be used.
- **NFR-009 (Auditability)**: Audit records of live reads MUST be kept and be retrievable by operators for review. [NEEDS CLARIFICATION: audit retention period not specified]
- **NFR-010 (Credential safety)**: Credentials for one application MUST NEVER be sent to a different application.

### Key Entities

- **Enterprise Application**: a business system the assistant can read from. Has an owning team, an environment, a lifecycle state (registered, active, degraded, retired), and one operation description.
- **Application Registration**: the single, authoritative record that an application should be reachable in a given environment. It holds the link between the application's source and its live address for each environment (FR-022). Either side may be absent. Created and retired by operators.
- **Operation Description**: an application's published description of the operations it offers. Has a freshness (when it was last retrieved successfully) and changes over time.
- **Operation**: one callable read made available by an application. Belongs to exactly one application. Classed as read-only or data-changing. Only read-only operations are callable.
- **Capability**: a named business function in the capability catalog, linked to its owning code and owning application, and mapped to the operation(s) that carry it out.
- **Access Arrangement**: how the assistant is allowed to read from a given application. Set per application, can be granted, missing, or revoked, and is independent of the chosen access model.
- **Application Health**: the current state of one application as seen by operators: indexed or not, description freshness, and access check result.
- **Environment**: an isolated deployment scope (dev, stage, prod). Applications, catalogs, and access never cross environments.
- **Audit Record**: a record of one live read: which application and operation, when, under which environment, and with what outcome.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 30 enterprise applications are onboarded and discoverable, each through one registration action, with no second list kept by hand.
- **SC-002**: For a benchmark set of questions with known correct operations, the correct operation appears in the top 5 results for at least 90% of questions at full scale. [NEEDS CLARIFICATION: confirm top-5 / 90% bar]
- **SC-003**: Discovery responds in under 1.5 seconds at the 95th percentile with 30+ applications and thousands of operations registered (see NFR-003).
- **SC-004**: After a restart, the assistant is ready to answer within 10 seconds whether 5 or 30+ applications are registered (see NFR-002).
- **SC-005**: With 20% of registered applications made unreachable, 100% of the healthy applications stay discoverable and callable, and 100% of the unreachable ones are shown as degraded, not missing.
- **SC-006**: Re-running the 2026-10-08 smoke test (loan summary, payment schedules, escrow) returns live data for every application that has granted access. Every application that has not granted access produces a user message naming that application, with zero generic "unauthorized" failures.
- **SC-007**: 100% of read-only, permitted capabilities in the catalog can be called by name.
- **SC-008**: 100% of live-data answers include citations to the application and operation used, and 100% of live reads have an audit record.
- **SC-009**: Zero data-changing operations are called in any environment.
- **SC-010**: The full onboarding, discovery, health, and sample-read flow passes locally with zero cloud credentials.

---

## Dependencies & Constraints

### External Dependencies

- **Application-owning teams**: must publish a usable operation description and grant access for their applications to be reachable.
- **Enterprise identity / access decision**: the final access model (FR-011) depends on an organizational decision that has not been made yet.
- **Capability catalog owners**: needed to keep capability-to-operation mappings accurate for Story 5.

### Business Constraints

- **Read-only only**: this version must never change data in any enterprise application.
- **Citation-grounded**: answers without a citation are not acceptable.
- **Local-first**: development and demos must work with zero cloud credentials using synthetic data.

---

## Security & Privacy Considerations

### Privacy Considerations

- **What user data is collected?** The questions users ask and the application data returned for them; audit records of which application and operation was called.
- **How long is data retained?** [NEEDS CLARIFICATION: retention for audit records and question history not specified]
- **Who has access to the data?** Audit and health information is available to platform operators. Application data is shown only to the user whose question retrieved it, within the access that application granted.
- **Are there regulatory requirements?** Loan servicing data may be subject to financial-privacy regulation. [NEEDS CLARIFICATION: applicable regulations and data-classification rules to confirm with compliance]

---

## Out of Scope

The following are explicitly OUT OF SCOPE for this feature:

- Data-changing operations (payments, plan starts, holds, any create/update/delete) — read-only is a non-negotiable constraint for this version.
- Deciding the final access model — this feature only has to keep the access model swappable (FR-011). The decision belongs to a separate identity/access effort.
- Generating feature documentation wikis from application code — a separate capability, not needed for discovery and reads.
- Redesigning the web UI or chat experience — existing surfaces are reused. Only the information they show changes (citations, access and availability messages, health).

These may be considered for future iterations.

---

## Open Questions

1. **Q**: Which access model will be used — a service identity per application, acting on behalf of the signed-in user, or a mix per application?  
   **Status**: open  
   **Answer**: —

2. **Q**: Are the proposed targets acceptable — readiness under 10 s, discovery p95 under 1.5 s, correct operation in the top 5 for 90% of benchmark questions?  
   **Status**: open  
   **Answer**: —

3. **Q**: How often should the catalog refresh, and after how long should an application's operation description be flagged as stale?  
   **Status**: open  
   **Answer**: —

4. **Q**: How long must audit records and question history be kept, and which regulations apply?  
   **Status**: open  
   **Answer**: —

5. **Q**: Should per-user permission filtering (Story 8) reflect the user's own entitlements in each application, or the assistant's access to that application?  
   **Status**: open  
   **Answer**: — (depends on Q1)

---

## Stakeholders & Reviewers

- **Product Owner**: [NEEDS CLARIFICATION: not specified]
- **Technical Lead**: [NEEDS CLARIFICATION: not specified]
- **Other Stakeholders**: platform operators; application-owning teams; compliance / identity owners for the access-model decision
