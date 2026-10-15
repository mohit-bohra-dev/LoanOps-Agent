"""Approved pattern files under data/eakg/patterns/ (ADR-029)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


@dataclass
class PatternSet:
    """Loaded declarative patterns for deterministic extractors."""

    sdk_client_suffixes: list[str] = field(default_factory=lambda: [".Client"])
    sdk_domain_suffixes: list[str] = field(default_factory=lambda: [".Domain"])
    datastore_owners: dict[str, str] = field(default_factory=dict)
    proxy_base_classes: list[str] = field(default_factory=list)
    service_url_key_suffixes: list[str] = field(default_factory=lambda: ["Url"])
    topic_key_suffixes: list[str] = field(default_factory=lambda: ["TopicName"])
    router_names: list[str] = field(default_factory=list)
    decorator_names: list[str] = field(default_factory=list)
    version_blob: str = ""

    @property
    def patterns_hash(self) -> str:
        if not self.version_blob:
            return ""
        return hashlib.sha256(self.version_blob.encode("utf-8")).hexdigest()[:16]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def load_patterns(patterns_dir: str | Path | None) -> PatternSet:
    """Load pattern YAMLs; missing dir → built-in defaults."""
    root = Path(patterns_dir) if patterns_dir else None
    if root is None or not root.is_dir():
        return PatternSet()

    blobs: list[str] = []
    sdk = _load_yaml(root / "sdk_suffixes.yaml")
    owners = _load_yaml(root / "datastore_owners.yaml")
    proxies = _load_yaml(root / "proxy_bases.yaml")
    urls = _load_yaml(root / "service_url_keys.yaml")
    topics = _load_yaml(root / "topic_keys.yaml")
    routers = _load_yaml(root / "routers.yaml")
    decorators = _load_yaml(root / "decorators.yaml")

    for name, raw in (
        ("sdk_suffixes.yaml", sdk),
        ("datastore_owners.yaml", owners),
        ("proxy_bases.yaml", proxies),
        ("service_url_keys.yaml", urls),
        ("topic_keys.yaml", topics),
        ("routers.yaml", routers),
        ("decorators.yaml", decorators),
    ):
        if raw:
            blobs.append(f"{name}:{yaml.safe_dump(raw, sort_keys=True)}")

    client = [str(x) for x in (sdk.get("client_suffixes") or [".Client"])]
    domain = [str(x) for x in (sdk.get("domain_suffixes") or [".Domain"])]
    owners_raw = owners.get("owners") if isinstance(owners.get("owners"), dict) else owners
    owner_map = {
        str(k): str(v)
        for k, v in (owners_raw or {}).items()
        if k not in {"owners", "added_by", "approved_by", "approved_at", "motivating"}
    }

    return PatternSet(
        sdk_client_suffixes=client or [".Client"],
        sdk_domain_suffixes=domain or [".Domain"],
        datastore_owners=owner_map,
        proxy_base_classes=[str(x) for x in (proxies.get("base_classes") or [])],
        service_url_key_suffixes=[str(x) for x in (urls.get("suffixes") or ["Url"])],
        topic_key_suffixes=[str(x) for x in (topics.get("suffixes") or ["TopicName"])],
        router_names=[str(x) for x in (routers.get("names") or [])],
        decorator_names=[str(x) for x in (decorators.get("names") or [])],
        version_blob="\n".join(blobs),
    )


def default_patterns_dir() -> Path:
    return Path("data/eakg/patterns")
