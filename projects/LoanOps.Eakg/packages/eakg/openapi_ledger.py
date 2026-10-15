"""Build gap-ledger items from ApiIndex mismatch report (ADR-029 OpenAPI source)."""

from __future__ import annotations

from typing import Any

from packages.eakg.gap_ledger import LedgerItem, from_openapi_join_report


def ledger_from_api_index_report(
    report: dict[str, Any],
    *,
    repository_id: str = "",
) -> list[LedgerItem]:
    """Thin wrapper so OpenAPI join gaps have a named entry point."""
    return from_openapi_join_report(report, repository_id=repository_id)
