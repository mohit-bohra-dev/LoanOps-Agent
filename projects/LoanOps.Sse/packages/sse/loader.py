"""In-memory OpenAPI catalog loader (fixture or HTTP swagger URLs)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from collections.abc import Callable

from packages.sse.catalog import origin_of, parse_openapi_document
from packages.sse.types import AppTarget, CatalogSource, OpenApiCatalog

CatalogMode = str


def resolve_swagger_links(swagger_links: list[Any], swagger_urls: list[str]) -> list[dict[str, str]]:
    """Named links win. URL-only list becomes ids from the hostname."""
    if swagger_links:
        return [
            {"id": str(link.id), "label": str(link.label), "url": str(link.url)}
            if not isinstance(link, dict)
            else {"id": str(link["id"]), "label": str(link["label"]), "url": str(link["url"])}
            for link in swagger_links
        ]
    from urllib.parse import urlparse

    links: list[dict[str, str]] = []
    for i, url in enumerate(swagger_urls):
        host = urlparse(url).hostname or f"app-{i}"
        slug = host.split(".")[0].replace("-", "_")
        links.append({"id": slug, "label": host, "url": url})
    return links


def resolve_catalog_source(
    catalog_source: str,
    *,
    has_swagger_links: bool,
    registry_has_spec: bool,
    use_fixture: bool,
) -> CatalogMode:
    """auto: explicit swagger list, else registry with a spec, else fixture."""
    if catalog_source in {"registry", "swagger_links", "fixture"}:
        return catalog_source
    if has_swagger_links:
        return "swagger_links"
    if registry_has_spec:
        return "registry"
    if use_fixture:
        return "fixture"
    return "registry"

DEFAULT_SWAGGER_LINKS: list[dict[str, str]] = [
    {
        "id": "pennedocs-dev",
        "label": "PennEDocs API (dev)",
        "url": "https://pennedocsapi.dev.pennymac.plaisse.com/swagger/v1/swagger.json",
    },
    {
        "id": "corecomponents-dev",
        "label": "CoreComponents API (dev)",
        "url": "https://corecomponentsapi.dev.pennymac.plaisse.com/swagger/v1/swagger.json",
    },
]

DEFAULT_API_BASE_URL = "https://corecomponentsapi.dev.pennymac.plaisse.com"


class OpenApiCatalogService:
    """Load and cache OpenAPI catalogs from swagger URLs or a local fixture file."""

    def __init__(
        self,
        *,
        swagger_links: list[dict[str, str]] | None = None,
        api_base_url: str = DEFAULT_API_BASE_URL,
        bearer_token: str = "",
        fixture_path: str | None = None,
        timeout_seconds: float = 15.0,
        openapi_embed_path: str | None = None,
        registry_specs: list[dict[str, Any]] | None = None,
        reload_specs: Any | None = None,
        app_targets: Callable[[], dict[str, AppTarget]] | None = None,
        registry_mode: bool = False,
    ) -> None:
        self.swagger_links = swagger_links or list(DEFAULT_SWAGGER_LINKS)
        self.api_base_url = api_base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.fixture_path = fixture_path
        self.timeout_seconds = timeout_seconds
        self.openapi_embed_path = openapi_embed_path
        self.registry_specs = registry_specs
        self._reload_specs = reload_specs
        self._app_targets = app_targets
        self.registry_mode = registry_mode or registry_specs is not None
        self._catalog: OpenApiCatalog | None = None
        self.openapi_embed_cache: dict[str, list[float]] = {}
        self.openapi_embed_hashes: dict[str, str] = {}

    def reload_registry(self) -> None:
        """Re-read cached specs from disk and drop the in-memory catalog."""
        if self._reload_specs is None:
            return
        loaded = self._reload_specs()
        if isinstance(loaded, list):
            self.registry_specs = loaded
            self._catalog = None

    def app_targets(self) -> dict[str, AppTarget]:
        if self._app_targets is None:
            return {}
        return self._app_targets()

    def target_for(self, application_id: str) -> AppTarget | None:
        targets = self.app_targets()
        hit = targets.get(application_id)
        if hit is not None:
            return hit
        # Allow match by label (case-insensitive) for ergonomics.
        needle = application_id.strip().lower()
        for target in targets.values():
            if target.application_id.lower() == needle or target.label.lower() == needle:
                return target
        return None

    def allowed_origins(self) -> list[str]:
        if self.registry_mode:
            targets = self.app_targets()
            if targets:
                return sorted({t.origin for t in targets.values()})
        origins: set[str] = set()
        try:
            origins.add(origin_of(self.api_base_url))
        except Exception:  # noqa: BLE001
            pass
        for link in self.swagger_links:
            try:
                origins.add(origin_of(link["url"]))
            except Exception:  # noqa: BLE001
                pass
        return sorted(origins)

    def _seed_embeddings(self, catalog: OpenApiCatalog) -> None:
        """Load OpenAPI embed sidecar into the in-process cache (hash-validated)."""
        from packages.sse.semantic import load_openapi_index, seed_cache_from_index

        self.openapi_embed_cache = {}
        self.openapi_embed_hashes = {}
        if not self.openapi_embed_path:
            return
        index = load_openapi_index(self.openapi_embed_path)
        if not index:
            return
        seed_cache_from_index(
            catalog.operations,
            index,
            self.openapi_embed_cache,
            hashes=self.openapi_embed_hashes,
        )

    async def load(self, *, refresh: bool = False) -> OpenApiCatalog:
        if self._catalog is not None and not refresh:
            return self._catalog
        if refresh:
            self.openapi_embed_cache = {}
            self.openapi_embed_hashes = {}
        if self.registry_specs is not None:
            self._catalog = self._load_registry_specs()
            self._seed_embeddings(self._catalog)
            return self._catalog
        if self.fixture_path:
            self._catalog = self._load_fixture(Path(self.fixture_path))
            self._seed_embeddings(self._catalog)
            return self._catalog

        sources: list[CatalogSource] = []
        operations = []
        headers = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        async with httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers) as client:
            for link in self.swagger_links:
                try:
                    resp = await client.get(link["url"])
                    resp.raise_for_status()
                    doc = resp.json()
                    if not isinstance(doc, dict):
                        raise ValueError("OpenAPI root is not an object")
                    base = origin_of(str(resp.url))
                    ops = parse_openapi_document(doc, link["id"], link["label"], base)
                    operations.extend(ops)
                    sources.append(
                        CatalogSource(
                            id=link["id"],
                            label=link["label"],
                            url=str(resp.url),
                            operation_count=len(ops),
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    sources.append(
                        CatalogSource(
                            id=link["id"],
                            label=link["label"],
                            url=link["url"],
                            operation_count=0,
                            error=str(exc),
                        )
                    )

        self._catalog = OpenApiCatalog(
            operations=operations,
            loaded_at=datetime.now(UTC).isoformat(),
            sources=sources,
        )
        self._seed_embeddings(self._catalog)
        return self._catalog

    def _load_registry_specs(self) -> OpenApiCatalog:
        """Build the catalog from cached documents. Does not open a network client."""
        sources: list[CatalogSource] = []
        operations = []
        for spec in self.registry_specs or []:
            doc = spec.get("document")
            source_id = str(spec.get("source_id") or "")
            label = str(spec.get("label") or source_id)
            base = str(spec.get("base_url") or "")
            error = spec.get("error")
            if not isinstance(doc, dict):
                sources.append(
                    CatalogSource(
                        id=source_id,
                        label=label,
                        url=base,
                        operation_count=0,
                        error=str(error or "no cached spec"),
                    )
                )
                continue
            ops = parse_openapi_document(doc, source_id, label, base)
            operations.extend(ops)
            sources.append(
                CatalogSource(
                    id=source_id,
                    label=label,
                    url=base,
                    operation_count=len(ops),
                )
            )
        return OpenApiCatalog(
            operations=operations,
            loaded_at=datetime.now(UTC).isoformat(),
            sources=sources,
        )

    def _load_fixture(self, path: Path) -> OpenApiCatalog:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        # Accept either a full catalog dump or a raw OpenAPI doc.
        if "operations" in raw:
            return OpenApiCatalog.model_validate(raw)
        source_id = "loanservices" if "loanservices" in path.name.lower() else "fixture"
        source_label = "LoanServices" if source_id == "loanservices" else "Local fixture"
        ops = parse_openapi_document(
            raw,
            source_id,
            source_label,
            self.api_base_url,
        )
        return OpenApiCatalog(
            operations=ops,
            loaded_at=datetime.now(UTC).isoformat(),
            sources=[
                CatalogSource(
                    id=source_id,
                    label=source_label,
                    url=str(path),
                    operation_count=len(ops),
                )
            ],
        )


def assert_allowed_url(url: str, allowed_origins: list[str]) -> None:
    origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    if origin not in allowed_origins:
        raise PermissionError(
            f"Refusing to call {origin}: host must be a configured SSE API "
            f"({', '.join(allowed_origins) or 'none'})."
        )
