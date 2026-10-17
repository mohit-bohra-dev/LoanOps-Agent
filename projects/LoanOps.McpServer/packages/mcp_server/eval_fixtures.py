"""In-code MCP fixture cases for Bedrock-free eval (no JSONL on disk)."""

from __future__ import annotations

from typing import Literal, TypedDict


class McpEvalCase(TypedDict):
    id: str
    tool: str
    arguments: dict[str, object]
    authorization: str | None
    expect: Literal["ok", "denied", "policy"]


# Auth + policy + happy-path cases. FakeClient used at runtime for "ok".
MCP_EVAL_CASES: tuple[McpEvalCase, ...] = (
    {
        "id": "missing_bearer",
        "tool": "search_docs",
        "arguments": {"query": "escrow"},
        "authorization": None,
        "expect": "denied",
    },
    {
        "id": "wrong_bearer",
        "tool": "search_docs",
        "arguments": {"query": "escrow"},
        "authorization": "Bearer wrong",
        "expect": "denied",
    },
    {
        "id": "post_rejected",
        "tool": "call_sse_api",
        "arguments": {"method": "POST", "path": "/api/Loans/1"},
        "authorization": "Bearer secret-token",
        "expect": "policy",
    },
    {
        "id": "body_rejected",
        "tool": "call_sse_api",
        "arguments": {"operation_id": "getLoanSummary", "body": {"amount": 1}},
        "authorization": "Bearer secret-token",
        "expect": "policy",
    },
    {
        "id": "search_docs_ok",
        "tool": "search_docs",
        "arguments": {"query": "escrow"},
        "authorization": "Bearer secret-token",
        "expect": "ok",
    },
    {
        "id": "search_sse_apis_ok",
        "tool": "search_sse_apis",
        "arguments": {"query": "loan"},
        "authorization": "Bearer secret-token",
        "expect": "ok",
    },
    {
        "id": "call_sse_api_get_ok",
        "tool": "call_sse_api",
        "arguments": {"operation_id": "getLoanSummary"},
        "authorization": "Bearer secret-token",
        "expect": "ok",
    },
)
