"""P5 extract: cache key, grounding, PII, Confluence refuse, cache hit."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.graph_rag.artifact import refuse_confluence_repo_write
from packages.graph_rag.cache import cache_key, read_cache, write_cache
from packages.graph_rag.extract import extract_chunk
from packages.graph_rag.grounding import ground_extraction
from packages.graph_rag.pii_scrub import scrub_extraction
from packages.graph_rag.schema import PROMPT_VERSION, SCHEMA_VERSION


def test_cache_key_deterministic() -> None:
    a = cache_key(
        "hello",
        model_id="m1",
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
    )
    b = cache_key(
        "hello",
        model_id="m1",
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
    )
    c = cache_key(
        "hello",
        model_id="m2",
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
    )
    assert a == b
    assert a != c


def test_grounding_keeps_names_in_text() -> None:
    text = "Disaster forbearance applies in Florida after FEMA declaration."
    ents = [
        {"name": "forbearance", "type": "policy"},
        {"name": "Florida", "type": "state"},
        {"name": "MadeUpPolicy", "type": "policy"},
    ]
    rels = [
        {"source": "forbearance", "target": "Florida", "type": "applies_in"},
        {"source": "forbearance", "target": "Texas", "type": "applies_in"},
    ]
    ke, kr, dropped = ground_extraction(text, ents, rels)
    names = {e["name"] for e in ke}
    assert "forbearance" in names
    assert "Florida" in names
    assert "MadeUpPolicy" not in names
    assert len(kr) == 1
    assert any(d["kind"] == "entity_ungrounded" for d in dropped)


def test_pii_scrub_drops_personish_keeps_state() -> None:
    ents = [
        {"name": "John Smith", "type": "person"},
        {"name": "Florida", "type": "state"},
        {"name": "SCRA", "type": "law"},
    ]
    rels = [
        {"source": "John Smith", "target": "Florida", "type": "lives"},
        {"source": "SCRA", "target": "Florida", "type": "covers"},
    ]
    ke, kr, dropped = scrub_extraction(ents, rels)
    names = {e["name"] for e in ke}
    assert "John Smith" not in names
    assert "Florida" in names
    assert "SCRA" in names
    assert len(kr) == 1
    assert any(d["kind"] == "pii_entity" for d in dropped)


def test_refuse_confluence_repo_write() -> None:
    with pytest.raises(SystemExit, match="refuse"):
        refuse_confluence_repo_write(sop_source="confluence", write_repo_artifact=True)
    refuse_confluence_repo_write(sop_source="local", write_repo_artifact=True)
    refuse_confluence_repo_write(sop_source="confluence", write_repo_artifact=False)


@pytest.mark.asyncio
async def test_extract_chunk_uses_cache(tmp_path: Path) -> None:
    chat = MagicMock()
    chat.complete = AsyncMock(
        return_value=MagicMock(
            content='{"entities":[{"name":"forbearance","type":"policy"}],'
            '"relations":[]}'
        )
    )
    text = "Standard forbearance may pause payments."
    e1, r1, g1, hit1 = await extract_chunk(
        chunk_id="c1",
        path="hardship/x.md",
        content=text,
        model_id="test-model",
        chat=chat,
        cache_dir=tmp_path,
    )
    assert hit1 is False
    assert chat.complete.await_count == 1
    assert any(e["name"] == "forbearance" for e in e1)

    e2, _r2, _g2, hit2 = await extract_chunk(
        chunk_id="c1",
        path="hardship/x.md",
        content=text,
        model_id="test-model",
        chat=chat,
        cache_dir=tmp_path,
    )
    assert hit2 is True
    assert chat.complete.await_count == 1
    assert e2 == e1

    # Twin-checkout: same key file readable
    key = cache_key(
        text,
        model_id="test-model",
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
    )
    assert read_cache(tmp_path, key) is not None


def test_write_cache_roundtrip(tmp_path: Path) -> None:
    key = cache_key(
        "x",
        model_id="m",
        prompt_version="1",
        schema_version="1",
    )
    write_cache(tmp_path, key, {"entities": [], "relations": []})
    assert read_cache(tmp_path, key) == {"entities": [], "relations": []}
