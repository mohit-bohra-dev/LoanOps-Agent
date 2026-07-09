"""Provider factory functions â€” the DI layer.

Each ``get_*_provider()`` reads from ``Settings()`` and returns the
appropriate concrete implementation imported from ``provider_contracts``.

These are the **only** functions in LoanOps Agent_Demos that import concrete
provider classes.  Everything else programmes against the ABCs re-exported
from the sibling protocol modules.
"""

from __future__ import annotations

from functools import lru_cache

# ---------------------------------------------------------------------------
# Type imports (ABCs) â€” for return annotations only
# ---------------------------------------------------------------------------
from provider_contracts.audit_sink import AbstractAuditSinkProvider
from provider_contracts.content_safety import AbstractContentSafetyProvider
from provider_contracts.embedding import AbstractEmbeddingProvider
from provider_contracts.llm import AbstractLLMProvider
from provider_contracts.pii import AbstractPiiProvider
from provider_contracts.prompt_store import AbstractPromptStoreProvider
from provider_contracts.reranker import AbstractRerankerProvider
from provider_contracts.secrets import AbstractSecretsProvider
from provider_contracts.telemetry import AbstractTelemetryProvider
from provider_contracts.tools_client import AbstractToolsClientProvider
from provider_contracts.vector_store import AbstractVectorStoreProvider

from packages.common.providers.base import ProviderConfigError
from packages.common.providers.loan_data import AbstractLoanDataProvider
from packages.common.providers.policy_source import AbstractPolicySourceProvider
from packages.common.providers.session_store import AbstractSessionStoreProvider
from packages.common.settings import Settings


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    """Return a cached Settings instance — reads .env exactly once per process."""
    return Settings()


# ── Data Providers ─────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_loan_data_provider() -> AbstractLoanDataProvider:
    """Return the configured loan data provider."""
    cfg = _get_settings()
    if cfg.data.mode == "real":
        from packages.common.providers.loan_data import RestApiLoanProvider
        return RestApiLoanProvider(cfg.data.loan_api)
    from packages.common.providers.loan_data import JsonFileLoanProvider
    return JsonFileLoanProvider()


@lru_cache(maxsize=1)
def get_policy_source_provider() -> AbstractPolicySourceProvider:
    """Return the configured policy source provider."""
    cfg = _get_settings()
    if cfg.data.mode == "real":
        from packages.common.providers.policy_source import ConfluencePolicyProvider
        return ConfluencePolicyProvider(cfg.data.confluence)
    from packages.common.providers.policy_source import LocalFilePolicyProvider
    return LocalFilePolicyProvider()


# ── Chat / LLM ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_chat_provider() -> AbstractLLMProvider:
    """Return the configured chat (LLM) provider."""
    cfg = _get_settings()
    if cfg.llm.provider == "ollama":
        from provider_contracts.llm.ollama import OllamaProvider

        return OllamaProvider(
            base_url=cfg.llm.ollama.base_url,
            model=cfg.llm.ollama.model_fast,
        )
    if cfg.llm.provider == "aoai":
        from provider_contracts.llm.azure_openai import AzureOpenAIProvider

        if cfg.llm.aoai is None:
            raise ProviderConfigError("LLM__AOAI config section is required for 'aoai' provider")
        return AzureOpenAIProvider(
            endpoint=cfg.llm.aoai.endpoint,
            api_key="",  # Managed Identity in production; placeholder locally.
            deployment=cfg.llm.aoai.deployment_accurate,
            api_version=cfg.llm.aoai.api_version,
        )
    if cfg.llm.provider == "openai":
        from provider_contracts.llm.openai import OpenAIProvider

        if cfg.llm.openai is None:
            raise ProviderConfigError(
                "LLM__OPENAI config section is required for 'openai' provider"
            )
        return OpenAIProvider(
            api_key=cfg.llm.openai.api_key,
            model=cfg.llm.openai.model,
            base_url=cfg.llm.openai.base_url,
        )
    if cfg.llm.provider == "bedrock":
        from provider_contracts.llm.bedrock import BedrockProvider

        if cfg.llm.bedrock is None:
            raise ProviderConfigError(
                "LLM__BEDROCK config section is required for 'bedrock' provider"
            )
        return BedrockProvider(
            model_id=cfg.llm.bedrock.model_id,
            region=cfg.llm.bedrock.region,
            api_key=cfg.llm.bedrock.api_key,
            access_key_id=cfg.llm.bedrock.access_key_id,
            secret_access_key=cfg.llm.bedrock.secret_access_key,
            session_token=cfg.llm.bedrock.session_token,
        )
    if cfg.llm.provider == "gemini":
        from provider_contracts.llm.gemini import GeminiProvider

        if cfg.llm.gemini is None:
            raise ProviderConfigError(
                "LLM__GEMINI config section is required for 'gemini' provider"
            )
        return GeminiProvider(
            api_key=cfg.llm.gemini.api_key,
            model=cfg.llm.gemini.model,
        )
    raise ProviderConfigError(f"Unknown chat provider: {cfg.llm.provider}")


