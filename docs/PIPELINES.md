# Offline / batch pipelines (source → knowledge)

How raw data becomes knowledge (or a search index) so AI tools can find and use it
without reading full codebases or SOP folders every turn.

**Default ops mode (D10):** run transforms by hand when needed. Schedulers / CI
schedules are optional later. How-to commands live in
[`EAKG_INDEX_SCHEDULE.md`](EAKG_INDEX_SCHEDULE.md) and package CLIs — not here.

Related: [`EAKG_COMMITTED_VS_LOCAL.md`](EAKG_COMMITTED_VS_LOCAL.md),
[`ENGINEERING_GRAPH_ANALYSIS.md`](ENGINEERING_GRAPH_ANALYSIS.md),
[`ARCHITECTURE.md`](../ARCHITECTURE.md) §11 (RAG).

---

## Data → knowledge (AI-accessible)

| Transform | Raw data | Knowledge / index | AI tools use it for |
|---|---|---|---|
| **Code → EAKG (KG)** | App source (controllers, extractors) | Capability / app RDF shards | “What can this app do?” / impact |
| **OpenAPI → EAKG (KG)** | API specs | Same EAKG, richer ops + summaries | Discovery with better labels |
| **OpenAPI → ApiIndex vectors** | API specs | Searchable operation vectors (+ sidecar) | Fast find-the-right-call |
| **EAKG → capability embeddings** | Capability text in the KG | `embeddings.json` | Natural language → capability |
| **SOP → docs embeddings** | Confluence SOP markdown (`_confluence`) | Vectors in namespace `docs` | Cited policy answers |
| **SOP → GraphRAG (doc KG)** | Same Confluence SOPs | Document communities / topic map | Multi-doc policy context |
| **Code → Engineering KG** | App AST (Graphify on clones) | `engineering/graph.json` (+ links) | “Where in code is this op?” (dev; not main chat discovery) |

```text
Raw world          Transform              Knowledge AI can grab
─────────          ─────────              ─────────────────────
Code / OpenAPI  →  EAKG RDF            →  capability menu + ownership
OpenAPI         →  ApiIndex vectors    →  find callable ops fast
EAKG text       →  capability vectors  →  natural-language match
SOPs            →  doc vectors         →  cited policy answers
SOPs            →  GraphRAG            →  related-policy context
Code AST        →  Engineering KG      →  code wiring (optional)
```

**Two jobs**

1. **Knowledge** — structured facts (KG): apps, capabilities, doc communities, code structure  
2. **Easy AI access** — vectors / indexes so tools retrieve the right slice in one call  

Product chat mainly uses: **EAKG + ApiIndex + docs (+ GraphRAG if on)**.  
Engineering KG is optional code navigation, not the default agent menu.

---

## Pipeline summary

| Name | Source (input) | Output | Example (one line) | Description |
|---|---|---|---|---|
| **EAKG sync** (repo / nightly / audit) | Registered app repos (git), cached OpenAPI specs, TAAC app list, extractors | `data/eakg/repos/`, `data/eakg/enterprise/`, proposals / audit reports | OpenAPI `getPaymentSchedules` → `repos/loanservices/graph.ttl` capability | Enterprise map of apps, APIs, capabilities, and cross-app links |
| **API index refresh** | EAKG registry + OpenAPI specs (live or cached) | Unified operations + vector/sidecar search index | Same op → `api_index/<env>/operations.json` public_id `loanservices:getPaymentSchedules` | Searchable menu of callable API operations |
| **SOP / policy ingest** | Confluence cache `data/sops/_confluence` | Vector namespace `docs` (same store `search_docs` reads) | `escrow/annual-analysis.md` → chunk in `docs` with that path | Loads Confluence SOPs so the agent can answer with policy citations |
| **GraphRAG build** | SOP / doc corpus (local markdown) | GraphRAG artifact dir (communities, summaries, related vectors) | Escrow SOP cluster → `data/graphrag/communities.json` id `c0001` | Offline document map (topics / links) for richer doc answers |
| **EAKG capability embeddings** | Merged EAKG capability text from shards | `data/eakg/enterprise/embeddings.json` | `get_payment_schedules` text → vector row in `embeddings.json` | Natural-language ranking for capability search |
| **TAAC refresh** | Live TAAC config via `glab` (never committed) | Local drop under `.eakg-workspace/` | GitLab TAAC config → `.eakg-workspace/taac-client-config.json` | Pulls enterprise app inventory into the workspace |
| **Eval gate** | Golden Q&A, MCP cases, live/fixture tools | Scores / pass-fail (CI or local report) | Golden `g001` escrow prompt → pass/fail + citation metrics | Quality bar for agent and tools |
| **`index_docs` (on demand)** | Same local SOP markdown (or path the tool indexes) | Same `docs` vector namespace as SOP ingest | Tool `index_docs` → same writer as SOP ingest | Runtime re-index; **same writer** as ingest (`DocsService`) |

