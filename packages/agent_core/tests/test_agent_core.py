"""Tests for agent_core — happy, refuse, escalate paths using InMemory providers."""

from __future__ import annotations

import json
from types import MethodType
from typing import Any

import pytest

from packages.agent_core import (
    IntentType,
    classify_intent,
    load_system_prompt,
    parse_agent_output,
    run_agent_turn,
)
from packages.agent_core._output_parser import AgentParseError
from packages.agent_core.tests.conftest import (
    build_valid_json_output,
)
from packages.common.providers import LLMMessage, LLMResponse
from packages.common.providers.testing import (
    MockLLMProvider,
    MockPromptStoreProvider,
    MockToolsClientProvider,
)
from packages.common.schemas import AgentTurnOutput

# ── Intent Router Tests ─────────────────────────────────────────────────────


class TestIntentRouter:
    """Tests for the pure-function intent router."""

    def test_answer_intent_normal_query(self) -> None:
        """A normal servicing question should classify as ANSWER."""
        intent, reason, detail = classify_intent(
            "Loan 100245 escrow jumped $35 in May — draft a reply."
        )
        assert intent == IntentType.ANSWER
        assert reason == "answer"
        assert detail is None

    def test_refuse_rate_quote(self) -> None:
        """Rate quote queries should be refused."""
        intent, reason, detail = classify_intent("What rate could 100402 get if they refi today?")
        assert intent == IntentType.REFUSE
        assert "outside v1 scope" in reason

    def test_refuse_advice(self) -> None:
        """Requests for financial advice should be refused."""
        intent, reason, detail = classify_intent(
            "Should borrower 100118 pay extra principal this month?"
        )
        assert intent == IntentType.REFUSE
        assert "outside v1 scope" in reason

    def test_escalate_cfpb(self) -> None:
        """CFPB complaint mentions should escalate."""
        intent, reason, detail = classify_intent("Borrower says they're filing a CFPB complaint.")
        assert intent == IntentType.ESCALATE
        assert reason == "complaint_or_regulatory"

    def test_escalate_safety(self) -> None:
        """Self-harm mentions should escalate to safety."""
        intent, reason, detail = classify_intent("Borrower mentioned suicide on the call.")
        assert intent == IntentType.ESCALATE
        assert reason == "safety"

    def test_escalate_bankruptcy(self) -> None:
        """Bankruptcy mentions should escalate to legal_status."""
        intent, reason, detail = classify_intent("Loan 100515 in active bankruptcy.")
        assert intent == IntentType.ESCALATE
        assert reason == "legal_status"

    def test_escalate_fraud(self) -> None:
        """Fraud claims should escalate."""
        intent, reason, detail = classify_intent(
            "Borrower thinks someone accessed their account. Fraud."
        )
        assert intent == IntentType.ESCALATE
        assert reason == "fraud"

    def test_escalate_identity_theft(self) -> None:
        """Identity theft should escalate."""
        intent, reason, detail = classify_intent("Borrower claims identity theft.")
        assert intent == IntentType.ESCALATE
        assert reason == "fraud"

    def test_escalate_lawsuit(self) -> None:
        """Lawsuit mentions should escalate."""
        intent, reason, detail = classify_intent("Borrower mentioned they are filing a lawsuit.")
        assert intent == IntentType.ESCALATE
        assert reason == "complaint_or_regulatory"


# ── Output Parser Tests ────────────────────────────────────────────────────


