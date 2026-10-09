"""Incremental embed + upsert into the vector store (Phase 3)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IndexReport(BaseModel):
    environment: str
    namespace: str = ""
    embed_model_id: str = ""
    embedded: int = 0
    deleted: int = 0
    unchanged: int = 0
    failed_apps: dict[str, str] = Field(default_factory=dict)
