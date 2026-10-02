"""System prompt loader — reads the Helix system prompt from the prompt store.

The system prompt is loaded via the ``PromptStoreProvider`` abstraction
(never a concrete class) and is expected to live in
``docs/01-servicing-agent-prompts.md`` under the name ``"agent.system"``.

The loader extracts the fenced code block from Section B of the project brief.
If the raw template is stored directly (already extracted), it is returned
as-is.
"""

from __future__ import annotations

import re

from packages.common.providers import PromptStoreProvider

_SYSTEM_PROMPT_NAME = "agent.system"

# Regex to extract the fenced code block from Section B
_FENCED_BLOCK_RE = re.compile(
    r"```text\s*\n(.*?)```",
    re.DOTALL,
)


async def load_system_prompt(
    prompt_store: PromptStoreProvider,
    prompt_name: str = _SYSTEM_PROMPT_NAME,
) -> str:
    """Load and return the system prompt template.

    The prompt store is expected to return the full markdown content of
    ``docs/01-servicing-agent-prompts.md``. This function extracts the
    first fenced ``text`` code block (Section B).

    If the prompt store already returns just the prompt (no fenced block),
    the string is returned as-is.
    """
    raw = await prompt_store.get(prompt_name)

    # Try to extract the fenced block
    match = _FENCED_BLOCK_RE.search(raw)
    if match:
        return match.group(1).strip()

    # If no fenced block found, return raw content (might already be the prompt)
    return raw.strip()
