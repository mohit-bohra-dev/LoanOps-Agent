"""OpenAPI catalog search via embeddings (query has no keyword overlap)."""

from __future__ import annotations

from pathlib import Path

import pytest
from packages.sse.catalog import parse_openapi_document, search_operations
from packages.sse.fixture import FIXTURE_OPENAPI
from packages.sse.semantic import (
    OpenApiEmbeddingEntry,
    load_openapi_index,
    operation_text,
    save_openapi_index,
    search_operations_semantic,
    search_operations_with_embeddings,
    seed_cache_from_index,
    text_hash,
)


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


def test_openapi_sidecar_round_trip(tmp_path: Path) -> None:
    ops = parse_openapi_document(FIXTURE_OPENAPI, "fixture", "Fixture", "https://fixture.local")
    entries: dict[str, OpenApiEmbeddingEntry] = {}
    for op in ops:
        text = operation_text(op)
        entries[op.id] = OpenApiEmbeddingEntry(
            id=op.id,
            text=text,
            text_hash=text_hash(text),
            vector=[1.0, 0.0],
        )
    path = tmp_path / "openapi_embeddings.json"
    save_openapi_index(path, entries)
    loaded = load_openapi_index(path)
    assert set(loaded) == set(entries)
    assert loaded[ops[0].id].text_hash == entries[ops[0].id].text_hash


def test_stale_hash_not_seeded(tmp_path: Path) -> None:
    ops = parse_openapi_document(FIXTURE_OPENAPI, "fixture", "Fixture", "https://fixture.local")
    op = ops[0]
    text = operation_text(op)
    entries = {
        op.id: OpenApiEmbeddingEntry(
            id=op.id,
            text=text,
            text_hash="deadbeefdeadbeef",
            vector=[9.0, 9.0],
        )
    }
    path = tmp_path / "openapi_embeddings.json"
    save_openapi_index(path, entries)
    index = load_openapi_index(path)
    cache: dict[str, list[float]] = {}
    hashes: dict[str, str] = {}
    seed_cache_from_index(ops, index, cache, hashes=hashes)
    assert op.id not in cache
    assert hashes[op.id] == text_hash(text)


@pytest.mark.asyncio
async def test_embed_failure_returns_keyword_flag() -> None:
    ops = parse_openapi_document(FIXTURE_OPENAPI, "fixture", "Fixture", "https://fixture.local")

    async def _boom(_text: str) -> list[float]:
        raise RuntimeError("embed down")

    hits, used = await search_operations_with_embeddings(
        ops, "loan", cache={}, limit=5, embed=_boom
    )
    assert used is False
    assert hits
