"""Best-effort telemetry helpers for api_index / sse metrics (spec §9.5)."""

from __future__ import annotations

from typing import Any


async def record_metric(
    name: str,
    value: float,
    *,
    unit: str = "1",
    attributes: dict[str, Any] | None = None,
) -> None:
    """Record a metric; never raise into callers."""
    try:
        from packages.common.providers.factory import get_telemetry_provider

        await get_telemetry_provider().record_metric(
            name, value, unit=unit, attributes=attributes
        )
    except Exception:  # noqa: BLE001 — telemetry must not break request path
        return
