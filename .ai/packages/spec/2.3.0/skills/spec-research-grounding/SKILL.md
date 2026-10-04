---
name: spec-research-grounding
description: >-
  How the readonly spec-research agent grounds a spec in the actual codebase
  before execution: build a context brief (relevant existing files, integration
  and wiring points, and conventions the implementation must follow) and
  classify every gap as either a BIG gap that becomes an open question for the
  user or a SMALL gap that becomes a documented assumption execution can make.
  Covers the investigator contract (note gaps, never block, never modify, never
  execute, return findings to the coordinator) and the structured output the
  agent produces. Use when grounding a spec before execution, exploring a
  codebase to find integration and wiring points, building a research context
  brief, classifying gaps, or deciding whether an unknown must be asked or
  assumed.
---

# Spec Research Grounding

How to ground a spec in the **actual codebase** before any execution begins. This is the depth fix: plans go thin and execution improvises because the integration and wiring points were never discovered up front. Grounding closes that gap by reading the spec, then exploring the real code the implementation must connect to, and turning every unknown into either an explicit open question or a documented assumption.

This skill is used by the `spec-research` agent — a **readonly investigator**. It pairs with `spec-sizing` (sizing method), `spec-artifact-model` (what each spec artifact is and where Open Questions live), and `spec-plan-format` (the plan/todo structure the brief informs).

## When to Use

- Grounding a spec in the codebase before an execution pass
- Exploring a codebase to find the integration points, wiring points, and conventions a feature must follow
- Building a research context brief for the execution coordinator
- Classifying a gap or unknown as a big open question vs. a small assumption
- Formatting open questions and proposed assumptions for handoff

## The Grounding Method

Run these steps in order. Steps 1–3 produce the brief; step 4 sizes the work; step 5 assembles the handoff.

### 1. Orient on the spec

Read the spec artifacts in the spec directory: `README.md`, `[feature].story.md` (the WHAT/WHY), `[feature].spec.md` (the HOW), and `[feature].plan.md` (the phases/todos). Extract the requirements (FR-/NFR-/SC- IDs), the intended design, and the planned phases. Treat the plan as a **hypothesis**, not ground truth — your job is to verify it against the real code.

### 2. Explore the actual codebase

Do not stop at the spec. Open the real files the implementation will touch and trace the seams it must connect to. You are hunting three things:

- **Relevant existing files** — the code that will be modified, extended, or must stay consistent with the new work.
- **Integration & wiring points** — the concrete seams where new code attaches to existing code: where it gets registered, routed, called, injected, exported, subscribed, or configured. **This is the part thin plans miss.** A handler that is written but never registered, a module that is created but never imported, a config key that is read but never set — those are wiring failures grounding exists to prevent.
- **Conventions** — the established patterns the implementation must follow: naming, file placement, error handling, logging, test layout, module boundaries. Find the file(s) that exemplify each.

Every entry in the brief must cite a real file or location you actually read — not a guess from the spec.

### 3. Classify gaps as you find them

Whenever the spec is silent, ambiguous, or contradicted by the code, you have a gap. Classify each one immediately as **BIG** (→ open question) or **SMALL** (→ proposed assumption) using the framework below. Note it and keep exploring — never block.

### 4. Assess size

Judge whether the spec is one executable block or should be split. Apply the **`spec-sizing`** skill for the method; this skill only requires that a sizing verdict be part of your output.

### 5. Assemble the handoff

Produce the context brief, the sizing verdict, the open questions, and the proposed assumptions (structure in "What the Agent Returns" below) and return them to the coordinator.

## The Context Brief

The brief is the grounded picture of where this feature lives in the code. It has three parts:

| Part | What it contains | Each entry includes |
|---|---|---|
| Relevant files | Existing files the work will touch or must match | Path + one line on why it matters (modified / integration surface / convention exemplar) |
| Integration & wiring points | The seams new code must connect to | Location + what must be wired + the existing pattern to follow |
| Conventions | Patterns the implementation must obey | The convention + the file(s) that exemplify it |

A brief that only restates the spec has failed. Its value is the wiring points and conventions that the spec did not capture but the code requires.

