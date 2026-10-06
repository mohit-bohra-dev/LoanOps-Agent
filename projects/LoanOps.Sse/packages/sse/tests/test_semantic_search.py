"""OpenAPI catalog search via embeddings (query has no keyword overlap)."""

from __future__ import annotations

import pytest
from packages.sse.catalog import parse_openapi_document, search_operations
from packages.sse.fixture import FIXTURE_OPENAPI
from packages.sse.semantic import search_operations_semantic


async def _stub_embed(text: str) -> list[float]:
    t = text.lower()
    schedule = 1.0 if any(w in t for w in ("payment", "schedule", "installment")) else 0.0
    loan_only = 1.0 if "loan" in t and schedule == 0.0 else 0.0
    return [schedule, loan_only]


@pytest.mark.asyncio
async def test_semantic_ranks_installment_to_payment_schedules() -> None:
    ops = parse_openapi_document(FIXTURE_OPENAPI, "fixture", "Fixture", "https://fixture.local")
    query = "when is the next installment due"
    kw = search_operations(ops, query, limit=5)
    assert all("Payment" not in o.path for o in kw)

    cache: dict[str, list[float]] = {}
    hits = await search_operations_semantic(ops, query, embed=_stub_embed, cache=cache, limit=5)
    assert hits
    assert hits[0].operation_id == "getPaymentSchedules"
    assert cache
