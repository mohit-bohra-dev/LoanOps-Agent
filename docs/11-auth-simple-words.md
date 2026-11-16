# Auth in simple words — Wiki, MCP Gateway, and LoanOps

**Date:** 2026-11-11  
**Audience:** Anyone who needs the story without jargon  
**Status:** Working note (not an ADR yet)

Related: [`PLAISSE_WIKI_VS_LOANOPS.md`](PLAISSE_WIKI_VS_LOANOPS.md) · [`PLAISSE_MCP_GATEWAY_VS_LOANOPS.md`](PLAISSE_MCP_GATEWAY_VS_LOANOPS.md) · [`MCP_SECURITY.md`](MCP_SECURITY.md) · D7 in [`DECIDE_AND_CLEANUP.md`](DECIDE_AND_CLEANUP.md)

**Lucid (ideal auth):** [LoanOps Ideal Auth Architecture](https://lucid.app/lucidchart/7205bc1c-9deb-4577-b765-bc8e185d7b8f/edit)

---

## The two questions

Before any live API call, ask:

1. **Who is asking?** — which person, and which app (Cursor, our Agent API, …)
2. **Who is the call made as?** — the person, or a shared robot account?

Wiki, the Plaisse MCP Gateway, and LoanOps answer those differently.

---

## Picture in plain words

```text
WIKI
  Person → App (Auth0) → wiki checks AppAuth (app + person)
  Wiki calls Plaisse APIs as ITSELF (machine login)

MCP GATEWAY
  Person signs in (OneLogin → Auth0)
  Gateway checks Cedar rules
  Gateway calls Plaisse APIs AS THAT PERSON (on-behalf-of)

LOANOPS TODAY
  Shared password into our MCP
  We find the right GET from our catalog
  We call Plaisse with a machine login (shared service token)
  We do NOT yet know the real person or the real client for sure
```

---

## Plaisse wiki — how login works

**Job:** shared feature docs + occasional live GET/SQL.

| Piece | Simple meaning |
|-------|----------------|
| Front door | API Gateway checks an Auth0 token |
| Who calls the wiki | Usually an **app** (e.g. LAMP), not a person typing into the gateway |
| Naming the person | App must also say **which colleague** is asking |
| Permission | AppAuth roles on app `PlaisseWiki`: **Reader** / **Admin** — checked for **both** the app and the person |
| Live API calls | Wiki uses its own machine account (`00plaissewiki-…`), not the human |

**Does the wiki know who called?** Yes, at its own front door. Every request has two names: the **app** (from the Auth0 token, e.g. `00lamp-dev`) and the **person** (the app must name them). If nobody is named, the wiki refuses the call. It checks permission for both, and it keeps conversations per person.

**Does a Plaisse API (Escrow, and so on) see that person?** No. When the wiki calls those APIs, it signs in as **itself**. Those APIs see the wiki bot, not the colleague.

Local console (`npm start`) has **no login** — developers only.

---

## Plaisse MCP Gateway — how login works

**Job:** let Cursor (and similar) call Plaisse APIs safely, as the signed-in user.

| Piece | Simple meaning |
|-------|----------------|
| Front door | User signs in with OneLogin → Auth0; token audience `https://plaisse-mcp` |
| Permission | **Cedar** allow/deny rules (a developer writes them per app from OpenAPI) |
| Live API calls | Gateway **exchanges** the user token for an on-behalf-of token (`aud=https://pennymac`) |
| What the API sees | The **real person’s** id — not a shared AI account |
| Network | Private path into the Plaisse VPC |

Status: DEV/STG. Read-only GETs by design. Cedar in DEV is mostly “log only” for now.

---

## LoanOps today — what we actually do

| Piece | Simple meaning |
|-------|----------------|
| Front door | One shared bearer (`MCP__AUTH_TOKEN`) |
| Role | Process-wide role (`MCP__ROLE`) — which tools are allowed |
| Safety we own | GET-only, host allow-list, capability bind, citations, eval |
| Live API calls | Auth0 **machine** token (Subservicing M2M) into Plaisse |
| “User” headers | `x-loanops-user` / env defaults — **easy to fake**; audit hint only |

Settled for this phase (**D7**): keep machine login. Full “call as the person” comes later.

---

## Product goal — LoanOps MCP is the shared tool server

**Intent:** LoanOps MCP is the one place that finds known GETs and calls Plaisse (read-only). Several **clients** talk to it. The Plaisse wiki product can keep its UI / docs flow, but for live API tools it becomes a **client of our MCP** — not a second catalog and invoke stack.

### Who calls our MCP

| Client | How it reaches us | Who we must record |
|--------|-------------------|--------------------|
| **Plaisse wiki client** | Wiki (or LAMP embedding wiki) calls LoanOps MCP tools | Calling **app** + **person** (wiki-style) |
| **Cursor** | Direct MCP connection | **User JWT** + client = Cursor |
| **LoanOps Agent API** | Our `/chat` agent uses MCP as its tool backend | Agent API as client + end **user** on whose behalf |
| **Future agents** | Same MCP contract | Each gets its own client id; always name the **person** |

```text
  Plaisse wiki client ──┐
  Cursor ───────────────┼──▶ LoanOps MCP ──▶ catalog ──▶ Plaisse GET (M2M now)
  LoanOps Agent API ────┤         │
  Future agents ────────┘         └─ audit: person + which client
```

One shared bearer for all of these is **not** enough. Every client must prove **which product** it is and **which person** it acts for.

That does **not** mean “become a copy of the MCP Gateway.” It means:

| Take from wiki (must match or beat) | Take from Gateway (only where needed) | Keep LoanOps strength |
|-------------------------------------|----------------------------------------|------------------------|
| Know **who** asked (person + calling app/client) | Real user JWT when Cursor talks to us directly | Catalog = which known GET |
| Refuse unnamed callers | OBO later if APIs must see the person | GET-only, bind, citations, eval |
| Outbound M2M as “the assistant” is OK at first (wiki does this) | Cedar — **reuse their gateway**, do not rebuild | EAKG / ApiIndex, not `mcp-catalog.json` alone |

**Still not automatic “full wiki replace”** (unless we build these later):

- GitLab → write feature docs → commit → re-index (wiki’s doc factory)
- Broad TAAC “every service in the env” live registry
- SQL specialist over many TAAC databases

First shared-MCP target = **any client → find known API → read-only call → attributable to person + client**. Docs-factory can stay on the wiki side.

---

## Which is better for LoanOps

**Use pieces of both. Do not copy either product whole.**

LoanOps has two jobs that those products split apart:

1. **Know the caller** — which person, and which client (Cursor, our Agent API, LAMP, …).
2. **Pick the right read** — a known GET from our catalog, then call it.

| If we copied only… | What we would get | Why that is not enough |
|--------------------|-------------------|------------------------|
| **Wiki** | We would know the app and the person at our door. Calls out would still be “as the bot.” | Good for “replace wiki” on identity. Weak if Cursor hits MCP with no host app naming the user — then we also need a user JWT (Gateway-style). Catalog still beats wiki at “exactly which GET.” |
| **MCP Gateway** | We would know the signed-in person, and Plaisse APIs would see that person. Fine allow/deny rules (Cedar) per tool. | Weaker at “which GET is the right one.” Rebuilding Cedar inside LoanOps repeats their job. Replacing wiki does **not** require becoming their gateway. |

**What we should do (wiki-replace target)**

| Layer | Take this | In plain words |
|-------|-----------|----------------|
| Who called **us** | Wiki-grade: person + client/app. JWT when Cursor is direct. App + named person when LAMP embeds us. | No shared password. No spoofable header as proof. |
| What they may call | Our catalog | Search first. Only a known read. GET-only. Capability bind. Citations. Eval. |
| Who Plaisse APIs see | Same as wiki at first (LoanOps M2M). OBO / their gateway later if product needs “as this person.” | Matching wiki is enough to replace the wiki coworker. Beating wiki on outbound identity is optional Phase 2. |
| Cedar | Theirs if we route through their gateway | Do not rebuild Cedar in LoanOps. |

```text
1. Signed-in user / embedding app hits LoanOps MCP  → record person + client
2. We search the catalog                              → pick a known GET
3. We call Plaisse                                    → M2M (wiki-like) first
                                                      → OBO later only if required
```

**One line:** Replace the wiki coworker with LoanOps MCP = wiki-grade “who asked” + LoanOps catalog “which GET” + wiki-like M2M out at first; Gateway OBO/Cedar only when we must call as the person — not a Gateway clone.

---

## What we want next — who called us, and from which client

We need two facts on **every** tool call:

| Fact | Meaning | Must be trusted? |
|------|---------|------------------|
| **User** | Which person | Yes — from a signed login token, not a free-text header |
| **Client** | Which product called us (Cursor, LoanOps Agent, Gemini, …) | Yes — from the login client id, plus the MCP handshake name for display |

### Why headers alone are not enough

Anyone who knows the shared password can set `x-loanops-user: alice`. That is not proof Alice called.

### Simple target

```text
User JWT in  →  we read: person (sub) + client (azp / client_id)
MCP handshake → we also record: clientInfo.name (e.g. "cursor")
Audit log     → every tool call stores both
```

### Three small steps

1. **Client name (quick)**  
   Read MCP `initialize` → `clientInfo.name` / `version`. Put on every audit/telemetry span. Stop defaulting everything to `unknown`.

2. **Real user (next)**  
   Replace the shared password with an Auth0 **user** token on our MCP. Person = token `sub`. Reject if the person changes mid-session.

3. **Trusted client (with step 2)**  
   Separate Auth0 apps (or client ids) for Cursor vs our Agent API vs others. Client = claim on the token. Optional: reuse the Plaisse MCP Gateway login for Cursor instead of building a second login.

Outbound Plaisse calls can stay **machine login** until product needs “as this person.” Then use **on-behalf-of** (same idea as the Gateway), not wiki’s “bot is itself,” for workforce use.

---

## How the three fit together (long term)

Do **not** copy everything into LoanOps.

| Keep from Gateway / Wiki | Keep from LoanOps |
|--------------------------|-------------------|
| User login + on-behalf-of (when we need call-as-user) | Catalog / knowledge graph — **which** GET exists |
| Fine permission edge (Cedar) when using their gateway | Capability bind, GET-only, citations, eval |

Safe sequence:

1. **We** pick a **known** read operation (search catalog).  
2. **Identity** says this person + this client may use our MCP.  
3. **Call** — machine token today; on-behalf-of later if the API must see the person.

---

## Words used in the flows

| Word | Simple meaning |
|------|----------------|
| **Auth0** | Login system that issues a signed token (JWT). Proves “this request is from this account.” |
| **JWT** | The signed digital badge. Holds claims such as person id (`sub`) and client id (`azp`). |
| **AppAuth** | PennyMac’s role book: does this account have Reader / Admin / … on this application? |
| **AppServices** | The central API that looks up AppAuth roles (`/api/Authorization`). |
| **Cedar** | Allow/deny rules on the MCP Gateway for each tool (written per app). |
| **OBO (on-behalf-of)** | Swap a user token for a short token the Plaisse API trusts, still for the **same person**. |
| **M2M (machine login)** | A program (not a person) signs in. Shared service account. |
| **Catalog** | LoanOps’ fixed menu of known GETs (from code + OpenAPI). Search picks a row; inventing a path fails. |
| **Capability bind** | If the call names a capability id, it must match that catalog row. |

---

## Detailed flows

Read these as “what happens on one question that needs a live GET.”

### Flow A — Plaisse wiki (knows caller; APIs see the bot)

```text
1. Colleague opens LAMP (or another Plaisse app).
2. LAMP holds an Auth0 token for its service account (e.g. 00lamp-dev).
3. LAMP also names the colleague (OBO claim or x-requesting-user).
4. Request hits wiki API Gateway → Auth0 JWT checked.
5. Wiki asks AppServices AppAuth:
      - Does the APP have Reader on PlaisseWiki?
      - Does the PERSON have Reader on PlaisseWiki?
     Either “no” → refuse.
6. Wiki answers from docs when it can.
7. If it must call a live Plaisse API:
      - Wiki mints its OWN M2M token (00plaissewiki-…).
      - GET goes to Escrow / … as the wiki bot.
8. Plaisse API sees the wiki bot, not the colleague.
9. Wiki returns the answer; conversation stays bound to that person.
```

```text
Colleague ─▶ LAMP ─▶ Wiki front door (JWT)
                │         │
                │         ├─ AppAuth(app)  ──▶ allow?
                │         └─ AppAuth(person)▶ allow?
                │
                └─ (live GET) Wiki M2M ──▶ Plaisse API ──▶ bot identity
```

**Takeaway:** Wiki knows **who asked**. Downstream APIs do **not**.

---

### Flow B — Plaisse MCP Gateway (caller = person end to end)

```text
1. Person signs in (OneLogin → Auth0). Gets user JWT (audience = https://plaisse-mcp).
2. Cursor (or another MCP client) sends tools/call with that Bearer token.
3. Gateway validates the JWT.
4. Cedar checks: is this tool allowed for this caller? (GET allow rules; in DEV often log-only.)
5. Gateway exchanges the token (OBO):
      - Same person (same sub)
      - New audience = https://pennymac
6. HTTPS to Foreclosure / Bankruptcy / … inside the Plaisse VPC.
7. Plaisse API runs AppAuth as that person → 200 or 403.
8. Tool result returns to Cursor.
```

```text
Person ─▶ OneLogin/Auth0 ─▶ Cursor ─▶ MCP Gateway
                                      │
                                      ├─ validate JWT
                                      ├─ Cedar allow/deny
                                      └─ OBO exchange
                                            │
                                            ▼
                                      Plaisse API (AppAuth as person)
                                            │
                                            ▼
                                      tool result ─▶ Cursor
```

**Takeaway:** Person is known at the gateway **and** on the Plaisse API. “Which GET is right?” is weaker (OpenAPI to the model + allow-list), not a LoanOps-style catalog search.

---

### Flow C — LoanOps today (catalog strong; identity weak)

```text
1. Cursor / Agent hits LoanOps MCP with shared bearer (MCP__AUTH_TOKEN).
2. Role check (MCP__ROLE) → which tools are allowed.
3. Optional headers x-loanops-user / tenant → audit hint only (spoofable).
4. Agent searches catalog (search_sse_apis / search_capabilities).
5. Picks a known GET. Capability bind must match if capability_id is used.
6. call_sse_api: GET-only, host allow-list, no invented absolute URL.
7. Outbound: Subservicing Auth0 M2M (service account) → Plaisse GET.
8. Plaisse API sees our service account, not a proven person.
9. Answer returns with citations when the agent path requires them.
```

```text
Client ─▶ LoanOps MCP (shared token + role)
              │
              ├─ search catalog ──▶ known GET?
              ├─ bind / GET-only / host allow-list
              └─ M2M service token ──▶ Plaisse API
```

**Takeaway:** Strong on **what** (known GET). Weak on **who** (shared token; headers not proof).

---

### Flow D — LoanOps target (best combo)

Two phases. Phase 1 is enough for attributable MCP use. Phase 2 only when product needs “API sees this person.”

#### Phase 1 — know who called us; still call as machine

```text
1. Person (or Agent API on their behalf) presents Auth0 JWT to LoanOps MCP.
2. LoanOps reads person (sub) + client (azp / client_id). Reject bad/missing token.
3. Audit every tool call with person + client (+ clientInfo.name when present).
4. Search catalog → pick known GET → bind + GET-only + host allow-list.
5. Call Plaisse with M2M (same as today / D7).
6. Plaisse API still sees the service account.
```

```text
Person/client JWT ─▶ LoanOps MCP
                         │
                         ├─ record who + which client
                         ├─ catalog: which known GET
                         └─ M2M ──▶ Plaisse API
```

#### Phase 2 — also call as the person (when required)

```text
1–4. Same as Phase 1 (JWT in + catalog pick).
5. Instead of M2M: OBO exchange (or hand off to Plaisse MCP Gateway).
6. Plaisse API sees the same person; AppAuth decides 200 / 403.
7. Optional: Cedar on their gateway if the call goes through that edge.
```

```text
JWT in ─▶ LoanOps (what: catalog)
              │
              └─ OBO / their Gateway (who: person) ─▶ Plaisse API
```

**Takeaway:** Catalog stays ours. Identity and “as the person” reuse Gateway patterns. Do not replace EAKG with a flat `mcp-catalog.json`.

---

### Side-by-side on one question

Example: “Get foreclosure info for loan 1000002245.”

| Step | Wiki (A) | MCP Gateway (B) | LoanOps today (C) | LoanOps target (D) |
|------|----------|-----------------|-------------------|--------------------|
| Prove person at our door | App + named person + AppAuth | User JWT | Shared token only | User JWT `sub` + client |
| Choose the GET | Docs / Swagger search | Model + OpenAPI + allow-list | **Catalog search + bind** | **Same catalog** |
| Call Plaisse as | Wiki bot (M2M) | That person (OBO) | Our service M2M | M2M now; OBO later |
| API AppAuth sees | Bot | Person | Service account | Service now; person later |

---

## Cheat sheet

| Question | Wiki | MCP Gateway | LoanOps today | LoanOps target |
|----------|------|-------------|-----------------|----------------|
| Who is the person? | AppAuth + named user | Auth0 user JWT | Shared token / spoofable header | Auth0 user JWT `sub` |
| Which client called? | Calling app’s service account | OAuth client + Cursor | Not really known | Token client id + `clientInfo` |
| Who does the Plaisse API see? | Wiki bot | The person | Our service account | Service now; person later (OBO) |
| Fine “may call this GET”? | AppAuth roles | Cedar per tool | Role + GET + bind | Same + real user when needed |

---

## One sentence

**Goal: replace the wiki coworker with LoanOps MCP — wiki-grade who-asked, our catalog for which GET, M2M out like the wiki at first; add Gateway-style OBO (and their Cedar only if we use their edge) later if APIs must see the person — not a full MCP Gateway clone, and not a docs-factory clone unless we build that separately.**