## Gap Classification: Big vs. Small

Every unknown becomes one of two things. Nothing is left implicit, and nothing is silently decided.

**A gap is BIG when getting it wrong forces rework across a boundary.** It changes architecture, scope, or a contract other code depends on; it requires a product, business, or security decision; or it has multiple materially different answers with no codebase precedent to settle it. **BIG gaps become open questions** destined for the story's Open Questions section.

**A gap is SMALL when any reasonable choice satisfies the requirement.** The decision is local and reversible, it does not cross a contract boundary, and it is typically a naming, placement, format, or local-technique choice already constrained by an existing convention. **SMALL gaps become proposed assumptions** that execution makes and documents.

**Tiebreaker — blast radius and reversibility.** Cheap, local, reversible → small. Cross-boundary, architectural, expensive to unwind → big. When you genuinely cannot decide, **treat it as BIG**: asking the user is cheaper than unwinding wrong work.

For the full dimension table, extended paired examples across architecture / scope / contract / security / naming / placement / format, and the exact output formats, read `references/gap-classification-rubric.md` when classifying a gap you are unsure about or when formatting the open-questions and proposed-assumptions output.

## The Investigator Contract

The research agent is a readonly investigator. Four rules govern its behavior:

- **Note gaps; never block.** Record every unknown and keep going. Do not halt the research because something is unresolved — surfacing the gap is the deliverable.
- **Never modify files.** Read and search only. Do not write open questions onto the story, do not edit the plan, do not touch code. Producing the questions and assumptions is your output; recording them on the spec is the coordinator's job downstream.
- **Never execute.** No implementation, no running builds or tests, no code changes.
- **Do not talk to the user.** Return findings to the coordinator. The coordinator triages — answering what it can from its own context and escalating only the genuinely unknown big gaps to the user. Your job is to make that triage possible by classifying and framing gaps cleanly: big gaps ready to escalate, small gaps ready to assume.

## What the Agent Returns

Return four things to the coordinator:

1. **Context brief** — relevant files, integration & wiring points, conventions (every entry evidence-cited). For a large brief, write it to disk under the spec working area and return the path.
2. **Sizing verdict** — single executable block vs. should-split, with reasoning (method: `spec-sizing`).
3. **Open questions** — the BIG gaps, each framed for the story's Open Questions section: the question, why it matters / what it blocks, and the candidate options if any are known.
4. **Proposed assumptions** — the SMALL gaps, each as: the assumption, the evidence or convention it rests on, and the note that it must be documented in the deliverable.

## Worked Examples

**Wiring point the brief catches (what a thin plan misses).** The plan says "add an `OrderConfirmedHandler`." Exploring the code, you find handlers are only invoked if registered in `src/events/registry.ts`, and every existing handler is wired there. Brief entry — *Integration & wiring point:* `src/events/registry.ts` — the new `OrderConfirmedHandler` must be registered here following the existing `register(...)` pattern, or it will never fire. Without this entry, execution writes a handler that silently never runs.

**BIG gap (contract / architecture).** The story implies order events but never says which topic the publisher writes to — the existing `orders` topic or a new one. Consumers depend on the topic name, and the codebase shows no single precedent. → **Open question:** "Should `OrderConfirmed` publish to the existing `orders` topic or a new dedicated topic? This changes which consumers receive it." Escalate via the coordinator.

**SMALL gap (naming / placement).** The spec needs a helper that formats the confirmation number but does not name it, and `src/formatters/` already holds analogous `format*` helpers. → **Proposed assumption:** "Add `formatConfirmationNumber` to `src/formatters/`, matching the existing `format*` naming and placement. Documented in the deliverable." Local, reversible, convention-constrained — no need to ask.

## Reference Documents

- `references/gap-classification-rubric.md` — The full big-vs-small dimension table, extended paired examples across architecture, scope, contract, security, naming, placement, and format, the unsure→big tiebreaker, and the exact output formats for an open question and a proposed assumption. Read when classifying a gap you are unsure about, or when formatting the open-questions and proposed-assumptions handoff.
