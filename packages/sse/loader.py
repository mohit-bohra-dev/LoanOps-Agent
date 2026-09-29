"""In-memory OpenAPI catalog loader (fixture or HTTP swagger URLs)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from packages.sse.catalog import origin_of, parse_openapi_document
from packages.sse.types import CatalogSource, OpenApiCatalog

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
    ) -> None:
        self.swagger_links = swagger_links or list(DEFAULT_SWAGGER_LINKS)
        self.api_base_url = api_base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.fixture_path = fixture_path
        self.timeout_seconds = timeout_seconds
        self._catalog: OpenApiCatalog | None = None

    def allowed_origins(self) -> list[str]:
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

    async def load(self, *, refresh: bool = False) -> OpenApiCatalog:
        if self._catalog is not None and not refresh:
            return self._catalog
        if self.fixture_path:
            self._catalog = self._load_fixture(Path(self.fixture_path))
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
        return self._catalog

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
