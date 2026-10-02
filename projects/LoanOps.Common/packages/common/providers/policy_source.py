"""Policy Source Provider Protocol and Implementations."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

import httpx
from packages.common.settings import ConfluenceConfig

logger = logging.getLogger(__name__)

# Seed category map for curated Escrow + Hardship (Loss Mitigation) pages.
_ESCROW_SEED_IDS: frozenset[str] = frozenset(
    {
        "1887175341",  # Annual Analysis (book)
        "1887338919",  # Account Maintenance (book)
        "1886978615",  # Interest on Escrow Management (book)
        "1885930603",  # Overages (book)
        "4178706738",  # Escrow Removal - Low UPB
    }
)
_HARDSHIP_SEED_IDS: frozenset[str] = frozenset(
    {
        "2324660235",  # Loss Mitigation SOP
        "2260566121",  # Loss Mitigation Repayment & Forbearance Plan Procedure
        "1913979067",  # Loss Mitigation Inbound Call Handling Scripts
        "1899331673",  # Disaster Forbearance Plan Procedure
        "1888551030",  # Loss Mitigation - Repayment Plans (book)
    }
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)"
)
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_LOAN_NUM_RE = re.compile(r"\b(?:loan\s*(?:#|number|num)?\s*)?\d{7,12}\b", re.IGNORECASE)
_DP_CODE_RE = re.compile(r"\b(DP17-[A-Za-z0-9]+\.v\d+)\b", re.IGNORECASE)
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class PolicyPage:
    """Represents a policy page (e.g., from Confluence or Markdown)."""

    def __init__(
        self,
        title: str,
        content: str,
        source: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self.title = title
        self.content = content
        self.source = source
        self.metadata = metadata or {}


class AbstractPolicySourceProvider(ABC):
    """Protocol for fetching policy source documents."""

    @abstractmethod
    async def fetch_pages(self) -> list[PolicyPage]:
        """Fetch all policy pages to be ingested."""
        pass


class CompositePolicyProvider(AbstractPolicySourceProvider):
    """Concatenate pages from multiple policy source providers."""

    def __init__(self, providers: list[AbstractPolicySourceProvider]) -> None:
        self._providers = providers

    async def fetch_pages(self) -> list[PolicyPage]:
        pages: list[PolicyPage] = []
        for provider in self._providers:
            batch = await provider.fetch_pages()
            pages.extend(batch)
        return pages


class LocalFilePolicyProvider(AbstractPolicySourceProvider):
    """Mock provider that reads SOPs from local data/sops/*.md files."""

    def __init__(
        self,
        sops_dir: str | Path = "data/sops",
        *,
        include_confluence_artifacts: bool = False,
    ) -> None:
        self.sops_dir = Path(sops_dir)
        # When True, also read data/sops/_confluence/*.md (cached Confluence pages).
        # Default False avoids double-count when Composite + ConfluencePolicyProvider.
        self.include_confluence_artifacts = include_confluence_artifacts

    async def fetch_pages(self) -> list[PolicyPage]:
        if not self.sops_dir.exists():
            logger.warning("SOPs directory not found: %s", self.sops_dir)
            return []

        pages: list[PolicyPage] = []
        md_files = sorted(self.sops_dir.glob("**/*.md"))
        for file_path in md_files:
            rel_parts = file_path.relative_to(self.sops_dir).parts
            # Skip underscore dirs (e.g. _confluence) unless artifacts explicitly enabled
            if any(part.startswith("_") for part in rel_parts):
                if not (
                    self.include_confluence_artifacts
                    and rel_parts
                    and rel_parts[0] == "_confluence"
                ):
                    continue

            text = file_path.read_text(encoding="utf-8")
            content = text
            metadata: dict[str, str] = {
                "source": str(file_path.relative_to(self.sops_dir)).replace("\\", "/")
            }
            if text.startswith("---"):
                try:
                    parts = text.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]
                        content = parts[2].strip()
                        for line in frontmatter.splitlines():
                            if ":" in line:
                                k, v = line.split(":", 1)
                                metadata[k.strip()] = v.strip().strip('"').strip("'")
                except Exception as e:
                    logger.warning("Failed to parse frontmatter in %s: %s", file_path.name, e)

            pages.append(
                PolicyPage(
                    title=file_path.name,
                    content=content,
                    source=metadata["source"],
                    metadata=metadata,
                )
            )
        return pages


