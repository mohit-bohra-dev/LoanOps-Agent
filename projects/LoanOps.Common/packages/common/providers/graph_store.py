"""Graph store Provider — SPARQL 1.1 HTTP (ADR-026).

Protocol + HTTP client + test double live here (precedent: credential_broker.py).
Only ``factory.get_graph_store`` imports the concrete HTTP class from app code.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import httpx
from rdflib import Dataset, Graph, Literal, URIRef
from rdflib.term import BNode, Identifier, Variable

DEFAULT_GRAPH_NAMESPACE = "https://loanops.local/ontology/"


class GraphStoreError(Exception):
    """Base error for graph store failures."""


class GraphStoreUnavailable(GraphStoreError):
    """Endpoint unreachable or returned a transport error."""


class GraphStoreQueryError(GraphStoreError):
    """SPARQL query/update rejected by the endpoint."""


def named_graph_iri(
    repository_id: str,
    *,
    namespace: str = DEFAULT_GRAPH_NAMESPACE,
) -> str:
    """Canonical named-graph IRI for one repository shard."""
    base = namespace if namespace.endswith("/") or namespace.endswith("#") else f"{namespace}/"
    return f"{base}namedGraph/{repository_id}"


class AbstractGraphStore(ABC):
    """SPARQL query + named-graph replace surface."""

    @abstractmethod
    async def query(self, sparql: str) -> dict[str, Any]:
        """Run SPARQL SELECT/ASK; return SPARQL Results JSON."""

    @abstractmethod
    async def update(self, sparql: str) -> None:
        """Run SPARQL UPDATE (CLEAR / INSERT / DELETE)."""

    @abstractmethod
    async def replace_named_graph(self, graph_iri: str, turtle: str) -> None:
        """Replace all triples in ``graph_iri`` with ``turtle`` content."""

    async def aclose(self) -> None:
        """Release HTTP resources (optional)."""


class HttpSparqlGraphStore(AbstractGraphStore):
    """SPARQL 1.1 over HTTP — GraphDB Free locally, Neptune RDF later."""

    def __init__(
        self,
        *,
        query_url: str,
        update_url: str,
        auth_token: str = "",
        timeout_seconds: int = 30,
    ) -> None:
        if not query_url.strip():
            raise GraphStoreError("GRAPH_STORE__QUERY_URL is required")
        if not update_url.strip():
            raise GraphStoreError("GRAPH_STORE__UPDATE_URL is required")
        self._query_url = query_url.strip()
        self._update_url = update_url.strip()
        self._auth_token = auth_token.strip()
        self._timeout = timeout_seconds
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    def _headers(self, *, content_type: str, accept: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": content_type}
        if accept:
            headers["Accept"] = accept
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        return headers

    def _auth_headers_only(self) -> dict[str, str]:
        if not self._auth_token:
            return {}
        return {"Authorization": f"Bearer {self._auth_token}"}

    async def query(self, sparql: str) -> dict[str, Any]:
        try:
            resp = await self._client.post(
                self._query_url,
                content=sparql.encode("utf-8"),
                headers=self._headers(
                    content_type="application/sparql-query",
                    accept="application/sparql-results+json",
                ),
            )
        except httpx.HTTPError as exc:
            raise GraphStoreUnavailable(f"SPARQL query failed: {exc}") from exc
        if resp.status_code >= 400:
            raise GraphStoreQueryError(
                f"SPARQL query HTTP {resp.status_code}: {resp.text[:500]}"
            )
        try:
            data: dict[str, Any] = resp.json()
        except json.JSONDecodeError as exc:
            raise GraphStoreQueryError("SPARQL query returned non-JSON body") from exc
        return data

    async def update(self, sparql: str) -> None:
        try:
            resp = await self._client.post(
                self._update_url,
                content=sparql.encode("utf-8"),
                headers=self._headers(content_type="application/sparql-update"),
            )
        except httpx.HTTPError as exc:
            raise GraphStoreUnavailable(f"SPARQL update failed: {exc}") from exc
        if resp.status_code < 400:
            return
        # GraphDB /statements often accepts form-encoded update=.
        try:
            resp2 = await self._client.post(
                self._update_url,
                data={"update": sparql},
                headers=self._auth_headers_only(),
            )
        except httpx.HTTPError as exc:
            raise GraphStoreUnavailable(f"SPARQL update failed: {exc}") from exc
        if resp2.status_code >= 400:
            raise GraphStoreQueryError(
                f"SPARQL update HTTP {resp.status_code}/{resp2.status_code}: "
                f"{resp.text[:300]} | {resp2.text[:300]}"
            )

    async def replace_named_graph(self, graph_iri: str, turtle: str) -> None:
        """Atomic replace via SPARQL UPDATE (CLEAR + INSERT). No DELETE-then-fail path."""
        g = Graph()
        g.parse(data=turtle, format="turtle")
        ntriples = g.serialize(format="nt")
        if isinstance(ntriples, bytes):
            ntriples = ntriples.decode("utf-8")
        update = (
            f"CLEAR SILENT GRAPH <{graph_iri}> ;\n"
            f"INSERT DATA {{ GRAPH <{graph_iri}> {{\n{ntriples}\n}} }}\n"
        )
        await self.update(update)

    async def aclose(self) -> None:
        await self._client.aclose()


class FakeGraphStore(AbstractGraphStore):
    """In-process SPARQL double for unit/contract tests (not a product backend)."""

    def __init__(self) -> None:
        self._ds = Dataset()

    async def query(self, sparql: str) -> dict[str, Any]:
        try:
            result = self._ds.query(sparql)
        except Exception as exc:  # noqa: BLE001 — surface as query error
            raise GraphStoreQueryError(str(exc)) from exc
        return _rdflib_result_to_json(result)

    async def update(self, sparql: str) -> None:
        try:
            self._ds.update(sparql)
        except Exception as exc:  # noqa: BLE001
            raise GraphStoreQueryError(str(exc)) from exc

    async def replace_named_graph(self, graph_iri: str, turtle: str) -> None:
        ctx = URIRef(graph_iri)
        # DROP + recreate (avoid SPARQL CLEAR — slow on large graphs in RDFLib).
        try:
            self._ds.remove_graph(self._ds.graph(ctx))
        except Exception:  # noqa: BLE001
            pass
        g = Graph(store=self._ds.store, identifier=ctx)
        g.parse(data=turtle, format="turtle")


def _term_to_binding(val: Identifier) -> dict[str, str]:
    if isinstance(val, URIRef):
        return {"type": "uri", "value": str(val)}
    if isinstance(val, BNode):
        return {"type": "bnode", "value": str(val)}
    if isinstance(val, Literal):
        entry: dict[str, str] = {"type": "literal", "value": str(val)}
        if val.datatype is not None:
            entry["datatype"] = str(val.datatype)
        if val.language:
            entry["xml:lang"] = str(val.language)
        return entry
    return {"type": "literal", "value": str(val)}


def _rdflib_result_to_json(result: Any) -> dict[str, Any]:
    """Convert RDFLib query result to SPARQL Results JSON shape."""
    if getattr(result, "type", None) == "ASK":
        return {"head": {}, "boolean": bool(result.askAnswer)}
    raw_vars = list(result.vars) if result.vars else []
    var_names = [str(v) for v in raw_vars]
    bindings: list[dict[str, Any]] = []
    for row in result:
        binding: dict[str, Any] = {}
        for var in raw_vars:
            name = str(var)
            try:
                val = row[var] if isinstance(var, Variable) else row[name]
            except Exception:  # noqa: BLE001
                try:
                    val = row[name]
                except Exception:  # noqa: BLE001
                    continue
            if val is None:
                continue
            binding[name] = _term_to_binding(val)
        bindings.append(binding)
    return {
        "head": {"vars": var_names},
        "results": {"bindings": bindings},
    }