### Same purpose, one writer

| Concern | Single writer | Removed duplicate |
|---|---|---|
| Capability / app map | EAKG sync (+ shared `capability_kg` library) | Single-TTL capability catalog build CLI |
| Policy vectors | `DocsService.index_directory` | Separate chunk/embed loop in old rag ingest |
| OpenAPI search sidecar | ApiIndex refresh (sidecar-only mode) | Standalone OpenAPI embed wrapper CLI |

---

## Examples (source → output)

### 1. EAKG sync

**Source (example)**
- Registry entry for `loanservices` (git URL + branch)
- OpenAPI: `getPaymentSchedules` on `/api/Loans/{loan_id}/PaymentSchedules`
- Optional TAAC app list

**Output (shape)**
```text
data/eakg/repos/loanservices/graph.ttl      # capabilities + ops for that app
data/eakg/repos/loanservices/interface.json # structured interface for ApiIndex
data/eakg/enterprise/cross_app.ttl          # links across apps (nightly)
data/eakg/proposals/…                      # items needing human review
```

Turtle flavor (capability):
```turtle
loanops:cap_get_payment_schedules a loanops:Capability ;
    rdfs:label "get_payment_schedules" ;
    loanops:implementedBy loanops:op_getPaymentSchedules ;
    loanops:readOnly true .
```

**Why:** agent can discover “which app owns payment schedules” and what is callable.

---

### 2. API index refresh

**Source (example)**
```json
{
  "operationId": "getPaymentSchedules",
  "summary": "Get payment schedules for loan",
  "path": "/api/Loans/{loan_id}/PaymentSchedules",
  "method": "GET",
  "application_id": "loanservices"
}
```

**Output (shape)** — under `data/eakg/enterprise/api_index/<env>/`:
```text
operations.json            # unified op list
openapi_embeddings.json    # local vector sidecar (fallback)
index.manifest.json        # build metadata / hashes
```

`operations.json` flavor:
```json
{
  "environment": "dev",
  "operations": [
    {
      "public_id": "loanservices:getPaymentSchedules",
      "application_id": "loanservices",
      "method": "GET",
      "path": "/api/Loans/{loan_id}/PaymentSchedules",
      "summary": "Get payment schedules for loan",
      "read_only": true,
      "callable": true
    }
  ]
}
```

**Why:** API search finds the right operation by meaning or keywords.

---

### 3. SOP / policy ingest

**Source (example)** — Confluence cache page
`data/sops/_confluence/escrow/annual-analysis.md` (gitignored; refresh via live Confluence).

**Output** — vectors in namespace `docs`, metadata like:
```json
{
  "corpus": "sop",
  "path": "escrow/annual-analysis.md",
  "category": "escrow"
}
```

**Why:** doc search can cite Confluence-backed policy paths.

---

### 4. GraphRAG build

**Source** — same Confluence SOP corpus as ingest (`data/sops/_confluence`).

**Output (example)** — `data/graphrag/communities.json` (community of related Confluence SOP paths + summary).

Plus `data/graphrag/manifest.json` (corpus hash, phase, model pin).

**Why:** groups related policies so doc answers can use community context, not only one chunk.

---

### 5. EAKG capability embeddings

**Source** — capability from EAKG shards:
```text
id: get_payment_schedules
description: Get payment schedules for loan
operation: getPaymentSchedules
http_path: /api/Loans/{loan_id}/PaymentSchedules
```

**Embed text (built, then vectorized)**
```text
get payment schedules. Get payment schedules for loan. operation getPaymentSchedules.
path /api/Loans/{loan_id}/PaymentSchedules. Loans Payment Schedules. domain loan servicing.
```

