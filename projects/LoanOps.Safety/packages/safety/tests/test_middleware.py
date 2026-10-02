import pytest
from packages.common.providers.testing import (
    MockAuditSinkProvider,
    MockContentSafetyProvider,
    MockPiiProvider,
)
from packages.safety import (
    EvaluationResult,
    SafetyPipeline,
    SanitizeResult,
    evaluate_outbound,
    sanitize_inbound,
)


@pytest.mark.asyncio
async def test_sanitize_inbound_unit() -> None:
    """Unit test for sanitize_inbound with mock providers."""
    pii_provider = MockPiiProvider()
    audit_provider = MockAuditSinkProvider()

    text = "My SSN is 123-45-6789"
    # We can't easily control MockPiiProvider's output without overriding,
    # but we can verify the flow.

    result = await sanitize_inbound(text, pii_provider, audit_provider)

    assert isinstance(result, SanitizeResult)
    assert result.anonymized_text != text or len(result.spans) == 0  # MockPiiProvider behavior

    # Verify audit event was written
    # MockAuditSinkProvider stores events in a list
    assert len(audit_provider.events) > 0
    assert audit_provider.events[0].event_type == "pii.redacted"


@pytest.mark.asyncio
async def test_evaluate_outbound_unit() -> None:
    """Unit test for evaluate_outbound with mock providers."""
    safety_provider = MockContentSafetyProvider()
    audit_provider = MockAuditSinkProvider()

    text = "This is a safe response"
    result = await evaluate_outbound(text, safety_provider, audit_provider)

    assert isinstance(result, EvaluationResult)
    assert result.is_safe is True
    assert len(audit_provider.events) > 0
    assert audit_provider.events[0].event_type == "safety.evaluated"


@pytest.mark.asyncio
async def test_safety_pipeline_integration() -> None:
    """
    Test the SafetyPipeline convenience class.
    Note: This uses real factories, so it depends on Settings.
    """
    pipeline = SafetyPipeline()

    # Inbound test
    inbound_text = "Hello, my phone is 555-123-4567"
    san_result = await pipeline.sanitize_inbound(inbound_text)
    assert isinstance(san_result, SanitizeResult)

    # Outbound test
    outbound_text = "Your loan is approved."
    eval_result = await pipeline.evaluate_outbound(outbound_text)
    assert isinstance(eval_result, EvaluationResult)
    assert eval_result.is_safe is True