class TestOutputParser:
    """Tests for the JSON output parser."""

    def test_parse_valid_output(self) -> None:
        """Valid JSON matching the schema should parse successfully."""
        raw = build_valid_json_output(
            answer="Here is the reply.",
            confidence=0.85,
        )
        result = parse_agent_output(raw)
        assert isinstance(result, AgentTurnOutput)
        assert result.answer == "Here is the reply."
        assert result.confidence == 0.85
        assert result.refusal is None

    def test_parse_with_citations(self) -> None:
        """Citations should be parsed correctly."""
        raw = build_valid_json_output(
            citations=[
                {
                    "id": 1,
                    "source": "policy:escrow/annual-analysis.md",
                    "snippet": "Annual analysis...",
                },
                {"id": 2, "source": "tool:get_escrow_breakdown", "snippet": "+$35.12"},
            ],
        )
        result = parse_agent_output(raw)
        assert len(result.citations) == 2
        assert result.citations[0].source.startswith("policy:")
        assert result.citations[1].source.startswith("tool:")

    def test_parse_with_tool_calls(self) -> None:
        """Tool calls should be parsed correctly."""
        raw = build_valid_json_output(
            tool_calls=[
                {
                    "name": "lookup_loan",
                    "args": {"loan_id": "100245"},
                    "result_summary": "active, CA",
                },
            ],
        )
        result = parse_agent_output(raw)
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "lookup_loan"

    def test_parse_refusal(self) -> None:
        """Refusal JSON should parse correctly."""
        raw = build_valid_json_output(
            answer="",
            confidence=0.0,
            refusal="This request is outside v1 scope.",
        )
        result = parse_agent_output(raw)
        assert result.answer == ""
        assert result.refusal == "This request is outside v1 scope."

    def test_parse_escalation(self) -> None:
        """Escalation JSON should parse correctly."""
        raw = build_valid_json_output(
            answer="",
            confidence=0.0,
            refusal="Escalating per policy.",
            escalation={"category": "complaint_or_regulatory", "reason": "CFPB complaint"},
        )
        result = parse_agent_output(raw)
        assert result.escalation is not None
        assert result.escalation.category == "complaint_or_regulatory"

    def test_parse_from_code_fence(self) -> None:
        """JSON wrapped in ```json code fence should still parse."""
        raw = f"Some text\n```json\n{build_valid_json_output()}\n```\nmore text"
        result = parse_agent_output(raw)
        assert isinstance(result, AgentTurnOutput)

    def test_parse_invalid_json_raises(self) -> None:
        """Invalid JSON should raise AgentParseError."""
        with pytest.raises(AgentParseError):
            parse_agent_output("this is not json at all {{{")

    def test_parse_schema_violation_raises(self) -> None:
        """JSON that doesn't match the schema should raise AgentParseError."""
        raw = json.dumps({"answer": "hi"})  # missing required fields
        with pytest.raises(AgentParseError):
            parse_agent_output(raw)

    def test_parse_empty_text_raises(self) -> None:
        """Empty text with no JSON should raise."""
        with pytest.raises(AgentParseError):
            parse_agent_output("")

    def test_parse_no_json_found(self) -> None:
        """Text with no JSON object should raise."""
        with pytest.raises(AgentParseError):
            parse_agent_output("Just some regular text without any JSON object.")


# ── Prompt Loader Tests ────────────────────────────────────────────────────


class TestPromptLoader:
    """Tests for the system prompt loader."""

    async def test_load_raw_prompt(self, mock_prompt_store: MockPromptStoreProvider) -> None:
        """Loading a raw prompt (no fenced block) should return it as-is."""
        prompt = await load_system_prompt(mock_prompt_store)
        assert "Helix" in prompt
        assert "OUTPUT CONTRACT" in prompt

    async def test_load_extracts_fenced_block(self) -> None:
        """When prompt contains a ```text fence, the fenced block should be extracted."""
        store = MockPromptStoreProvider()
        store.set(
            "agent.system",
            """
Some intro text.

```text
This is the system prompt.
It has multiple lines.
```

Some outro text.
""".strip(),
        )
        prompt = await load_system_prompt(store)
        assert prompt == "This is the system prompt.\nIt has multiple lines."

    async def test_prompt_not_found_raises_key_error(self) -> None:
        """A missing prompt name should raise KeyError."""
        store = MockPromptStoreProvider()
        with pytest.raises(KeyError):
            await load_system_prompt(store, prompt_name="nonexistent.prompt")


# ── Agent Runner Tests ─────────────────────────────────────────────────────


