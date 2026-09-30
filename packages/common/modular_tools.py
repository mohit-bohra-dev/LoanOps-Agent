"""In-process tools client — routes SSE/docs/db/wiki (no tools_api)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from provider_contracts.tools_client import ToolCall, ToolResult
from provider_contracts.tools_client._base import AbstractToolsClientProvider

from packages.common.scopes import tools_for_role, tools_for_scopes
from packages.db.client import SqlServerClient
from packages.docs.service import DocsService
from packages.sse.catalog import find_operation
from packages.sse.loader import OpenApiCatalogService
from packages.sse.tools import SSE_TOOL_NAMES, dispatch_sse_tool
from packages.sse.types import ApiOperation
from packages.wiki.tools import WIKI_TOOL_NAMES, dispatch_wiki_tool

_LOCAL_TOOLS = (
    *SSE_TOOL_NAMES,
    "get_customer_servicing_summary",
    "run_read_only_sql",
    "search_docs",
    "index_docs",
    *WIKI_TOOL_NAMES,
)


class ModularToolsClient(AbstractToolsClientProvider):
    """Single tools client for the modular product."""

    def __init__(
        self,
        *,
        sse: OpenApiCatalogService,
        db: SqlServerClient,
        docs: DocsService | None = None,
        cache: Any | None = None,
        scopes: list[str] | None = None,
        role: str = "system",
        docs_root: Path | None = None,
    ) -> None:
        self._sse = sse
        self._db = db
        self._docs = docs
        self._cache = cache
        self._docs_root = docs_root or Path("data/sops")
        self._allowed = (
            tools_for_scopes(scopes) if scopes is not None else tools_for_role(role)
        )

    @property
    def allowed_tools(self) -> frozenset[str]:
        return self._allowed

    def _ok(self, name: str, text: str) -> ToolResult:
        return ToolResult(tool_name=name, success=True, data={"text": text})

    def _err(self, name: str, error: str) -> ToolResult:
        return ToolResult(tool_name=name, success=False, error=error)

    async def list_tools(self) -> list[str]:
        return [n for n in _LOCAL_TOOLS if n in self._allowed]

    async def find_sse_operation(
        self,
        *,
        operation_id: str | None = None,
        method: str | None = None,
        path: str | None = None,
    ) -> ApiOperation | None:
        """Look up a catalog operation. Does not call the API."""
        catalog = await self._sse.load()
        return find_operation(
            catalog.operations,
            operation_id=operation_id,
            method=method,
            path=path,
        )

    async def call(self, tool: ToolCall) -> ToolResult:
        name = tool.tool_name
        if name not in self._allowed:
            return self._err(name, f"Tool '{name}' not allowed for current scope")
        args = dict(tool.parameters)
        try:
            if name in ("search_sse_apis", "list_sse_apis", "call_sse_api"):
                text = await dispatch_sse_tool(self._sse, name, args, cache=self._cache)
                return self._ok(name, text)
            if name == "get_customer_servicing_summary":
                text = await self._db.get_customer_servicing_summary(
                    str(args.get("customer_id") or "")
                )
                return self._ok(name, text)
            if name == "run_read_only_sql":
                text = await self._db.run_read_only_query(str(args.get("sql") or ""))
                return self._ok(name, text)
            if name == "search_docs":
                if self._docs is None:
                    return self._err(name, "docs not configured")
                text = await self._docs.search(
                    str(args.get("query") or ""),
                    top_k=int(args.get("top_k") or 5),
                )
                return self._ok(name, text)
            if name == "index_docs":
                if self._docs is None:
                    return self._err(name, "docs not configured")
                await self._docs.ensure_collection()
                count = await self._docs.index_directory(self._docs_root, corpus="sop")
                return ToolResult(
                    tool_name=name,
                    success=True,
                    data={"indexed_chunks": count},
                )
            if name.startswith("wiki_"):
                text = await dispatch_wiki_tool(name, args)
                return self._ok(name, text)
            return self._err(name, f"No handler for {name}")
        except Exception as exc:  # noqa: BLE001
            return self._err(name, str(exc))
