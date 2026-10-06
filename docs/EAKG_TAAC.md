# How TAAC becomes part of the knowledge graph

Plain-language map of what TAAC is, what we turn it into, and where the code lives.

Related: [`EAKG_COMMITTED_VS_LOCAL.md`](EAKG_COMMITTED_VS_LOCAL.md), [`STACK_LAYER_DECISIONS.md`](STACK_LAYER_DECISIONS.md).

---

## Two graphs (do not mix them)

| Graph | What it is | Used by the agent at runtime? |
|---|---|---|
| **EAKG** | Map of **servicing apps** (Escrow, Fees, Loan Services): who they are, which APIs they expose, how they call each other | **Yes** — MCP capability search when shards exist |
| **Graphify** | Map of **this LoanOps-Agent repo** (Python files, functions) | **No** — for developers/agents working on this codebase only |

TAAC feeds **EAKG only**. It never feeds Graphify.

---

## What TAAC is

TAAC is a **client config JSON** used by servicing apps (service URLs, feature flags, SQL connection names, SQS queue names, Auth0).

We do **not** invent that file. We **read** a copy:

- **Safe for git:** `data/eakg/fixtures/taac-client-config.redacted.json` (fake hosts, no secrets).
- **Live (local only):** copy via `scripts/eakg/refresh-taac.ps1` into `.eakg-workspace/`. Never commit. Point `EAKG__TAAC_CONFIG_PATH` at it.

Think of TAAC as a **directory of the company**: “these apps exist, they live at these hosts, they use these databases and queues.”

---

## What we build from TAAC (the skeleton)

The function `build_enterprise_graph` walks the JSON and writes RDF triples:

| TAAC section | Becomes in the graph |
|---|---|
| `Auth0` | An **auth provider** node |
| `ServiceUrls` (e.g. `FeesApiUrl`) | An **application** node (id `fees`) plus hostname |
| `FeatureManagement` (e.g. `EscrowManagerApiEnabled`) | Extra **application** nodes when the flag is on |
| `ConnectionStrings` | **Data store** nodes (database catalog name only — not passwords) |
| `AWS.SQS` | **Event topic / queue** nodes |

That skeleton is written under gitignored `data/eakg/enterprise/` (enterprise apps Turtle).

**TAAC does not list loan APIs.** There is no `getLoanSummary` in TAAC. Those operations come from **reading .NET code** (Roslyn, with regex fallback) and **OpenAPI**, then stored per repo under `data/eakg/repos/`.

---

## How the rest of EAKG attaches

After the skeleton exists, a **cross-app** pass runs:

1. Load TAAC again as **lookup maps** (URL key → app id, connection key → database name).
2. Load each repo’s extracted **interface** (controllers, packages, routes).
3. **Detectors** look for evidence in code (NuGet clients, hardcoded URLs, SQS topics, SQL catalogs, auth) and draw **edges** between apps.
4. Those edges become `cross_app.ttl`.

So: **TAAC names the buildings. Code extract + detectors draw the roads.**

---

## Where the code is

All under `projects/LoanOps.Eakg/packages/eakg/` (import path `packages.eakg`).

| File | Role |
|---|---|
| `taac.py` | Parse TAAC JSON → RDF (`build_enterprise_graph`, `ingest_taac_file`, URL/DB maps) |
| `onboard.py` | `rebuild_cross_app()` — ingest TAAC, then run detectors |
| `sync.py` | Same ingest on a scheduled/manual sync |
| `__main__.py` | CLI: `ingest-taac`, `onboard`, `cross-app` |
| `detectors.py` | Cross-app edges; uses TAAC helpers `url_key_to_app_id`, `normalize_topic` |
| `graph_build.py` | Turns **repo extractor facts** into Turtle — **not** TAAC |
| `store.py` | Writes shards to `data/eakg/` |
| `packages/capability_kg/ontology.py` | Shared RDF type and predicate names |

---

## Commands

```powershell
# Skeleton only (from fixture or EAKG__TAAC_CONFIG_PATH)
uv run python -m packages.eakg ingest-taac

# Skeleton + detector edges (needs onboarded repos)
uv run python -m packages.eakg cross-app
```

Settings: `EAKG__TAAC_CONFIG_PATH` (live file) or `EAKG__TAAC_FIXTURE_PATH` (default redacted fixture).

---

## Is there a TTL file?

**Yes, after ingest.** TAAC itself is JSON. The graph is saved as Turtle:

| File | From | In git? |
|---|---|---|
| `data/eakg/enterprise/applications.ttl` | TAAC (`write_enterprise_apps`) | **No** — folder gitignored |
| `data/eakg/enterprise/cross_app.ttl` | Detectors, not TAAC | **No** |
| `data/eakg/fixtures/taac-client-config.redacted.json` | Source JSON | **Yes** |

This machine already has `applications.ttl` (local only). Rebuild:

```powershell
uv run python -m packages.eakg ingest-taac
```

---

## One sentence

We developed the TAAC part of the KG by **translating a redacted client-config JSON into RDF apps/hosts/DBs/topics** in `packages/eakg/taac.py`; we **did not** generate API operations from TAAC — those come from code and OpenAPI, then detectors **join** them using TAAC as the name map.
