"""Single source of truth for all configuration.

All application code reads config from Settings(). No direct os.environ calls
outside this module.
"""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoanApiConfig(BaseModel):
    base_url: str = ""
    api_key: str = ""  # Bearer token for upstream Loan Services API
    timeout_seconds: int = 30
    api_version: str = "1.0"
    summary_pdm_model: bool = False
    # Path templates — Loan Services swagger uses PascalCase /api/Loans/...
    get_loan_path: str = "/api/Loans/{loan_id}"
    get_loan_summary_path: str = "/api/Loans/{loan_id}/Summary"
    get_borrower_summary_path: str = "/api/Loans/{loan_id}/BorrowerSummary"
    get_payment_schedules_path: str = "/api/Loans/{loan_id}/PaymentSchedules"
    get_escrows_path: str = "/api/Loans/{loan_id}/Escrows"
    get_delinquencies_path: str = "/api/Loans/{loan_id}/Delinquencies"
    search_path: str = "/api/loans/search"  # unused — real API has no name search
    search_query_param: str = "borrowerName"  # unused — real API has no name search


class ConfluenceConfig(BaseModel):
    base_url: str = ""
    api_token: str = ""
    username: str = ""
    space_keys: list[str] = []
    # Curated ingest allowlist (SC space Escrow + Hardship seeds)
    page_ids: list[str] = Field(default_factory=list)
    ancestor_ids: list[str] = Field(default_factory=list)
    expand_children: bool = True
    pii_scrub: Literal["regex", "presidio", "off"] = "regex"
    artifact_dir: str = "data/sops/_confluence"


