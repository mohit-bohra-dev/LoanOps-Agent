"""Per-app circuit breaker (spec §3.8). Protocol lives in packages.sse.types."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

from packages.sse.types import BreakerRegistry

_BREAKER_THRESHOLD = 5
_BREAKER_COOLDOWN_S = 30.0

BreakerState = Literal["closed", "open", "half_open"]


@dataclass
class _AppBreaker:
    state: BreakerState = "closed"
    failures: int = 0
    open_until: float = 0.0


@dataclass
class InMemoryBreaker:
    """Implements BreakerRegistry: 5 consecutive unavailable → open 30s → half_open trial."""

    threshold: int = _BREAKER_THRESHOLD
    cooldown_s: float = _BREAKER_COOLDOWN_S
    _apps: dict[str, _AppBreaker] = field(default_factory=dict)

    def _entry(self, application_id: str) -> _AppBreaker:
        entry = self._apps.get(application_id)
        if entry is None:
            entry = _AppBreaker()
            self._apps[application_id] = entry
        return entry

    def is_open(self, application_id: str) -> bool:
        entry = self._entry(application_id)
        if entry.state == "closed":
            return False
        if entry.state == "open":
            if time.monotonic() >= entry.open_until:
                entry.state = "half_open"
                return False  # allow one trial
            return True
        # half_open: allow the single trial (caller must record success/failure)
        return False

    def record_failure(self, application_id: str) -> None:
        entry = self._entry(application_id)
        if entry.state == "half_open":
            entry.state = "open"
            entry.open_until = time.monotonic() + self.cooldown_s
            entry.failures = self.threshold
            return
        entry.failures += 1
        if entry.failures >= self.threshold:
            entry.state = "open"
            entry.open_until = time.monotonic() + self.cooldown_s

    def record_success(self, application_id: str) -> None:
        entry = self._entry(application_id)
        entry.state = "closed"
        entry.failures = 0
        entry.open_until = 0.0

    def state_of(self, application_id: str) -> BreakerState:
        """Current breaker state for /ready (may transition open → half_open)."""
        entry = self._entry(application_id)
        if entry.state == "open" and time.monotonic() >= entry.open_until:
            entry.state = "half_open"
        return entry.state


__all__ = ["BreakerRegistry", "InMemoryBreaker"]
