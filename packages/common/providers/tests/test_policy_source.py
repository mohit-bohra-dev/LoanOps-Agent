"""Unit tests for policy source providers (local skip + scrub + composite)."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.common.providers.policy_source import (
    CompositePolicyProvider,
    LocalFilePolicyProvider,
    PolicyPage,
    scrub_text,
)


@pytest.mark.asyncio
async def test_local_provider_skips_underscore_dirs(tmp_path: Path) -> None:
    (tmp_path / "escrow").mkdir()
    (tmp_path / "escrow" / "annual.md").write_text(
        "---\nid: sop-esc-001\ncategory: escrow\nstate: national\nversion: \"1\"\n---\nBody A\n",
        encoding="utf-8",
    )
    conf_dir = tmp_path / "_confluence" / "escrow"
    conf_dir.mkdir(parents=True)
    (conf_dir / "secret.md").write_text(
        "---\nid: conf-1\ncategory: escrow\nstate: national\n---\nShould skip\n",
        encoding="utf-8",
    )

    pages = await LocalFilePolicyProvider(tmp_path).fetch_pages()
    assert len(pages) == 1
    assert pages[0].metadata["id"] == "sop-esc-001"
    assert "Should skip" not in pages[0].content


@pytest.mark.asyncio
async def test_local_provider_includes_confluence_artifacts(tmp_path: Path) -> None:
    (tmp_path / "escrow").mkdir()
    (tmp_path / "escrow" / "annual.md").write_text(
        "---\nid: sop-esc-001\ncategory: escrow\nstate: national\nversion: \"1\"\n---\nBody A\n",
        encoding="utf-8",
    )
    conf_dir = tmp_path / "_confluence" / "escrow"
    conf_dir.mkdir(parents=True)
    (conf_dir / "from-confluence.md").write_text(
        "---\nid: conf-1\ncategory: escrow\nstate: national\n---\nConfluence body\n",
        encoding="utf-8",
    )
    # Other underscore dirs still skipped
    other = tmp_path / "_other"
    other.mkdir()
    (other / "ignored.md").write_text("# ignore\n", encoding="utf-8")

    pages = await LocalFilePolicyProvider(
        tmp_path, include_confluence_artifacts=True
    ).fetch_pages()
    ids = {p.metadata.get("id") for p in pages}
    assert ids == {"sop-esc-001", "conf-1"}
    assert any("Confluence body" in p.content for p in pages)


@pytest.mark.asyncio
async def test_composite_concatenates() -> None:
    class _Stub(LocalFilePolicyProvider):
        def __init__(self, title: str) -> None:
            self._title = title

        async def fetch_pages(self) -> list[PolicyPage]:
            return [PolicyPage(title=self._title, content="x", source=self._title)]

    pages = await CompositePolicyProvider([_Stub("a"), _Stub("b")]).fetch_pages()
    assert [p.title for p in pages] == ["a", "b"]


def test_scrub_regex_redacts_email_and_ssn() -> None:
    text = "Contact jane.doe@pnmac.com or SSN 123-45-6789"
    out = scrub_text(text, "regex")
    assert "jane.doe@pnmac.com" not in out
    assert "123-45-6789" not in out
    assert "[REDACTED_EMAIL]" in out
    assert "[REDACTED_SSN]" in out


def test_scrub_off_passthrough() -> None:
    text = "keep me@example.com"
    assert scrub_text(text, "off") == text
