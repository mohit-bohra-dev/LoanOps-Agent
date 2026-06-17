"""Session store provider — abstracts conversation memory persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """A single turn in a conversation."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    turn_id: str


class ConversationSession(BaseModel):
    """A conversation session with its message history."""

    session_id: str
    created_at: datetime
    last_accessed_at: datetime
    expires_at: datetime
    loan_id: str | None = None
    rep_id: str | None = None
    turns: list[ConversationTurn] = Field(default_factory=list)


class AbstractSessionStoreProvider(Protocol):
    """Protocol for conversation session storage."""

    async def create_session(
        self,
        session_id: str,
        loan_id: str | None = None,
        rep_id: str | None = None,
    ) -> ConversationSession:
        """Create a new conversation session."""
        ...

    async def get_session(self, session_id: str) -> ConversationSession | None:
        """Retrieve a session by ID, returning None if expired or not found."""
        ...

    async def append_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """Append a new turn to an existing session."""
        ...

    async def delete_session(self, session_id: str) -> None:
        """Delete a session entirely."""
        ...
