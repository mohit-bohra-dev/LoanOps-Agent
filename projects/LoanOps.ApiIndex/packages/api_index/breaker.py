"""Per-app circuit breaker state (Phase 4/5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class BreakerRegistry(Protocol):
    def is_open(self, application_id: str) -> bool: ...

    def record_failure(self, application_id: str) -> None: ...

    def record_success(self, application_id: str) -> None: ...


@dataclass
class InMemoryBreaker:
    failures: dict[str, int] = field(default_factory=dict)
    threshold: int = 5

    def is_open(self, application_id: str) -> bool:
        return self.failures.get(application_id, 0) >= self.threshold

    def record_failure(self, application_id: str) -> None:
        self.failures[application_id] = self.failures.get(application_id, 0) + 1

    def record_success(self, application_id: str) -> None:
        self.failures[application_id] = 0
