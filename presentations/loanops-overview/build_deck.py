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
        "Fallback :: Chat UI can call tools directly for demos if the tool room is down",
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
        "Today :: Auth0 machine credentials to Plaisse",
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
        "How often pipelines run",
        "Today vs later",
        "Today :: run on demand when sources change",
        "Later :: scheduled (e.g. nightly) once stable",
        "Ask-time :: no pipeline runs — tools read prepared knowledge only",
        "Live data :: the only thing fetched at ask-time is the business API call itself",
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
        "Today and next",
        "Into the tool room :: access token required; empty token is rejected",
        "Roles :: each role sees only its allowed tools",
        "Out to Plaisse :: machine credentials per destination",
        "Next :: per-user identity passed through, and permission checks at each call",
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
        "Core Components",
        "Escrow Manager",
        "Fees",
        "Loan Services",
        "More apps :: can be onboarded into the same map over time",
    ),
    S(
        "Current status",
        "Working internal prototype",
        "Working :: tool room, Agent, live read-only calls, enterprise map, API index",
        "Working :: engineering map, document search path, evaluation gate",
        "In progress :: Chat UI as evaluation harness",
        "Partial :: per-user auth, human review screen for the enterprise map",
        "Not yet :: production cloud deployment as the daily home",
    ),
    S(
        "Known gaps",
        "Honest list",
        "Auth :: shared tool-room token today; per-user identity still to come",
        "Governance :: review of map links is command-line, no review screen yet",
        "Coverage :: four applications connected; more to onboard",
        "Docs :: full Confluence policy coverage still growing",
    ),
    S(
        "Roadmap",
        "Now → next → later",
        "Now :: prove the tool room with IDE + Chat UI + evaluation gate",
        "Next :: onboard more apps · per-user auth · review screen",
        "Then :: Chat UI as a real internal client · richer policy knowledge · cloud deploy",
        "Later (optional) :: write actions only after explicit policy approval + proven quality",
    ),
    S(
        "Decisions we recommend",
        "For tech lead and sponsors",
        "Endorse :: MCP-first — one tool room for IDE assistants and Chat UI",
        "Endorse :: Chat UI as the evaluation harness for that room",
        "Endorse :: read-only + citations + quality gate for v1",
        "Prioritize :: next apps to onboard and auth hardening",
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
        f"Architecture visuals (Lucid) :: {LUCID_URL}",
        "Live demo on request :: one loan + policy question end to end",
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


def build_pptx(path: Path) -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    total = len(SLIDES)

    for i, sl in enumerate(SLIDES, start=1):
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
            [(f"LoanOps Complete Guide  ·  Internal  ·  {i}/{total}", False, MUTED)],
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


def build_pdf(path: Path) -> None:
    W, H = landscape(letter)
    c = pdf_canvas.Canvas(str(path), pagesize=(W, H))
    c.setTitle("LoanOps — Complete Guide")
    total = len(SLIDES)
    col = {k: HexColor(f"#{v}") for k, v in dict(NAVY=NAVY, CARD=CARD, TEAL=TEAL, CREAM=CREAM, MUTED=MUTED, AMBER=AMBER).items()}

    for i, sl in enumerate(SLIDES, start=1):
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
        c.drawRightString(W - 0.5 * inch, 0.35 * inch, f"LoanOps Complete Guide  ·  Internal  ·  {i}/{total}")
        c.showPage()
    c.save()


def main() -> None:
    pptx_path, pdf_path = OUT / f"{NAME}.pptx", OUT / f"{NAME}.pdf"
    build_pptx(pptx_path)
    build_pdf(pdf_path)
    print(f"{len(SLIDES)} slides")
    print(f"Wrote {pptx_path}")
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
