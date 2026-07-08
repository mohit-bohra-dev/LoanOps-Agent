"""Single source of truth for all configuration.

All application code reads config from Settings(). No direct os.environ calls
outside this module.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoanApiConfig(BaseModel):
    base_url: str = ""
    api_key: str = ""
    timeout_seconds: int = 10


class ConfluenceConfig(BaseModel):
    base_url: str = ""
    api_token: str = ""
    username: str = ""
    space_keys: list[str] = []


class DataConfig(BaseModel):
    mode: Literal["mock", "real"] = "mock"
    loan_api: LoanApiConfig = Field(default_factory=LoanApiConfig)
    confluence: ConfluenceConfig = Field(default_factory=ConfluenceConfig)


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


class AISearchConfig(BaseModel):
    endpoint: str = ""
    api_key: str = ""
    index: str = "sops"
    dimensions: int = 1536


class VectorStoreConfig(BaseModel):
    provider: Literal["qdrant", "ai_search"] = "qdrant"
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    ai_search: AISearchConfig | None = None


class AOAIEmbeddingConfig(BaseModel):
    endpoint: str = ""
    deployment: str = "text-embedding-3-large"
    api_version: str = "2024-08-01-preview"


class GeminiEmbeddingConfig(BaseModel):
    """Google Gemini embedding configuration."""
    api_key: str = ""
    model: str = "gemini-embedding-2"
    # api_key: str = Field(alias="GEMINI_API_KEY")
    # model: str = "gemini-embedding-2"


class EmbeddingConfig(BaseModel):
    provider: Literal["local_bge", "aoai", "gemini"] = "gemini"
    aoai: AOAIEmbeddingConfig | None = None
    gemini: GeminiEmbeddingConfig = Field(default_factory=GeminiEmbeddingConfig)


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
    provider: Literal["http", "http_mtls"] = "http"
    base_url: str = "http://localhost:8001"
    token: str = "dev-token"


class PromptStoreConfig(BaseModel):
    provider: Literal["file", "promptflow"] = "file"
    file_base_dir: str = "./docs"


class SessionStoreConfig(BaseModel):
    provider: Literal["memory"] = "memory"
    ttl_minutes: int = 60
    max_turns: int = 50


class RerankerConfig(BaseModel):
    provider: Literal["sentence_transformers"] = "sentence_transformers"
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="forbid",
        case_sensitive=False,
    )

    data: DataConfig = Field(default_factory=DataConfig)
    tools_api_token: str = Field(default="dev-token", validation_alias="TOOLS_API_TOKEN")
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