def scrub_text(text: str, mode: Literal["regex", "presidio", "off"]) -> str:
    """Redact common PII patterns from policy text (sync; regex or off)."""
    if mode == "off":
        return text
    return _scrub_regex(text)


def _scrub_regex(text: str) -> str:
    out = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    out = _PHONE_RE.sub("[REDACTED_PHONE]", out)
    out = _SSN_RE.sub("[REDACTED_SSN]", out)
    out = _LOAN_NUM_RE.sub("[REDACTED_LOAN_ID]", out)
    return out


async def _scrub_async(text: str, mode: Literal["regex", "presidio", "off"]) -> str:
    if mode == "off":
        return text
    if mode == "presidio":
        try:
            from provider_contracts.pii.presidio import PresidioPiiProvider

            result = await PresidioPiiProvider().anonymise(text)
            return result.anonymised
        except Exception as exc:
            logger.warning("Presidio scrub failed (%s); falling back to regex", exc)
    return _scrub_regex(text)


def _slugify(title: str) -> str:
    slug = _SLUG_RE.sub("-", title.lower()).strip("-")
    return slug[:80] or "page"


def _category_for(page_id: str, ancestor_id: str | None) -> str:
    if page_id in _ESCROW_SEED_IDS or (ancestor_id and ancestor_id in _ESCROW_SEED_IDS):
        return "escrow"
    if page_id in _HARDSHIP_SEED_IDS or (ancestor_id and ancestor_id in _HARDSHIP_SEED_IDS):
        return "hardship"
    return "confluence"


def _extract_dp_code(text: str) -> str:
    match = _DP_CODE_RE.search(text)
    return match.group(1) if match else ""


