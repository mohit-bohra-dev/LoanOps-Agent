"""Contract tests for the prompt store provider."""

import pytest

from packages.common.providers.prompt_store import PromptStoreProvider
from packages.common.providers.testing import MockPromptStoreProvider


@pytest.fixture
def provider() -> MockPromptStoreProvider:
    return MockPromptStoreProvider(
        prompts={
            "agent.system": "You are a helpful assistant.",
            "tool.summary": "Summarise the tool output.",
        }
    )


class TestPromptStoreProviderContract:
    """Every PromptStoreProvider implementation must pass these tests."""

    async def test_isinstance(self, provider: PromptStoreProvider) -> None:
        assert isinstance(provider, PromptStoreProvider)

    async def test_get_existing_prompt(self, provider: PromptStoreProvider) -> None:
        template = await provider.get("agent.system")
        assert isinstance(template, str)
        assert len(template) > 0

    async def test_get_missing_prompt_raises(self, provider: PromptStoreProvider) -> None:
        with pytest.raises(KeyError):
            await provider.get("nonexistent.prompt")

    async def test_list_names(self, provider: PromptStoreProvider) -> None:
        names = await provider.list_names()
        assert isinstance(names, list)
        assert "agent.system" in names
        assert "tool.summary" in names
