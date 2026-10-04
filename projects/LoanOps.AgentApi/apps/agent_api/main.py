"""Servicing Agent API — FastAPI on :8000.

Endpoints:
    POST /chat   — streaming SSE; runs a single agent turn
    GET  /health — aggregated provider health (503 on failure)
    GET  /version — API version
    GET  /chat/memory/{session_id} — get chat memory with active/inactive status
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from apps.agent_api.mcp_routes import router as mcp_router
from apps.agent_api.models import (
    AuditRecord,
    ChatMemoryResponse,
    ChatRequest,
    HealthResponse,
    MemoryMessage,
    ProviderHealthStatus,
)
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from packages.agent_core import run_agent_turn
from packages.agent_core._memory import (
    build_history_messages,
    estimate_tokens,
    export_memory_markdown,
)
from packages.common.providers import AuditEvent, ConversationTurn, LLMMessage
from packages.common.providers.factory import (
    get_audit_sink_provider,
    get_chat_provider,
    get_content_safety_provider,
    get_embedding_provider,
    get_pii_provider,
    get_prompt_store_provider,
    get_secrets_provider,
    get_session_store_provider,
    get_telemetry_provider,
    get_vector_store_provider,
)
from packages.common.settings import Settings
from packages.safety.middleware import evaluate_outbound, sanitize_inbound
from packages.tools.factory import get_tools_client_provider


def _agent_owns_vector_store() -> bool:
    """False when Qdrant runs in embedded path mode — Tools API owns the lock."""
    path = Settings().vector_store.qdrant.path
    return not (Settings().vector_store.provider == "qdrant" and path)

# ---------------------------------------------------------------------------
# Version — read once at import time
# ---------------------------------------------------------------------------
_VERSION = "0.1.0"
try:
    import tomllib

    with open("pyproject.toml", "rb") as _f:
        _pyproject = tomllib.load(_f)
        _VERSION = _pyproject.get("project", {}).get("version", _VERSION)
except Exception:  # noqa: BLE001
    pass  # Fall back to hardcoded default


# ---------------------------------------------------------------------------
# Provider registry — maps name → factory callable
# ---------------------------------------------------------------------------
_PROVIDER_FACTORIES: list[tuple[str, Any]] = [
    ("chat", get_chat_provider),
    ("embedding", get_embedding_provider),
    ("pii", get_pii_provider),
    ("content_safety", get_content_safety_provider),
    ("audit_sink", get_audit_sink_provider),
    ("secrets", get_secrets_provider),
    ("telemetry", get_telemetry_provider),
    ("tools_client", get_tools_client_provider),
    ("prompt_store", get_prompt_store_provider),
    ("session_store", get_session_store_provider),
]
# Embedded Qdrant (path=) allows one process only — Tools API owns RAG.
if _agent_owns_vector_store():
    _PROVIDER_FACTORIES.insert(2, ("vector_store", get_vector_store_provider))


# ---------------------------------------------------------------------------
# Lifespan — flush audit sink on shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Application lifespan: warm up providers on startup, flush audit sink on shutdown.

    All factory functions are decorated with ``@lru_cache``, so calling them here
    pays the cold-start cost once at boot (Presidio/spaCy model loading, HTTP
    client construction, etc.) rather than on the first user request.
    """
    # Warm up every provider so the first /chat request isn't slow.
    for _name, factory in _PROVIDER_FACTORIES:
        import contextlib

        with contextlib.suppress(Exception):
            factory()  # Individual provider failures surface in /health; don't abort boot.

    yield

    # Flush audit sink on graceful shutdown.
    try:
        audit = get_audit_sink_provider()
        await audit.flush()
    except Exception:  # noqa: BLE001
        pass  # Best-effort flush; don't crash on shutdown


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="LoanOps Agent API",
    description=(
        "Internal AI platform API for enterprise users (any role). "
        "Provides streaming chat, health aggregation, and audit logging."
    ),
    version=_VERSION,
    lifespan=lifespan,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mcp_router)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse | Any:
    """Aggregate health of all 10 providers; 503 on any failure."""
    results: dict[str, ProviderHealthStatus] = {}
    all_ok = True

    for name, factory in _PROVIDER_FACTORIES:
        t0 = time.perf_counter()
        try:
            factory()
            elapsed = (time.perf_counter() - t0) * 1000
            results[name] = ProviderHealthStatus(
                ok=True,
                latency_ms=round(elapsed, 2),
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = (time.perf_counter() - t0) * 1000
            results[name] = ProviderHealthStatus(
                ok=False,
                latency_ms=round(elapsed, 2),
                detail=str(exc),
            )
            all_ok = False

    resp = HealthResponse(
        status="healthy" if all_ok else "unhealthy",
        providers=results,
    )

    if not all_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=resp.model_dump(),
        )

    return resp


