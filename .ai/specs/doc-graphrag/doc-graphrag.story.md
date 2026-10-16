# Feature Specification: Doc GraphRAG

**Feature Branch**: `feat/doc-graphrag`  
**Created**: 2026-10-15  
**Status**: Draft  
**Input**: User description: "Architect GraphRAG over the LoanOps doc corpus" — override ADR-025 only if measurement and cheaper retrieval upgrades still leave global/multi-policy questions failing; deliver as a kill-gated design with citation trust fixed first.

### Problem Today (user-observable)

- Policy answers cite sources, but a user cannot tell whether a cited policy path was actually retrieved this turn or invented / auto-prefixed by the assistant.
- Evaluation can score an answer as "faithful" even when the evidence was the assistant's own citation text, not what search returned — so quality gates can look green while grounding is weak.
- Flat document search returns a handful of nearest chunks. Questions that need several related policies at once (for example "what hardship options apply across states" or joins like "Florida + disaster") often miss a needed policy.
- The golden set has almost no global or multi-policy questions, so product teams cannot measure whether retrieval upgrades actually help those cases.
- A prior decision (ADR-025) deferred GraphRAG because the corpus is small and citations must stay trustworthy. Any override must prove the need after simpler upgrades, not before.

### Users

- **Internal users**: engineers, PMs, ops, analysts who ask policy/SOP questions via Cursor chat or the web UI and need cited answers they can trust.
- **Platform operators / evaluators**: run golden evals, decide whether to adopt heavier retrieval, keep artifact freshness honest.
- **Spec / ADR owners**: approve new metrics, any ADR override, and any new configuration surface.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cited policy sources must have been retrieved (Priority: P1)

As an internal user, I want every policy citation on an answer to refer to a document chunk that search actually returned this turn, so that I can trust citations and never treat invented or summary-only text as a policy source.

**Why this priority**: Without this, any later retrieval upgrade (including GraphRAG) can look green on existing gates while citing unverifiable text. Trust is a prerequisite for every other story.

**Independent Test**: Ask a policy question where search returns known documents. Confirm citations only name those documents (or refuse / drop ungrounded citations). Ask again with a model prompted to cite a path that was not returned; confirm that citation is rejected or stripped and the answer does not present it as retrieved evidence.

**Acceptance Scenarios**:

1. **Given** search returned specific policy documents this turn, **When** the assistant answers with policy citations, **Then** every policy citation names one of those returned documents (including any heading fragment that matches returned content).
2. **Given** the assistant attempts to cite a policy path that was not returned this turn, **When** the answer is finalized, **Then** that citation is not accepted as a valid policy source and the user is not shown it as if it were retrieved.
3. **Given** the assistant cites a tool rather than a policy document, **When** the answer is finalized, **Then** the citation is labeled as a tool source (not rewritten into a policy source).
4. **Given** evaluation runs on a turn, **When** citation trust is scored, **Then** the score reflects whether citations match retrieved documents, not only whether required prefixes appear.

---

### User Story 2 - Evaluation measures grounding against retrieved evidence (Priority: P1)

As a platform evaluator, I want faithfulness and related quality scores to be judged against what search actually returned, so that a green eval means the answer stuck to retrieved evidence — not to the model's own paraphrased footnotes.

**Why this priority**: Today's faithfulness path can grade the model against itself. Fixing measurement is required before any claim that GraphRAG (or cheaper upgrades) helped or hurt.

**Independent Test**: Run the golden suite (or a fixed subset) before and after the measurement change. Confirm faithfulness contexts come from tool/search results. Confirm scores may move; thresholds are not lowered to hide the movement.

**Acceptance Scenarios**:

1. **Given** a golden item that used document search, **When** faithfulness is computed, **Then** the evidence set is the retrieved document text from that turn, not citation snippets invented by the model.
2. **Given** measurement is fixed, **When** scores change versus the previous method, **Then** existing pass thresholds remain unchanged and the new baseline is recorded for comparison.
3. **Given** a golden item expects document search, **When** the item is validated, **Then** it names the real document-search capability (not a retired/alias name that does not exist on the assistant).

