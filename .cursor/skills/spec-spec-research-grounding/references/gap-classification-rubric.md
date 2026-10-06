# Gap Classification Rubric

The full method for deciding whether a gap is BIG (→ open question for the user) or SMALL (→ documented assumption). Read this when a gap is not obviously one or the other, or when formatting the handoff output.

A **gap** is anything the spec leaves silent, ambiguous, or that the codebase contradicts. Every gap is classified — none are left implicit, none are silently decided.

## The Dimension Table

Score the gap on these dimensions. **Any single BIG signal makes the gap BIG.** A gap is SMALL only when it is small on every dimension.

| Dimension | BIG signal (→ open question) | SMALL signal (→ assumption) |
|---|---|---|
| Architecture | Changes which component/service/module owns the behavior, or sync vs. async, or introduces a new component | Stays inside one already-decided component |
| Scope | Could expand or contract what this spec delivers (is X in or out?) | Does not move the scope boundary |
| Contract | Changes an API shape, event/message schema, public interface, or a data model other code reads | Touches only internals invisible across the boundary |
| Precedent | Multiple materially different answers and the codebase shows no dominant pattern to settle it | One dominant existing pattern the choice can follow |
| Decision type | Needs a product, business, security, compliance, money, retention, or PII decision | Pure local engineering choice |
| Reversibility | Expensive to unwind once built; ripples into other code | Cheap to change later; change stays local |

**Tiebreaker:** weigh blast radius against reversibility. Cheap + local + reversible → SMALL. Cross-boundary + architectural + expensive to unwind → BIG. **When you genuinely cannot decide, classify it BIG** — asking the user costs one question; unwinding wrong work costs an execution pass.

## What Makes a Gap BIG

A gap is BIG when getting it wrong forces rework across a boundary. Typical triggers:

- **Architecture** — where the behavior lives, how components communicate, whether something new is introduced.
- **Scope** — whether a capability is inside or outside this spec.
- **Contract** — the shape of anything other code depends on: endpoints, event schemas, public function signatures, persisted data models, config keys consumers read.
- **Security / compliance / data** — authentication, authorization, encryption, retention, PII handling, audit, money movement.
- **Product / business judgment** — priority calls, which user segment, SLA/latency targets, UX decisions with no engineering-only answer.
- **Unverifiable external behavior** — a dependency whose behavior cannot be confirmed readonly and that changes the implementation.
- **Genuine ambiguity** — several plausible answers with materially different implementations and no codebase precedent to disambiguate.

## What Makes a Gap SMALL

A gap is SMALL when any reasonable choice satisfies the requirement, the decision is local and reversible, and it does not cross a contract boundary. Typical cases:

- **Local naming** — a variable, function, or internal file name already constrained by repo naming conventions.
- **File placement** — where a new file goes when an established directory pattern already answers it.
- **Format / style** — log message wording, comment style, ordering, a detail with an obvious repo convention.
- **Local technique** — an internal implementation approach where any reasonable choice meets the requirement and stays behind the boundary.
- **Convention-settled** — anything where the codebase already shows a dominant precedent the agent can simply follow.

## Paired Examples

Each pair shows a BIG gap and a SMALL gap in the same area, so the line is concrete.

**Architecture**
- BIG: "Should the new pricing calculation run in the request path or be precomputed by a background job?" — changes the component model and latency contract.
- SMALL: "Should the pricing helper be a standalone function or a private method on the existing service?" — internal, reversible, no boundary crossed.

**Scope**
- BIG: "Does this feature need to support multi-tenant isolation?" — materially changes what is built.
- SMALL: "Should the success log line include the request id?" — does not move the scope boundary.

**Contract**
- BIG: "Which queue does the `OrderConfirmed` publisher write to — the existing `orders` topic or a new one?" — consumers depend on it; no single precedent.
- SMALL: "What do I name the new private DTO used only inside the mapper?" — invisible across the boundary.

**Security / data**
- BIG: "Are expired sessions revoked server-side immediately, or allowed to lapse?" — a security decision with user-visible consequences.
- SMALL: "What name for the in-memory cache key prefix for session lookups?" — local and reversible.

**Naming / placement / format**
- BIG: *(rare)* "Should the public response field be `total` or `amountDue`?" — it is part of the API contract, so it is BIG despite looking like naming.
- SMALL: "Where does the new validator file go?" — `src/validators/` is the established home; follow it.

The naming pair shows the key trap: a naming choice that crosses a contract boundary (a public field name) is BIG. Naming that stays internal is SMALL.

## Output Formats

### Open question (BIG gap)

Frame each open question so the coordinator can drop it straight into the story's Open Questions section. Include what it blocks and any known options.

```markdown
- **[Open Question] <one-line question>**
  - Why it matters / what it blocks: <the rework or decision that hinges on this>
  - Options (if known): <option A> | <option B>
  - Blocks: <FR-/NFR- id or phase/todo this gates, if identifiable>
```

### Proposed assumption (SMALL gap)

Frame each assumption so execution can act on it and the coordinator can document it. Nothing is silently decided.

```markdown
- **[Assumption] <the choice being made>**
  - Rests on: <the convention or evidence — cite the file/pattern>
  - Reversible: <why changing it later stays local>
  - Must be documented in the deliverable.
```

## Quick Checklist

- [ ] Every gap is classified BIG or SMALL — none left implicit.
- [ ] Each BIG gap is written as an open question with what it blocks.
- [ ] Each SMALL gap is written as a proposed assumption citing the convention it rests on.
- [ ] Naming/format gaps that cross a contract boundary were classified BIG, not SMALL.
- [ ] Ties and genuine uncertainty were resolved toward BIG.
