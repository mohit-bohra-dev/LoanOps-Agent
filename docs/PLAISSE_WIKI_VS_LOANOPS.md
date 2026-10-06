# Plaisse wiki vs LoanOps — simple comparison

**Date:** 2026-10-04  
**Wiki repo:** `D:\Users\v-mbohra\Documents\Projects\plaisse-wiki`  
**LoanOps repo:** this project (`LoanOps-Agent`)

This note compares **two products**, not two names for the same thing. Both help people who should not have to hunt through code, databases, and APIs by hand. They store knowledge in different ways and they are good at different jobs.

---

## One sentence each

**Plaisse wiki** is a **read-only Plaisse coworker**. When a feature has no write-up, it **reads GitLab code**, **writes shared docs**, then answers from those docs. If you still need live numbers, it can **query SQL** or **GET a real API**.

**LoanOps** is a **citation-grounded internal agent platform**. It **extracts APIs from code and Swagger**, keeps a **capability catalog (EAKG)**, searches **existing SOP docs**, and may **GET only known operations** through MCP. It does **not** publish a feature wiki from GitLab.

---

## What each is trying to do

| | Plaisse wiki | LoanOps |
|--|----------------|---------|
| North star | Shared **documentation** that stays in GitLab and gets better over time | **Discover + call** the right capability, with a citation |
| Who it is for | Plaisse people asking about **features, data, and “what the app shows”** | Internal users (any role) asking about **policy, tools, and APIs** we have catalogued |
| Success looks like | Next person asks the same feature → answer from **docs**, not a full code reread | Agent picks a **known GET**, cites `policy:` / `tool:`, eval set still passes |

Same problem class. Different load-bearing idea.

---

## How knowledge is made (the important split)

A useful slogan, with a caveat:

- **Wiki feature docs ≈ probabilistic knowledge** (an LLM **wrote** the pages).
- **LoanOps EAKG / OpenAPI / Roslyn ≈ deterministic knowledge** (the **same code in → same APIs out**).

**Wiki is not only LLM.** It also has hard lists: TAAC destinations, Swagger GET/HEAD endpoints, database schema. Those are not “the model made them up.”

**LoanOps is not only machines.** The **chat answer** is still an LLM. The **catalog of which GET exists** is not.

| Knowledge | Wiki: who fills it | LoanOps: who fills it |
|-----------|--------------------|------------------------|
| Feature story + glossary | LLM reads GitLab, writes two markdown files, commits to `plaisse-wiki-docs` | **Does not do this** |
| API list | GET Swagger, copy `summary` / path, embed in Postgres | Roslyn + OpenAPI → `interface.json` + `graph.ttl` |
| API “summary” text for search | Copied from Swagger (not LLM-written) | OpenAPI summary + heuristic label (`GetLoanSummary` → “Get loan summary”); optional LLM **label only** |
| Database shape | Schema pull + embed | SQL client exists; not a tenant-wide schema index |
| Policy / SOP | Not the wiki’s core | Ingest existing markdown (`data/sops/`, docs search) |
| Code map (who calls what) | Not a first-class graph | Optional Graphify + `links.json` joined to EAKG ops |

---

## What the wiki docs are for

When the LLM writes docs, those files are **shared memory**, not a throwaway chat:

1. **Answer first from docs** — next question about that feature searches the pages, instead of re-reading the whole repo.
2. **Two files on purpose** — a **business narrative** (plain language) and a **technical glossary** (tables, APIs, codes, file paths). Humans read the story; the agent uses the glossary to know **where to look** if it must call an API or SQL.
3. **Team property** — stored in GitLab, versioned, reviewable.
4. **Search index** — those files are embedded. That index is the long-term store for **features**.

Personal chat history is separate (your thread). Docs are **what the company should remember**.

**LoanOps** uses **docs people already wrote** (SOPs). The agent does not become the author of a shared feature wiki.

---

## Live APIs: find and GET

Both can **only read** (GET/HEAD; LoanOps MCP also enforces GET). How they **find** the call is different.

### Wiki

1. **TAAC** lists service URLs for the env (`dev` / `stg` / `prd`) — many destinations, not one repo at a time.
2. **`index:api`** fetches Swagger, keeps GET/HEAD, embeds `destination + method + path + swagger summary`.
3. Concierge prefers **docs**. For “as the app computes it,” it **delegates** to an API specialist: `search_endpoints` → `describe_endpoint` → `call_api`.
4. Auth is **Auth0 machine-to-machine** with `requested_destination` resolved the **same way Plaisse apps do**. The wiki calls APIs **as itself**, not as the human.

**Strength:** English question → nearby Swagger text; many apps in one env.  
**Weakness:** dest list is a directory, not a tight allow-list; grants lag → 401; path parameters filled by the model; **no** proof of which C# action owns the route unless the glossary happened to say so.

### LoanOps

