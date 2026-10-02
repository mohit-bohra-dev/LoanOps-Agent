"""Tests for the Agent API (apps/agent_api).

All provider dependencies are mocked via their factory functions.
No concrete provider classes are imported here.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from packages.common.schemas import AgentTurnOutput

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_provider(name: str = "mock") -> MagicMock:
    """Create a MagicMock that looks like a provider instance."""
    provider = MagicMock()
    provider.__class__.__name__ = f"Mock{name.title()}Provider"
    return provider


def _make_agent_output(**overrides: Any) -> AgentTurnOutput:
    """Create a valid AgentTurnOutput with sensible defaults."""
    defaults: dict[str, Any] = {
        "answer": "Test answer for the rep.",
        "citations": [],
        "tool_calls": [],
        "requires_human_approval": True,
        "confidence": 0.9,
        "refusal": None,
        "escalation": None,
    }
    defaults.update(overrides)
    return AgentTurnOutput(**defaults)


# ---------------------------------------------------------------------------
# Factories that return mock providers for all 10 categories
# ---------------------------------------------------------------------------

_FACTORY_PATHS = {
    "chat": "apps.agent_api.main.get_chat_provider",
    "embedding": "apps.agent_api.main.get_embedding_provider",
    "vector_store": "apps.agent_api.main.get_vector_store_provider",
    "pii": "apps.agent_api.main.get_pii_provider",
    "content_safety": "apps.agent_api.main.get_content_safety_provider",
    "audit_sink": "apps.agent_api.main.get_audit_sink_provider",
    "secrets": "apps.agent_api.main.get_secrets_provider",
    "telemetry": "apps.agent_api.main.get_telemetry_provider",
    "tools_client": "apps.agent_api.main.get_tools_client_provider",
    "prompt_store": "apps.agent_api.main.get_prompt_store_provider",
}


@pytest.fixture()
def mock_all_factories() -> Any:
    """Patch all 10 provider factory functions with mock providers.

    Also patches _PROVIDER_FACTORIES in main so the health endpoint
    uses the same mocked factories.

    Returns a dict mapping provider name -> {factory, provider}.
    """
    mocks: dict[str, Any] = {}
    patchers = []
    patched_registry: list[tuple[str, Any]] = []

    for name, path in _FACTORY_PATHS.items():
        provider = _make_mock_provider(name)
        if name == "pii":

            async def mock_anonymise(text: str) -> MagicMock:
                res = MagicMock()
                res.anonymised = text
                res.entities = []
                return res

            provider.anonymise = AsyncMock(side_effect=mock_anonymise)
        elif name == "content_safety":
            safety_mock_result = MagicMock()
            safety_mock_result.verdict.name = "SAFE"
            safety_mock_result.verdict.value = "SAFE"
            safety_mock_result.reason = ""
            safety_mock_result.score = 0.0
            provider.check = AsyncMock(return_value=safety_mock_result)

        patcher = patch(path, return_value=provider)
        mock_factory = patcher.start()
        patchers.append(patcher)
        mocks[name] = {"factory": mock_factory, "provider": provider}
        patched_registry.append((name, mock_factory))

    # Also patch the _PROVIDER_FACTORIES list so /health iterates our mocks
    registry_patcher = patch("apps.agent_api.main._PROVIDER_FACTORIES", patched_registry)
    registry_patcher.start()
    patchers.append(registry_patcher)

    yield mocks

    for p in patchers:
        p.stop()


def _get_app() -> Any:
    """Import the app fresh (after patches are applied)."""
    from apps.agent_api.main import app

    return app


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_all_healthy(mock_all_factories: dict[str, Any]) -> None:
    """When all factories succeed, /health returns 200 with all providers ok."""
    app = _get_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert len(body["providers"]) == 10
    for name, prov in body["providers"].items():
        assert prov["ok"] is True, f"Provider {name} should be ok"


@pytest.mark.asyncio
async def test_health_one_unhealthy(mock_all_factories: dict[str, Any]) -> None:
    """When one factory raises, /health returns 503."""
    mock_all_factories["chat"]["factory"].side_effect = RuntimeError("Ollama is down")

    app = _get_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert detail["status"] == "unhealthy"
    assert detail["providers"]["chat"]["ok"] is False
    assert "Ollama is down" in detail["providers"]["chat"]["detail"]


# ---------------------------------------------------------------------------
# GET /version
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_version_returns_string() -> None:
    """/version returns a dict with a 'version' key."""
    app = _get_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/version")

    assert resp.status_code == 200
    body = resp.json()
    assert "version" in body
    assert isinstance(body["version"], str)
    assert len(body["version"]) > 0


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_returns_sse(mock_all_factories: dict[str, Any]) -> None:
    """POST /chat streams a single SSE data event with the agent output."""
    expected_output = _make_agent_output()

    audit_provider = mock_all_factories["audit_sink"]["provider"]
    audit_provider.emit = AsyncMock()

    with patch(
        "apps.agent_api.main.run_agent_turn",
        new_callable=AsyncMock,
        return_value=expected_output,
    ):
        app = _get_app()
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/chat",
                json={"message": "Loan 100245 escrow question", "rep_id": "rep-001"},
            )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    # Parse SSE body
    body = resp.text
    assert body.startswith("data: ")
    json_str = body.replace("data: ", "").strip()
    data = json.loads(json_str)

    assert data["answer"] == "Test answer for the rep."
    assert data["requires_human_approval"] is True
    assert data["confidence"] == 0.9


@pytest.mark.asyncio
async def test_chat_writes_audit_record(mock_all_factories: dict[str, Any]) -> None:
    """POST /chat emits an audit event with the correct schema."""
    expected_output = _make_agent_output()

    audit_provider = mock_all_factories["audit_sink"]["provider"]
    audit_provider.emit = AsyncMock()

    with patch(
        "apps.agent_api.main.run_agent_turn",
        new_callable=AsyncMock,
        return_value=expected_output,
    ):
        app = _get_app()
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/chat",
                json={
                    "message": "Test prompt",
                    "rep_id": "rep-42",
                    "session_id": "sess-99",
                },
            )

    # Verify audit was emitted (1 for PII, 1 for Safety, 1 for Turn)
    assert audit_provider.emit.call_count == 3
    audit_event = audit_provider.emit.call_args_list[-1][0][0]

    assert audit_event.event_type == "agent_api.chat.turn"
    assert audit_event.user_id == "rep-42"
    assert audit_event.session_id == "sess-99"

    payload = audit_event.payload
    assert "turn_id" in payload
    assert payload["rep_id"] == "rep-42"
    assert payload["prompt_redacted"] == "Test prompt"
    assert "latency_ms" in payload
    assert "providers_bound" in payload
    assert isinstance(payload["providers_bound"], dict)


@pytest.mark.asyncio
async def test_chat_handles_agent_error(mock_all_factories: dict[str, Any]) -> None:
    """POST /chat returns an error SSE event when the agent raises."""
    audit_provider = mock_all_factories["audit_sink"]["provider"]
    audit_provider.emit = AsyncMock()

    with patch(
        "apps.agent_api.main.run_agent_turn",
        new_callable=AsyncMock,
        side_effect=RuntimeError("LLM timeout"),
    ):
        app = _get_app()
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/chat",
                json={"message": "test"},
            )

    assert resp.status_code == 200  # SSE always returns 200
    body = resp.text
    json_str = body.replace("data: ", "").strip()
    data = json.loads(json_str)
    assert "error" in data
    assert "LLM timeout" in data["error"]


# ---------------------------------------------------------------------------
# Provider abstraction gate — no concrete imports
# ---------------------------------------------------------------------------

# The pattern we check for — split to avoid self-matching in this test file
_IMPORT_PATTERN = "from " + "provider_" + "contracts"


def test_no_concrete_provider_imports() -> None:
    """Verify apps/agent_api/ source has no direct imports from the
    concrete provider_contracts package.

    This mirrors the CI grep gate: no concrete provider classes imported
    outside packages/common/providers/.
    """
    import pathlib
    import re

    pattern = re.compile(_IMPORT_PATTERN)
    source_dir = pathlib.Path("projects/LoanOps.AgentApi/apps/agent_api")
    matches: list[tuple[pathlib.Path, str]] = []

    for f in source_dir.rglob("*.py"):
        # Skip test files — they may reference the pattern in strings
        if "test_" in f.name:
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            if pattern.search(line):
                matches.append((f, line))

    assert len(matches) == 0, (
        f"Found {len(matches)} concrete provider imports in apps/agent_api/:\n"
        + "\n".join(f"  {f}: {line}" for f, line in matches)
    )


def test_no_direct_env_access() -> None:
    """Verify apps/agent_api/ has no direct os.environ / os.getenv calls."""
    import pathlib
    import re

    pattern = re.compile(r"os\.environ|os\.getenv")
    source_dir = pathlib.Path("projects/LoanOps.AgentApi/apps/agent_api")
    matches: list[tuple[pathlib.Path, str]] = []

    for f in source_dir.rglob("*.py"):
        if "test_" in f.name:
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            if pattern.search(line):
                matches.append((f, line))

    assert len(matches) == 0, (
        f"Found {len(matches)} direct env access in apps/agent_api/:\n"
        + "\n".join(f"  {f}: {line}" for f, line in matches)
    )
