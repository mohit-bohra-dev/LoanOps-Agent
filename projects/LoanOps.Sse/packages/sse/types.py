"""SSE OpenAPI types."""

from __future__ import annotations

from typing import Literal

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


class OpenApiCatalog(BaseModel):
    operations: list[ApiOperation] = Field(default_factory=list)
    loaded_at: str
    sources: list[CatalogSource] = Field(default_factory=list)
