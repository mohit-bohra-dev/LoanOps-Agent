# Plaisse MCP Gateway vs LoanOps — comparison

**Date:** 2026-10-12  
**Their diagram:** [Plaisse MCP Gateway (Lucid)](https://lucid.app/lucidchart/5bde0882-4c55-4eb1-9ded-754ab9db2686/view)  
**Our diagram (one page):** [LoanOps MCP Architecture (Lucid)](https://lucid.app/lucidchart/214feeb3-4a57-4947-b742-38e660794ada/view)

**Sources:** Their side comes from their Lucid diagram and what their team told us on a call (it runs in Dev; OpenAPI is given to Bedrock; a developer writes the Cedar rules for each new app, starting from that app’s OpenAPI). We have not reviewed their code. Our side comes from our own code and diagram.

This note compares **two different builds** aimed at the same problem: let people use AI (for example Cursor) to reach Plaisse APIs safely and correctly.  
They are not two names for the same product. Each team invested in a **different half** of the problem.  
Their team is **infrastructure-focused**: who may call what. Ours is **knowledge-focused**: what exists, and which call is the right one.

---

## One sentence each

**Plaisse MCP Gateway** is an **enterprise front door**. The user proves who they are; the gateway checks whether they are **allowed** to use that API; then it calls the real Plaisse service on their behalf.

**LoanOps** is a **find-the-right-API platform**. It keeps a structured catalog of what exists (knowledge graph + API index + engineering graph), searches that catalog first, and only allows **known read-only** calls — so the AI is less likely to invent a fake endpoint.

---

## Scorecard

| Area | Who is ahead | Why |
|------|--------------|-----|
| **Login and permissions** (who is the user, what may they call, call the API as that user) | **Them** | They started this track about a month earlier. Their design includes workforce login, fine-grained allow/deny rules (Cedar, written by developers for each new app), and token exchange so the backend sees the right person. We used a simpler shared token at our MCP edge and put that time into other layers. |
| **Fewer wrong / invented APIs** (hallucinations) | **Us, by design** | We focused on a knowledge graph, search over a fixed catalog, and “only call what we already know.” Their team gives OpenAPI to Bedrock so the model picks from the spec — faster to wire, but easier for the model to pick a close-but-wrong call. We have not yet measured this side by side (see “Where we are still exposed”). |
| **Deployment stage** | **Them** | Their gateway is running in a Dev environment on AWS (confirmed by their team). Their Lucid shows VPC, Secrets Manager, CloudWatch and multi-AZ APIs. Ours runs on a developer machine so far and calls Plaisse dev APIs; it is not deployed to AWS yet. |
| **Discovering capabilities across apps** | **Us** | We built EAKG, API search, and engineering-graph tools (`describe_application`, `search_code`). Their gateway’s main job is secure access, not explaining every capability. |

Neither side “won” overall.  
They are ahead on **trust and identity**.  
We are ahead on **grounding** (knowing what exists) and **reducing invented endpoints**.

---

## Three questions every system must answer

Before a live API call succeeds, three things must be clear:

1. **What** — Which API / operation should we use for this question?  
2. **Permission** — Is **this person** allowed to call **that** API?  
3. **Do** — Actually make the HTTP call and return the result.

| Question | Them | Us |
|----------|------|----|
| **What** | OpenAPI list is given to **Bedrock**. The model reads the API “menu” and chooses an operation. | OpenAPI is loaded into a **catalog and knowledge graph**. We **search** first; the model picks from a shortlist of known hits. |
| **Permission** | **Cedar** allow/deny rules + user login token (JWT) + on-behalf-of tokens so the call runs as that user. | Tool allow-lists, read-only (GET) rules, capability bind, and roles. Today the MCP edge uses one shared bearer token — weaker on real per-user identity. |
| **Do** | Gateway exchanges tokens, then HTTPS to Foreclosure / Bankruptcy / other Plaisse APIs. | `call_sse_api` (and related tools) through our MCP server, with CredentialBroker / Auth0 machine login for outbound credentials. |

---

## Picture in plain words

```text
THEM (permission-first)
  Cursor → user login → Gateway checks Cedar rules → call Plaisse API
                 ↑
           Bedrock uses OpenAPI to pick "what"

US (catalog-first)
  User / agent → search catalog / knowledge graph → only known read (GET) → call API
                 ↑
           citations + quality tests; simpler MCP login today
```

### Our Lucid (what we built)

One chart to share: [LoanOps MCP Architecture](https://lucid.app/lucidchart/214feeb3-4a57-4947-b742-38e660794ada/view)

It shows the full path in one place:

- Clients (Web UI / Cursor) → Agent API / MCP server → tools  
- **What:** ApiIndex + EAKG catalog/knowledge graph + engineering graph (`describe_application`, `search_code`)  
- **Do:** read-only GET to Plaisse APIs via CredentialBroker / Auth0 machine login  
- **Permission** at our MCP edge today is simpler than their Cedar + user-login gateway  

**Status:** the engineering-graph tools are built and wired into our MCP server, but not yet released. Today the whole system runs on a developer machine and has made real read-only calls to Plaisse dev APIs.

---

## Terms in simple words

| Term | Simple meaning |
|------|----------------|
| **MCP** | A standard plug so an AI client (like Cursor) can call tools on a server. |
| **MCP Gateway** | Middle server: receives the AI’s tool call, checks security, then calls real company APIs. |
| **OpenAPI / Swagger** | A machine-readable “menu” of an API: paths, methods (GET/POST), parameters. |
| **Bedrock** | Amazon’s hosted AI models. Their team gives it OpenAPI so the model chooses which endpoint to call. |
| **Cedar** | Amazon’s language for allow/deny rules, for example: “Alice is allowed to GET loan status on Foreclosure.” |
| **Cedar policy** | One allow/deny rule. At their team, a developer writes these for each new app, starting from the app’s OpenAPI. |
| **JWT** | A signed digital ID badge. Proves “this request is from this logged-in user or app.” |
| **Bearer token** | A secret string sent with each request, like a key. Ours is one shared token for the MCP server; theirs is a per-user JWT. |
| **Login (authentication)** | **Who are you?** |
| **Permission (authorization)** | **What are you allowed to do?** |
| **On-behalf-of (OBO)** | The gateway gets a short-lived token to call an API **as that user**, not as a generic robot account. |
| **Machine login (M2M)** | A program, not a person, signs in to get a token. We use this for our calls out to Plaisse APIs. |
| **Auth0 / OneLogin / Active Directory** | Company login systems. People sign in there; Auth0 often issues the JWT that apps trust. |
| **VPC** | Private network inside AWS. Internal services live there, not on the open internet. |
| **Secrets Manager** | AWS vault for passwords and client secrets. |
| **CloudWatch** | AWS logs and metrics. |
| **Hallucination** | When the AI invents something that is not real — for example a fake API path. |
| **Knowledge graph (KG)** | A structured map of things and how they connect (apps, APIs, capabilities) — not a free-form chat dump. |
| **EAKG** | Our enterprise app knowledge graph: catalog of apps and APIs built from code + OpenAPI so we know what exists. |
| **ApiIndex** | Our searchable index of API operations. It matches by meaning as well as exact words. |
| **Capability** | A named business action via an API (for example “get loan summary”), tied to a real operation. |
| **Capability bind** | If the agent asks to call by capability id, it must match a known catalog entry — inventing a new one fails. |
| **GET-only / read-only** | Only read requests. No create / update / delete through the agent in this version. |
| **Catalog** | The fixed list of known operations we loaded ahead of time. |
| **Citation** | Proof in the answer: “this came from policy X or tool Y.” |
| **Eval / golden set** | Fixed test questions we re-run so quality does not silently get worse. |
| **CredentialBroker** | Our helper that fetches tokens for outbound API calls (including machine login). |
| **Engineering graph** | A map of an app’s structure built from its code (service proxies, packages, classes), so we can answer “what does this app call, and which classes does it use?” |
| **Graphify** | The tool that reads source code and builds that map of classes and how they connect. |

---

## Login and permissions: they are ahead

They spent early time on the hard enterprise path:

- Real user identity (not only a shared server password)
- Fine-grained allow/deny (Cedar), written by a developer for each new app
- Token exchange so the backend sees the right caller
- Gateway sitting in AWS the way Plaisse apps already do

We did **not** prioritize that path the same way in the first month. Our MCP edge today is closer to “shared token + role + read-only checks.” That supports catalog and discovery work; it is **not** yet their full workforce permission story.

In short: on login and permissions they are ahead because they started that track earlier. We spent the same period on the knowledge graph and on reducing invented APIs.

---

## Invented APIs: we focused here

Wrong API calls hurt trust. Our bets:

| Bet | What it does |
|-----|----------------|
| Build catalog / EAKG from OpenAPI + code | The model does not invent the menu; the menu is pre-built |
| Search, then call | The model sees a **shortlist**, not the whole OpenAPI dump |
| Capability bind + read-only | Unknown or write operations fail closed |
| Citations + eval tests | Answers must point at sources; regressions get caught |

Their **what** path (OpenAPI → Bedrock) fits Bedrock’s tool style and can stand up quickly. It is also more open to “close but wrong” endpoint or parameter guesses.  
Cedar blocks **unauthorized** callers. It does **not** by itself stop a call that is **allowed but wrong**, or that looks invented.

In short: we are less prone to inventing endpoints because we limit what is callable. They are stronger on who is allowed to call.

### Where we are still exposed

Our approach lowers the risk. It does not remove it:

- **Only loaded apps.** We can only find APIs for apps already in our catalog.
- **Wrong known API.** Search can return a real operation that is not the best match for the question.
- **Parameters.** The model still fills in values such as a loan number in the URL path.
- **Answer text.** The final wording is still written by the model. Citations help but do not guarantee correctness.
- **Not yet measured.** “Less prone” is a design advantage. We have not run a side-by-side test of wrong-call rates on the same questions. That test would confirm it.

---

## Same starting material, different cooking

Both start from **OpenAPI JSON** (the API menu). They use it in different places:

```text
OpenAPI
  ├─ Them → Bedrock (what) + Cedar (permission) + Gateway (do)
  └─ Us   → Catalog / knowledge graph + search (what)
            + our policy checks (permission today) + MCP call (do)
```

---

## Adding a new app

This is where the infrastructure focus shows.

| | Them | Us |
|--|------|----|
| **Who does the work** | A developer writes the Cedar rules for the new app, starting from its OpenAPI. | An onboarding run reads the app’s code and OpenAPI and adds it to the catalog. No per-app rule files to write by hand. |
| **What you get** | Precise, reviewable permissions for that app: who may call which operation. | A searchable map of what the app offers, with read-only and “known operation” checks built from the catalog. |
| **Risk** | Every new app needs a developer, and the rules can fall out of date when the API changes. | We do not yet give per-user permissions, so we depend on a gateway like theirs for that. |
| **Scales by** | Developer effort per app | Automated onboarding and sync |

---

## Can Cedar describe relationships between two apps?

**For permission rules: yes.**  
Example: “The Foreclosure app is allowed to call Bankruptcy read APIs.”

**For discovering and storing “who calls whom” as knowledge: no.**  
That is catalog / graph work (our EAKG and engineering graph). Cedar **enforces** relationships you already give it; it does not **discover** them from source code.

---

## How to combine later (not built yet)

Do not throw either side away. The best long-term shape uses both strengths.

| Keep from them | Keep from us |
|----------------|--------------|
| User login tokens, Cedar rules, on-behalf-of gateway | EAKG + search + capability bind + citations + eval tests |
| Production AWS edge | Catalog / knowledge-graph grounding |

Safe sequence:

1. **We** answer **what** — search the catalog / knowledge graph and pick a known operation.  
2. **They** answer **permission** — Cedar + user identity confirm this person may call that operation.  
3. Only then **do** the read (GET) against the Plaisse API.

Idea (not built): our catalog already lists every operation of an onboarded app. That list could give developers a starting point when they write Cedar rules for a new app.

---

## Cheat sheet

| Question | Lean them | Lean us |
|----------|-----------|---------|
| “Is this user allowed to call that API?” | Yes | Not yet at their level |
| “Which known read API matches this question, with less inventing?” | Weaker by design | Stronger by design (not yet measured) |
| “Call Foreclosure / Bankruptcy with real workforce identity” | Their design | Gap for us |
| “Explain capabilities / impact across onboarded apps” | Not their focus | Yes |
| “Who does the work when a new app is added?” | A developer writes Cedar rules | Automated onboarding from code + OpenAPI |
