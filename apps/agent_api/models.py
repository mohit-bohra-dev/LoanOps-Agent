"""Request and response models for the Agent API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Inbound chat request from a care rep."""

    message: str
    session_id: str | None = None
    rep_id: str | None = None
    loan_id: str | None = None
    max_history_tokens: int = 2048


class ProviderHealthStatus(BaseModel):
    """Health status of a single provider."""

    ok: bool
    latency_ms: float = 0.0
    detail: str = ""


class HealthResponse(BaseModel):
    """Aggregated health response for all providers."""

    status: str  # "healthy" | "unhealthy"
    providers: dict[str, ProviderHealthStatus]


class AuditRecord(BaseModel):
    """Audit payload stored per agent turn.

    Matches the spec: turn_id, rep_id, prompt_redacted,
    retrieved_chunk_ids, tool_calls, raw_model_output,
    final_output, latency_ms, cost_usd, providers_bound.
    """

    turn_id: str
    rep_id: str | None = None
    session_id: str | None = None
    prompt_redacted: str = ""
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    raw_model_output: str = ""
    final_output: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    providers_bound: dict[str, str] = Field(default_factory=dict)


class MemoryMessage(BaseModel):
    """Simplified representation of a conversation message for memory display."""

    role: str
    content: str
    is_active: bool = True
    token_count: int = 0


class ChatMemoryResponse(BaseModel):
    """Response model for the chat memory endpoint."""

    session_id: str
    total_messages: int
    active_messages: int
    max_history_tokens: int
    current_prompt_tokens: int
    markdown: str
    messages: list[MemoryMessage]