1. Apps are **onboarded** into EAKG (clone, extract, OpenAPI join). That OpenAPI join is **pipeline**, not a chat turn.
2. Search is **`search_sse_apis`** over an **already-loaded** catalog (**embeddings** over OpenAPI text, keyword fallback) plus optional EAKG vectors (`embeddings.json`).
3. Call is **`call_sse_api`**: host allow-list, GET-only, optional **capability bind** so the invoke must match a known operation.
4. Join key is deterministic: `application|METHOD|normalized_path`. Optional engineering graph: **which code symbol** that op maps to.

**OpenAPI is not fetched when the user asks a question.** EAKG attach happens at onboard (spec cached next to the shard). SSE `search_sse_apis` / `call_sse_api` read an in-memory catalog from `service.load()` (cached after first load). The **live** HTTP on a turn is the **business GET**, not a new `swagger.json`. (If no fixture, swagger URLs may be pulled **once** when the process first loads the catalog — still not per question, and not the EAKG graph.) Wiki is the opposite shape: TAAC dests + `index:api` crawl swagger into pgvector; each dest’s spec is the catalog.

Wiki **call** is still live GET at answer time. LoanOps **call** is also live GET. Only **discovery from OpenAPI** is batch/load on LoanOps, not runtime discovery.

**Strength:** hard to invent a fake endpoint; citations; eval; local demo without Auth0.  
**Weakness:** only onboarded apps; **no** Plaisse destination-token algorithm.

### Which is better at “which API, and when?”

- **When to call live vs stay in docs:** wiki is clearer (docs first; API vs SQL vs code).
- **Exactly which GET, with proof:** LoanOps.
- **Which code calls which API:** LoanOps (Graphify / Roslyn). Wiki does not build that graph.

---

## Auth, env, safety

| | Wiki | LoanOps |
|--|------|---------|
| Human login | Auth0 / AppAuth (Reader vs Admin) | Local / platform auth; not Plaisse AppAuth |
| Calling APIs | Dedicated M2M client per env | SSE catalog + allow-listed hosts |
| Env switch | `PLAISSE_WIKI_ENV` + TAAC registry | Settings / onboarded shards; EAKG can read TAAC for app list, not the wiki’s full live registry |
| Mutate data | No (SQL write keywords rejected; APIs GET/HEAD) | No mutating tools in v1 |
| Honesty on 401 | Say the bot lacks access | Policy / invoke errors |

---

## Extra specialists (wiki only)

Wiki also has (or aims at) **Jira**, **NuGet package** tracing, **screenshots**, durable **owner-bound** conversation memory, and a **DB specialist** over many TAAC databases.

LoanOps extra: **eval golden set**, **PII / content-safety** providers, **MCP**, **Graphify for this repo’s own code**, EAKG **cross-app** detectors.

---

## Are we “achieving wiki” with LoanOps?

**No.** Overlap is the **slice**: chat, read-only GET, citations, some API search.

LoanOps does **not** replace:

- on-demand **GitLab → two docs → commit → re-index**
- **docs-first** concierge with glossary-driven API/SQL
- **Auth0 destination** tokens for all TAAC services
- wiki as the **long-term shared feature store**

EAKG + Graphify make LoanOps better at **naming and explaining APIs**. They do not make it a documentation factory.

---

## How to think about combining them (not built)

Do **not** throw either away.

| Take from wiki | Take from LoanOps |
|----------------|-------------------|
| TAAC destination list + dest tokens | EAKG join key + GET policy + capability bind |
| Vector search over Swagger (and over **reviewed** docs) | Roslyn/OpenAPI as source of truth for “this GET exists” |
| Docs-first UX; API vs SQL split | Citations, eval, local-first, engineering graph |

Safe shape: **LLM may write human docs**; **only extractors may add an invokable GET**. Search can be semantic; **invoke** must still hit a catalogued operation.

---

## Cheat sheet

| Question | Lean wiki | Lean LoanOps |
|----------|-----------|--------------|
| “Explain this feature in English, keep it for the team” | Yes | No |
| “What does Escrow return for loan X right now?” | Yes, if M2M is granted | Yes, if that app is onboarded |
| “List every TAAC API this env” | Yes | No (until similar registry) |
| “Call only a known GET; show controller/file” | Weak | Yes |
| Run locally with zero AWS/Auth0 | Harder | Designed for this |
| Shared wiki from code | Core | Missing |

---

## Related docs (LoanOps)

- [`ENGINEERING_GRAPH_ANALYSIS.md`](ENGINEERING_GRAPH_ANALYSIS.md) — Graphify vs EAKG (this repo / clones)
- [`EAKG_ONBOARD_REPO.md`](EAKG_ONBOARD_REPO.md) — how an app enters the catalog
- [`SSE_LIVE_SWAGGER.md`](SSE_LIVE_SWAGGER.md) — live swagger checks
- Wiki architecture: `plaisse-wiki/docs/what-is-plaisse-wiki.md`, `docs/architecture/05-documentation-generation.md`, `docs/architecture/07-live-apis.md`
