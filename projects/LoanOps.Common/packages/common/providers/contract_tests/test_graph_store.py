"""Contract tests for AbstractGraphStore (Fake + HTTP against a fake ASGI app)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from packages.common.providers.graph_store import (
    FakeGraphStore,
    GraphStoreQueryError,
    HttpSparqlGraphStore,
    named_graph_iri,
)

_SAMPLE_TTL = """\
@prefix lo: <https://loanops.local/ontology/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

lo:op1 a lo:APIOperation ;
    lo:operationId "getLoan" ;
    lo:httpMethod "GET" ;
    lo:httpPath "/api/Loans/{id}" ;
    rdfs:label "getLoan" .
"""


@pytest.fixture
def fake_store() -> FakeGraphStore:
    return FakeGraphStore()


@pytest.mark.asyncio
async def test_fake_replace_and_select(fake_store: FakeGraphStore) -> None:
    iri = named_graph_iri("loanservices")
    await fake_store.replace_named_graph(iri, _SAMPLE_TTL)
    data = await fake_store.query(
        """
        PREFIX lo: <https://loanops.local/ontology/>
        SELECT ?oid ?method WHERE {
          GRAPH ?g {
            ?op a lo:APIOperation ;
                lo:operationId ?oid ;
                lo:httpMethod ?method .
          }
        }
        """
    )
    bindings = data["results"]["bindings"]
    assert len(bindings) == 1
    assert bindings[0]["oid"]["value"] == "getLoan"
    assert bindings[0]["method"]["value"] == "GET"


@pytest.mark.asyncio
async def test_fake_replace_clears_prior(fake_store: FakeGraphStore) -> None:
    iri = named_graph_iri("fees")
    await fake_store.replace_named_graph(iri, _SAMPLE_TTL)
    await fake_store.replace_named_graph(
        iri,
        """\
@prefix lo: <https://loanops.local/ontology/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
lo:op2 a lo:APIOperation ; lo:operationId "getFee" .
""",
    )
    data = await fake_store.query(
        """
        PREFIX lo: <https://loanops.local/ontology/>
        SELECT ?oid WHERE {
          GRAPH ?g { ?op a lo:APIOperation ; lo:operationId ?oid . }
        }
        """
    )
    oids = {b["oid"]["value"] for b in data["results"]["bindings"]}
    assert oids == {"getFee"}


@pytest.mark.asyncio
async def test_http_store_against_fake_endpoint() -> None:
    """HTTP client posts SPARQL query/update; no GraphDB required."""

    state: dict[str, Any] = {"turtle": "", "updates": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        body = request.content.decode("utf-8")
        if path.endswith("/statements") or "update" in body.lower()[:80]:
            state["updates"] += 1
            if "INSERT DATA" in body or "CLEAR" in body:
                state["loaded"] = True
            return httpx.Response(204)
        if "SELECT" in body or request.headers.get("content-type", "").startswith(
            "application/sparql-query"
        ):
            return httpx.Response(
                200,
                json={
                    "head": {"vars": ["oid"]},
                    "results": {
                        "bindings": [{"oid": {"type": "literal", "value": "getLoan"}}]
                    },
                },
            )
        return httpx.Response(400, text=f"unexpected {path}")

    transport = httpx.MockTransport(handler)
    store = HttpSparqlGraphStore(
        query_url="http://graph.test/repositories/loanops",
        update_url="http://graph.test/repositories/loanops/statements",
    )
    store._client = httpx.AsyncClient(transport=transport, timeout=5)

    await store.replace_named_graph(named_graph_iri("escrow"), _SAMPLE_TTL)
    assert state["updates"] >= 1

    data = await store.query("SELECT ?oid WHERE { ?s ?p ?oid }")
    assert data["results"]["bindings"][0]["oid"]["value"] == "getLoan"
    await store.aclose()


@pytest.mark.asyncio
async def test_http_query_error_surface() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    store = HttpSparqlGraphStore(
        query_url="http://graph.test/repositories/loanops",
        update_url="http://graph.test/repositories/loanops/statements",
    )
    store._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5)
    with pytest.raises(GraphStoreQueryError):
        await store.query("SELECT * WHERE { ?s ?p ?o }")
    await store.aclose()


def test_named_graph_iri() -> None:
    assert named_graph_iri("loanservices").endswith("namedGraph/loanservices")
