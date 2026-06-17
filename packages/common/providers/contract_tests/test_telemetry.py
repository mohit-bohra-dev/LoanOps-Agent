"""Contract tests for the telemetry provider."""

import pytest

from packages.common.providers.telemetry import SpanContext, TelemetryProvider
from packages.common.providers.testing import MockTelemetryProvider


@pytest.fixture
def provider() -> MockTelemetryProvider:
    return MockTelemetryProvider()


class TestTelemetryProviderContract:
    """Every TelemetryProvider implementation must pass these tests."""

    async def test_isinstance(self, provider: TelemetryProvider) -> None:
        assert isinstance(provider, TelemetryProvider)

    async def test_span_yields_span_context(self, provider: TelemetryProvider) -> None:
        async with provider.span("test-op") as ctx:
            assert isinstance(ctx, SpanContext)
            assert ctx.name == "test-op"
            assert isinstance(ctx.trace_id, str)
            assert isinstance(ctx.span_id, str)

    async def test_record_metric(self, provider: MockTelemetryProvider) -> None:
        await provider.record_metric("latency_ms", 42.0, unit="ms")
        assert len(provider.recorded_metrics) == 1
        assert provider.recorded_metrics[0]["name"] == "latency_ms"
        assert provider.recorded_metrics[0]["value"] == 42.0
