"""Pytest configuration for agent_core tests."""

from __future__ import annotations

import pytest_asyncio

from packages.common.providers import ToolResult
from packages.common.providers.testing import (
    MockLLMProvider,
    MockPromptStoreProvider,
    MockToolsClientProvider,
)


@pytest_asyncio.fixture
async def mock_chat_provider() -> MockLLMProvider:
    """Return a clean MockLLMProvider for each test."""
    return MockLLMProvider()


@pytest_asyncio.fixture
async def mock_tools_client() -> MockToolsClientProvider:
    """Return a MockToolsClientProvider pre-registered with all 5 tools."""
    client = MockToolsClientProvider()
    # Register all 5 servicing tools with canned success responses
    client.register(
        "lookup_loan",
        ToolResult(
            tool_name="lookup_loan",
            success=True,
            data={
                "loan_id": "100245",
                "borrower_first_name": "Alex",
                "state": "CA",
                "status": "active",
                "escrowed": True,
            },
        ),
    )
    client.register(
        "get_payment_schedule",
        ToolResult(
            tool_name="get_payment_schedule",
            success=True,
            data={
                "loan_id": "100245",
                "schedule": [
                    {
                        "due_date": "2026-06-01",
                        "principal": 412.55,
                        "interest": 1180.12,
                        "escrow": 615.30,
                        "total": 2207.97,
                    },
                ],
            },
        ),
    )
    client.register(
        "get_escrow_breakdown",
        ToolResult(
            tool_name="get_escrow_breakdown",
            success=True,
            data={
                "loan_id": "100245",
                "as_of": "2026-04-30",
                "current_balance_usd": 1842.10,
                "monthly_escrow_usd": 615.30,
                "monthly_escrow_change_usd": 35.12,
                "change_effective": "2026-05-01",
            },
        ),
    )
    client.register(
        "check_hardship_eligibility",
        ToolResult(
            tool_name="check_hardship_eligibility",
            success=True,
            data={
                "loan_id": "100118",
                "program": "disaster_forbearance",
                "hint": "likely_eligible",
                "binding": False,
            },
        ),
    )
    client.register(
        "search_policy",
        ToolResult(
            tool_name="search_policy",
            success=True,
            data={
                "query": "escrow analysis",
                "results": [
                    {
                        "chunk_id": "policy:escrow/annual-analysis.md#sec-2",
                        "score": 0.84,
                        "snippet": "Annual escrow analysis statement...",
                        "source_path": "data/sops/escrow/annual-analysis.md",
                        "version": "2026.03",
                    }
                ],
            },
        ),
    )
    return client


@pytest_asyncio.fixture
async def mock_prompt_store() -> MockPromptStoreProvider:
    """Return a MockPromptStoreProvider with a canned system prompt."""
    store = MockPromptStoreProvider()
    store.set(
        "agent.system",
        """
You are "Helix", an internal copilot for licensed mortgage-servicing care representatives.

HARD RULES
1. Cite every factual claim.
2. Never invent loan numbers, dollar amounts, dates, names, etc.

OUTPUT CONTRACT (return ONLY this JSON, no prose)
{
  "answer": "<rep-facing draft reply>",
  "citations": [{"id": 1, "source": "policy:...", "snippet": "..."}],
  "tool_calls": [{"name": "...", "args": {}, "result_summary": "..."}],
  "requires_human_approval": true,
  "confidence": 0.0,
  "refusal": null,
  "escalation": null
}
""".strip(),
    )
    return store


# Default test system prompt used when mock is dynamically configured
TEST_SYSTEM_PROMPT = """
You are "Helix", an internal copilot for licensed mortgage-servicing care representatives.

HARD RULES
1. Cite every factual claim.
2. Never invent values.

OUTPUT CONTRACT (return ONLY this JSON, no prose)
{
  "answer": "<rep-facing draft reply>",
  "citations": [],
  "tool_calls": [],
  "requires_human_approval": true,
  "confidence": 0.0,
  "refusal": null,
  "escalation": null
}
""".strip()


def build_valid_json_output(
    *,
    answer: str = "Draft reply here.",
    confidence: float = 0.9,
    refusal: str | None = None,
    escalation: dict[str, object] | None = None,
    citations: list[dict[str, object]] | None = None,
    tool_calls: list[dict[str, object]] | None = None,
) -> str:
    """Build a valid JSON string matching the AgentTurnOutput schema."""
    output: dict[str, object] = {
        "answer": answer,
        "citations": citations or [],
        "tool_calls": tool_calls or [],
        "requires_human_approval": True,
        "confidence": confidence,
        "refusal": refusal,
        "escalation": escalation,
    }
    import json

    return json.dumps(output)
