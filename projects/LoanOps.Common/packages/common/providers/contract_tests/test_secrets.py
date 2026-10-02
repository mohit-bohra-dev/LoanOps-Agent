"""Contract tests for the secrets provider."""

import pytest
from packages.common.providers.secrets import SecretsProvider
from packages.common.providers.testing import MockSecretsProvider


@pytest.fixture
def provider() -> MockSecretsProvider:
    return MockSecretsProvider(secrets={"API_KEY": "test-key-123"})


class TestSecretsProviderContract:
    """Every SecretsProvider implementation must pass these tests."""

    async def test_isinstance(self, provider: SecretsProvider) -> None:
        assert isinstance(provider, SecretsProvider)

    async def test_get_existing_secret(self, provider: SecretsProvider) -> None:
        value = await provider.get("API_KEY")
        assert value == "test-key-123"

    async def test_get_missing_secret_raises(self, provider: SecretsProvider) -> None:
        with pytest.raises(KeyError):
            await provider.get("NONEXISTENT")

    async def test_get_or_default_existing(self, provider: SecretsProvider) -> None:
        value = await provider.get_or_default("API_KEY", "fallback")
        assert value == "test-key-123"

    async def test_get_or_default_missing(self, provider: SecretsProvider) -> None:
        value = await provider.get_or_default("NONEXISTENT", "fallback")
        assert value == "fallback"