---

### User Story 3 - Multi-policy and global questions are measurable (Priority: P1)

As a platform evaluator, I want a golden slice of at least twenty questions that require combining or surveying multiple policies, so that we can prove whether retrieval upgrades help the cases flat nearest-neighbour search struggles with.

**Why this priority**: ADR-025's revisit trigger requires this slice. Without it, GraphRAG cannot be justified or killed with evidence.

**Independent Test**: Add the slice; run it against current flat search; record faithfulness, citation trust, and latency. The slice alone is a deliverable even if no retrieval code changes yet.

**Acceptance Scenarios**:

1. **Given** the slice exists (≥20 items), **When** an evaluator runs it against current document search, **Then** each item has expected citations and clear pass/fail against existing thresholds.
2. **Given** a question that needs two related policies (for example state + disaster overlay), **When** the item is scored, **Then** success requires citing both relevant sources (or an explicit refusal if none apply) — not a single near miss.
3. **Given** a global / survey-style question, **When** flat search is used, **Then** the recorded result becomes the baseline for later upgrade comparison.

---

### User Story 4 - Cheaper retrieval upgrades before heavy graph methods (Priority: P1)

As an internal user, I want document search to use ranking improvements and deterministic related-document expansion first, so that multi-policy questions get better answers without waiting on LLM-extracted graphs.

**Why this priority**: Matches ADR-025's preferred path. Cheaper upgrades may close the gap; if they do, GraphRAG must not ship.

**Independent Test**: Enable ranking + related-document expansion only. Re-run the Story 3 slice against the Story 2/3 baseline. Compare faithfulness, citation trust, and latency.

**Acceptance Scenarios**:

1. **Given** ranking of a larger candidate set is enabled, **When** I ask a policy question, **Then** the top results are at least as relevant as before and still fully citable as real document chunks.
2. **Given** a top hit has a related linked policy, **When** search expands one hop, **Then** the neighbour appears as its own citable document chunk (not a generated summary presented as policy).
3. **Given** the Story 3 slice is re-run after these upgrades, **When** faithfulness meets the existing threshold and citation trust is complete, **Then** the product treats GraphRAG as unnecessary and stops (kill gate).

---

### User Story 5 - Graph-assisted retrieval only if the kill gate fails (Priority: P2)

As an internal user, I want global/multi-policy questions to use graph-assisted retrieval (community summaries for routing, then verbatim member chunks for citation) only when Story 4 still fails the slice — so that we adopt complexity only when proven necessary.

**Why this priority**: Valuable if needed; harmful if adopted early (cost, staleness, citation risk). Depends on Stories 1–4.

**Independent Test**: Only after Story 4 fails the kill gate. Enable summary-based routing without LLM entity extraction first; re-measure the slice. Proceed to LLM extraction only if routing helps but graph quality is still the limit.

**Acceptance Scenarios**:

1. **Given** Story 4 failed the kill gate, **When** summary routing is enabled, **Then** answers that use communities still cite only verbatim member document chunks, never the summary as a policy source.
2. **Given** summary routing does not improve the slice, **When** operators review results, **Then** LLM entity/relation extraction is not adopted.
3. **Given** summary routing helps and extraction is later enabled, **When** the index is built twice with the same corpus and model, **Then** the graph artifact is identical and the second build performs no new extraction calls for unchanged chunks.
4. **Given** the graph artifact is missing, corrupt, or stale relative to the corpus, **When** a user searches, **Then** the assistant falls back to safe flat (or local) search and does not silently use mismatched graph data for global routing.

---

### User Story 6 - Operators can see readiness and trust signals (Priority: P3)

As a platform operator, I want health and eval reports to show whether grounded citation checks are in force and whether graph-assisted mode is active or degraded, so that I can operate the system without guessing.

**Why this priority**: Operational clarity; not required for the trust MVP (Stories 1–3).

