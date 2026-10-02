"""Ingest redacted TAAC client config → enterprise applications graph."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from packages.capability_kg.ontology import (
    CLASS_APPLICATION,
    CLASS_AUTH_PROVIDER,
    CLASS_DATA_STORE,
    CLASS_ENTERPRISE,
    CLASS_EVENT_TOPIC,
    DEFAULT_NAMESPACE,
    PRED_CONN_KEY,
    PRED_HOSTS,
    PRED_PACKAGE_ID,
    PRED_SERVICE_URL_KEY,
    PRED_TOPIC_NAME,
    loanops_ns,
)
from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS


def _safe(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_")[:120]


def url_key_to_app_id(key: str) -> str:
    """FeesApiUrl → fees; LoanServicesUrl → loanservices; EscrowManagerApiUrl → escrow."""
    name = key
    for suffix in ("ApiUrl", "Url", "BaseUrl"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    name = re.sub(r"(Manager|Batch|Shared|Hangfire)$", "", name, flags=re.I)
    return _safe(name.lower()) or "unknown"


def host_from_url(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:  # noqa: BLE001
        return ""


def normalize_topic(value: str) -> str:
    """Strip ARN and svt-{env}- prefix → canonical topic name."""
    name = value.rsplit(":", 1)[-1]
    return re.sub(r"^svt-(dev|stg|prd)-", "", name, flags=re.I)


def _catalog_from_connection(value: str) -> str | None:
    m = re.search(r"(?:initial\s+catalog|database)\s*=\s*([^;]+)", value, flags=re.I)
    if not m:
        return None
    return m.group(1).strip().strip("&quot;").strip('"')


def build_enterprise_graph(
    taac: dict[str, Any],
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> Graph:
    ns = loanops_ns(namespace)
    g = Graph()
    g.bind("loanops", ns)
    g.bind("rdfs", RDFS)

    enterprise = ns["enterprise_pennymac"]
    g.add((enterprise, RDF.type, ns[CLASS_ENTERPRISE]))
    g.add((enterprise, RDFS.label, Literal(str(taac.get("Title") or "Enterprise"))))

    # Auth0
    auth0 = taac.get("Auth0") or {}
    domain = (auth0.get("Domain") or "") if isinstance(auth0, dict) else ""
    audience = ""
    if isinstance(auth0, dict):
        api = auth0.get("Api") or {}
        if isinstance(api, dict):
            audience = str(api.get("Identifier") or "")
    auth = ns["auth_auth0"]
    g.add((auth, RDF.type, ns[CLASS_AUTH_PROVIDER]))
    g.add((auth, RDFS.label, Literal("Auth0")))
    if domain:
        g.add((auth, RDFS.comment, Literal(f"domain={domain}; audience={audience}")))

    service_urls = taac.get("ServiceUrls") or {}
    if isinstance(service_urls, dict):
        for key, url in service_urls.items():
            if not isinstance(url, str):
                continue
            app_id = url_key_to_app_id(str(key))
            app = ns[f"app_{app_id}"]
            g.add((app, RDF.type, ns[CLASS_APPLICATION]))
            g.add((app, RDFS.label, Literal(app_id)))
            g.add((app, ns[PRED_SERVICE_URL_KEY], Literal(str(key))))
            host = host_from_url(url)
            if host:
                # Redacted fixtures may use example.invalid hosts
                g.add((app, ns[PRED_HOSTS], Literal(host)))

    features = taac.get("FeatureManagement") or {}
    if isinstance(features, dict):
        for feat, enabled in features.items():
            if str(enabled).lower() not in {"true", "1"}:
                continue
            # EscrowManagerApiEnabled → escrow
            name = str(feat)
            for suffix in ("ApiEnabled", "Enabled", "WebEnabled"):
                if name.endswith(suffix):
                    name = name[: -len(suffix)]
                    break
            app_id = _safe(name.lower())
            app = ns[f"app_{app_id}"]
            g.add((app, RDF.type, ns[CLASS_APPLICATION]))
            g.add((app, RDFS.label, Literal(app_id)))

    conns = taac.get("ConnectionStrings") or {}
    if isinstance(conns, dict):
        for key, value in conns.items():
            if not isinstance(value, str):
                continue
            store_id = _safe(str(key).lower())
            store = ns[f"db_{store_id}"]
            g.add((store, RDF.type, ns[CLASS_DATA_STORE]))
            g.add((store, ns[PRED_CONN_KEY], Literal(str(key))))
            catalog = _catalog_from_connection(value)
            label = catalog or str(key)
            g.add((store, RDFS.label, Literal(label)))

    aws = taac.get("AWS") or {}
    sqs = (aws.get("SQS") or {}) if isinstance(aws, dict) else {}
    if isinstance(sqs, dict):
        for key, qname in sqs.items():
            if not isinstance(qname, str):
                continue
            topic = ns[f"topic_{_safe(normalize_topic(qname))}"]
            g.add((topic, RDF.type, ns[CLASS_EVENT_TOPIC]))
            g.add((topic, ns[PRED_TOPIC_NAME], Literal(normalize_topic(qname))))
            g.add((topic, RDFS.label, Literal(str(qname))))
            g.add((topic, ns[PRED_PACKAGE_ID], Literal(str(key))))

    return g


def ingest_taac_file(
    path: str | Path,
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> Graph:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("TAAC config must be a JSON object")
    return build_enterprise_graph(raw, namespace=namespace)


def load_service_url_map(path: str | Path) -> dict[str, str]:
    """key → application_id from TAAC ServiceUrls."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    urls = raw.get("ServiceUrls") or {}
    out: dict[str, str] = {}
    if isinstance(urls, dict):
        for key in urls:
            out[str(key)] = url_key_to_app_id(str(key))
    return out


def load_connection_catalogs(path: str | Path) -> dict[str, str]:
    """connection key → database catalog name (redacted ok)."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    conns = raw.get("ConnectionStrings") or {}
    out: dict[str, str] = {}
    if isinstance(conns, dict):
        for key, value in conns.items():
            if isinstance(value, str):
                cat = _catalog_from_connection(value)
                if cat:
                    out[str(key)] = cat
    return out
