"""Agent runner — orchestrates a single agent turn.

Flow:
1. Load the system prompt via PromptStoreProvider
2. Classify intent via the pure-function router
3. If ANSWER: call the LLM via ChatProvider (Pass 1 with tools)
4. If tools are requested, execute them, append results, call LLM again (Pass 2)
5. Parse the final JSON output
6. If schema failure: retry once, then return a refusal with explanation
"""

from __future__ import annotations

from typing import Any

from packages.agent_core._intent_router import IntentType, classify_intent
from packages.agent_core._output_parser import AgentParseError, parse_agent_output
from packages.agent_core._prompt_loader import load_system_prompt
from packages.common.providers import (
    ChatProvider,
    LLMMessage,
    PromptStoreProvider,
    ToolCall,
    ToolCallRequest,
    ToolDefinition,
    ToolsClientProvider,
)
from packages.common.schemas import AgentTurnOutput, EscalationItem, ToolCallItem
from packages.safety.tokenizer import PiiTokenizer

_SYSTEM_PROMPT_NAME = "agent.system"
_MAX_RETRIES = 1

_SERVICING_TOOLS = [
    ToolDefinition(
        name="lookup_loan",
        description="Retrieve basic details about a loan.",
        parameters={
            "type": "object",
            "properties": {"loan_id": {"type": "string"}},
            "required": ["loan_id"],
        },
    ),
    ToolDefinition(
        name="search_borrower",
        description=(
            "Search for loans by borrower name. Available only with local mock "
            "fixtures — not supported on the real Loan Services API. Prefer "
            "lookup_loan with loan_id when the loan number is known."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Borrower first or last name (partial match)",
                }
            },
            "required": ["name"],
        },
    ),
    ToolDefinition(
        name="get_payment_schedule",
        description="Get upcoming payment schedule details.",
        parameters={
            "type": "object",
            "properties": {
                "loan_id": {"type": "string"},
                "months": {"type": "integer"},
            },
            "required": ["loan_id"],
        },
    ),
    ToolDefinition(
        name="get_escrow_breakdown",
        description="Get escrow account breakdown and disbursement history.",
        parameters={
            "type": "object",
            "properties": {"loan_id": {"type": "string"}},
            "required": ["loan_id"],
        },
    ),
    ToolDefinition(
        name="check_hardship_eligibility",
        description="Get non-binding hardship program eligibility hint.",
        parameters={
            "type": "object",
            "properties": {
                "loan_id": {"type": "string"},
                "program": {
                    "type": "string",
                    "description": "The specific program to check.",
                    "enum": ["disaster_forbearance", "covid_forbearance", "repayment_plan"]
                },
            },
            "required": ["loan_id", "program"],
        },
    ),
    ToolDefinition(
        name="search_policy",
        description="Search policy documents. Always use this for policy, rules, "
        "state law, or SOPs.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "state": {"type": "string"},
                "k": {"type": "integer"},
            },
            "required": ["query"],
        },
    ),
]


async def _execute_tools(
    tool_calls: list[ToolCallRequest],
    tools_client: ToolsClientProvider,
    pii_token_map: dict[str, str] | None = None,
) -> list[ToolCallItem]:
    """Execute tool calls and return recorded items.

    If *pii_token_map* is provided, string values inside tool arguments
    are detokenized (e.g. ``[PERSON_1]`` → ``Sam Patel``) before the
    HTTP call leaves the trust boundary.  The *recorded* items keep the
    **tokenized** args so audit logs never contain real PII.
    """
    recorded: list[ToolCallItem] = []
    for tc in tool_calls:
        # Detokenize args for the actual API call (real PII stays server-side)
        resolved_args: dict[str, Any] = (
            PiiTokenizer.detokenize_dict(tc.arguments, pii_token_map)
            if pii_token_map
            else tc.arguments
        )

        tool = ToolCall(tool_name=tc.name, parameters=resolved_args)
        result = await tools_client.call(tool)
        recorded.append(
            ToolCallItem(
                name=tc.name,
                args=tc.arguments,  # tokenized args for audit trail
                result_summary=str(result.data)[:500]
                if result.success
                else result.error or "error",
            )
        )
    return recorded


