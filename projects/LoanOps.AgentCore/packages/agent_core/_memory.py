"""Memory strategy — builds history context for the LLM."""

from __future__ import annotations

from packages.common.providers import LLMMessage
from packages.common.providers.session_store import ConversationSession, ConversationTurn


def estimate_tokens(text: str) -> int:
    """Estimate token count from free text using a lightweight heuristic."""
    return int(len(text.split()) * 1.3)


def build_history_messages(
    session: ConversationSession,
    current_prompt: str,
    max_tokens: int = 2048,
) -> list[LLMMessage]:
    """Build history messages from a session using a sliding window strategy.

    Strategy:
    1. Walk backward through turns.
    2. Keep turns that mention the session's loan_id (if set).
    3. Keep other turns until we hit the max_tokens budget.
    4. Return messages in chronological order.

    Tokens are estimated roughly as words * 1.3.
    """
    if not session.turns:
        return []

    current_prompt_tokens = estimate_tokens(current_prompt)
    available_budget = max(0, max_tokens - current_prompt_tokens)

    retained_turns: list[ConversationTurn] = []

    # Process turns newest to oldest
    for turn in reversed(session.turns):
        turn_tokens = estimate_tokens(turn.content)
        if available_budget - turn_tokens < 0:
            if session.loan_id and session.loan_id in turn.content:
                retained_turns.append(turn)
            available_budget = 0
            continue

        retained_turns.append(turn)
        available_budget -= turn_tokens

    # Put them back in chronological order
    retained_turns.reverse()

    messages = []
    for t in retained_turns:
        role = t.role
        if role not in ("system", "user", "assistant"):
            role = "user"  # Fallback
        messages.append(LLMMessage(role=role, content=t.content))

    return messages


def export_memory_markdown(session: ConversationSession) -> str:
    """Export session memory as structured markdown for audit/debugging."""
    lines: list[str] = []
    lines.append(f"# Session: {session.session_id}")
    lines.append(f"- **Created**: {session.created_at.isoformat()}")
    lines.append(f"- **Last Accessed**: {session.last_accessed_at.isoformat()}")
    lines.append(f"- **Expires**: {session.expires_at.isoformat()}")
    lines.append(f"- **Loan ID**: {session.loan_id or 'N/A'}")
    lines.append(f"- **Rep ID**: {session.rep_id or 'N/A'}")
    lines.append(f"- **Turns**: {len(session.turns)}")
    lines.append("")

    for i, turn in enumerate(session.turns, 1):
        token_est = estimate_tokens(turn.content)
        lines.append(f"## Turn {i} — {turn.role}")
        lines.append(f"- **Turn ID**: {turn.turn_id}")
        lines.append(f"- **Timestamp**: {turn.timestamp.isoformat()}")
        lines.append(f"- **Tokens**: ~{token_est}")
        lines.append("")
        lines.append(turn.content)
        lines.append("")

    return "\n".join(lines)
