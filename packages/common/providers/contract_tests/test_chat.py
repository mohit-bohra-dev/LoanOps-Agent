"""Contract tests for the chat (LLM) provider."""

import pytest

from packages.common.providers.chat import ChatProvider, LLMMessage, LLMResponse
from packages.common.providers.testing import MockLLMProvider


@pytest.fixture
def provider() -> ChatProvider:
    return MockLLMProvider()


class TestChatProviderContract:
    """Every ChatProvider implementation must pass these tests."""

    async def test_isinstance(self, provider: ChatProvider) -> None:
        assert isinstance(provider, ChatProvider)

    async def test_complete_returns_llm_response(self, provider: ChatProvider) -> None:
        result = await provider.complete("Hello")
        assert isinstance(result, LLMResponse)
        assert isinstance(result.content, str)
        assert len(result.content) > 0

    async def test_chat_returns_llm_response(self, provider: ChatProvider) -> None:
        messages = [LLMMessage(role="user", content="Hi")]
        result = await provider.chat(messages)
        assert isinstance(result, LLMResponse)
        assert isinstance(result.content, str)

    async def test_stream_yields_strings(self, provider: ChatProvider) -> None:
        messages = [LLMMessage(role="user", content="Hi")]
        chunks: list[str] = []
        async for chunk in provider.stream(messages):
            chunks.append(chunk)
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)