class ConfluencePolicyProvider(AbstractPolicySourceProvider):
    """Fetch curated Confluence pages, scrub, save local markdown, return PolicyPages."""

    def __init__(self, config: ConfluenceConfig) -> None:
        if not config.base_url:
            raise ValueError(
                "DATA__CONFLUENCE__BASE_URL is required when "
                "DATA__SOP_CONFLUENCE_MODE=live"
            )
        if not config.username:
            raise ValueError(
                "DATA__CONFLUENCE__USERNAME is required when "
                "DATA__SOP_CONFLUENCE_MODE=live"
            )
        if not config.api_token:
            raise ValueError(
                "DATA__CONFLUENCE__API_TOKEN is required when "
                "DATA__SOP_CONFLUENCE_MODE=live"
            )
        if not config.page_ids and not config.ancestor_ids:
            raise ValueError(
                "DATA__CONFLUENCE__PAGE_IDS or DATA__CONFLUENCE__ANCESTOR_IDS required"
            )
        self._config = config
        base = config.base_url.rstrip("/")
        # Accept site root or /wiki; normalize to .../wiki
        if base.endswith("/wiki"):
            self._wiki_base = base
        else:
            self._wiki_base = f"{base}/wiki"
        self._api_base = f"{self._wiki_base}/api/v2"
        self._artifact_dir = Path(config.artifact_dir)

    async def fetch_pages(self) -> list[PolicyPage]:
        targets = await self._resolve_targets()
        logger.info("Resolved %d Confluence page(s) for ingest", len(targets))

        pages: list[PolicyPage] = []
        timeout = httpx.Timeout(60.0)
        auth = httpx.BasicAuth(self._config.username, self._config.api_token)
        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient(
            timeout=timeout, auth=auth, headers=headers, follow_redirects=True
        ) as client:
            for page_id, ancestor_id in targets:
                try:
                    page = await self._fetch_one(client, page_id, ancestor_id)
                except Exception as exc:
                    logger.warning("Skipping Confluence page %s: %s", page_id, exc)
                    continue
                if page is not None:
                    pages.append(page)
        return pages

    async def _resolve_targets(self) -> list[tuple[str, str | None]]:
        """Return (page_id, ancestor_id) pairs; expand books to direct leaf children."""
        seen: set[str] = set()
        targets: list[tuple[str, str | None]] = []

        timeout = httpx.Timeout(60.0)
        auth = httpx.BasicAuth(self._config.username, self._config.api_token)
        async with httpx.AsyncClient(
            timeout=timeout, auth=auth, headers={"Accept": "application/json"}, follow_redirects=True
        ) as client:
            for ancestor_id in self._config.ancestor_ids:
                if self._config.expand_children:
                    leaves = await self._direct_leaf_children(client, ancestor_id)
                    logger.info(
                        "Ancestor %s → %d direct leaf child(ren)", ancestor_id, len(leaves)
                    )
                    for leaf_id in leaves:
                        if leaf_id not in seen:
                            seen.add(leaf_id)
                            targets.append((leaf_id, ancestor_id))
                # Also include the book page itself (may have useful overview text)
                if ancestor_id not in seen:
                    seen.add(ancestor_id)
                    targets.append((ancestor_id, ancestor_id))

            for page_id in self._config.page_ids:
                if page_id not in seen:
                    seen.add(page_id)
                    targets.append((page_id, None))

        return targets

    async def _direct_leaf_children(
        self, client: httpx.AsyncClient, page_id: str
    ) -> list[str]:
        children = await self._list_children(client, page_id)
        leaves: list[str] = []
        for child in children:
            child_id = str(child.get("id", ""))
            if not child_id:
                continue
            grandchildren = await self._list_children(client, child_id)
            if grandchildren:
                logger.info(
                    "Skip sub-book child %s (%s)", child_id, child.get("title", "")
                )
                continue
            leaves.append(child_id)
        return leaves

    async def _list_children(
        self, client: httpx.AsyncClient, page_id: str
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        url: str | None = f"{self._api_base}/pages/{page_id}/children"
        params: dict[str, str] | None = {"limit": "250"}
        while url:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()
            results.extend(payload.get("results") or [])
            next_link = (payload.get("_links") or {}).get("next")
            if not next_link:
                break
            url = (
                str(next_link)
                if str(next_link).startswith("http")
                else f"{self._wiki_base}{next_link}"
            )
            params = None  # cursor already embedded in next link
        return results

    async def _fetch_one(
        self,
        client: httpx.AsyncClient,
        page_id: str,
        ancestor_id: str | None,
    ) -> PolicyPage | None:
        url = f"{self._api_base}/pages/{page_id}"
        resp = await client.get(url, params={"body-format": "export_view"})
        if resp.status_code == 404:
            logger.warning("Confluence page not found: %s", page_id)
            return None
        resp.raise_for_status()
        data = resp.json()

        title = str(data.get("title") or f"page-{page_id}")
        version_obj = data.get("version") or {}
        version_num = version_obj.get("number", "")
        body = data.get("body") or {}
        export_view = body.get("export_view") or body.get("view") or {}
        html = str(export_view.get("value") or "")
        if not html.strip():
            logger.warning("Empty body for Confluence page %s (%s)", page_id, title)
            return None

        markdown = self._html_to_markdown(html)
        markdown = await _scrub_async(markdown, self._config.pii_scrub)

        category = _category_for(page_id, ancestor_id)
        slug = _slugify(title)
        dp_code = _extract_dp_code(markdown) or f"confluence-{page_id}"
        source = f"confluence/{category}/{slug}"
        source_url = f"{self._wiki_base}/spaces/SC/pages/{page_id}/{quote(title)}"

        metadata: dict[str, str] = {
            "source": source,
            "id": dp_code,
            "category": category,
            "state": "national",
            "version": str(version_num) if version_num != "" else "1",
            "title": title,
            "source_url": source_url,
            "confluence_page_id": page_id,
        }

        self._write_artifact(category, slug, metadata, markdown)

        return PolicyPage(title=title, content=markdown, source=source, metadata=metadata)

    def _html_to_markdown(self, html: str) -> str:
        from markitdown import MarkItDown

        converter = MarkItDown(enable_plugins=False)
        result = converter.convert_stream(BytesIO(html.encode("utf-8")), file_extension=".html")
        text = getattr(result, "text_content", None) or getattr(result, "markdown", None) or ""
        return str(text).strip()

    def _write_artifact(
        self,
        category: str,
        slug: str,
        metadata: dict[str, str],
        body: str,
    ) -> None:
        out_dir = self._artifact_dir / category
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{slug}.md"
        frontmatter_lines = [
            "---",
            f"id: {metadata.get('id', '')}",
            f"category: {metadata.get('category', '')}",
            f"state: {metadata.get('state', 'national')}",
            f'version: "{metadata.get("version", "1")}"',
            f"title: {metadata.get('title', '')}",
            f"source_url: {metadata.get('source_url', '')}",
            f"confluence_page_id: {metadata.get('confluence_page_id', '')}",
            "---",
            "",
        ]
        path.write_text("\n".join(frontmatter_lines) + body + "\n", encoding="utf-8")
        logger.info("Wrote Confluence artifact %s", path)
