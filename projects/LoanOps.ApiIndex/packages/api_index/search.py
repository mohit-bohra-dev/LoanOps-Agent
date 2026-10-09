"""Two-stage API operation search (Phase 3)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchOutcome(BaseModel):
    hits: list[Any] = Field(default_factory=list)
    backend: str = "none"
    confident: bool = False


class ApiSearchService:
    """Placeholder until vector shortlist lands."""

    async def search(
        self,
        query: str,
        *,
        limit: int = 15,
        application_ids: list[str] | None = None,
        permission: str | None = None,
    ) -> SearchOutcome:
        _ = (query, limit, application_ids, permission)
        return SearchOutcome()
