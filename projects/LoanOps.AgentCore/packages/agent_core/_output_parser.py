"""Output parser — enforces the JSON output contract from Section B.

Parses the LLM's raw text output into an ``AgentTurnOutput`` Pydantic model.
On schema violation, it returns a detailed ``AgentParseError``.
"""

from __future__ import annotations

import json
import re
from typing import Any

from packages.common.schemas import AgentTurnOutput


class AgentParseError(Exception):
    """Raised when the LLM output cannot be parsed into ``AgentTurnOutput``."""

    def __init__(self, message: str, raw_output: str) -> None:
        self.raw_output = raw_output
        super().__init__(f"{message}\nRaw output: {raw_output[:500]}")


def _try_extract_json(text: str) -> str | None:
    """Try to extract a JSON object from the LLM response.

    Handles cases where the LLM wraps the JSON in markdown code fences
    or prepends explanatory text.
    """
    # Try to find a ```json ... ``` block
    start = text.find("```json")
    if start != -1:
        start += len("```json")
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()

    # Try to find a { ... } block (any top-level JSON object)
    brace_start = text.find("{")
    if brace_start != -1:
        # Find matching closing brace
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[brace_start : i + 1]

    return None


def _strip_thinking_tags(text: str) -> str:
    """Remove <think>...</think> blocks that thinking models prepend.

    Some models (e.g. qwen3, deepseek) wrap their reasoning in
    ``<think>`` tags before the actual output. Strip these so the
    JSON extractor can find the real payload.
    """
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


_TOOL_NAMES = frozenset(
    {
        "lookup_loan",
        "get_payment_schedule",
        "get_escrow_breakdown",
        "check_hardship_eligibility",
        "search_policy",
    }
)


def _fix_citations(data: dict[str, Any], recorded_tools: list[Any] | None = None) -> None:
    """Best-effort fixup for citation objects produced by smaller models.

    Fixes applied (in-place):
    * Missing ``id`` — assign sequential integers starting at 1.
    * Missing ``tool:`` / ``policy:`` prefix on ``source``.
    * Empty citations when tools were used — auto-inject tool citations.
    """
    citations = data.get("citations")
    if citations is None:
        citations = []
        data["citations"] = citations

    if isinstance(citations, list) and len(citations) == 0 and recorded_tools:
        # Auto-inject citations if the model used tools but forgot to cite them
        for idx, tool in enumerate(recorded_tools, start=1):
            tool_name = (
                tool.name
                if hasattr(tool, "name")
                else tool.get("name", "unknown")
                if isinstance(tool, dict)
                else "unknown"
            )
            citations.append(
                {
                    "id": idx,
                    "source": f"tool:{tool_name}",
                    "snippet": "Auto-injected from tool result",
                }
            )

    if not isinstance(citations, list):
        return

    for idx, cite in enumerate(citations, start=1):
        if not isinstance(cite, dict):
            continue

        # --- inject missing id ------------------------------------------------
        if "id" not in cite:
            cite["id"] = idx

        # --- fix source prefix ------------------------------------------------
        source = cite.get("source", "")
        if isinstance(source, str) and not source.startswith(("policy:", "tool:")):
            if source in _TOOL_NAMES:
                cite["source"] = f"tool:{source}"
            else:
                cite["source"] = f"policy:{source}"


def parse_agent_output(raw: str, recorded_tools: list[Any] | None = None) -> AgentTurnOutput:
    """Parse the raw LLM output string into an ``AgentTurnOutput``.

    Raises ``AgentParseError`` if parsing or validation fails.
    """
    # Strip thinking tags first (qwen3, deepseek, etc.)
    cleaned = _strip_thinking_tags(raw)

    extracted = _try_extract_json(cleaned)
    if extracted is None:
        raise AgentParseError("No JSON object found in LLM output", raw)

    try:
        data: dict[str, Any] = json.loads(extracted)
    except json.JSONDecodeError as exc:
        raise AgentParseError(f"Invalid JSON: {exc}", raw) from exc

    # Best-effort fixups for smaller local models before Pydantic validation
    _fix_citations(data, recorded_tools)

    try:
        return AgentTurnOutput(**data)
    except Exception as exc:  # noqa: BLE001 — Pydantic validation errors are fine to catch
        raise AgentParseError(f"Schema validation error: {exc}", raw) from exc
