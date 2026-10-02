"""SSE module — OpenAPI catalog, invoke, API keys, MCP tools."""

from packages.sse.api_keys import ApiKeyStore, hash_api_key
from packages.sse.catalog import find_operation, search_operations, summarize_operation
from packages.sse.invoke import InvokeResult, invoke_sse_api
from packages.sse.loader import DEFAULT_API_BASE_URL, DEFAULT_SWAGGER_LINKS, OpenApiCatalogService
from packages.sse.tools import SSE_TOOL_NAMES, dispatch_sse_tool
from packages.sse.types import ApiOperation, OpenApiCatalog

__all__ = [
    "ApiKeyStore",
    "ApiOperation",
    "DEFAULT_API_BASE_URL",
    "DEFAULT_SWAGGER_LINKS",
    "InvokeResult",
    "OpenApiCatalog",
    "OpenApiCatalogService",
    "SSE_TOOL_NAMES",
    "dispatch_sse_tool",
    "find_operation",
    "hash_api_key",
    "invoke_sse_api",
    "search_operations",
    "summarize_operation",
]
