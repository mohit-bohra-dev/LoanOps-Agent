"""Contract tests for the audit sink provider."""

import pytest
from packages.common.providers.audit_sink import AuditEvent, AuditSinkProvider
from packages.common.providers.testing import MockAuditSinkProvider


@pytest.fixture
def provider() -> MockAuditSinkProvider:
    return MockAuditSinkProvider()


class TestAuditSinkProviderContract:
    """Every AuditSinkProvider implementation must pass these tests."""

    async def test_isinstance(self, provider: AuditSinkProvider) -> None:
        assert isinstance(provider, AuditSinkProvider)

    async def test_emit_records_event(self, provider: MockAuditSinkProvider) -> None:
        event = AuditEvent(event_id="e1", event_type="chat.request")
        await provider.emit(event)
        assert len(provider.events) == 1
        assert provider.events[0].event_id == "e1"

    async def test_flush_is_callable(self, provider: AuditSinkProvider) -> None:
        await provider.flush()  # Should not raise.

    async def test_multiple_events(self, provider: MockAuditSinkProvider) -> None:
        for i in range(5):
            await provider.emit(AuditEvent(event_id=f"e{i}", event_type="test"))
        assert len(provider.events) == 5