# ---------------------------------------------------------------------------
# GET /version
# ---------------------------------------------------------------------------
@app.get("/version")
async def version() -> dict[str, str]:
    """Return the current API version."""
    return {"version": _VERSION}


# ---------------------------------------------------------------------------
# POST /chat (SSE)
# ---------------------------------------------------------------------------
@app.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Handle a chat turn and stream the result as SSE.

    The agent output is computed as a single turn (not token-level streaming)
    and wrapped in one SSE ``data:`` event.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        turn_id = str(uuid.uuid4())
        t0 = time.perf_counter()

        try:
            # 1. Obtain providers via factories (no concrete imports)
            chat_provider = get_chat_provider()
            # LAYER2-BP A1: /chat entry — inspect type(tools_client)
            tools_client = get_tools_client_provider()
            prompt_store = get_prompt_store_provider()
            audit_sink = get_audit_sink_provider()
            pii_provider = get_pii_provider()
            safety_provider = get_content_safety_provider()

            # 1.5 PII handling — mode controlled by PII__MODE env var
            from packages.common.settings import Settings

            pii_mode = Settings().pii.mode

            sanitize_result = await sanitize_inbound(request.message, pii_provider, audit_sink)
            pii_token_map: dict[str, str] = {}

            if pii_mode == "tokenize":
                # Tokenize mode: LLM sees [PERSON_1] tokens, tools detokenize server-side
                agent_prompt = sanitize_result.anonymized_text
                pii_token_map = sanitize_result.token_map
            else:
                # Redact-audit-only mode: LLM sees real PII, audit stores redacted copy
                agent_prompt = request.message

            # 1.8 Handle memory if session_id is provided
            session_store = get_session_store_provider()
            history: list[LLMMessage] | None = None

            if request.session_id:
                session = await session_store.get_session(request.session_id)
                if session is None:
                    session = await session_store.create_session(
                        session_id=request.session_id,
                        rep_id=request.rep_id,
                        loan_id=request.loan_id,
                    )
                history = build_history_messages(
                    session, agent_prompt, max_tokens=request.max_history_tokens
                )

            # 2. Run agent turn with configured prompt mode; tools detokenize server-side
            output = await run_agent_turn(
                prompt=agent_prompt,
                chat_provider=chat_provider,
                tools_client=tools_client,
                prompt_store=prompt_store,
                history=history,
                pii_token_map=pii_token_map,
            )

            # 2.1 Detokenize the final answer for the rep (they already know the names)
            if pii_token_map:
                from packages.safety.tokenizer import PiiTokenizer

                output.answer = PiiTokenizer.detokenize(output.answer, pii_token_map)

            # 2.2 Record turns to session store
            if request.session_id:
                now = datetime.now(UTC)
                await session_store.append_turn(
                    request.session_id,
                    ConversationTurn(
                        role="user",
                        content=agent_prompt,
                        timestamp=now,
                        turn_id=f"{turn_id}-user",
                    ),
                )
                await session_store.append_turn(
                    request.session_id,
                    ConversationTurn(
                        role="assistant",
                        content=output.answer,
                        timestamp=now,
                        turn_id=f"{turn_id}-assistant",
                    ),
                )

                # Dump structured memory to audit/memory.md for local inspection
                session_for_dump = await session_store.get_session(request.session_id)
                if session_for_dump:
                    import os

                    from packages.agent_core._memory import export_memory_markdown

                    os.makedirs("audit", exist_ok=True)
                    with open("audit/memory.md", "w", encoding="utf-8") as f:
                        f.write(export_memory_markdown(session_for_dump))

            # 2.5 Evaluate outbound safety
            eval_result = await evaluate_outbound(output.answer, safety_provider, audit_sink)

            if not eval_result.is_safe:
                output.answer = ""
                output.refusal = f"Blocked by safety policy: {eval_result.reason}"
                output.confidence = 0.0

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            output_dict = output.model_dump()

            # 3. Build audit record (always uses redacted prompt — no real PII)
            audit_payload = AuditRecord(
                turn_id=turn_id,
                rep_id=request.rep_id,
                session_id=request.session_id,
                prompt_redacted=sanitize_result.anonymized_text,
                retrieved_chunk_ids=[
                    c.source for c in output.citations if c.source.startswith("policy:")
                ],
                tool_calls=[tc.model_dump() for tc in output.tool_calls],
                raw_model_output=output.answer,
                final_output=output_dict,
                latency_ms=latency_ms,
                cost_usd=0.0,
                providers_bound=_get_bound_providers(),
            )

            # 4. Emit audit event
            audit_event = AuditEvent(
                event_id=turn_id,
                event_type="agent_api.chat.turn",
                user_id=request.rep_id,
                session_id=request.session_id,
                payload=audit_payload.model_dump(),
            )
            await audit_sink.emit(audit_event)

            # 5. Yield result as SSE
            yield f"data: {json.dumps(output_dict)}\n\n"

        except Exception as exc:  # noqa: BLE001
            error_payload = {"error": str(exc), "turn_id": turn_id}
            yield f"data: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _get_bound_providers() -> dict[str, str]:
    """Snapshot which concrete provider is bound for each category.

    Returns a dict like {"chat": "OllamaProvider", "embedding": "SentenceTransformer..."}.
    Best-effort: swallows errors for providers that failed to instantiate.
    """
    bound: dict[str, str] = {}
    for name, factory in _PROVIDER_FACTORIES:
        try:
            provider = factory()
            bound[name] = type(provider).__name__
        except Exception:  # noqa: BLE001
            bound[name] = "unavailable"
    return bound


