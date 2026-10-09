"""Per-app health aggregation for /ready (Phase 5)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthSnapshot(BaseModel):
    environment: str
    apps: dict[str, dict[str, object]] = Field(default_factory=dict)


class AppHealthService:
    def snapshot(self, *, environment: str) -> HealthSnapshot:
        return HealthSnapshot(environment=environment)
