"""Eval feedback / health / promote API tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from packages.eval.traces import build_agent_trace, persist_agent_trace


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.asyncio
async def test_feedback_and_health(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_STORE__JSONL_DIR", str(tmp_path))
    from packages.common.settings import get_settings

    get_settings.cache_clear()

    persist_agent_trace(
        build_agent_trace(trace_id="trace-xyz", user_query="q", answer="a")
    )

    from apps.agent_api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        bad = await client.post(
            "/eval/feedback",
            json={"trace_id": "trace-xyz", "label": "fail"},
        )
        assert bad.status_code == 422

        ok = await client.post(
            "/eval/feedback",
            json={
                "trace_id": "trace-xyz",
                "label": "fail",
                "primary_category": "incorrect_answer",
                "severity": "major",
                "root_component": "generation",
                "reviewer": "tester",
                "model_critique": "Polite but factually wrong date.",
                "model_outcome": "good",
                "suggested_answer": "Payment is due November 20.",
                "recommended_action": "improve_prompt",
                "flags": ["hallucination"],
            },
        )
        assert ok.status_code == 200

        tr = await client.get("/eval/traces/trace-xyz")
        assert tr.status_code == 200
        assert tr.json()["user_query"] == "q"

        matrix = await client.get("/eval/matrix")
        assert matrix.status_code == 200
        body = matrix.json()
        assert "rows" in body
        assert "agreement_rate" in body
        ids = {r["trace_id"] for r in body["rows"]}
        assert "trace-xyz" in ids
        row = next(r for r in body["rows"] if r["trace_id"] == "trace-xyz")
        assert row["model_outcome"] == "good"
        assert row["human_outcome"] == "bad"
        assert row["alignment"] == 0
        assert row["recommended_action"] == "improve_prompt"

        health = await client.get("/eval/health")
        assert health.status_code == 200
        assert health.json()["ops_separate"] is True

        promo = await client.post(
            "/eval/promote",
            json={"trace_id": "trace-xyz", "reviewer": "tester"},
        )
        assert promo.status_code == 200
        assert promo.json()["draft_registry_rows"] >= 1

    get_settings.cache_clear()