# â”€â”€ Embedding â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
@lru_cache(maxsize=1)
def get_embedding_provider() -> AbstractEmbeddingProvider:
    """Return the configured embedding provider."""
    cfg = _get_settings()
    if cfg.embedding.provider == "local_bge":
        from provider_contracts.embedding.sentence_transformers import (
            SentenceTransformerEmbeddingProvider,
        )

        # this is very slow is it GPU or CPU ?
        return SentenceTransformerEmbeddingProvider(model_name="BAAI/bge-small-en-v1.5")
    if cfg.embedding.provider == "aoai":
        from provider_contracts.embedding.azure_openai import AzureOpenAIEmbeddingProvider

        if cfg.embedding.aoai is None:
            raise ProviderConfigError(
                "EMBEDDING__AOAI config section is required for 'aoai' provider"
            )
        return AzureOpenAIEmbeddingProvider(
            endpoint=cfg.embedding.aoai.endpoint,
            api_key="",  # Managed Identity in production.
            deployment=cfg.embedding.aoai.deployment,
            api_version=cfg.embedding.aoai.api_version,
        )
    if cfg.embedding.provider == "gemini":
        from provider_contracts.embedding.gemini import GeminiEmbeddingProvider

        if cfg.embedding.gemini is None:
            raise ProviderConfigError(
                "EMBEDDING__GEMINI config section is required for 'gemini' provider"
            )
        return GeminiEmbeddingProvider(
            api_key=cfg.embedding.gemini.api_key,
            model=cfg.embedding.gemini.model,
        )
    raise ProviderConfigError(f"Unknown embedding provider: {cfg.embedding.provider}")


# â”€â”€ Vector Store â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
@lru_cache(maxsize=1)
def get_vector_store_provider() -> AbstractVectorStoreProvider:
    """Return the configured vector store provider."""
    cfg = _get_settings()
    if cfg.vector_store.provider == "qdrant":
        from provider_contracts.vector_store.qdrant import QdrantVectorStoreProvider

        return QdrantVectorStoreProvider(
            url=cfg.vector_store.qdrant.url,
            collection=cfg.vector_store.qdrant.collection,
            path=cfg.vector_store.qdrant.path,
        )
    if cfg.vector_store.provider == "ai_search":
        from provider_contracts.vector_store.azure_ai_search import (
            AzureAISearchVectorStoreProvider,
        )

        if cfg.vector_store.ai_search is None:
            raise ProviderConfigError(
                "VECTOR_STORE__AI_SEARCH config section is required for 'ai_search' provider"
            )
        return AzureAISearchVectorStoreProvider(
            endpoint=cfg.vector_store.ai_search.endpoint,
            api_key=cfg.vector_store.ai_search.api_key,
            index_name=cfg.vector_store.ai_search.index,
            embedding_dimensions=cfg.vector_store.ai_search.dimensions,
        )
    raise ProviderConfigError(f"Unknown vector store provider: {cfg.vector_store.provider}")


# â”€â”€ PII â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
@lru_cache(maxsize=1)
def get_pii_provider() -> AbstractPiiProvider:
    """Return the configured PII provider."""
    cfg = _get_settings()
    if cfg.pii.provider == "presidio":
        from provider_contracts.pii.presidio import PresidioPiiProvider

        return PresidioPiiProvider()
    if cfg.pii.provider == "stub":
        from provider_contracts.pii.mock import MockPiiProvider

        return MockPiiProvider()
    raise ProviderConfigError(f"Unknown PII provider: {cfg.pii.provider}")


# â”€â”€ Content Safety â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
@lru_cache(maxsize=1)
def get_content_safety_provider() -> AbstractContentSafetyProvider:
    """Return the configured content safety provider."""
    cfg = _get_settings()
    if cfg.safety.provider == "stub":
        from provider_contracts.content_safety.rule_based import (
            RuleBasedContentSafetyProvider,
        )

        return RuleBasedContentSafetyProvider()
    if cfg.safety.provider == "azure":
        raise ProviderConfigError(
            "Azure Content Safety provider not yet implemented in provider_contracts"
        )
    raise ProviderConfigError(f"Unknown safety provider: {cfg.safety.provider}")


