"""Contract tests for the content safety provider."""

import pytest
from packages.common.providers.content_safety import (
    ContentSafetyProvider,
    SafetyResult,
    SafetyVerdict,
)
from packages.common.providers.testing import MockContentSafetyProvider


@pytest.fixture
def provider() -> ContentSafetyProvider:
    return MockContentSafetyProvider()


class TestContentSafetyProviderContract:
    """Every ContentSafetyProvider implementation must pass these tests."""

    async def test_isinstance(self, provider: ContentSafetyProvider) -> None:
        assert isinstance(provider, ContentSafetyProvider)

    async def test_check_returns_safety_result(self, provider: ContentSafetyProvider) -> None:
        result = await provider.check("This is a normal message")
        assert isinstance(result, SafetyResult)
        assert isinstance(result.verdict, SafetyVerdict)
        assert isinstance(result.score, float)
        assert 0.0 <= result.score <= 1.0

    async def test_safe_content_passes(self, provider: ContentSafetyProvider) -> None:
        result = await provider.check("Hello, how can I help?")
        assert result.verdict == SafetyVerdict.SAFE