class DataConfig(BaseModel):
    """Loan + SOP source selection.

    Prefer independent switches:
      DATA__LOAN_SOURCE=mock|real
      DATA__SOP_SOURCE=local|confluence|both
      DATA__SOP_CONFLUENCE_MODE=cache|live

    Deprecated: DATA__MODE=mock|real (maps loan_source; real → sop both+live).
    """

    # Deprecated unified switch — prefer loan_source + sop_source.
    mode: Literal["mock", "real"] | None = None
    loan_source: Literal["mock", "real"] = "mock"
    sop_source: Literal["local", "confluence", "both"] = "local"
    # cache = data/sops/_confluence only (offline); live = Confluence REST API
    sop_confluence_mode: Literal["cache", "live"] = "cache"
    loan_api: LoanApiConfig = Field(default_factory=LoanApiConfig)
    confluence: ConfluenceConfig = Field(default_factory=ConfluenceConfig)

    @model_validator(mode="before")
    @classmethod
    def _apply_legacy_mode(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        mode = data.get("mode")
        if mode is None:
            return data
        if data.get("loan_source") is None:
            data["loan_source"] = mode
        if data.get("sop_source") is None:
            data["sop_source"] = "both" if mode == "real" else "local"
        if mode == "real" and data.get("sop_confluence_mode") is None:
            data["sop_confluence_mode"] = "live"
        return data

    @model_validator(mode="after")
    def _legacy_mode_mirror(self) -> Self:
        # Keep mode populated for older callers that still read data.mode.
        if self.mode is None:
            object.__setattr__(self, "mode", self.loan_source)
        return self


class OllamaChatConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    model_fast: str = "llama3.1:8b"
    model_accurate: str = "llama3.1:8b"


class AOAIChatConfig(BaseModel):
    endpoint: str = ""
    deployment_fast: str = "gpt-4o-mini"
    deployment_accurate: str = "gpt-4o"
    api_version: str = "2024-08-01-preview"


class OpenAIChatConfig(BaseModel):
    api_key: str = ""
    base_url: str | None = None
    model: str = "gpt-4o-mini"


class BedrockChatConfig(BaseModel):
    region: str = "us-east-1"
    model_id: str = "us.amazon.nova-pro-v1:0"
    # Named profile from ~/.aws/credentials or SSO (e.g. "dev")
    profile: str | None = None
    # --- Auth option A: Bedrock API key (bearer token, easiest for local dev) ---
    api_key: str | None = None
    # --- Auth option B: IAM credentials (leave None to use boto3 default chain) ---
    access_key_id: str | None = None
    secret_access_key: str | None = None
    session_token: str | None = None


class GeminiChatConfig(BaseModel):
    api_key: str = ""
    model: str = "gemini-2.5-flash"


class ChatConfig(BaseModel):
    provider: Literal["ollama", "aoai", "openai", "bedrock", "gemini"] = "bedrock"
    ollama: OllamaChatConfig = Field(default_factory=OllamaChatConfig)
    aoai: AOAIChatConfig | None = None
    openai: OpenAIChatConfig | None = None
    bedrock: BedrockChatConfig = Field(default_factory=BedrockChatConfig)
    gemini: GeminiChatConfig | None = None
    deterministic_by_default: bool = False


class QdrantConfig(BaseModel):
    url: str = "http://localhost:6333"
    collection: str = "sops"
    # Local embedded mode (no Docker): set path to a directory or ":memory:".
    # When set, url is ignored. Leanest no-Docker option via qdrant-client.
    path: str | None = None


class AISearchConfig(BaseModel):
    endpoint: str = ""
    api_key: str = ""
    index: str = "sops"
    dimensions: int = 1536


class VectorStoreConfig(BaseModel):
    provider: Literal["qdrant", "ai_search", "pgvector"] = "qdrant"
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    ai_search: AISearchConfig | None = None
    pgvector_dsn: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/loanops"
    pgvector_dimensions: int = 384


class AOAIEmbeddingConfig(BaseModel):
    endpoint: str = ""
    deployment: str = "text-embedding-3-large"
    api_version: str = "2024-08-01-preview"


class BedrockEmbeddingConfig(BaseModel):
    region: str = "us-west-2"
    model_id: str = "amazon.titan-embed-text-v2:0"
    profile: str | None = None
    dimensions: int = 1024
    api_key: str | None = None
    access_key_id: str | None = None
    secret_access_key: str | None = None
    session_token: str | None = None


class GeminiEmbeddingConfig(BaseModel):
    """Google Gemini embedding configuration."""

    api_key: str = ""
    model: str = "gemini-embedding-2"
    # api_key: str = Field(alias="GEMINI_API_KEY")
    # model: str = "gemini-embedding-2"


class EmbeddingConfig(BaseModel):
    provider: Literal["local_bge", "aoai", "gemini", "bedrock"] = "gemini"
    aoai: AOAIEmbeddingConfig | None = None
    gemini: GeminiEmbeddingConfig = Field(default_factory=GeminiEmbeddingConfig)
    bedrock: BedrockEmbeddingConfig = Field(default_factory=BedrockEmbeddingConfig)


class PiiConfig(BaseModel):
    provider: Literal["presidio", "stub"] = "presidio"
    mode: Literal["redact_audit_only", "tokenize"] = "redact_audit_only"


class SafetyConfig(BaseModel):
    provider: Literal["stub", "azure"] = "stub"


class AuditConfig(BaseModel):
    sink: Literal["jsonl", "appinsights"] = "jsonl"
    jsonl_dir: str = "./audit"


class SecretsConfig(BaseModel):
    provider: Literal["env", "keyvault"] = "env"


class LangfuseConfig(BaseModel):
    public_key: str = "pk-lf-local"
    secret_key: str = "sk-lf-local"
    host: str = "http://localhost:3000"
    flush_on_shutdown: bool = True


class TelemetryConfig(BaseModel):
    provider: Literal["console", "appinsights", "langfuse"] = "console"
    langfuse: LangfuseConfig | None = None


class ToolsClientConfig(BaseModel):
    """Tools routing.

    ``modular`` = in-process SSE OpenAPI catalog + docs (+ optional SQL).
    ``mcp`` = Streamable HTTP client to ``packages.mcp_server`` (ADR-013).
    """

    provider: Literal["modular", "mcp"] = "modular"


class PromptStoreConfig(BaseModel):
    provider: Literal["file", "promptflow"] = "file"
    file_base_dir: str = "./docs"


class SessionStoreConfig(BaseModel):
    provider: Literal["memory", "postgres"] = "memory"
    ttl_minutes: int = 60
    max_turns: int = 50
    postgres_dsn: str = "postgresql://postgres:postgres@localhost:5432/loanops"


class SwaggerLinkConfig(BaseModel):
    """One SSE app OpenAPI source (10+ apps = 10+ links)."""

    id: str
    label: str
    url: str


class SseConfig(BaseModel):
    """SSE OpenAPI gateway (packages.sse) — sole live data path for answers."""

    api_base_url: str = "https://corecomponentsapi.dev.pennymac.plaisse.com"
    api_key: str = ""
    use_fixture: bool = True
    fixture_path: str = ""
    # Prefer named links for many apps:
    # SSE__SWAGGER_LINKS=[{"id":"pennedocs","label":"PennEDocs","url":"https://.../swagger.json"},...]
    swagger_links: list[SwaggerLinkConfig] = Field(default_factory=list)
    # Shorthand: list of swagger URLs only (ids derived from hostname)
    swagger_urls: list[str] = Field(default_factory=list)


class SqlServerConfig(BaseModel):
    """SQL Server for packages.db — requires ODBC Driver 18 + aioodbc when live."""

    fixture_mode: bool = True
    server: str = ""
    database: str = ""
    user: str = ""
    password: str = ""
    driver: str = "ODBC Driver 18 for SQL Server"


class RerankerConfig(BaseModel):
    provider: Literal["sentence_transformers"] = "sentence_transformers"
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class McpConfig(BaseModel):
    """Streamable HTTP MCP listener. Empty auth_token rejects every MCP call."""

    host: str = "127.0.0.1"
    port: int = 8001
    auth_token: str = ""
    role: str = "system"
    path: str = "/mcp"
    # Optional principal forwarded to SSE as x-loanops-* (audit + outbound headers).
    # Not a substitute for OBO; SSE__API_KEY remains the service bearer.
    principal_user: str = ""
    principal_tenant: str = ""


class CapabilityKgConfig(BaseModel):
    """RDF capability knowledge graph (ADR-014 facade). Product truth is EAKG shards."""

    enabled: bool = True
    namespace: str = "https://loanops.local/ontology/"
    # Deprecated for product discovery (D4). Kept for `capability_kg.build` experiments only.
    ttl_path: str = "data/capability_kg/capabilities.ttl"
    approved_only: bool = False
    # Phase 9: cosine over embeddings.json; ignored unless enabled=true
    semantic: bool = False


class EakgConfig(BaseModel):
    """Enterprise Application Knowledge Graph (ADR-015..019). Multi-repo shards."""

    workspace_dir: str = ".eakg-workspace"
    registry_path: str = "data/eakg/registry/repositories.yaml"
    shard_dir: str = "data/eakg"
    gitlab_host: str = "gitlab.pnmac.com"
    openapi_mode: Literal["static", "hybrid", "live"] = "hybrid"
    live_spec_token: str = ""
    confidence_threshold: float = 0.85
    auto_approve_structural: bool = True
    nightly_hour: int = 2
    review_stale_days: int = 14
    taac_config_path: str = ""
    # Source analysis: roslyn (primary) | regex (interim) | auto (roslyn then regex)
    extractor: Literal["auto", "roslyn", "regex"] = "auto"
    # Synthetic / redacted TAAC fixture for local/CI (never commit real secrets)
    taac_fixture_path: str = "data/eakg/fixtures/taac-client-config.redacted.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="forbid",
        case_sensitive=False,
    )

    data: DataConfig = Field(default_factory=DataConfig)
    llm: ChatConfig = Field(default_factory=ChatConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    pii: PiiConfig = Field(default_factory=PiiConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    tools_client: ToolsClientConfig = Field(default_factory=ToolsClientConfig)
    prompt_store: PromptStoreConfig = Field(default_factory=PromptStoreConfig)
    session_store: SessionStoreConfig = Field(default_factory=SessionStoreConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)
    sse: SseConfig = Field(default_factory=SseConfig)
    sql_server: SqlServerConfig = Field(default_factory=SqlServerConfig)
    mcp: McpConfig = Field(default_factory=McpConfig)
    capability_kg: CapabilityKgConfig = Field(default_factory=CapabilityKgConfig)
    eakg: EakgConfig = Field(default_factory=EakgConfig)
    agent_role: str = Field(default="system", validation_alias="AGENT_ROLE")