**Independent Test**: Inspect health/readiness output with graph off, graph on, and graph stale/missing. Confirm distinct signals.

**Acceptance Scenarios**:

1. **Given** graph-assisted retrieval is disabled or unavailable, **When** an operator checks readiness, **Then** they see that flat/local document search is in use.
2. **Given** the corpus changed and the graph artifact is stale, **When** an operator checks readiness, **Then** they see a warning and global routing is disabled while local/flat search continues.

---

## Edge Cases

- What happens when search returns no documents but the model still emits policy citations?
- What happens when a citation path matches a returned document but the snippet is not substring of that chunk?
- What happens when the same policy path appears in both a community summary and a member chunk — which may be cited?
- What happens when Confluence (or another remote) is the policy source — may a graph artifact be committed into the repository?
- What happens when two developers index from different machine paths — must chunk identity stay stable?
- What happens when `index_docs` updates vectors at runtime without refreshing the graph artifact?
- What happens when latency rises because full chunks replace short snippets in the prompt?
- What happens when PII scrubbing would redact state names or agency names that multi-policy joins need?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a policy citation only when its source matches a document chunk returned by document search in the same turn (path and optional heading), and MUST reject or strip citations that do not.
- **FR-002**: System MUST treat tool citations as tool sources and MUST NOT rewrite them into policy sources.
- **FR-003**: Evaluation MUST compute faithfulness (and related context-based metrics) using retrieved tool/search evidence for the turn, not model-authored citation snippets alone.
- **FR-004**: Evaluation MUST report a citation-trust metric that fails when any required or emitted policy citation is ungrounded; the gate MUST NOT lower existing thresholds to compensate.
- **FR-005**: Golden data MUST name the live document-search tool used by the assistant; retired or alias tool names MUST NOT validate as success.
- **FR-006**: System MUST provide a golden slice of at least twenty global or multi-policy questions with expected citations before any graph-assisted retrieval ships.
- **FR-007**: System MUST ship ranking over a larger candidate set and deterministic related-document expansion (one hop) as the first retrieval upgrade path, with every returned neighbour remaining a separately citable document chunk.
- **FR-008**: System MUST record a baseline eval (including latency) on flat search after FR-001–FR-006, then re-measure after FR-007; if the slice meets faithfulness and citation-trust gates, GraphRAG MUST NOT ship (kill gate).
- **FR-009**: If the kill gate fails, system MAY enable summary-based routing over a document-link graph; community summaries MUST NOT be accepted as policy citation sources — only verbatim member chunks.
- **FR-010**: LLM entity/relation extraction over the doc corpus MUST NOT run unless summary routing (FR-009) demonstrably improves the slice and graph quality remains the limiting factor.
- **FR-011**: When extraction runs, repeated indexing of an unchanged corpus and pinned model MUST reproduce an identical artifact and MUST NOT re-call the model for cached chunks.
- **FR-012**: When the graph artifact is missing, corrupt, schema-mismatched, or corpus-stale, system MUST fall back to flat/local search for safety and MUST disable global graph routing.
- **FR-013**: Document chunk identity and citation paths MUST be stable across machines (corpus-relative paths), so shared artifacts resolve correctly.
- **FR-014**: Operators MUST be able to observe whether citation grounding is active and whether graph-assisted mode is on, off, or degraded.

### Non-Functional Requirements

- **NFR-001**: Existing eval thresholds MUST NOT be lowered (faithfulness ≥ 0.85, answer relevance ≥ 0.85, citation coverage ≥ 1.0, refusal correctness ≥ 0.95, latency p95 ≤ 4000 ms unless explicitly waived with approval).
- **NFR-002**: Document search p95 SHOULD stay within stated budgets once measured (target: ~300 ms local upgrade path, ~500 ms global routing, warm), and tool payload size SHOULD be capped so prompt growth does not dominate turn latency.
- **NFR-003**: Indexing the current SOP-scale corpus SHOULD complete in under about 10 minutes locally when extraction is enabled.
- **NFR-004**: Committed graph artifacts MUST stay small enough for normal git use (order of a few MB); CI SHOULD fail oversized artifacts.
- **NFR-005**: No new external capability Protocol unless a surviving design after the kill gate proves a runtime graph store is required; prefer checked-in artifacts for local corpus.
- **NFR-006**: Remote/Confluence-derived graph content MUST NOT be committed into the repository; local synthetic SOP corpus only for committed artifacts.
- **NFR-007**: Local demo (`make demo`) MUST continue to work with graph-assisted retrieval disabled by default.

