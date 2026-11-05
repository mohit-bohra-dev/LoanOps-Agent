# LoanOps Agent — One-Pager

**Audience:** Stakeholders / demos  
**Status:** Working demo / internal prototype  
**Owner:** Mohit Bohra  

---

## What it is

**LoanOps** is an **internal, citation-grounded AI platform** for enterprise teams — not locked to one job title.

Anyone internal can ask in plain English. The agent:

1. Discovers the right **APIs / capabilities** (EAKG + OpenAPI via MCP)
2. Searches **docs / SOPs** (with citations)
3. Calls **read-oriented tools** and drafts a **grounded answer** for human review

It is **not** a public borrower chatbot. Mutating business actions stay out of v1 tool policy unless explicitly approved later.

---

## Who it is for

| User | Need |
|------|------|
| Engineer / analyst | Find and call the right API; impact / capability questions |
| PM / ops | Docs + Jira/wiki context (wiki tools when ported); grounded drafts |
| Any internal role | Same MCP surface; scopes differ by `AGENT_ROLE` |

---

## Problem → outcome

| Today | With LoanOps |
|-------|----------------|
| Hunt swagger, wiki, repo docs, many UIs | One ask → cited answer + tool trace |
| “Which API?” tribal knowledge | EAKG + semantic capability search |
| Weak audit of what was used | Citations (`policy:` / `tool:`) + audit log |

**Scope:** platform for general internal use (ADR-021). Domain content today is mortgage-servicing APIs/docs; the product shape is role-agnostic.

---

## How it works (short)

```
Cursor → MCP :8001                    (protocol / tool proof)
Chat UI → Agent API → MCP :8001       (built to evaluate MCP under chat turns)
                 → search_sse_apis / EAKG / search_docs
                 → call_sse_api → grounded draft
```

- **MCP-first:** Chat UI exists so we can evaluate the MCP tool room, not as the finished product surface yet
- **Hybrid:** same Python codebase local (Ollama + Qdrant) or cloud (Bedrock + Qdrant Cloud) via env swap
- **Providers:** chat, embeddings, vector store, audit — backends swapped by config
- **Quality gate:** interactive Chat UI harness + offline golden eval (groundedness / citations / refusals)

---

## Links

- Current vs possible (plain-language explainer): `docs/10-loanops-explainer.md`
- Runtime visuals: [Lucid chart](https://lucid.app/lucidchart/214feeb3-4a57-4947-b742-38e660794ada/edit?invitationId=inv_2762b1f0-d514-4b3f-8209-6b9a048b0edf&page=fzdJNN-SrbJ0#)
- ADR-021 (audience): `decisions.md`
- PRD (historical care-rep framing): `docs/PRD.md`
- Demo pitch: `presentations/demo-pitch/slides.md`
