# Spec Section Examples

Paired good/shallow examples for the spec sections where authors most often under-deliver depth. Each pair shows the shallow version (passes a skim, fails an implementer), the operational version, and why the difference matters. Read the pair for the section you are drafting or reviewing.

The governing test for every section: *could an engineer who was not in the design conversation implement this as written, and would two such engineers produce substantially the same thing?*

---

## Architecture & Data Flow

**Shallow** — a box diagram with no flow:

```markdown
## Architecture
The API talks to the service, which talks to the database.
```

**Operational** — components with responsibilities, interfaces, and the flow between them:

```markdown
## Architecture

### Components
- **OrderController** — validates the request, maps it to a command. Interface: `POST /orders → 201 | 4xx`.
- **OrderService** — owns the submit workflow (idempotency, pricing call, persistence).
- **PricingClient** — wraps the pricing service; retries, timeout, circuit-break.

### Data Flow
1. Controller validates payload → rejects malformed input (see Edge Cases).
2. Service checks the idempotency key; a repeat returns the prior result.
3. Service calls PricingClient; on timeout it fails the request (no partial order).
4. Service persists the order, then publishes `OrderPlaced`.
```

**Why it matters:** the flow is where the real decisions live (order of operations, what happens on failure between steps). A box diagram hides exactly the parts an implementer must get right.

---

## Algorithms & Logic

**Shallow** — prose that restates the goal:

```markdown
We deduplicate orders by checking whether a matching order was placed recently.
```

**Operational** — pseudocode plus complexity, so the implementer picks the right structure:

```markdown
**Approach**: idempotency key = hash(customerId, cartFingerprint). Look it up in a
keyed store with a 60s window before accepting a submit.

**Pseudocode**:
  key = hash(customerId, cartFingerprint)
  if store.get(key) exists: return store.get(key)   # prior result
  result = placeOrder(...)
  store.setex(key, 60s, result)
  return result

**Complexity**: O(1) average per submit with a keyed lookup.
A naive "scan recent orders" would be O(n) per submit and degrade under load.
```

**Why it matters:** the complexity line is what drives the data-structure choice. Without it, an implementer may ship the O(n) scan that looks equivalent in a code review and fails under production volume.

---

## Data Model

**Shallow** — a field list with no rules:

```markdown
Order has id, customerId, items, status, total.
```

**Operational** — types, validation rules, and relationships:

```typescript
interface Order {
  id: string;            // UUID v4, server-assigned
  customerId: string;    // FK → Customer.id, required
  items: OrderItem[];    // min 1, max 100
  status: OrderStatus;   // 'draft' | 'placed' | 'cancelled'; transitions draft→placed→cancelled only
  total: Money;          // derived from items; never client-supplied
}
```

```markdown
**Validation rules**:
- `items` must contain 1–100 entries; an empty cart is rejected at submit.
- `total` is computed server-side; a client-provided total is ignored.
- `status` follows the transition graph above; illegal transitions return 409.

**Relationships**: an Order belongs to exactly one Customer; OrderItems are owned
by the Order (cascade delete).
```

**Why it matters:** validation rules and ownership/transition constraints are the part of the data model that prevents corruption. A field list alone leaves every one of those decisions to the implementer.

---

## Technical Decisions

**Shallow** — an assertion with no reasoning:

```markdown
### Decision: Use Kafka for events.
```

**Operational** — context, decision, alternatives with why-not, and consequences:

```markdown
### Decision: Event transport — Kafka
**Context**: NFR-006 requires at-least-once delivery of `OrderPlaced` to 3 consumers,
ordered per customer.
**Decision**: Publish to a Kafka topic partitioned by `customerId`.
**Alternatives considered**:
1. SNS/SQS fan-out — rejected: no per-key ordering guarantee.
2. Synchronous calls to each consumer — rejected: couples submit latency to the
   slowest consumer and loses replay.
**Consequences**: + ordered, replayable, decoupled. − adds Kafka ops burden and a
new runtime dependency (see Dependencies); consumers must be idempotent.
```

**Why it matters:** the alternatives and consequences are what let a reviewer trust the decision and what tell the implementer the constraints they must honor (here: consumer idempotency). A bare "use Kafka" invites the same debate again at review time.

---

## Edge Cases & Error Handling

**Shallow** — lists the case, hand-waves the handling:

```markdown
- Duplicate submit: we handle it.
- Payment provider down: we handle errors gracefully.
```

**Operational** — each case paired with a mechanism, plus error types and recovery:

```markdown
### Duplicate submit within seconds
**Scenario**: user double-clicks submit.
**Handling**: idempotency key (see Algorithms) returns the first result; the second
request is a 200 with the original order, not a new order.

### Pricing provider unavailable
**Scenario**: PricingClient times out or 5xxs.
**Handling**: fail the submit with 503; do not persist a partial order. Client may retry.
**Error types**: `PricingTimeoutError` (retryable) vs `PricingRejectedError` (terminal, 422).
**Recovery**: circuit breaker opens after 5 consecutive failures; submits fast-fail 503
while open.
```

**Why it matters:** "we handle it" is precisely the decision the spec exists to make. The edge cases the story raised as *questions* must be *answered* here with a concrete mechanism.

---

## Testing Strategy

**Shallow** — intent without scenarios or traceability:

```markdown
We will write unit and integration tests with good coverage.
```

**Operational** — scenarios mapped to requirement IDs, with coverage targets:

```markdown
### Unit
- OrderService.submit — happy path (FR-001), empty cart rejected (FR-003),
  duplicate submit returns prior result (FR-004).
- Coverage: ≥ 90% for OrderService; 100% for the idempotency path.

### Integration
- Submit → OrderPlaced published and consumed (FR-001, NFR-006).
- Pricing timeout → 503, no order persisted (edge case above).

### Performance
- p95 submit latency < 300ms at 200 rps (SC-002).
```

**Why it matters:** mapping tests to `FR-`/`NFR-`/`SC-` IDs is what proves the implementation satisfies the story. "Good coverage" is unverifiable and lets critical paths go untested.
