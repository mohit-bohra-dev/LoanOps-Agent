"""Shared provider base types for the Servicing Agent.

Project-specific helpers that complement the abstract contracts from
``provider_contracts``.  ABCs themselves are imported directly from
``provider_contracts`` where type annotations are needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderHealth:
    """Result of a single provider health check."""

    name: str
    ok: bool
    detail: str = ""


class ProviderError(Exception):
    """Raised when a provider call fails after retries."""


class ProviderConfigError(ProviderError):
    """Raised when provider configuration is invalid or missing."""


@dataclass
class ProviderCallEvent:
    """Lightweight audit record for a provider invocation."""

    provider: str
    method: str
    success: bool
    elapsed_ms: float
    error: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
