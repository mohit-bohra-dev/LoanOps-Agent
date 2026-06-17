"""Tests for the memory strategy."""

from __future__ import annotations

from datetime import UTC, datetime

from packages.agent_core._memory import build_history_messages
from packages.common.providers.session_store import ConversationSession, ConversationTurn


def test_build_history_messages_empty() -> None:
    session = ConversationSession(
        session_id="1",
        rep_id="1",
        created_at=datetime.now(UTC),
        last_accessed_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
        turns=[],
    )
    messages = build_history_messages(session, "hello")
    assert messages == []


def test_build_history_messages_budget() -> None:
    turn1 = ConversationTurn(
        role="user",
        content="hello " * 1000,
        timestamp=datetime.now(UTC),
        turn_id="t1",
    )
    turn2 = ConversationTurn(
        role="assistant",
        content="hi " * 10,
        timestamp=datetime.now(UTC),
        turn_id="t2",
    )
    session = ConversationSession(
        session_id="1",
        rep_id="1",
        created_at=datetime.now(UTC),
        last_accessed_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
        turns=[turn1, turn2],
    )
    messages = build_history_messages(session, "how are you", max_tokens=100)
    assert len(messages) == 1
    assert messages[0].content == turn2.content


def test_build_history_messages_loan_retention() -> None:
    turn1 = ConversationTurn(
        role="user",
        content="loan 1234 is great " * 1000,
        timestamp=datetime.now(UTC),
        turn_id="t1",
    )
    turn2 = ConversationTurn(
        role="assistant",
        content="yes " * 1000,
        timestamp=datetime.now(UTC),
        turn_id="t2",
    )
    session = ConversationSession(
        session_id="1",
        rep_id="1",
        loan_id="1234",
        created_at=datetime.now(UTC),
        last_accessed_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
        turns=[turn1, turn2],
    )
    messages = build_history_messages(session, "how are you", max_tokens=100)
    assert len(messages) == 1
    assert messages[0].content == turn1.content