### Key Entities

- **Policy document / chunk**: A citable unit of SOP/docs text with a stable path (and optional heading). The only valid target of a `policy:`-style citation.
- **Retrieved evidence set**: The chunks (and tool texts) actually returned this turn; the authority for citation trust and faithfulness contexts.
- **Global / multi-policy question**: A golden item needing survey or join across multiple policies; the kill-gate measuring stick.
- **Related-document edge**: A deterministic link between policies (e.g. markdown link, shared category, state overlay) used for one-hop expansion.
- **Community summary**: Optional routing aid over a cluster of chunks; never a policy citation source.
- **Graph artifact**: Versioned offline product of indexing (links, communities, optional extractions) with a corpus fingerprint for staleness checks.

---

## Success Criteria *(mandatory)*

- **SC-001**: Citation-trust metric reaches 1.0 on the golden suite with grounding checks enabled; ungrounded policy citations do not survive finalization.
- **SC-002**: Faithfulness contexts for doc-search turns are taken from retrieved evidence; a recorded baseline exists in session logs after the change.
- **SC-003**: At least 20 global/multi-policy golden items exist and run under the same gates as the main suite.
- **SC-004**: After ranking + one-hop expansion, either (a) the slice meets faithfulness ≥ 0.85 and citation trust 1.0 — GraphRAG stopped — or (b) the fail is documented and FR-009 work is authorized.
- **SC-005**: If GraphRAG ships past the kill gate, every factual policy citation in eval still resolves to a verbatim retrieved chunk; summaries never count as policy sources.
- **SC-006**: Cross-machine index of the same local corpus yields identical chunk identities / artifact hashes when path normalisation is in force.
- **SC-007**: With graph features off, `make demo` and existing happy-path policy Q&A still work.

---

## Out of Scope

- Replacing EAKG / capability catalog search with doc GraphRAG (capability questions stay on EAKG).
- Mutating tools, payments, or any write actions.
- Lowering eval thresholds to make GraphRAG "pass".
- Committing Confluence or other remote-sourced graph content into git.
- Building a new runtime graph-store Provider as a first step (deferred unless kill gate + later phases require it).
- Rewriting the web UI for graph visualisation.
- Authoring a new enterprise wiki; LoanOps consumes docs, it does not become the wiki platform.

---

## Dependencies & Constraints

- ADR-025 currently defers GraphRAG; any override is ADR-030 and must respect the kill gate in this story.
- Human approval required for: new ADR, new env vars (if any survive the gate), new eval metric gate, new external capability Protocol.
- Provider abstraction and settings-module rules remain in force.
- Corpus today is small (~60 synthetic SOP files); expect limited GraphRAG upside — the kill gate exists for that reason.

---

## Security & Privacy

- Extracted entities and summaries MUST be scrubbed for PII before persistence, with care not to destroy legitimate policy join keys (e.g. state names) via over-redaction.
- No real borrower PII in fixtures, golden data, or committed artifacts.

---

## Open Questions

- **OQ-001**: Product owner sign-off path for the new citation-trust metric gate (FR-004) — same as other eval approvals? Status: open.
- **OQ-002**: If Story 4 passes the kill gate, is ADR-030 still filed as "upheld ADR-025" or is no ADR needed? Status: open (recommend short ADR note either way).
- **OQ-003**: Exact ownership of authoring the 20+ golden slice content (domain SMEs vs synthetic authoring). Status: open.
