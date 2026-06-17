"""PII provider protocol — re-exports from provider_contracts."""

from provider_contracts.pii import AbstractPiiProvider as PiiProvider
from provider_contracts.pii import PiiResult, PiiSpan

__all__ = ["PiiProvider", "PiiResult", "PiiSpan"]
