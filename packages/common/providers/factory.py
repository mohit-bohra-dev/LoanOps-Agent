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
    """Return the configured loan data provider (DATA__LOAN_SOURCE)."""
    cfg = _get_settings()
    if cfg.data.loan_source == "real":
        from packages.common.providers.loan_data import RestApiLoanProvider

        return RestApiLoanProvider(cfg.data.loan_api)
    from packages.common.providers.loan_data import (
        FixtureLoanProvider,
        JsonFileLoanProvider,
        loan_fixtures_dir,
    )

    if loan_fixtures_dir() is not None:
        return FixtureLoanProvider()
    return JsonFileLoanProvider()


def _confluence_policy_provider(
    cfg: Settings,
) -> AbstractPolicySourceProvider:
    """Build Confluence SOP source from DATA__SOP_CONFLUENCE_MODE."""
    from packages.common.providers.policy_source import (
        ConfluencePolicyProvider,
        LocalFilePolicyProvider,
    )

    if cfg.data.sop_confluence_mode == "live":
        return ConfluencePolicyProvider(cfg.data.confluence)
    # Offline cache written by a prior live ingest
    return LocalFilePolicyProvider(sops_dir=cfg.data.confluence.artifact_dir)


@lru_cache(maxsize=1)
def get_policy_source_provider() -> AbstractPolicySourceProvider:
    """Return the configured policy source provider (DATA__SOP_SOURCE).

    local      → synthetic data/sops (excludes _confluence)
    confluence → Confluence only (cache or live per DATA__SOP_CONFLUENCE_MODE)
    both       → local + Confluence
    """
    cfg = _get_settings()
    from packages.common.providers.policy_source import (
        CompositePolicyProvider,
        LocalFilePolicyProvider,
    )

    local = LocalFilePolicyProvider()
    if cfg.data.sop_source == "local":
        return local
    confluence = _confluence_policy_provider(cfg)
    if cfg.data.sop_source == "confluence":
        return confluence
    return CompositePolicyProvider([local, confluence])


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
            profile=cfg.llm.bedrock.profile,
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
    if cfg.embedding.provider == "bedrock":
        from provider_contracts.embedding.bedrock import BedrockEmbeddingProvider

        return BedrockEmbeddingProvider(
            model_id=cfg.embedding.bedrock.model_id,
            region=cfg.embedding.bedrock.region,
            profile=cfg.embedding.bedrock.profile,
            dimensions=cfg.embedding.bedrock.dimensions,
            api_key=cfg.embedding.bedrock.api_key,
            access_key_id=cfg.embedding.bedrock.access_key_id,
            secret_access_key=cfg.embedding.bedrock.secret_access_key,
            session_token=cfg.embedding.bedrock.session_token,
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
    if cfg.vector_store.provider == "pgvector":
        from provider_contracts.vector_store.pgvector import PgVectorProvider
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(cfg.vector_store.pgvector_dsn)
        return PgVectorProvider(
            engine,
            dimensions=cfg.vector_store.pgvector_dimensions,
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
def build_modular_tools_client(cfg: Settings, *, role: str) -> AbstractToolsClientProvider:
    """Build the in-process tools client for a role. Shared by the agent and MCP server."""
    import json
    from pathlib import Path

    from packages.common.modular_tools import ModularToolsClient
    from packages.db.client import DbConfig, SqlServerClient
    from packages.docs.service import DocsService
    from packages.sse.fixture import FIXTURE_OPENAPI
    from packages.sse.loader import DEFAULT_SWAGGER_LINKS, OpenApiCatalogService

    swagger_links = list(DEFAULT_SWAGGER_LINKS)
    if cfg.sse.swagger_links:
        swagger_links = [
            {"id": link.id, "label": link.label, "url": link.url} for link in cfg.sse.swagger_links
        ]
    elif cfg.sse.swagger_urls:
        from urllib.parse import urlparse

        swagger_links = []
        for i, u in enumerate(cfg.sse.swagger_urls):
            host = urlparse(u).hostname or f"app-{i}"
            slug = host.split(".")[0].replace("-", "_")
            swagger_links.append({"id": slug, "label": host, "url": u})

    fixture_path = cfg.sse.fixture_path or None
    if cfg.sse.use_fixture and not fixture_path:
        path = Path("data/sse-fixture-openapi.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(FIXTURE_OPENAPI), encoding="utf-8")
        fixture_path = str(path)
    # Catalog-only fixture: use_fixture=false but fixture_path set
    # (e.g. local Loan Services OpenAPI when live swagger needs auth).
    catalog_fixture = fixture_path if (cfg.sse.use_fixture or cfg.sse.fixture_path) else None

    sse = OpenApiCatalogService(
        swagger_links=swagger_links,
        api_base_url=cfg.sse.api_base_url,
        bearer_token=cfg.sse.api_key,
        fixture_path=catalog_fixture,
    )
    db = SqlServerClient(
        DbConfig(
            server=cfg.sql_server.server,
            database=cfg.sql_server.database,
            user=cfg.sql_server.user,
            password=cfg.sql_server.password,
            driver=cfg.sql_server.driver,
        ),
        fixture_mode=cfg.sql_server.fixture_mode,
    )
    docs: DocsService | None = None
    try:
        docs = DocsService(get_embedding_provider(), get_vector_store_provider())
    except Exception:  # noqa: BLE001
        docs = None

    # Answers come from SSE OpenAPI (+ docs / optional SQL). No tools_api.
    return ModularToolsClient(
        sse=sse,
        db=db,
        docs=docs,
        role=role,
    )


@lru_cache(maxsize=1)
def get_tools_client_provider() -> AbstractToolsClientProvider:
    """Return the configured tools client provider."""
    cfg = _get_settings()
    if cfg.tools_client.provider == "modular":
        return build_modular_tools_client(cfg, role=cfg.agent_role)
    raise ProviderConfigError(
        f"Unknown tools client provider: {cfg.tools_client.provider} "
        "(only 'modular' is supported; apps/tools_api was removed)"
    )


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
    if cfg.session_store.provider == "postgres":
        from provider_contracts.session_store.postgres import PostgresSessionStoreProvider

        return PostgresSessionStoreProvider(
            cfg.session_store.postgres_dsn,
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
