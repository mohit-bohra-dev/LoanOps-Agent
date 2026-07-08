"""Policy Source Provider Protocol and Implementations."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PolicyPage:
    """Represents a policy page (e.g., from Confluence or Markdown)."""
    def __init__(self, title: str, content: str, source: str, metadata: dict[str, str] | None = None):
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


class LocalFilePolicyProvider(AbstractPolicySourceProvider):
    """Mock provider that reads SOPs from local data/sops/*.md files."""

    def __init__(self, sops_dir: str | Path = "data/sops") -> None:
        self.sops_dir = Path(sops_dir)

    async def fetch_pages(self) -> list[PolicyPage]:
        if not self.sops_dir.exists():
            logger.warning(f"SOPs directory not found: {self.sops_dir}")
            return []

        pages = []
        md_files = list(self.sops_dir.glob("**/*.md"))
        for file_path in md_files:
            text = file_path.read_text(encoding="utf-8")
            
            content = text
            metadata = {"source": str(file_path.relative_to(self.sops_dir))}
            if text.startswith("---"):
                try:
                    parts = text.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]
                        content = parts[2].strip()
                        for line in frontmatter.splitlines():
                            if ":" in line:
                                k, v = line.split(":", 1)
                                metadata[k.strip()] = v.strip()
                except Exception as e:
                    logger.warning(f"Failed to parse frontmatter in {file_path.name}: {e}")
            
            pages.append(PolicyPage(title=file_path.name, content=content, source=metadata["source"], metadata=metadata))
        return pages


class ConfluencePolicyProvider(AbstractPolicySourceProvider):
    """Real provider that fetches pages from Confluence."""

    def __init__(self, config: Any) -> None:
        self.config = config

    async def fetch_pages(self) -> list[PolicyPage]:
        raise NotImplementedError("Real Confluence API not yet implemented (waiting for endpoint details)")