async def run_agent_turn(
    *,
    prompt: str,
    chat_provider: ChatProvider,
    tools_client: ToolsClientProvider,
    prompt_store: PromptStoreProvider,
    history: list[LLMMessage] | None = None,
    pii_token_map: dict[str, str] | None = None,
) -> AgentTurnOutput:
    """Run a single agent turn and return structured output."""
    # Step 1: Classify intent
    intent, reason, detail = classify_intent(prompt)

    if intent == IntentType.REFUSE:
        return AgentTurnOutput(
            answer="",
            citations=[],
            tool_calls=[],
            requires_human_approval=True,
            confidence=0.0,
            refusal=reason,
            escalation=None,
        )

    if intent == IntentType.ESCALATE:
        return AgentTurnOutput(
            answer="",
            citations=[],
            tool_calls=[],
            requires_human_approval=True,
            confidence=0.0,
            refusal="Escalating per policy; do not draft a reply.",
            escalation=EscalationItem(
                category=reason,  # type: ignore[arg-type]
                reason=detail or "Escalation triggered by router",
            ),
        )

    # Step 2: Load system prompt
    system_prompt = await load_system_prompt(prompt_store, _SYSTEM_PROMPT_NAME)

    _TEXT_ONLY_PREAMBLE = (
        "IMPORTANT: This is a TEXT-ONLY conversation. There are no images, "
        "files, or attachments. Do not reference or request images. "
        "You MUST respond with ONLY valid JSON matching the OUTPUT CONTRACT.\n\n"
    )
    full_system_prompt = _TEXT_ONLY_PREAMBLE + system_prompt

    # Step 3: Build messages
    messages = [
        LLMMessage(role="system", content=full_system_prompt),
        *(history or []),
        LLMMessage(role="user", content=prompt),
    ]

    # Step 4: First Pass (Tool Calling)
    response = await chat_provider.chat(
        messages,
        temperature=0.0,
        max_tokens=2048,
        json_mode=True,
        tools=_SERVICING_TOOLS,
    )

    recorded_tools: list[ToolCallItem] = []

    # If the model requested tools, execute them and do a Second Pass
    if response.tool_calls:
        recorded_tools = await _execute_tools(
            response.tool_calls, tools_client, pii_token_map=pii_token_map
        )

        # Append tool results as a system/user context update
        tool_results_text = "Here are the results from the tools you requested:\n"
        for item in recorded_tools:
            tool_results_text += f"[{item.name}]: {item.result_summary}\n"
        tool_results_text += (
            "\nNow provide your final valid JSON response matching "
            "the OUTPUT CONTRACT. Ensure your `answer` field contains "
            "a drafted prose reply for the rep as a string, not raw JSON."
        )

        messages.append(
            LLMMessage(
                role="assistant", content=response.content or "Let me check that using my tools."
            )
        )
        messages.append(LLMMessage(role="user", content=tool_results_text))

        response = await chat_provider.chat(
            messages,
            temperature=0.0,
            max_tokens=2048,
            json_mode=True,
        )

    # Step 5: Parse the final JSON output with retry logic
    last_error: str | None = None
    for attempt in range(_MAX_RETRIES + 1):
        if attempt > 0:
            # Re-call if we are retrying
            response = await chat_provider.chat(
                messages,
                temperature=0.1,
                max_tokens=2048,
                json_mode=True,
            )

        raw_output = response.content

        try:
            parsed = parse_agent_output(raw_output, recorded_tools)

            return AgentTurnOutput(
                answer=parsed.answer,
                citations=parsed.citations,
                tool_calls=recorded_tools,  # Use the natively executed tools!
                requires_human_approval=True,
                confidence=parsed.confidence,
                refusal=parsed.refusal,
                escalation=parsed.escalation,
            )
        except AgentParseError as exc:
            last_error = str(exc)
            if attempt < _MAX_RETRIES:
                messages.append(LLMMessage(role="assistant", content=raw_output))
                messages.append(
                    LLMMessage(
                        role="user",
                        content=(
                            "Your previous response did not conform to the required JSON schema. "
                            "Please respond with ONLY valid JSON matching the output contract. "
                            f"Validation error: {last_error}"
                        ),
                    )
                )
                continue

    return AgentTurnOutput(
        answer="",
        citations=[],
        tool_calls=recorded_tools,
        requires_human_approval=True,
        confidence=0.0,
        refusal=(
            f"I could not produce a valid response after {_MAX_RETRIES + 1} attempts. {last_error}"
        ),
        escalation=None,
    )
