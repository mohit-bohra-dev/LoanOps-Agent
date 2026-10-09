"""In-memory last-invoke outcome ring for /ready (spec §5.2 / §9.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class LastInvoke:
    outcome: str
    at: str


@dataclass
class LastInvokeRing:
    """Per-app last invoke outcome (single slot; not a history log)."""

    _entries: dict[str, LastInvoke] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def record(self, application_id: str, outcome: str) -> None:
        if not application_id:
            return
        with self._lock:
            self._entries[application_id] = LastInvoke(outcome=outcome, at=_now())

    def last(self, application_id: str) -> LastInvoke | None:
        with self._lock:
            return self._entries.get(application_id)

    def as_dict(self, application_id: str) -> dict[str, str] | None:
        entry = self.last(application_id)
        if entry is None:
            return None
        return {"outcome": entry.outcome, "at": entry.at}
