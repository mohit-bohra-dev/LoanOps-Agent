"""Registry field checks for enterprise-app-scale (spec §4.1)."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from packages.eakg.registry import VALID_ENV, RepositoryRecord, RepositoryRegistry

_APP_ID = re.compile(r"^[a-z][a-z0-9_]{1,62}$")
_ENV_MARKERS: dict[str, frozenset[str]] = {
    "dev": frozenset({"dev"}),
    "stage": frozenset({"stg", "stage"}),
    "prod": frozenset({"prd", "prod"}),
}
_ALL_MARKERS = frozenset().union(*_ENV_MARKERS.values())


@dataclass(frozen=True)
class RegistryIssue:
    code: str
    severity: Literal["blocking", "warning"]
    application_id: str
    environment: str | None
    field: str
    message: str


def blocking_issues(
    rec: RepositoryRecord,
    environment: str,
    issues: dict[str, list[RegistryIssue]],
) -> list[RegistryIssue]:
    return [
        issue
        for issue in issues.get(rec.application_id, [])
        if issue.severity == "blocking" and issue.environment in (None, environment)
    ]


def validate_registry(registry: RepositoryRegistry) -> dict[str, list[RegistryIssue]]:
    issues: dict[str, list[RegistryIssue]] = {}
    seen_ids: dict[str, str] = {}
    origins_by_env: dict[str, dict[str, str]] = {}

    for record in registry.list():
        bucket = issues.setdefault(record.application_id, [])
        if not _APP_ID.match(record.application_id):
            bucket.append(
                _issue(
                    "bad_app_id",
                    "blocking",
                    record,
                    None,
                    "application_id",
                    "application_id must match ^[a-z][a-z0-9_]{1,62}$",
                )
            )
        previous = seen_ids.get(record.application_id)
        if previous is not None and previous != record.repository_id:
            bucket.append(
                _issue(
                    "duplicate_app_id",
                    "blocking",
                    record,
                    None,
                    "application_id",
                    f"application_id already used by {previous}",
                )
            )
        else:
            seen_ids[record.application_id] = record.repository_id

        origins_in_record: dict[str, str] = {}
        for env_name, env in record.environments.items():
            field = f"environments.{env_name}"
            if env_name not in VALID_ENV:
                bucket.append(
                    _issue(
                        "bad_env",
                        "blocking",
                        record,
                        env_name,
                        field,
                        f"unknown environment {env_name}",
                    )
                )
                continue
            _check_base_url(bucket, record, env_name, env.base_url)
            if env.spec_fixture and env_name != "local":
                bucket.append(
                    _issue(
                        "fixture_outside_local",
                        "blocking",
                        record,
                        env_name,
                        f"{field}.spec_fixture",
                        "spec_fixture is only allowed on the local environment",
                    )
                )
            if env.enabled and env_name != "local" and not env.auth_audience:
                bucket.append(
                    _issue(
                        "audience_missing",
                        "warning",
                        record,
                        env_name,
                        f"{field}.auth_audience",
                        "non-local environment has no auth audience",
                    )
                )
            origin = _origin_key(env.base_url)
            if origin:
                other_env = origins_in_record.get(origin)
                if other_env is not None:
                    bucket.append(
                        _issue(
                            "env_origin_reuse",
                            "blocking",
                            record,
                            env_name,
                            f"{field}.base_url",
                            f"same origin already used by environment {other_env}",
                        )
                    )
                else:
                    origins_in_record[origin] = env_name
                shared = origins_by_env.setdefault(env_name, {})
                owner = shared.get(origin)
                if owner is not None and owner != record.application_id:
                    bucket.append(
                        _issue(
                            "origin_collision",
                            "blocking",
                            record,
                            env_name,
                            f"{field}.base_url",
                            f"origin already used by {owner}",
                        )
                    )
                else:
                    shared[origin] = record.application_id
    return issues


def _check_base_url(
    bucket: list[RegistryIssue],
    record: RepositoryRecord,
    env_name: str,
    base_url: str,
) -> None:
    field = f"environments.{env_name}.base_url"
    if not base_url:
        return
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    loopback = host in {"localhost", "127.0.0.1", "::1"}
    http_ok = parsed.scheme == "http" and loopback and env_name == "local"
    if parsed.scheme not in {"https", "http"} or (parsed.scheme == "http" and not http_ok):
        bucket.append(_issue("bad_base_url", "blocking", record, env_name, field, "base_url scheme is not allowed"))
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        bucket.append(
            _issue("bad_base_url", "blocking", record, env_name, field, "base_url must not include userinfo, query, or fragment")
        )
    if host and _is_non_loopback_ip(host):
        bucket.append(_issue("ip_literal_host", "blocking", record, env_name, field, "host must not be a non-loopback IP"))
    markers = _host_markers(host)
    expected = _ENV_MARKERS.get(env_name, frozenset())
    if env_name == "local":
        if markers:
            bucket.append(_issue("env_mismatch", "blocking", record, env_name, field, "local host must not carry another environment marker"))
    elif markers and markers != expected and not markers <= expected:
        bucket.append(
            _issue(
                "env_mismatch",
                "blocking",
                record,
                env_name,
                field,
                "host environment marker does not match this environment",
            )
        )
    if len(markers) > 1 and not markers <= expected:
        bucket.append(_issue("env_mismatch", "blocking", record, env_name, field, "host carries markers from more than one environment"))


def _host_markers(host: str) -> frozenset[str]:
    tokens = {part for part in re.split(r"[.\-]", host) if part}
    return frozenset(token for token in tokens if token in _ALL_MARKERS)


def _is_non_loopback_ip(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return not addr.is_loopback


def _origin_key(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc.lower()}{path}"


def _issue(
    code: str,
    severity: Literal["blocking", "warning"],
    record: RepositoryRecord,
    environment: str | None,
    field: str,
    message: str,
) -> RegistryIssue:
    return RegistryIssue(
        code=code,
        severity=severity,
        application_id=record.application_id,
        environment=environment,
        field=field,
        message=message,
    )
