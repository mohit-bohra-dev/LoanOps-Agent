# Constrained Decoding — Simple Guide

What we talked about in one place. Plain words.

---

## 1. What is constrained decoding?

A language model picks the next word (token) from a big list of options.

**Normal decoding:** model can pick any token it likes.

**Constrained decoding:** before it picks, we block every token that would break a rule (for example: “must be valid JSON”). Those blocked tokens get probability zero. The model *cannot* write illegal output.

Think of it as a wall, not a request.

| Approach | What it does | Guarantee |
|----------|--------------|-----------|
| Prompt (“please reply as JSON”) | Asks nicely | None |
| Validate + retry | Parse output; if bad, ask again | Soft — may fail after retries |
| Forced tool use | Make model fill a tool’s fields | Medium — provider validates shape |
| Constrained decoding | Mask illegal tokens while generating | Hard — illegal tokens unreachable |

**How it works (short):**

1. You give a rule (JSON Schema, regex, or grammar).
2. That rule becomes a state machine.
3. At each step, only legal next tokens stay allowed.
4. Model samples from that short list.

**What it does *not* fix:** wrong facts. Schema-perfect JSON can still lie. Syntax ≠ truth.

**Cost / catch:** needs logit access (often local or first-party APIs). Can hurt long prose if you force a rigid shape.

---

## 2. plaisse-wiki

### Do we use it?

**No.**

Stack: AWS Bedrock Claude + LangChain `createAgent`.

- **Zod** = only for **tool inputs** (normal tool calling).
- Final answers = free text / markdown.
- No `response_format`, no `withStructuredOutput`, no grammar masking.

Shape comes from **prompts** + light string cleanup:

- Flow/trace agents: strip text before first `# ` heading.
- Prober: parse `- ` bullet lines, or `NONE`.

### Should we use it?

**Mostly no.**

Why:

1. **Deliverable is prose** — wiki pages and chat replies are markdown for humans, not records for code.
2. **Bedrock Claude** has no real grammar-level constrained decoding; LangChain “structured output” there is usually forced tool use under the hood.
3. **Forced tools clash with extended thinking** — concierge / doc writers use adaptive thinking; forced `tool_choice` often cannot pair with that.

### Real gaps (cheap fixes, not constrained decoding)

| Spot | Risk | Better fix |
|------|------|------------|
| `parseProbes` | Weird bullet format → empty list → probe round silently skipped | Tolerant parser + warn when text isn’t `NONE` but parses to zero probes |
| Flow/trace heading strip | No `# ` found → preamble committed to wiki | Check required headings; one retry if missing |

Validation + retry beats constrained decoding for these.

---

## 3. LoanOps-Agent

### Do we use it?

**Partly — and only on Ollama.**

Agent always sets `json_mode=True` when calling chat. What that means depends on the provider:

| Provider | What `json_mode` does | Real constrained decoding? |
|----------|----------------------|----------------------------|
| **Ollama** (local) | `format: "json"` → GBNF grammar | **Yes** — must emit JSON |
| **Bedrock** (AWS) | Extra system line: “return valid JSON” | **No** — just a prompt |

So local can be *stricter* than production. Same flag, different strength.

### What sits on top

Even valid JSON ≠ valid `AgentTurnOutput`. So LoanOps also:

1. Strip `<think>…</think>`
2. Pull JSON out of fences / braces
3. Best-effort fix citations
4. Pydantic validate
5. Retry once on schema fail → then refuse

That stack exists because small models sometimes emit garbage (e.g. Python-like calls instead of JSON).

### Should we go further?

**Yes — opposite of plaisse-wiki.**

Here the model output *is* a record: answer, citations, confidence, refusal, escalation. API, audit, eval all consume it. That is the use case for constrained decoding.

**Cheap wins:**

1. **Ollama schema mode** — pass full `AgentTurnOutput` JSON Schema into `format`, not just `"json"`. Guarantee moves from “parses as JSON” → “matches schema”. Needs protocol change: `json_schema` instead of a bool.
2. **Bedrock forced tool** — Converse has no `response_format`. Add one tool (e.g. `emit_answer`) whose input schema = `AgentTurnOutput`, force that tool. Not token-masking, but closes Ollama vs Bedrock gap.
3. **Check tool + json_mode on pass 1** — first call sets both. Grammar on text vs tool-call channel can fight; confirm tools still fire before tightening schema.
4. **Citation auto-inject** — parser can invent citations when tools ran but model cited nothing. Constrained decoding does not fix grounding; eval gate must.

---

## 4. Side-by-side

| Question | plaisse-wiki | LoanOps |
|----------|--------------|---------|
| Constrained decoding today? | No | Yes on Ollama only; Bedrock = prompt |
| Output type | Markdown / prose | Structured JSON record |
| Should add constrained decoding? | No (fix parsers instead) | Yes (schema on Ollama; forced tool on Bedrock) |
| Main risk if ignored | Silent probe skip; preamble in wiki | Parse fails / soft Bedrock JSON |

---

## 5. One-line takeaway

**Constrained decoding = block illegal tokens while the model writes.**

- **plaisse-wiki:** don’t need it; deliverable is prose; tighten parsers.
- **LoanOps:** already half there on Ollama; finish with real schema + Bedrock parity.