# â”€â”€ Audit Sink â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â
@lru_cache(maxsize=1)
def get_audit_sink_provider() -> AbstractAuditSinkProvider:
    """Return the configured audit sink provider."""
    cfg = _get_settings()
    if cfg.audit.sink == "jsonl":
        from provider_contracts.audit_sink.jsonl import JsonlAuditSinkProvider

        return JsonlAuditSinkProvider(directory=cfg.audit.jsonl_dir)
    if cfg.audit.sink == "appinsights":
        raise ProviderConfigError(
            "App Insights audit sink not yet implemented in provider_contracts"
        )
    raise ProviderConfigError(f"Unknown audit sink: {cfg.audit.sink}")


# â”€â”€ Secrets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â
@lru_cache(maxsize=1)
def get_secrets_provider() -> AbstractSecretsProvider:
    """Return the configured secrets provider."""
    cfg = _get_settings()
    if cfg.secrets.provider == "env":
        from provider_contracts.secrets.env import EnvSecretsProvider

        return EnvSecretsProvider()
    if cfg.secrets.provider == "keyvault":
        raise ProviderConfigError(
            "Key Vault secrets provider not yet implemented in provider_contracts"
        )
    raise ProviderConfigError(f"Unknown secrets provider: {cfg.secrets.provider}")


# â”€â”€ Telemetry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
@lru_cache(maxsize=1)
def get_telemetry_provider() -> AbstractTelemetryProvider:
    """Return the configured telemetry provider."""
    cfg = _get_settings()
    if cfg.telemetry.provider == "console":
        from provider_contracts.telemetry.console import ConsoleTelemetryProvider

        return ConsoleTelemetryProvider()
    if cfg.telemetry.provider == "langfuse":
        from provider_contracts.telemetry.langfuse import LangfuseTelemetryProvider

        return LangfuseTelemetryProvider(
            public_key=cfg.telemetry.langfuse.public_key,
            secret_key=cfg.telemetry.langfuse.secret_key,
            host=cfg.telemetry.langfuse.host,
        )
    if cfg.telemetry.provider == "appinsights":

        raise ProviderConfigError(
            "App Insights telemetry provider not yet implemented in provider_contracts"
        )
    raise ProviderConfigError(f"Unknown telemetry provider: {cfg.telemetry.provider}")


# â”€â”€ Tools Client â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
@lru_cache(maxsize=1)
def get_tools_client_provider() -> AbstractToolsClientProvider:
    """Return the configured tools client provider."""
    cfg = _get_settings()
    if cfg.tools_client.provider in ("http", "http_mtls"):
        from provider_contracts.tools_client.http import HttpToolsClientProvider

        return HttpToolsClientProvider(
            base_url=cfg.tools_client.base_url,
            token=cfg.tools_client.token,
        )
    raise ProviderConfigError(f"Unknown tools client provider: {cfg.tools_client.provider}")


# â”€â”€ Prompt Store â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
@lru_cache(maxsize=1)
def get_prompt_store_provider() -> AbstractPromptStoreProvider:
    """Return the configured prompt store provider."""
    cfg = _get_settings()
    if cfg.prompt_store.provider == "file":
        from provider_contracts.prompt_store.file import FilePromptStoreProvider

        return FilePromptStoreProvider(base_dir=cfg.prompt_store.file_base_dir)
    if cfg.prompt_store.provider == "promptflow":
        raise ProviderConfigError(
            "Prompt Flow prompt store not yet implemented in provider_contracts"
        )
    raise ProviderConfigError(f"Unknown prompt store provider: {cfg.prompt_store.provider}")


# â”€â”€ Session Store â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â
@lru_cache(maxsize=1)
def get_session_store_provider() -> AbstractSessionStoreProvider:
    """Return the configured session store provider."""
    cfg = _get_settings()
    if cfg.session_store.provider == "memory":
        from provider_contracts.session_store.memory import InMemorySessionStoreProvider

        return InMemorySessionStoreProvider(
            ttl_minutes=cfg.session_store.ttl_minutes,
            max_turns=cfg.session_store.max_turns,
        )
    raise ProviderConfigError(f"Unknown session store provider: {cfg.session_store.provider}")


# â”€â”€ Re-ranker â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
@lru_cache(maxsize=1)
def get_reranker_provider() -> AbstractRerankerProvider:
    """Return the configured re-ranker provider."""
    cfg = _get_settings()
    if cfg.reranker.provider == "sentence_transformers":
        from provider_contracts.reranker.sentence_transformers import (
            SentenceTransformerRerankerProvider,
        )

        return SentenceTransformerRerankerProvider(model_name=cfg.reranker.model)
    raise ProviderConfigError(f"Unknown re-ranker provider: {cfg.reranker.provider}")