# ---------------------------------------------------------------------------
# GET /chat/memory/{session_id}
# ---------------------------------------------------------------------------
@app.get("/chat/memory/{session_id}", response_model=ChatMemoryResponse)
async def get_chat_memory(session_id: str, max_history_tokens: int = 2048) -> ChatMemoryResponse:
    """Retrieve the chat memory for a given session, showing which turns are active/inactive."""

    # Obtain session store provider
    session_store = get_session_store_provider()

    # Retrieve the session
    session = await session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found or expired.",
        )

    # Calculate the current prompt tokens (using an empty prompt as baseline)
    current_prompt_tokens = estimate_tokens("")

    # Calculate available budget
    available_budget = max(0, max_history_tokens - current_prompt_tokens)

    # Build active history messages (same logic as build_history_messages but with tracking)
    retained_turns: list[ConversationTurn] = []
    all_turns_with_status: list[tuple[ConversationTurn, bool]] = []  # (turn, is_active)

    # Process turns newest to oldest
    for turn in reversed(session.turns):
        turn_tokens = estimate_tokens(turn.content)

        if available_budget - turn_tokens < 0:
            is_active = False
            # Special case: keep turns that mention the session's loan_id even if over budget
            if session.loan_id and session.loan_id in turn.content:
                retained_turns.append(turn)
                is_active = True
            available_budget = 0
        else:
            is_active = True
            retained_turns.append(turn)
            available_budget -= turn_tokens

        all_turns_with_status.append((turn, is_active))

    # Put them back in chronological order
    all_turns_with_status.reverse()

    # Convert to MemoryMessage objects
    memory_messages = [
        MemoryMessage(
            role=turn.role,
            content=turn.content,
            is_active=is_active,
            token_count=estimate_tokens(turn.content),
        )
        for turn, is_active in all_turns_with_status
    ]

    # Count active messages
    active_count = sum(1 for msg in memory_messages if msg.is_active)

    # Build response
    response = ChatMemoryResponse(
        session_id=session_id,
        total_messages=len(memory_messages),
        active_messages=active_count,
        max_history_tokens=max_history_tokens,
        current_prompt_tokens=current_prompt_tokens,
        messages=memory_messages,
        markdown=export_memory_markdown(session),
    )

    return response
