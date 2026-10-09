"""Fill blank registry addresses from a TAAC ServiceUrls file (FR-022)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import json

from packages.eakg.registry import AppEnvironment, RepositoryRegistry
from packages.eakg.taac import load_service_url_map, url_key_to_app_id


@dataclass
class ImportReport:
    filled: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    unregistered: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "filled": self.filled,
            "conflicts": self.conflicts,
            "unregistered": self.unregistered,
        }


def load_api_identifier(path: str | Path) -> str:
    raw: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return ""
    auth0 = raw.get("Auth0")
    if not isinstance(auth0, dict):
        return ""
    api = auth0.get("Api")
    if not isinstance(api, dict):
        return ""
    return str(api.get("Identifier") or "")


def import_taac(
    registry: RepositoryRegistry,
    path: str | Path,
    environment: str,
    *,
    dry_run: bool = False,
) -> ImportReport:
    """Match existing rows and fill a blank base_url. Never writes git_url."""
    raw: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    urls = raw.get("ServiceUrls") if isinstance(raw, dict) else {}
    if not isinstance(urls, dict):
        urls = {}
    audience = load_api_identifier(path)
    hinted = load_service_url_map(path)
    report = ImportReport()
    by_id = {rec.application_id: rec for rec in registry.list()}
    by_key = {rec.service_url_key: rec for rec in registry.list() if rec.service_url_key}
    changed = False

    for key, url in urls.items():
        if not isinstance(url, str) or not url.strip():
            continue
        key_s = str(key)
        app_id = hinted.get(key_s) or url_key_to_app_id(key_s)
        record = by_key.get(key_s) or by_id.get(app_id)
        if record is None:
            report.unregistered.append(key_s)
            continue
        env = record.environments.get(environment)
        current = env.base_url if env is not None else ""
        if current and current.rstrip("/") != url.rstrip("/"):
            report.conflicts.append(f"{record.application_id}: {key_s}")
            continue
        if current:
            continue
        report.filled.append(record.application_id)
        if dry_run:
            continue
        if env is None:
            env = AppEnvironment(base_url=url, auth_audience=audience)
            record.environments[environment] = env
        else:
            env.base_url = url
            if not env.auth_audience and audience:
                env.auth_audience = audience
        if not record.service_url_key:
            record.service_url_key = key_s
        changed = True

    if changed and not dry_run:
        registry.save()
    return report
