"""Tools client factories (composition of SSE/docs/db/wiki + MCP hop)."""

from __future__ import annotations

from functools import lru_cache

from packages.common.providers.base import ProviderConfigError
from packages.common.providers.factory import (
    get_embedding_provider,
    get_vector_store_provider,
)
from packages.common.settings import Settings, get_settings
from provider_contracts.tools_client import AbstractToolsClientProvider


def build_modular_tools_client(cfg: Settings, *, role: str) -> AbstractToolsClientProvider:
    """Build the in-process tools client for a role. Shared by the agent and MCP server."""
    import json
    from pathlib import Path

    from packages.db.client import DbConfig, SqlServerClient
    from packages.docs.service import DocsService
    from packages.sse.fixture import FIXTURE_OPENAPI
    from packages.sse.loader import DEFAULT_SWAGGER_LINKS, OpenApiCatalogService, resolve_swagger_links
    from packages.tools.registry_catalog import build_registry_specs, catalog_mode
    from packages.tools.capability import make_eakg_capability_search_block
    from packages.tools.capability_catalog import CapabilityCatalogService
    from packages.tools.modular_tools import ModularToolsClient

    swagger_links = resolve_swagger_links(cfg.sse.swagger_links, cfg.sse.swagger_urls)
    if not swagger_links:
        swagger_links = list(DEFAULT_SWAGGER_LINKS)
    mode = catalog_mode(cfg)

    fixture_path = cfg.sse.fixture_path or None
    if cfg.sse.use_fixture and not fixture_path:
        path = Path("data/sse-fixture-openapi.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(FIXTURE_OPENAPI), encoding="utf-8")
        fixture_path = str(path)
    # Catalog-only fixture: use_fixture=false but fixture_path set
    # (e.g. local Loan Services OpenAPI when live swagger needs auth).
    catalog_fixture = fixture_path if (cfg.sse.use_fixture or cfg.sse.fixture_path) else None
    if mode == "registry":
        catalog_fixture = None
    elif mode == "swagger_links":
        catalog_fixture = None

    from packages.sse.semantic import openapi_embeddings_path

    embed_sidecar = str(openapi_embeddings_path(cfg.eakg.shard_dir))
    sse = OpenApiCatalogService(
        swagger_links=swagger_links,
        api_base_url=cfg.sse.api_base_url,
        bearer_token=cfg.sse.api_key,
        fixture_path=catalog_fixture,
        openapi_embed_path=embed_sidecar,
        registry_specs=build_registry_specs(cfg) if mode == "registry" else None,
        reload_specs=(lambda: build_registry_specs(cfg)) if mode == "registry" else None,
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

    kg = cfg.capability_kg
    embed_query = None
    if kg.enabled:

        async def _embed(text: str) -> list[float]:
            result = await get_embedding_provider().embed(text)
            return list(result.vector)

        from packages.tools.capability_catalog import use_semantic

        if use_semantic(semantic_flag=kg.semantic, shard_dir=cfg.eakg.shard_dir):
            embed_query = _embed

    catalog_service = CapabilityCatalogService(
        cfg.eakg.shard_dir,
        namespace=kg.namespace,
        approved_only=kg.approved_only,
        semantic=kg.semantic,
        embed_query=embed_query,
        enabled=kg.enabled,
    )
    capability_block = make_eakg_capability_search_block(catalog_service)

    # Answers come from SSE OpenAPI (+ docs / optional SQL). No tools_api.
    return ModularToolsClient(
        sse=sse,
        db=db,
        docs=docs,
        role=role,
        capability_block=capability_block,
        catalog_service=catalog_service,
        settings=cfg,
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
    cfg = get_settings()
    # LAYER2-BP A2: branch modular vs mcp
    if cfg.tools_client.provider == "modular":
        return build_modular_tools_client(cfg, role=cfg.agent_role)
    if cfg.tools_client.provider == "mcp":
        return build_mcp_tools_client(cfg, role=cfg.agent_role)
    raise ProviderConfigError(
        f"Unknown tools client provider: {cfg.tools_client.provider} "
        "(supported: 'modular', 'mcp')"
    )