class TestAgentRunner:
    """End-to-end tests for the agent runner against InMemory providers."""

    async def test_happy_path(
        self,
        mock_chat_provider: MockLLMProvider,
        mock_tools_client: MockToolsClientProvider,
        mock_prompt_store: MockPromptStoreProvider,
    ) -> None:
        """A normal servicing query should return a valid AgentTurnOutput."""
        # Override mock to return valid JSON

        async def patched_chat(
            self: MockLLMProvider,
            messages: list[LLMMessage],
            *,
            temperature: float = 0.7,
            max_tokens: int = 2048,
            json_mode: bool = False,
            **kwargs: Any,
        ) -> LLMResponse:
            return LLMResponse(
                content=build_valid_json_output(
                    answer="Here is the draft reply.",
                    confidence=0.92,
                    citations=[
                        {
                            "id": 1,
                            "source": "policy:escrow/annual-analysis.md",
                            "snippet": "... escrow analysis ...",
                        }
                    ],
                ),
                model="mock",
                usage={"prompt_tokens": 10, "completion_tokens": 5},
                raw={},
            )

        mock_chat_provider.chat = MethodType(patched_chat, mock_chat_provider)  # type: ignore[method-assign]

        result = await run_agent_turn(
            prompt="Loan 100245 escrow jumped $35 in May — draft a reply.",
            chat_provider=mock_chat_provider,
            tools_client=mock_tools_client,
            prompt_store=mock_prompt_store,
        )

        assert isinstance(result, AgentTurnOutput)
        assert "draft reply" in result.answer
        assert result.confidence == 0.92
        assert result.refusal is None
        assert result.escalation is None
        assert result.requires_human_approval is True
        assert len(result.citations) == 1

    async def test_refuse_rate_quote(
        self,
        mock_chat_provider: MockLLMProvider,
        mock_tools_client: MockToolsClientProvider,
        mock_prompt_store: MockPromptStoreProvider,
    ) -> None:
        """A rate quote query should be refused without calling the LLM."""
        result = await run_agent_turn(
            prompt="What rate could 100402 get if they refi today?",
            chat_provider=mock_chat_provider,
            tools_client=mock_tools_client,
            prompt_store=mock_prompt_store,
        )

        assert isinstance(result, AgentTurnOutput)
        assert result.answer == ""
        assert result.refusal is not None
        assert "outside v1 scope" in result.refusal
        assert result.confidence == 0.0
        assert result.escalation is None

    async def test_escalate_cfpb(
        self,
        mock_chat_provider: MockLLMProvider,
        mock_tools_client: MockToolsClientProvider,
        mock_prompt_store: MockPromptStoreProvider,
    ) -> None:
        """A CFPB escalation should return an escalation without calling the LLM."""
        result = await run_agent_turn(
            prompt="Borrower says they're filing a CFPB complaint about missed posting.",
            chat_provider=mock_chat_provider,
            tools_client=mock_tools_client,
            prompt_store=mock_prompt_store,
        )

        assert isinstance(result, AgentTurnOutput)
        assert result.answer == ""
        assert result.refusal == "Escalating per policy; do not draft a reply."
        assert result.escalation is not None
        assert result.escalation.category == "complaint_or_regulatory"
        assert result.confidence == 0.0

    async def test_escalate_safety(
        self,
        mock_chat_provider: MockLLMProvider,
        mock_tools_client: MockToolsClientProvider,
        mock_prompt_store: MockPromptStoreProvider,
    ) -> None:
        """A safety escalation should return the correct category."""
        result = await run_agent_turn(
            prompt="Borrower 100207 mentioned suicide on the call.",
            chat_provider=mock_chat_provider,
            tools_client=mock_tools_client,
            prompt_store=mock_prompt_store,
        )

        assert result.escalation is not None
        assert result.escalation.category == "safety"

    async def test_retry_on_schema_failure_then_succeed(
        self,
        mock_chat_provider: MockLLMProvider,
        mock_tools_client: MockToolsClientProvider,
        mock_prompt_store: MockPromptStoreProvider,
    ) -> None:
        """On first schema failure, the agent should retry. On second attempt, succeed."""
        call_count = 0

        async def failing_then_valid(
            self: MockLLMProvider,
            messages: list[LLMMessage],
            *,
            temperature: float = 0.7,
            max_tokens: int = 2048,
            json_mode: bool = False,
            **kwargs: Any,
        ) -> LLMResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call returns invalid JSON
                return LLMResponse(
                    content="This is not valid JSON at all.",
                    model="mock",
                    usage={"prompt_tokens": 10, "completion_tokens": 5},
                    raw={},
                )
            # Second call returns valid JSON
            return LLMResponse(
                content=build_valid_json_output(answer="Valid reply after retry.", confidence=0.8),
                model="mock",
                usage={"prompt_tokens": 10, "completion_tokens": 5},
                raw={},
            )

        mock_chat_provider.chat = MethodType(failing_then_valid, mock_chat_provider)  # type: ignore[method-assign]

        result = await run_agent_turn(
            prompt="Loan 100245 payment schedule.",
            chat_provider=mock_chat_provider,
            tools_client=mock_tools_client,
            prompt_store=mock_prompt_store,
        )

        assert call_count == 2
        assert result.answer == "Valid reply after retry."
        assert result.refusal is None

    async def test_exhaust_retries_returns_refusal(
        self,
        mock_chat_provider: MockLLMProvider,
        mock_tools_client: MockToolsClientProvider,
        mock_prompt_store: MockPromptStoreProvider,
    ) -> None:
        """When all retries are exhausted, a refusal should be returned."""

        async def always_fails(
            self: MockLLMProvider,
            messages: list[LLMMessage],
            *,
            temperature: float = 0.7,
            max_tokens: int = 2048,
            json_mode: bool = False,
            **kwargs: Any,
        ) -> LLMResponse:
            return LLMResponse(
                content="Still not valid JSON {{{",
                model="mock",
                usage={"prompt_tokens": 10, "completion_tokens": 5},
                raw={},
            )

        mock_chat_provider.chat = MethodType(always_fails, mock_chat_provider)  # type: ignore[method-assign]

        result = await run_agent_turn(
            prompt="Loan 100245 details.",
            chat_provider=mock_chat_provider,
            tools_client=mock_tools_client,
            prompt_store=mock_prompt_store,
        )

        assert result.answer == ""
        assert result.refusal is not None
        assert "could not produce a valid response" in result.refusal
        assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_agent_turn_via_mcp_tools_client(
    mock_chat_provider: MockLLMProvider,
    mock_prompt_store: MockPromptStoreProvider,
) -> None:
    """Phase 4: agent executes tools through McpToolsClient (fake session, no network)."""
    from packages.common.mcp_tools_client import McpToolsClient
    from packages.common.providers import ToolCallRequest

    class _FakeSession:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, Any]]] = []

        async def list_tool_names(self) -> list[str]:
            return ["search_sse_apis", "list_sse_apis", "call_sse_api", "search_docs"]

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
            self.calls.append((name, arguments))
            return True, "op:getLoanSummary"

    session = _FakeSession()
    tools_client = McpToolsClient(session=session, role="system")
    call_count = 0

    async def tool_then_answer(
        self: MockLLMProvider,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResponse(
                content="",
                model="mock",
                tool_calls=[
                    ToolCallRequest(name="search_sse_apis", arguments={"query": "loan summary"}),
                ],
            )
        return LLMResponse(
            content=build_valid_json_output(
                answer="Loan summary found via MCP hop.",
                confidence=0.9,
                citations=[{"id": 1, "source": "tool:search_sse_apis", "snippet": "getLoanSummary"}],
            ),
            model="mock",
        )

    mock_chat_provider.chat = MethodType(tool_then_answer, mock_chat_provider)  # type: ignore[method-assign]

    result = await run_agent_turn(
        prompt="Loan 100245 status — draft a reply.",
        chat_provider=mock_chat_provider,
        tools_client=tools_client,
        prompt_store=mock_prompt_store,
    )

    assert result.answer == "Loan summary found via MCP hop."
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search_sse_apis"
    assert "getLoanSummary" in result.tool_calls[0].result_summary
    assert session.calls == [("search_sse_apis", {"query": "loan summary"})]