"""Contract tests for the PII provider."""

import pytest

from packages.common.providers.pii import PiiProvider, PiiResult
from packages.common.providers.testing import MockPiiProvider


@pytest.fixture
def provider() -> PiiProvider:
    return MockPiiProvider()


class TestPiiProviderContract:
    """Every PiiProvider implementation must pass these tests."""

    async def test_isinstance(self, provider: PiiProvider) -> None:
        assert isinstance(provider, PiiProvider)

    async def test_anonymise_returns_pii_result(self, provider: PiiProvider) -> None:
        result = await provider.anonymise("John Doe called at 555-1234")
        assert isinstance(result, PiiResult)
        assert isinstance(result.original, str)
        assert isinstance(result.anonymised, str)
        assert isinstance(result.entities, list)

    async def test_anonymise_preserves_original(self, provider: PiiProvider) -> None:
        text = "Some text with no PII"
        result = await provider.anonymise(text)
        assert result.original == text
