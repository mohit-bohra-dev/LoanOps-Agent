"""Provider layer — ABCs (re-exported from provider_contracts) + factory functions.

Application code should import:
- **ABCs / DTOs** from the sibling protocol modules (``chat``, ``embedding``, …)
  or from this ``__init__`` module.
- **Factory functions** (``get_chat_provider()``, …) from ``factory`` or this module.
- **Mock implementations** from ``testing`` only inside test code.

No concrete provider classes are re-exported here.
"""

# ── ABCs (re-exports) ────────────────────────────────────────────────────
from packages.common.providers.audit_sink import AuditEvent, AuditSinkProvider
from packages.common.providers.base import (
    ProviderCallEvent,
    ProviderConfigError,
    ProviderError,
    ProviderHealth,
)
from packages.common.providers.chat import (
    ChatProvider,
    LLMMessage,
    LLMResponse,
    ToolCallRequest,
    ToolDefinition,
)
from packages.common.providers.content_safety import (
    ContentSafetyProvider,
    SafetyResult,
    SafetyVerdict,
)
from packages.common.providers.embedding import EmbeddingProvider, EmbeddingResult

# ── Factory functions ────────────────────────────────────────────────────
from packages.common.providers.factory import (
    get_audit_sink_provider,
    get_chat_provider,
    get_content_safety_provider,
    get_embedding_provider,
    get_pii_provider,
    get_prompt_store_provider,
    get_secrets_provider,
    get_session_store_provider,
    get_telemetry_provider,
    get_tools_client_provider,
    get_vector_store_provider,
)
from packages.common.providers.pii import PiiProvider, PiiResult, PiiSpan
from packages.common.providers.prompt_store import PromptStoreProvider
from packages.common.providers.secrets import SecretsProvider
from packages.common.providers.session_store import (
    ConversationSession,
    ConversationTurn,
)
from packages.common.providers.telemetry import SpanContext, TelemetryProvider
from packages.common.providers.tools_client import ToolCall, ToolResult, ToolsClientProvider
from packages.common.providers.vector_store import (
    SearchResult,
    VectorDocument,
    VectorStoreProvider,
)

__all__ = [
    # Base helpers
    "ProviderHealth",
    "ProviderError",
    "ProviderConfigError",
    "ProviderCallEvent",
    # ABCs
    "ChatProvider",
    "LLMMessage",
    "LLMResponse",
    "ToolDefinition",
    "ToolCallRequest",
    "EmbeddingProvider",
    "EmbeddingResult",
    "VectorStoreProvider",
    "VectorDocument",
    "SearchResult",
    "PiiProvider",
    "PiiResult",
    "PiiSpan",
    "ContentSafetyProvider",
    "SafetyResult",
    "SafetyVerdict",
    "AuditSinkProvider",
    "AuditEvent",
    "SecretsProvider",
    "TelemetryProvider",
    "SpanContext",
    "ToolsClientProvider",
    "ToolCall",
    "ToolResult",
    "PromptStoreProvider",
    "ConversationSession",
    "ConversationTurn",
    # Factories
    "get_chat_provider",
    "get_embedding_provider",
    "get_vector_store_provider",
    "get_pii_provider",
    "get_content_safety_provider",
    "get_audit_sink_provider",
    "get_secrets_provider",
    "get_telemetry_provider",
    "get_tools_client_provider",
    "get_prompt_store_provider",
    "get_session_store_provider",
]