**Output** — `data/eakg/enterprise/embeddings.json`:
```json
{
  "capabilities": [
    {
      "id": "get_payment_schedules",
      "text": "get payment schedules. Get payment schedules for loan. …",
      "text_hash": "a1b2c3d4e5f67890",
      "vector": [0.12, -0.04, 0.88]
    }
  ]
}
```
(`vector` shortened; real dims match the embedding provider.)

**Why:** question “when is the next payment due?” still ranks payment-schedule capability when keywords miss.

---

### 6. TAAC refresh

**Source** — live TAAC client config from GitLab (never committed).  
Synthetic fixture shape: `data/eakg/fixtures/taac-client-config.redacted.json`:
```json
{
  "Title": "Synthetic Servicing Enterprise",
  "ServiceUrls": {
    "EscrowManagerApiUrl": "https://escrowapi.example.invalid",
    "FeesApiUrl": "https://feesapi.example.invalid",
    "LoanServicesUrl": "https://loanservicesapi.example.invalid"
  }
}
```

**Output**
```text
.eakg-workspace/taac-client-config.json   # gitignored local copy
```
Then nightly / TAAC ingest can turn this into enterprise app nodes.

**Why:** EAKG knows which enterprise apps exist and their base URLs without committing secrets.

---

### 7. Eval gate

**Source (example)** — `data/golden.jsonl`:
```json
{
  "id": "g001",
  "rep_prompt": "Loan 100245 escrow jumped $35 in May — draft a reply explaining why.",
  "loan_id": "100245",
  "expected": {
    "must_cite": ["policy:escrow/annual-analysis.md", "tool:call_sse_api"],
    "must_call_tools": ["search_sse_apis", "call_sse_api", "search_docs"]
  }
}
```

**Output** — pass/fail + metric scores (local / CI artifact), e.g. citation rate, tool-call match, refusal correctness.

**Why:** stop regressions when prompts, tools, or indexes change.

---

### 8. `index_docs` (on demand)

**Source / output** — **same as §3 SOP ingest** (local markdown → `docs` namespace).

**Why:** re-index without leaving the app; one writer, two entry points (batch ingest vs tool).

---

### 9. Code → Engineering KG

**Source** — cloned app source under the EAKG workspace (AST extract).

**Output**
```text
data/eakg/repos/<id>/engineering/graph.json
data/eakg/repos/<id>/engineering/links.json
```

**Why:** join API operations back to code symbols for debugging / “where is this implemented?” — not the primary MCP capability menu.

---

## Not a product pipeline — Graphify (this LoanOps repo)

| Name | Source | Output | Description |
|---|---|---|---|
| **Graphify (this repo)** | LoanOps-Agent source + docs | `graphify-out/` (`graph.json`, `graph.html`, `GRAPH_REPORT.md`) | Dev / agent **code map** for this repo. Not used by MCP discovery at request time. |
| **Graphify (optional clones)** | Cloned apps under `.eakg-workspace/` | `.eakg-workspace/graphify/<id>/` | Optional AST dump; feeds Engineering KG when wired. **Not** EAKG product truth. |

**Source (example)** — Python module with symbol `ApiSearchService`.

**Output (flavor)** — node in `graphify-out/graph.json`:
```json
{
  "id": "…_apisearchservice",
  "label": "ApiSearchService",
  "source": "projects/LoanOps.ApiIndex/packages/api_index/search.py",
  "type": "code"
}
```

**Vs EAKG / GraphRAG / Engineering KG**

| Graph | Answers |
|---|---|
| EAKG | Which **apps / APIs** exist and how they relate |
| GraphRAG | How **policy documents** connect |
| Engineering KG | How a **registered app’s code** is wired |
| Graphify (`graphify-out/`) | How **this LoanOps-Agent repo** is structured |

---

## Quick flow (mental model)

```text
App repos + OpenAPI + TAAC  ──►  EAKG shards  ──►  discovery / impact
                              └─►  ApiIndex vectors  ──►  operation search
                              └─►  capability embeddings  ──►  NL capability rank
                              └─►  Engineering KG (optional)  ──►  code wiring

Confluence SOP cache        ──►  docs embeddings  ──►  search_docs
                              └─►  GraphRAG (optional)  ──►  related-policy context

This repo source            ──►  graphify-out/  ──►  dev code map only
```
