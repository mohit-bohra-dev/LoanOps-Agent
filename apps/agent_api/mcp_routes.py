"""MCP-style tool endpoints on the Agent API (stdio/HTTP clients use these)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from packages.common.providers.factory import get_tools_client_provider
from packages.sse.api_keys import ApiKeyStore

router = APIRouter(tags=["mcp"])

# Process-local API key store (register via POST /mcp/keys)
_API_KEYS = ApiKeyStore()


class McpToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class RegisterKeyRequest(BaseModel):
    label: str = "mcp-client"
    scopes: list[str] = Field(default_factory=lambda: ["sse.read", "docs.search"])


@router.get("/mcp/tools")
async def list_mcp_tools() -> dict[str, Any]:
    client = get_tools_client_provider()
    names = await client.list_tools()
    return {"tools": names}


@router.post("/mcp/tools/call")
async def call_mcp_tool(
    body: McpToolCallRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict[str, Any]:
    if x_api_key:
        record = _API_KEYS.verify(x_api_key)
        if record is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
    from provider_contracts.tools_client import ToolCall

    client = get_tools_client_provider()
    result = await client.call(ToolCall(tool_name=body.name, parameters=body.arguments))
    return {
        "success": result.success,
        "tool_name": result.tool_name,
        "data": result.data,
        "error": result.error,
    }


@router.post("/mcp/keys")
async def register_mcp_key(body: RegisterKeyRequest) -> dict[str, Any]:
    raw, record = _API_KEYS.register(body.label, body.scopes)
    return {
        "api_key": raw,
        "key_id": record.key_id,
        "scopes": record.scopes,
        "created_at": record.created_at,
    }
