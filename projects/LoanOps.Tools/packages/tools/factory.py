"""Tools client factories (composition of SSE/docs/db/wiki + MCP hop)."""

from __future__ import annotations

from functools import lru_cache

from packages.common.providers.base import ProviderConfigError
from packages.common.providers.factory import (
    get_embedding_provider,
    get_vector_store_provider,
)
from packages.common.settings import Settings
from provider_contracts.tools_client import AbstractToolsClientProvider


def build_modular_tools_client(cfg: Settings, *, role: str) -> AbstractToolsClientProvider:
    """Build the in-process tools client for a role. Shared by the agent and MCP server."""
    import json
    from pathlib import Path

    from packages.db.client import DbConfig, SqlServerClient
    from packages.docs.service import DocsService
    from packages.sse.fixture import FIXTURE_OPENAPI
    from packages.sse.loader import DEFAULT_SWAGGER_LINKS, OpenApiCatalogService
    from packages.tools.modular_tools import ModularToolsClient

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


def build_mcp_tools_client(cfg: Settings, *, role: str) -> AbstractToolsClientProvider:
    """Build the agent-side MCP tools client. Requires a running mcp_server process."""
    from packages.tools.mcp_tools_client import (
        McpToolsClient,
        StreamableHttpMcpSession,
        mcp_endpoint_url,
    )

    if not cfg.mcp.auth_token:
        raise ProviderConfigError(
            "TOOLS_CLIENT__PROVIDER=mcp requires MCP__AUTH_TOKEN "
            "(same bearer the mcp_server listener expects)"
        )
    url = mcp_endpoint_url(host=cfg.mcp.host, port=cfg.mcp.port, path=cfg.mcp.path)
    session = StreamableHttpMcpSession(
        url=url,
        auth_token=cfg.mcp.auth_token,
        user=cfg.mcp.principal_user or None,
        tenant=cfg.mcp.principal_tenant or None,
    )
    return McpToolsClient(session=session, role=role)


@lru_cache(maxsize=1)
def get_tools_client_provider() -> AbstractToolsClientProvider:
    """Return the configured tools client provider."""
    cfg = Settings()
    if cfg.tools_client.provider == "modular":
        return build_modular_tools_client(cfg, role=cfg.agent_role)
    if cfg.tools_client.provider == "mcp":
        return build_mcp_tools_client(cfg, role=cfg.agent_role)
    raise ProviderConfigError(
        f"Unknown tools client provider: {cfg.tools_client.provider} "
        "(supported: 'modular', 'mcp')"
    )
