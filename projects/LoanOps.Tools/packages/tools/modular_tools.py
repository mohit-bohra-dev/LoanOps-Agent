"""In-process tools client — routes SSE/docs/db/wiki/EAKG (no tools_api)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from packages.common.scopes import EAKG_TOOL_NAMES, tools_for_role, tools_for_scopes
from packages.common.settings import Settings, get_settings
from packages.db.client import SqlServerClient
from packages.docs.service import DocsService
from packages.sse.catalog import find_operation
from packages.sse.loader import OpenApiCatalogService
from packages.sse.tools import SSE_TOOL_NAMES, dispatch_sse_tool
from packages.sse.types import ApiOperation
from packages.tools.capability import eakg_capability_search_block
from packages.tools.capability_catalog import CapabilityCatalogService
from packages.tools.eakg_tools import dispatch_eakg_tool
from packages.tools.policy import ToolPolicyError, assert_sse_read_only, body_present
from packages.wiki.tools import WIKI_TOOL_NAMES, dispatch_wiki_tool
from provider_contracts.tools_client import ToolCall, ToolResult
from provider_contracts.tools_client._base import AbstractToolsClientProvider

_LOCAL_TOOLS = (
    *SSE_TOOL_NAMES,
    *EAKG_TOOL_NAMES,
    "get_customer_servicing_summary",
    "run_read_only_sql",
    "search_docs",
    "index_docs",
    *WIKI_TOOL_NAMES,
)

CapabilityBlock = Callable[[str, int], Awaitable[str | None]]


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
        capability_block: CapabilityBlock | None = eakg_capability_search_block,
        catalog_service: CapabilityCatalogService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._sse = sse
        self._db = db
        self._docs = docs
        self._cache = cache
        self._docs_root = docs_root or Path("data/sops")
        self._capability_block = capability_block
        self._catalog_service = catalog_service
        self._settings = settings
        self._catalog_fingerprint: tuple[tuple[str, int, int], ...] | None = None
        self._catalog_checked_at = 0.0
        self._allowed = (
            tools_for_scopes(scopes) if scopes is not None else tools_for_role(role)
        )

    @property
    def allowed_tools(self) -> frozenset[str]:
        return self._allowed

    def capability_catalog(self) -> CapabilityCatalogService | None:
        """Cached EAKG catalog service (for MCP bind / readiness)."""
        return self._catalog_service

    async def readiness_snapshot(self) -> dict[str, Any]:
        """Non-network readiness details for MCP /ready (no live SSE host probe)."""
        from pathlib import Path

        warnings: list[str] = []
        catalog = await self._sse.load()
        source_errors = [
            {"id": s.id, "label": s.label, "error": s.error}
            for s in catalog.sources
            if s.error
        ]
        if source_errors:
            warnings.append("openapi_source_errors")
        openapi = {
            "operation_count": len(catalog.operations),
            "source_count": len(catalog.sources),
            "source_errors": source_errors,
            "embed_cache_size": len(self._sse.openapi_embed_cache),
        }
        sidecar_path = self._sse.openapi_embed_path
        sidecar_present = bool(sidecar_path and Path(sidecar_path).is_file())
        coverage = 0.0
        if catalog.operations and sidecar_present:
            coverage = round(
                len(self._sse.openapi_embed_cache) / len(catalog.operations), 3
            )
        if not sidecar_present:
            warnings.append("openapi_embed_sidecar_missing")
        eakg: dict[str, Any] = {"enabled": False}
        svc = self._catalog_service
        if svc is not None and svc.enabled:
            eakg = {
                "enabled": True,
                "shard_dir": str(svc.shard_dir),
                "shard_dir_exists": svc.shard_dir.is_dir(),
                "fingerprint_files": len(svc.fingerprint()),
                "capability_count": svc.capability_count(),
            }
            if not svc.shard_dir.is_dir():
                warnings.append("eakg_shard_dir_missing")
        return {
            "openapi": openapi,
            "openapi_sidecar": {
                "path": sidecar_path,
                "present": sidecar_present,
                "coverage": coverage,
            },
            "eakg": eakg,
            "warnings": warnings,
        }

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

    def _maybe_reload_catalog(self) -> None:
        if self._settings is None:
            return
        import time

        now = time.monotonic()
        if now - self._catalog_checked_at < 5.0:
            return
        self._catalog_checked_at = now
        from packages.tools.registry_catalog import catalog_fingerprint

        current = catalog_fingerprint(self._settings)
        if self._catalog_fingerprint is None:
            self._catalog_fingerprint = current
            return
        if current != self._catalog_fingerprint:
            self._sse.reload_registry()
            self._catalog_fingerprint = current

    async def call(self, tool: ToolCall) -> ToolResult:
        # LAYER2-BP A5: in-process helpers (Agent modular OR MCP server)
        self._maybe_reload_catalog()
        name = tool.tool_name
        if name not in self._allowed:
            return self._err(name, f"Tool '{name}' not allowed for current scope")
        args = dict(tool.parameters)
        try:
            if name == "call_sse_api":
                try:
                    await self._assert_call_sse_read_only(args)
                except ToolPolicyError as exc:
                    return self._err(name, str(exc))
            if name in ("search_sse_apis", "list_sse_apis", "call_sse_api"):
                text = await dispatch_sse_tool(
                    self._sse,
                    name,
                    args,
                    cache=self._cache,
                    capability_block=self._capability_block,
                )
                return self._ok(name, text)
            if name in EAKG_TOOL_NAMES:
                settings = self._settings if self._settings is not None else get_settings()
                text = await dispatch_eakg_tool(
                    name,
                    args,
                    catalog_service=self._catalog_service,
                    settings=settings,
                )
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

    async def _assert_call_sse_read_only(self, args: dict[str, Any]) -> None:
        """Enforce GET-only / no body before dispatch (defense-in-depth)."""
        if body_present(args.get("body")):
            raise ToolPolicyError("call_sse_api body is not allowed")
        method_arg = args.get("method")
        method_text = str(method_arg) if method_arg is not None else None
        if method_text is not None and method_text.strip().upper() != "GET":
            raise ToolPolicyError("call_sse_api method must be GET")
        op_id = args.get("operation_id")
        path = args.get("path")
        operation = await self.find_sse_operation(
            operation_id=str(op_id) if op_id else None,
            method=method_text,
            path=str(path) if path else None,
        )
        resolved = operation.method if operation is not None else None
        assert_sse_read_only(
            method_arg=method_text,
            body=None,
            resolved_method=resolved,
        )
