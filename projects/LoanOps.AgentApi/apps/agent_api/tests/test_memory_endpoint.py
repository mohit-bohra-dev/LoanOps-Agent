"""Tests for the chat memory endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from packages.common.providers.session_store import ConversationSession, ConversationTurn


def _make_mock_session_store(get_return_value: ConversationSession | None) -> MagicMock:
    """Create a mock session store provider."""
    store = MagicMock()
    store.get_session = AsyncMock(return_value=get_return_value)
    return store


@pytest.fixture()
def mock_session_store_factory() -> Any:
    """Patch the session store factory function."""
    patcher = patch("apps.agent_api.main.get_session_store_provider")
    mock_factory = patcher.start()
    yield mock_factory
    patcher.stop()


@pytest.mark.asyncio
async def test_get_chat_memory_success(mock_session_store_factory: MagicMock) -> None:
    """Test successful retrieval of chat memory."""
    # Create a mock session with some turns
    turns = [
        ConversationTurn(
            role="user",
            content="Hello, I need help with my mortgage",
            timestamp=datetime.now(UTC),
            turn_id="turn-1",
        ),
        ConversationTurn(
            role="assistant",
            content="I'd be happy to help you with your mortgage questions",
            timestamp=datetime.now(UTC),
            turn_id="turn-2",
        ),
    ]

    session = ConversationSession(
        session_id="test-session",
        created_at=datetime.now(UTC),
        last_accessed_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
        turns=turns,
    )

    # Set up the mock
    mock_session_store = _make_mock_session_store(session)
    mock_session_store_factory.return_value = mock_session_store

    # Make request
    from apps.agent_api.main import app

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/chat/memory/test-session")

    # Check response
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "test-session"
    assert data["total_messages"] == 2
    assert data["active_messages"] == 2
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "Hello, I need help with my mortgage"
    assert data["messages"][0]["is_active"] is True
    assert data["messages"][1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_get_chat_memory_empty_session(mock_session_store_factory: MagicMock) -> None:
    """Test getting memory for an empty session."""
    # Create a mock session with no turns
    session = ConversationSession(
        session_id="test-empty-session",
        created_at=datetime.now(UTC),
        last_accessed_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
        turns=[],
    )

    # Set up the mock
    mock_session_store = _make_mock_session_store(session)
    mock_session_store_factory.return_value = mock_session_store

    # Make request
    from apps.agent_api.main import app

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/chat/memory/test-empty-session")

    # Check response
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "test-empty-session"
    assert data["total_messages"] == 0
    assert data["active_messages"] == 0
    assert data["messages"] == []


@pytest.mark.asyncio
async def test_get_chat_memory_not_found() -> None:
    """Test getting memory for a non-existent session."""
    # Create a mock that returns None
    mock_session_store = _make_mock_session_store(None)
    with patch("apps.agent_api.main.get_session_store_provider", return_value=mock_session_store):
        from apps.agent_api.main import app

        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/chat/memory/non-existent-session")

        assert resp.status_code == 404
