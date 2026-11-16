#!/usr/bin/env python3
"""Build the LoanOps Complete Guide (one PPTX + one PDF) for readers without code access.

Run: uv run --with python-pptx --with reportlab python presentations/loanops-overview/build_deck.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as pdf_canvas

OUT = Path(__file__).resolve().parent
NAME = "LoanOps-Complete-Guide"
LUCID_URL = "https://lucid.app/lucidchart/214feeb3-4a57-4947-b742-38e660794ada/view"
LUCID_CLOUD = "https://lucid.app/lucidchart/729e9984-d335-4bdc-bb6e-9a1a238a4208/edit"

NAVY = "0B1F33"
CARD = "14324A"
TEAL = "1AA6A6"
CREAM = "F4F7F9"
MUTED = "8A9BAA"
AMBER = "F2B134"


@dataclass
class Slide:
    title: str
    subtitle: str | None = None
    bullets: list[str] = field(default_factory=list)
    section: str | None = None  # set => section divider slide


def S(title: str, subtitle: str | None, *bullets: str) -> Slide:
    return Slide(title, subtitle, list(bullets))


def SECTION(label: str, title: str, subtitle: str) -> Slide:
    return Slide(title, subtitle, [], section=label)


# Bullets may use "Label :: text" to render the label in bold.
SLIDES: list[Slide] = [
    S(
        "LoanOps — Complete Guide",
        "Everything about the app in simple words: why it exists, how it works, every component, every pipeline",
        "For tech leads and stakeholders · no code access needed",
        "Architecture visuals: Lucid “LoanOps-Agent Runtime Architecture”",
    ),
    S(
        "How to read this guide",
        "Each component is explained the same way",
        "WHAT :: what the piece is, in one plain sentence",
        "USE :: what people or the system use it for",
        "WHY :: why we built it instead of doing without it",
        "Sections build on each other — skim the section dividers for the short story",
    ),
    S(
        "Contents",
        None,
        "A :: Why LoanOps exists — problem, goal, who it is for",
        "B :: How it is used — clients, a single answer step by step",
        "C :: Runtime building blocks — every live component",
        "D :: Knowledge — EAKG, embeddings, indexes, stores",
        "E :: Pipelines — how knowledge is prepared",
        "F :: Safety, security, quality · G :: Status, roadmap, glossary, FAQ",
    ),
    # ---------------- A
    SECTION("A", "Why LoanOps exists", "The problem, the goal, and who it serves"),
    S(
        "The problem today",
        "Answers are slow, scattered, and hard to trust",
        "Scattered :: one answer needs APIs, wikis, repos, SOPs and several screens",
        "Tribal :: “which system owns this?” lives in a few people’s heads",
        "Risky :: generic AI assistants guess facts and cannot show their sources",
        "Unauditable :: hard to prove what information an answer was based on",
        "Duplicated :: every new AI tool would rebuild its own integrations",
    ),
    S(
        "What we want instead",
        "Ask in plain English → grounded, cited draft for a human to check",
        "Find :: the right application capability or API operation automatically",
        "Read :: live business data from the real system — read-only",
        "Look up :: written policy / SOPs when the question needs rules",
        "Cite :: every fact points to its source (a policy doc or a tool call)",
        "Record :: an audit trail of what was asked, used and answered",
    ),
    S(
        "What LoanOps is",
        "An internal platform — one shared “tool room” over enterprise APIs and documents",
        "Platform :: not a single chatbot; a set of trusted tools many AI clients can use",
        "MCP-first :: tools are exposed through MCP, an industry standard for AI tool access",
        "Any role :: engineers, analysts, PMs, ops — not locked to one job title",
        "Hybrid :: same product runs locally or in the cloud by configuration only",
    ),
    S(
        "What LoanOps is not",
        "Boundaries are part of the design",
        "Not public :: no borrower-facing chat, voice or email channel",
        "Not an actor :: cannot post payments, start plans, place holds or change data (v1)",
        "Not an advisor :: no legal, tax, rate-quote or refinance advice",
        "Not finished UI :: the Chat UI is currently an evaluation harness, not the end product",
    ),
    S(
        "Who it is for",
        "Same tool room — different needs",
        "Engineers :: find and call the right API; understand apps and impact of change",
        "Analysts / ops :: get loan, escrow and fee facts with sources",
        "PMs :: understand capabilities and policy without hunting across systems",
        "Compliance / audit :: review what the assistant used for each answer",
        "Access differs by role :: each role sees only the tools it is allowed to use",
    ),
    # ---------------- B
    SECTION("B", "How it is used", "Two ways in, one tool room, one answer flow"),
    S(
        "Two clients, one tool room",
        "Everything flows through the same MCP tool room",
        "IDE assistant (e.g. Cursor) :: talks straight to the tool room — proves the tools work",
        "Chat UI :: goes through our Agent, which then uses the tool room — proves full answers",
        "Same website :: Eval Portal for quality checks and a Pipelines screen",
        "Later :: the wiki and other agents use this same room, and name the person and the app",
        "Why one room :: fix or improve a tool once and every client benefits",
    ),
    S(
        "Why we built the Chat UI",
        "To evaluate the tool room the way a real chat client would",
        "IDE use tests :: individual tools and the protocol",
        "Chat UI tests :: tool choice, multi-step answers, citations, refusals, speed",
        "It adds :: privacy checks, outbound safety, conversation memory and audit per turn",
        "Later :: once quality clears the bar, the same UI can become a real internal client",
    ),
    S(
        "Example questions",
        "What people ask — and what the platform does",
        "“What is the status of loan X?” :: finds the loan API, calls it, cites the tool",
        "“Why did escrow go up?” :: live escrow data + escrow analysis policy, both cited",
        "“Which API returns borrower summary?” :: searches the API index and capability map",
        "“What does the Escrow app expose?” :: describes the application from its map",
        "“Who provides payment schedules?” :: finds providers in the enterprise map",
        "“Give me a rate quote” :: politely refused — out of scope",
    ),
    S(
        "One answer, step by step (1/2)",
        "From the question arriving to tools being called",
        "1. Receive :: the message arrives with a conversation id",
        "2. Privacy check :: personal data is detected; an audit-safe copy is made",
        "3. Memory :: earlier turns of the conversation are loaded",
        "4. Fast gate :: risky or out-of-scope asks are refused or escalated before any AI cost",
        "5. Think + act :: the AI model may search and call tools, up to 3 rounds",
    ),
    S(
        "One answer, step by step (2/2)",
        "From tool results to what the person sees",
        "6. Tools run :: search APIs, search docs, call a live read-only API",
        "7. Structured answer :: the model must return answer + confidence + citations",
        "8. Validate :: malformed answers are retried once, otherwise safely refused",
        "9. Outbound safety :: unsafe content is blocked before display",
        "10. Audit + reply :: the turn is logged, and the answer is shown with its sources",
    ),
    S(
        "What the person sees",
        "Transparent by design",
        "Answer :: a draft in plain language",
        "Citations :: “policy: …” for documents, “tool: …” for live data",
        "Tool trace :: which tools were called and with what",
        "Confidence / refusal :: clear statement when it cannot or should not answer",
        "Human decides :: the person reviews before using the answer anywhere",
    ),
    S(
        "When a question is risky",
        "Refuse and escalate are features, not failures",
        "Refuse :: advice, rate quotes, mutating actions, anything out of scope",
        "Escalate :: legal, fraud, identity, safety or regulatory triggers",
        "Early :: a rule-based gate catches these before the AI model runs",
        "Late :: outbound safety catches anything unsafe the model produced",
    ),
    # ---------------- C
    SECTION("C", "Runtime building blocks", "Every live component — what, use, why"),
    S(
        "The big picture in layers",
        "Read top to bottom",
        "1. Clients :: Chat UI and IDE assistants",
        "2. Agent :: runs one conversation turn with safety and memory",
        "3. Tool room (MCP) :: shared, authenticated, read-only door to tools",
        "4. Tools :: API search, live API calls, document search, capability map, code map",
        "5. Knowledge stores :: graph database, operational database, vector search",
        "6. Business systems :: Plaisse servicing APIs (Escrow, Fees, Loan Services, …)",
    ),
    S(
        "North star",
        "The one sentence that guides every design choice",
        "The enterprise map fills the tools",
        "One MCP tool room serves every client",
        "IDE assistants and the Chat UI share that same room",
        "Only allow-listed, read-only calls reach business systems",
    ),
    S(
        "Chat UI",
        "The web chat screen",
        "WHAT :: a browser chat with a conversation pane and a loan lookup sidebar",
        "USE :: ask questions, see answers, citations and the tool trace",
        "WHY :: realistic way to evaluate the tool room end to end",
        "Eval Portal :: quality checks, traces, and a screen to start pipeline jobs",
        "Sidebar :: quick loan/borrower lookup that calls one API directly, without AI",
    ),
    S(
        "Agent",
        "The conversation engine behind the Chat UI",
        "WHAT :: the service that runs one chat turn from question to answer",
        "USE :: privacy check, memory, fast gate, AI model loop, validation, safety, audit",
        "WHY :: raw tools are not enough for chat — answers need control and structure",
        "Contract :: every answer is structured and must carry citations",
    ),
    S(
        "AI model (LLM)",
        "The reasoning part — swappable",
        "WHAT :: a large language model that reads the question and decides which tools to use",
        "USE :: picks tools, reads results, writes the draft answer",
        "WHY SWAPPABLE :: cloud model in enterprise (e.g. Amazon Bedrock) or local model in dev",
        "Guardrail :: the model never touches data directly — only through approved tools",
    ),
    S(
        "Tool room (MCP server)",
        "The shared door for every client",
        "WHAT :: a server exposing our tools through the MCP standard",
        "USE :: IDE assistants and the Agent call tools here",
        "Checks :: access token, role/scope allow-list, and “read-only only” at the door",
        "WHY :: one place to secure, evaluate and improve tools for all clients",
    ),
    S(
        "Tools available today",
        "Small, purposeful tool set",
        "API discovery :: search APIs, list APIs",
        "Live data :: call an API (read-only GET)",
        "Documents :: search policy / SOP documents",
        "Enterprise map :: search capabilities, explain capability, find providers, impact of change",
        "Engineering :: describe application, search code",
    ),
    S(
        "Live API calls",
        "Ground truth comes from real systems",
        "WHAT :: real web requests to Plaisse servicing APIs",
        "USE :: loan status, escrow, fees, schedules — current facts",
        "Safety :: only allow-listed hosts, only read (GET), time-limited",
        "WHY :: the model must never invent balances or statuses",
    ),
    S(
        "Credential broker",
        "Getting the right key for the right system",
        "WHAT :: component that fetches a machine-to-machine token per destination",
        "USE :: each live call gets a token tied to the system it is calling",
        "Today :: Auth0 machine login to Plaisse. Plaisse sees our bot, not the person",
        "WHY :: no shared master key; tokens bound to their destination",
    ),
    S(
        "Swappable providers",
        "A pattern behind every external dependency",
        "WHAT :: each external service (model, embeddings, vector DB, audit…) sits behind a standard plug",
        "USE :: switch local ↔ cloud vendors by configuration",
        "WHY :: no vendor lock-in in core logic; demo with zero cloud credentials",
        "Rule :: new external systems always enter through this same pattern",
    ),
    # ---------------- D
    SECTION("D", "Knowledge", "How the platform knows what exists and finds it fast"),
    S(
        "Two kinds of knowledge",
        "Facts and find-by-meaning",
        "Structured facts :: who owns what, what calls what — stored as graphs and registries",
        "Find-by-meaning :: match human wording to the right item — embeddings + vector search",
        "Prepared offline :: pipelines build knowledge in advance",
        "Used at ask-time :: tools fetch only the small slice a question needs",
    ),
    S(
        "EAKG — Enterprise Application Knowledge Graph",
        "The enterprise map",
        "WHAT :: a map of applications, their APIs, capabilities, and how they connect",
        "USE :: “what can this app do?”, “who provides X?”, “what breaks if this changes?”",
        "WHY :: turns tribal “which system?” knowledge into searchable memory",
        "BUILT FROM :: registered app repositories, API specs, enterprise app inventory",
        "Governance :: low-confidence links go to review; approved items can be published",
    ),
    S(
        "Embedding",
        "Meaning turned into numbers",
        "WHAT :: text converted into a list of numbers so similar meaning lands close together",
        "USE :: search by meaning when exact words do not match",
        "EXAMPLE :: “when is my next payment due?” ≈ the payment-schedule capability",
        "NOTE :: separate embedding sets for capabilities, APIs and documents",
    ),
    S(
        "Capability embeddings",
        "Meaning search over the enterprise map",
        "WHAT :: embeddings of each capability’s description from the EAKG",
        "USE :: rank the right capability for a plain-English question",
        "WHY :: people ask in English; systems are named for engineers",
        "Pairs with :: EAKG holds the facts; these vectors find them fast",
    ),
    S(
        "API search index (ApiIndex)",
        "The menu of callable operations",
        "WHAT :: searchable list of every callable API operation (meaning + keyword)",
        "USE :: find the exact operation to call before calling it",
        "Two-stage :: meaning match first, keyword check second, for accuracy",
        "WHY :: bridges human wording and exact operations across many apps",
    ),
    S(
        "Document embeddings",
        "Policy and SOP search",
        "WHAT :: embeddings of SOP / policy text chunks (from Confluence or a cached copy)",
        "USE :: find the passage that answers a policy question",
        "WHY :: some answers need written rules, not live data",
        "Citation :: answers point back to the exact policy source",
    ),
    S(
        "GraphRAG — document map",
        "How policies relate to each other",
        "WHAT :: groups of related policy documents (topics / communities)",
        "USE :: richer context when an answer spans several documents",
        "EXAMPLE :: escrow analysis + shortage + payment-change SOPs together",
        "WHY :: one chunk alone can miss the related rule",
    ),
    S(
        "Engineering map",
        "How an application’s code is wired",
        "WHAT :: map of an app’s classes, entry points and links back to its APIs",
        "USE :: “what does this app expose?”, “where is this implemented?”",
        "WHO :: mostly engineers; optional, not the main chat path",
        "WHY :: connect API behavior back to code for debugging and impact",
    ),
    S(
        "Graphify — the builders’ map",
        "Not part of answering business questions",
        "WHAT :: a code map of the LoanOps project itself",
        "USE :: helps the team and coding assistants work on LoanOps",
        "NOT USED :: when the tool room answers loan or policy questions",
        "WHY SEPARATE :: our own code ≠ enterprise applications",
    ),
    S(
        "Where knowledge is stored",
        "Three stores, three jobs",
        "Graph database :: relationships of the enterprise map (apps ↔ APIs ↔ capabilities)",
        "Operational database :: registries, operation lists, document maps, engineering maps",
        "Vector search :: embeddings for APIs, capabilities and documents",
        "WHY THREE :: relationships, records and meaning-search each need the right engine",
        "Product truth :: lives in these stores — not in files in a code repository",
    ),
    S(
        "Product mode vs test mode",
        "Same shapes, different homes",
        "Product :: graph DB + operational DB + vector search",
        "Test / offline :: a file mirror with the same layout",
        "WHY :: fast, repeatable tests without live databases",
        "Rule :: file mirror is never treated as product truth",
    ),
    # ---------------- E
    SECTION("E", "Pipelines", "How raw sources become knowledge the tools can use"),
    S(
        "Pipelines at a glance",
        "Source → transform → knowledge",
        "App code + API specs → enterprise map (EAKG)",
        "API specs → API search index",
        "Capability text → capability embeddings",
        "SOPs / Confluence → document embeddings (+ GraphRAG document map)",
        "App code structure → engineering map",
        "Golden test questions → quality scorecard",
    ),
    S(
        "Pipeline: Enterprise map sync",
        "Builds the EAKG",
        "SOURCE :: registered app repositories, API specs, enterprise app inventory",
        "OUTPUT :: map of apps, APIs, capabilities and cross-app links",
        "EXAMPLE :: “get payment schedules” → a capability owned by Loan Services",
        "WHY :: discovery and impact questions without reading code at ask-time",
    ),
    S(
        "Pipeline: API index refresh",
        "Builds the menu of callable operations",
        "SOURCE :: the app registry plus each app’s API specification",
        "OUTPUT :: searchable operations with meaning vectors",
        "EXAMPLE :: “Loan Services · get payment schedules · read-only · callable”",
        "WHY :: API specs are not fetched on every question — fast and stable",
    ),
    S(
        "Pipeline: SOP / policy ingest",
        "Builds document search",
        "SOURCE :: Confluence SOP pages (or a cached copy)",
        "OUTPUT :: document chunks with embeddings and source labels",
        "EXAMPLE :: escrow annual analysis page → searchable, citable chunks",
        "One writer :: batch ingest and on-demand re-index use the same path",
    ),
    S(
        "Pipeline: GraphRAG + capability embeddings",
        "Two enrichment steps",
        "GraphRAG :: groups related SOPs into topic communities",
        "Capability embeddings :: turns each capability description into a meaning vector",
        "USE :: richer policy context; better plain-English capability ranking",
        "WHY :: improves answers when keywords alone are not enough",
    ),
    S(
        "Pipeline: Inventory + engineering map",
        "Supporting knowledge",
        "App inventory refresh :: pulls the enterprise app list and URLs — never stored in code",
        "Engineering map build :: reads app code structure and links it to APIs",
        "USE :: complete app list; code-level answers for engineers",
        "WHY :: know every app exists without exposing secrets",
    ),
    S(
        "Pipeline: Evaluation gate",
        "The quality scorecard",
        "SOURCE :: golden questions with expected tools and citations",
        "OUTPUT :: pass / fail plus scores (citations, tool use, refusals, grounding)",
        "EXAMPLE :: “why did escrow rise?” must cite escrow policy and a live API call",
        "WHY :: catch regressions whenever prompts, tools or indexes change",
    ),
    S(
        "How pipelines are run",
        "Start a job, see if it finished, see if the data is fresh",
        "On demand :: start a job from the Eval Portal Pipelines screen, or from a command",
        "History :: each run is queued, running, done, or failed. A run stuck 30 minutes is marked failed",
        "Freshness :: after an API-index run, each app is fresh, stale, or unknown",
        "Cloud timer (designed) :: every night — map at 02:00, API menu at 02:30, policy docs at 03:00 UTC. Weekly map check Monday 06:00",
        "Ask-time :: no pipeline runs. The only live fetch is the business read itself",
    ),
    # ---------------- F
    SECTION("F", "Safety, security, quality", "Why the answers can be trusted"),
    S(
        "Privacy (personal data)",
        "Handled on the way in",
        "Detect :: personal data in each message is identified",
        "Audit-safe :: the stored copy has personal data tokenized",
        "Optional mode :: the AI model can see tokens instead of raw values",
        "Test data :: only synthetic data in fixtures — never real customer data",
    ),
    S(
        "Read-only, enforced in layers",
        "Defense in depth",
        "Tool policy :: only read tools are on the menu",
        "Tool room :: rejects anything that is not a read request",
        "Live call :: only GET to allow-listed hosts",
        "v1 promise :: no payments, plans, holds or data changes — at any layer",
    ),
    S(
        "Access and authentication",
        "Who is asking, and who Plaisse sees",
        "Today, in :: one shared password opens the tool room. One role applies to the whole process",
        "Today, out :: machine login. Plaisse sees our bot, not the person who asked",
        "Hint only :: a name sent with the call is not proof. Anyone with the shared password can type a name",
        "Target :: the person signs in with company login (OneLogin → Auth0). We check they have a LoanOps role",
        "Still the bot :: Plaisse keeps seeing our bot until we later choose to call as the person",
    ),
    S(
        "Citations and audit",
        "Every claim can be traced",
        "Citations :: policy:… for documents, tool:… for live data",
        "Rule :: factual answers without citations are not accepted",
        "Audit :: each turn records question (safe copy), tools used and answer",
        "USE :: compliance review, debugging, and quality sampling",
    ),
    S(
        "Quality bar",
        "Measured, not assumed",
        "Groundedness :: answers stick to retrieved sources (target ≥ 85%)",
        "Citation coverage :: 100% of non-refusal answers",
        "Refusal correctness :: ≥ 95% on out-of-scope prompts",
        "Speed / cost targets :: p95 ≤ 4 s · ≤ $0.04 per resolved query",
        "Rule :: thresholds are never lowered — the cause is fixed",
    ),
    # ---------------- G
    SECTION("G", "Status, roadmap, reference", "Where we are and where we can go"),
    S(
        "Business systems connected (dev)",
        "Plaisse applications in the enterprise map",
        "Escrow Manager :: live reads work in dev",
        "Fees :: live reads work in dev",
        "Loan Services :: live reads work in dev",
        "Core Components :: on the map. Live reads are paused — its dev address does not resolve",
        "More apps :: can join the same map over time",
    ),
    S(
        "Cloud home (designed)",
        "Written down. Daily work still runs on a developer machine",
        "Private :: company network or VPN only. No public front door",
        "Always on :: a chat service and the tool room, in one cluster",
        "Night jobs :: map, API menu, and policy docs, then the job stops. Weekly map check on Monday",
        "Data and model :: Aurora for records and search, Neptune for the map, Amazon Bedrock in the cloud",
        "Size :: dev uses one cheap task each. Prod uses two always-on tasks each",
    ),
    S(
        "Current status",
        "Working internal prototype",
        "Working :: tool room, Agent, live read-only calls, enterprise map, API index",
        "Working :: document search, quality gate, Pipelines screen (start, history, fresh or stale)",
        "Designed :: cloud home above. It is not the daily home yet",
        "Partial :: login is one shared password. Map-link review is still a command",
        "Paused :: Core Components live reads, until its address resolves",
    ),
    S(
        "Known gaps",
        "Honest list",
        "Login :: one shared password. We cannot yet prove which person or which app asked",
        "Core Components :: live reads stay off until its dev address resolves",
        "Review :: approving map links is still a command, not a screen",
        "Docs :: full policy coverage is still growing",
        "Cloud :: the design is written. People do not work there every day yet",
    ),
    S(
        "Roadmap",
        "Now → next → later",
        "Now :: prove the tool room with the IDE, Chat UI, quality gate, and visible pipeline runs",
        "Next :: person login · turn Core Components reads back on · more apps · a review screen",
        "Then :: cloud as the daily home · Chat UI as a real internal client · richer policy knowledge",
        "Later :: write actions only after explicit approval and a proven quality bar",
    ),
    S(
        "Decisions we recommend",
        "For tech lead and sponsors",
        "Endorse :: one tool room for IDE assistants and the Chat UI",
        "Endorse :: Chat UI as the evaluation harness, with a Pipelines screen to run and check jobs",
        "Endorse :: read-only, citations, and the quality gate for v1",
        "Prioritize :: person login, Core Components live reads, and the next apps",
        "Cloud :: build from the written design when we leave local-only",
    ),
    S(
        "Glossary cheat sheet (1/2)",
        None,
        "MCP :: standard door for AI clients to call tools",
        "Tool room :: our MCP server with its tools",
        "Agent :: service running one chat turn with safety",
        "LLM :: the AI model that reasons and writes",
        "EAKG :: enterprise map of apps, APIs, capabilities",
        "Embedding :: meaning as numbers, for similarity search",
    ),
    S(
        "Glossary cheat sheet (2/2)",
        None,
        "ApiIndex :: searchable menu of callable API operations",
        "GraphRAG :: map of related policy documents",
        "Engineering map :: how an app’s code is wired",
        "Graphify :: code map of LoanOps itself (builders only)",
        "Vector search :: engine that runs embedding search",
        "Citation :: tag linking a fact to its source",
    ),
    S(
        "FAQ",
        None,
        "Can it change loan data? :: No. Read-only at every layer in v1",
        "Does it make things up? :: Facts must come from tools or docs and be cited",
        "Can borrowers use it? :: No. Internal only",
        "Locked to one vendor? :: No. Models and stores swap by configuration",
        "Why not just use ChatGPT? :: it cannot see our systems safely or prove sources",
    ),
    S(
        "Thank you",
        "LoanOps — trusted internal answers from one tool room",
        "Questions and feedback welcome",
        f"Runtime picture (Lucid) :: {LUCID_URL}",
        f"Cloud picture (Lucid, ARC + Identity Auth) :: {LUCID_CLOUD}",
        "Live demo on request :: one loan + policy question end to end",
    ),
]


# Short room deck. Same facts as the complete guide, fewer slides.
BRIEFING: list[Slide] = [
    S(
        "LoanOps",
        "Internal AI platform for teams — find the right API or policy, call read-only data, answer with citations",
        "Briefing for tech leads and stakeholders · no code access needed",
        "Visual architecture: Lucid chart (link on the closing slide)",
    ),
    S(
        "What we need from you today",
        "Alignment — not a code review",
        "Confirm the problem is worth solving this way",
        "Confirm one shared tool room, with the Chat UI as the way we test it",
        "Confirm read-only answers, citations, and a quality bar we do not lower",
        "Align on next work: person login, Core Components live reads, more apps",
    ),
    S(
        "Agenda",
        None,
        "1. Problem and outcome",
        "2. What LoanOps is, and what it is not",
        "3. How people use it — IDE, Chat UI, Pipelines screen",
        "4. Building blocks — what each does and why it exists",
        "5. How knowledge is prepared",
        "6. Connected systems, login, cloud design, roadmap",
    ),
    S(
        "The problem",
        "Answers are slow, scattered, and hard to audit",
        "People jump across APIs, wikis, repos, and screens for one fact",
        "“Which system owns this?” lives in a few people’s heads",
        "Assistants that guess create compliance and trust risk",
        "We need one trusted tool room many clients can share",
    ),
    S(
        "The outcome we want",
        "Ask in plain English. Get a grounded, cited draft for a human to check",
        "Discover the right capability or API operation",
        "Search policy when the question needs written rules",
        "Call live loan-servicing APIs — read only",
        "Return an answer with clear citations",
        "Leave an audit trail of what was used",
    ),
    S(
        "What LoanOps is",
        "An internal platform — one tool room over enterprise APIs and documents",
        "MCP is the standard door AI clients use to call our tools",
        "Same tools for IDE assistants (for example Cursor) and our Chat UI",
        "Any internal role — engineers, analysts, PMs, ops",
        "Same product shape locally or in the cloud, by configuration",
    ),
    S(
        "What LoanOps is not",
        "Boundaries are part of the design",
        "No public borrower chat, voice, or email channel",
        "Cannot post payments, start plans, place holds, or change data (v1)",
        "No legal, tax, or rate-quote advice",
        "The Chat UI tests the tool room. It is not the finished client yet",
    ),
    S(
        "Why the Chat UI exists",
        "So we can test the tool room the way a real chat client would",
        "IDE use proves each tool and the protocol",
        "Chat UI proves tool choice, multi-step answers, citations, and refusals",
        "It adds memory, privacy checks, outbound safety, and an audit per turn",
        "The same website has an Eval Portal: quality checks and a Pipelines screen",
        "Once quality clears the bar, this UI can become a real internal client",
    ),
    S(
        "How people use it today",
        "Two clients now. One tool room",
        "Engineers in the IDE talk straight to the tool room",
        "Chat UI goes through our Agent, then the same tool room",
        "Pipelines screen starts a knowledge job and shows if it finished",
        "Later the wiki and other agents join this room and name the person and the app",
    ),
    S(
        "North star",
        "One picture to remember",
        "You ask in the Chat UI or the IDE",
        "The tool room checks the door, then allows a read-only call",
        "The brain finds an API, searches docs, calls live data, and cites sources",
        "Systems are Plaisse servicing APIs plus our knowledge stores",
        "Login today: one shared password in. Machine login out. Plaisse sees our bot",
    ),
    S(
        "One answer, step by step",
        "What happens when someone asks",
        "1. Privacy check on the message, then load earlier turns",
        "2. Fast gate: refuse risky or out-of-scope asks before the model runs",
        "3. The model may search and call a read-only API, up to a few rounds",
        "4. The answer must include citations. The shape is checked",
        "5. Outbound safety and an audit log, then the person sees the draft",
    ),
    S(
        "Tool room (MCP)",
        "Why we built it",
        "One place to expose tools, shared by every client",
        "One place for login, role limits, and read-only rules",
        "Test quality once. The IDE and the Chat UI both benefit",
        "Future clients plug into the same door",
    ),
    S(
        "Agent (chat path)",
        "Why we built it",
        "Chat needs memory, safety, and a structured answer — raw tools are not enough",
        "Turns a vague question into search, then call, then cite",
        "Lets us judge the tool room under realistic pressure",
        "Drafts for a person to review. No silent actions",
    ),
    S(
        "Live API calls",
        "Why we built them",
        "Loan facts come from real systems, not from model memory",
        "Find the right operation, then call it read-only",
        "Machine login to Plaisse. Only allow-listed hosts",
        "Plaisse sees our bot, not the person who asked",
        "Each data claim can be tagged as a tool call",
    ),
    S(
        "Enterprise map (EAKG)",
        "Why we built it",
        "Turns “which app can do this?” into searchable knowledge",
        "Built from registered app repos, API specs, and the enterprise app list",
        "Answers provider and impact questions across apps",
        "We do not re-read whole codebases on every question",
    ),
    S(
        "API search index",
        "Why we built it",
        "People ask in English. APIs are named for engineers",
        "Meaning search, then a keyword check, finds the operation to call",
        "Fed from the same registry and API specs as the enterprise map",
        "The bridge between a sentence and the exact read-only call",
    ),
    S(
        "Policy and document knowledge",
        "Why we built it",
        "Some answers need a written rule, not only live data",
        "Document search returns a passage the answer can cite",
        "Related policies can be grouped so one page is not the whole story",
        "Separates “what policy says” from “what the system returned just now”",
    ),
    S(
        "Engineering map (optional)",
        "Why we built it",
        "Helps engineers ask what an app exposes and where it is wired",
        "Built from application structure. Not the main path for every chat user",
        "Keeps “what can this app do?” separate from “where is the code?”",
    ),
    S(
        "Safety and quality",
        "Why we built them",
        "Privacy check on the way in. Content safety on the way out",
        "Audit record of the question, the tools used, and the answer",
        "Golden tests for grounding, citations, and correct refusals",
        "We fix the cause. We do not lower the quality bar to go green",
    ),
    S(
        "Swappable providers",
        "Why we use this pattern",
        "The model, embeddings, vector search, and audit can change without a rewrite",
        "Develop locally. Move to the enterprise cloud by configuration",
        "Vendor lock-in stays at the edge. Core logic stays ours",
    ),
    S(
        "How knowledge is prepared",
        "Batch jobs, so the AI does not read raw repos on every question",
        "App code and API specs become the enterprise map",
        "API specs become the searchable operation menu",
        "Policy pages become document search",
        "You can start a job from the Pipelines screen and see if it finished",
        "Freshness tells you if an app’s API spec is fresh, stale, or unknown",
        "Cloud design runs these at night. Ask-time only does the live business read",
    ),
    S(
        "Where knowledge lives",
        "Three stores, three jobs",
        "Graph database — links among apps, APIs, and capabilities",
        "Operational database — registries, operation lists, document maps",
        "Vector search — find the right API or policy passage by meaning",
        "Product truth lives in these stores, not in files in a code repo",
    ),
    S(
        "Words you will hear",
        "One line each. The long guide has a slide per word",
        "EAKG :: the enterprise map of apps, APIs, and capabilities",
        "Embedding :: meaning turned into numbers, so similar wording lands close",
        "ApiIndex :: the menu of callable API operations",
        "GraphRAG :: how policy documents relate to each other",
        "Graphify :: a map of this LoanOps repo for builders. Not used to answer a loan question",
    ),
    S(
        "Login today and the target",
        "Two different questions: who asked us, and who Plaisse sees",
        "Today, in: one shared password. One role for the whole process",
        "Today, out: machine login. Plaisse sees our bot",
        "A name sent with the call is a hint. It is not proof of who asked",
        "Target: the person signs in with company login. We check they have a LoanOps role",
        "Even then, Plaisse sees our bot until we choose to call as the person",
    ),
    S(
        "Cloud home (designed)",
        "Written down. Daily work still runs on a developer machine",
        "Company network or VPN only. No public front door",
        "Chat service and tool room stay on, in one cluster",
        "Night jobs: map at 02:00, API menu at 02:30, policy docs at 03:00 UTC. Weekly map check Monday 06:00",
        "Aurora for records and search. Neptune for the map. Amazon Bedrock for the model",
        "Dev uses one cheap task. Prod uses two always-on tasks",
    ),
    S(
        "Business systems in dev",
        "Plaisse apps in the enterprise map",
        "Escrow Manager, Fees, and Loan Services — live reads work in dev",
        "Core Components is on the map. Live reads are paused — its dev address does not resolve",
        "More apps can join the same map over time",
    ),
    S(
        "Guardrails we keep for v1",
        None,
        "Read-only. No payments, plans, holds, or data changes",
        "Every factual answer needs a citation",
        "Internal only. No borrower channel. No rate quotes or licensed advice",
        "Quality bar stays. We fix the cause instead of relaxing the gate",
        "A person reviews the draft before it is used",
    ),
    S(
        "Where we are",
        "Working prototype, with a written cloud home",
        "Now: IDE and Chat UI share one tool room. Pipeline runs are visible",
        "Live reads: three apps. Core Components is paused",
        "Next: person login, turn Core Components back on, more apps, a review screen",
        "Then: cloud as the daily home, and the Chat UI as a real internal client",
        "Later: write actions only after explicit approval and a proven quality bar",
    ),
    S(
        "Decisions we recommend",
        "For the tech lead and sponsors",
        "Endorse one tool room for the IDE and the Chat UI",
        "Endorse the Chat UI as the test client, with a Pipelines screen",
        "Endorse read-only answers, citations, and the quality gate for v1",
        "Prioritize person login, Core Components live reads, and the next apps",
        "Build the cloud home from the written design when we leave local-only",
    ),
    S(
        "Thank you",
        "LoanOps — trusted internal answers from one tool room",
        "Questions and feedback welcome",
        f"Runtime picture (Lucid) :: {LUCID_URL}",
        f"Cloud picture (Lucid, ARC + Identity Auth) :: {LUCID_CLOUD}",
        "Live demo on request: one loan and one policy question, end to end",
    ),
]


# ---------------------------------------------------------------- PPTX


def _rgb(hex_: str) -> RGBColor:
    return RGBColor.from_string(hex_)


def _split(bullet: str) -> tuple[str | None, str]:
    if " :: " in bullet:
        label, text = bullet.split(" :: ", 1)
        return label, text
    return None, bullet


def _rect(slide, x, y, w, h, color: str, shape=MSO_SHAPE.RECTANGLE):  # type: ignore[no-untyped-def]
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = _rgb(color)
    s.line.fill.background()
    return s


def _text(slide, x, y, w, h, parts, size, align=PP_ALIGN.LEFT):  # type: ignore[no-untyped-def]
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    for text, bold, color in parts:
        r = p.add_run()
        r.text = text
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.name = "Calibri"
        r.font.color.rgb = _rgb(color)
    return box


def _lines(text: str, chars_per_line: int) -> int:
    return max(1, math.ceil(len(text) / chars_per_line))


def build_pptx(path: Path, slides: list[Slide], footer: str) -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    total = len(slides)

    for i, sl in enumerate(slides, start=1):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        is_cover = i == 1 or i == total
        _rect(slide, 0, 0, 13.333, 7.5, NAVY if (is_cover or sl.section) else CARD)
        _rect(slide, 0, 0, 0.14, 7.5, TEAL)

        if sl.section:
            _text(slide, 0.9, 2.0, 3, 1.4, [(sl.section, True, TEAL)], 96)
            _text(slide, 0.9, 3.6, 11.5, 0.9, [(sl.title, True, CREAM)], 40)
            _text(slide, 0.9, 4.5, 11.5, 0.6, [(sl.subtitle or "", False, MUTED)], 20)
        elif is_cover:
            _text(slide, 0.9, 1.9, 11.5, 1.2, [(sl.title, True, CREAM)], 44)
            _text(slide, 0.9, 3.1, 11.5, 1.0, [(sl.subtitle or "", False, TEAL)], 20)
            y = 4.5
            for b in sl.bullets:
                label, txt = _split(b)
                parts = [(f"{label}: ", True, AMBER)] if label else []
                parts.append((txt, False, CREAM))
                _text(slide, 0.9, y, 11.8, 0.5, parts, 15)
                y += 0.5
        else:
            _text(slide, 0.6, 0.3, 12.2, 0.7, [(sl.title, True, CREAM)], 28)
            y = 1.05
            if sl.subtitle:
                _text(slide, 0.6, y, 12.2, 0.45, [(sl.subtitle, False, TEAL)], 15)
            y = 1.65
            for b in sl.bullets:
                label, txt = _split(b)
                n = _lines((label or "") + txt, 118)
                h = 0.22 + 0.27 * n
                _rect(slide, 0.6, y, 12.1, h, NAVY, MSO_SHAPE.ROUNDED_RECTANGLE).adjustments[0] = 0.12
                parts = [(f"{label}  ", True, AMBER)] if label else []
                parts.append((txt, False, CREAM))
                _text(slide, 0.8, y + 0.04, 11.7, h, parts, 14)
                y += h + 0.12

        _text(
            slide, 0.5, 7.05, 12.3, 0.3,
            [(f"{footer}  ·  Internal  ·  {i}/{total}", False, MUTED)],
            10, PP_ALIGN.RIGHT,
        )

    prs.save(path)


# ---------------------------------------------------------------- PDF


def _wrap(c: pdf_canvas.Canvas, text: str, font: str, size: float, width: float) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if c.stringWidth(trial, font, size) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def build_pdf(path: Path, slides: list[Slide], footer: str, doc_title: str) -> None:
    W, H = landscape(letter)
    c = pdf_canvas.Canvas(str(path), pagesize=(W, H))
    c.setTitle(doc_title)
    total = len(slides)
    col = {k: HexColor(f"#{v}") for k, v in dict(NAVY=NAVY, CARD=CARD, TEAL=TEAL, CREAM=CREAM, MUTED=MUTED, AMBER=AMBER).items()}

    for i, sl in enumerate(slides, start=1):
        is_cover = i == 1 or i == total
        c.setFillColor(col["NAVY"] if (is_cover or sl.section) else col["CARD"])
        c.rect(0, 0, W, H, fill=1, stroke=0)
        c.setFillColor(col["TEAL"])
        c.rect(0, 0, 8, H, fill=1, stroke=0)
        left = 0.65 * inch
        width = W - 2 * left

        if sl.section:
            c.setFillColor(col["TEAL"]); c.setFont("Helvetica-Bold", 80)
            c.drawString(left, H - 3.0 * inch, sl.section)
            c.setFillColor(col["CREAM"]); c.setFont("Helvetica-Bold", 34)
            c.drawString(left, H - 3.8 * inch, sl.title)
            c.setFillColor(col["MUTED"]); c.setFont("Helvetica", 16)
            c.drawString(left, H - 4.3 * inch, sl.subtitle or "")
        else:
            y = H - (1.6 if is_cover else 0.75) * inch
            c.setFillColor(col["CREAM"]); c.setFont("Helvetica-Bold", 34 if is_cover else 24)
            for ln in _wrap(c, sl.title, "Helvetica-Bold", 34 if is_cover else 24, width):
                c.drawString(left, y, ln); y -= 0.45 * inch
            if sl.subtitle:
                c.setFillColor(col["TEAL"]); c.setFont("Helvetica", 14 if is_cover else 12)
                for ln in _wrap(c, sl.subtitle, "Helvetica", 14 if is_cover else 12, width):
                    c.drawString(left, y, ln); y -= 0.25 * inch
            y -= 0.2 * inch
            size, lead = 12, 16
            for b in sl.bullets:
                label, txt = _split(b)
                prefix = f"{label}:  " if label else ""
                lines = _wrap(c, prefix + txt, "Helvetica", size, width - 28)
                box_h = len(lines) * lead + 16
                c.setFillColor(col["NAVY"])
                c.roundRect(left, y - box_h + lead, width, box_h, 6, fill=1, stroke=0)
                ty = y
                for n, ln in enumerate(lines):
                    x = left + 14
                    if n == 0 and label and ln.startswith(prefix):
                        c.setFillColor(col["AMBER"]); c.setFont("Helvetica-Bold", size)
                        c.drawString(x, ty, prefix)
                        x += c.stringWidth(prefix, "Helvetica-Bold", size)
                        ln = ln[len(prefix):]
                    c.setFillColor(col["CREAM"]); c.setFont("Helvetica", size)
                    c.drawString(x, ty, ln)
                    ty -= lead
                y -= box_h + 8

        c.setFillColor(col["MUTED"]); c.setFont("Helvetica", 8)
        c.drawRightString(W - 0.5 * inch, 0.35 * inch, f"{footer}  ·  Internal  ·  {i}/{total}")
        c.showPage()
    c.save()


def main() -> None:
    decks = (
        (SLIDES, NAME, "LoanOps Complete Guide", "LoanOps — Complete Guide"),
        (BRIEFING, "LoanOps-Stakeholder-Briefing-v2", "LoanOps Agent", "LoanOps — Stakeholder Briefing"),
    )
    for slides, name, footer, title in decks:
        pptx_path, pdf_path = OUT / f"{name}.pptx", OUT / f"{name}.pdf"
        build_pptx(pptx_path, slides, footer)
        build_pdf(pdf_path, slides, footer, title)
        print(f"{name}: {len(slides)} slides")
        print(f"Wrote {pptx_path}")
        print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
