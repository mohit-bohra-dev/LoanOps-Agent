"""SSE OpenAPI types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field

HttpMethod = Literal["get", "post", "put", "patch", "delete", "head", "options"]


class ApiParameter(BaseModel):
    name: str
    in_: Literal["path", "query", "header", "cookie"] = Field(alias="in")
    required: bool = False
    description: str | None = None
    schema_type: str | None = None

    model_config = {"populate_by_name": True}


class ApiOperation(BaseModel):
    id: str
    source_id: str
    source_label: str
    method: HttpMethod
    path: str
    operation_id: str | None = None
    summary: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    parameters: list[ApiParameter] = Field(default_factory=list)
    has_request_body: bool = False
    server_url: str | None = None
    source_base_url: str


class CatalogSource(BaseModel):
    id: str
    label: str
    url: str
    operation_count: int
    error: str | None = None
    status: str = "ok"
    fetched_at: str | None = None
    environment: str | None = None
    stale: bool = False


class OpenApiCatalog(BaseModel):
    operations: list[ApiOperation] = Field(default_factory=list)
    loaded_at: str
    sources: list[CatalogSource] = Field(default_factory=list)


class AppTarget(BaseModel):
    """Per-app invoke binding (registry mode)."""

    application_id: str
    label: str
    environment: str
    base_url: str
    origin: str
    audience: str


class BreakerRegistry(Protocol):
    """Per-app circuit breaker — Protocol lives in sse so invoke never imports api_index."""

    def is_open(self, application_id: str) -> bool: ...

    def record_failure(self, application_id: str) -> None: ...

    def record_success(self, application_id: str) -> None: ...

    def state_of(self, application_id: str) -> str: ...


class OperationRefResolver(Protocol):
    """Duck-typed api_index.OperationResolver — sse must not import api_index."""

    def resolve(self, ref: str, *, application_id: str | None = None) -> object: ...


@dataclass(frozen=True)
class InvokeTarget:
    operation: ApiOperation | None
    target: AppTarget | None


@dataclass(frozen=True)
class Rejection:
    reason: Literal[
        "application_required",
        "unknown_application",
        "operation_not_in_application",
        "ambiguous",
        "not_found",
    ]
    message: str
    application_id: str | None = None
