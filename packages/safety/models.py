from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PiiSpan(BaseModel):
    """Represents a redacted PII entity in text."""

    entity_type: str
    start: int
    end: int
    original_text: str


class SanitizeResult(BaseModel):
    """Result of inbound PII anonymization."""

    anonymized_text: str
    spans: list[PiiSpan] = Field(default_factory=list)
    token_map: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """Result of outbound content safety evaluation."""

    is_safe: bool
    original_text: str
    blocked_text: str | None = None
    verdict: str | None = None
    reason: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
