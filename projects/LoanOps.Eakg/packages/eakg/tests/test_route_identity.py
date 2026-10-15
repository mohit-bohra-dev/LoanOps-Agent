"""Tests for canonical route identity and multi-adapter merge."""

from __future__ import annotations

from packages.capability_kg.ontology import CLASS_API_OPERATION
from packages.eakg.graph_build import interface_to_graph
from packages.eakg.join import eakg_operation_local_name
from packages.eakg.merge_api import merge_operation_facts
from packages.eakg.models import ApiOperationFact, Evidence, RepoInterface
from packages.eakg.route_identity import normalize_path, route_key, route_key_hash
from rdflib.namespace import RDF


def _ev(detector: str, line: int = 1, version: str = "1.0.0") -> Evidence:
    return Evidence(
        repository_id="app",
        commit_sha="abc",
        file_path="src/a.cs",
        line_start=line,
        line_end=line,
        detector_id=detector,
        detector_version=version,
        confidence=0.9,
    )


def test_normalize_path_frameworks() -> None:
    assert normalize_path("/items/:id") == "/items/{id}"
    assert normalize_path("/items/<int:id>") == "/items/{id}"
    assert normalize_path("/items/{id:int}") == "/items/{id}"
    assert normalize_path("items//x/") == "/items/x"


def test_route_key_stable() -> None:
    assert route_key("get", "/Items/:id") == "GET:/Items/{id}"
    assert route_key_hash("GET:/a") == route_key_hash("GET:/a")


def test_merge_controller_beats_minimal_and_keeps_evidence() -> None:
    ctrl = ApiOperationFact(
        operation_key="GET:/api/x:C.Get",
        http_method="GET",
        http_path="/api/x",
        controller="LoansController",
        action="Get",
        authz_policy="Authorize",
        authz_source="attribute",
        read_only=True,
        evidence=[_ev("dotnet_roslyn", 10, "2.1.0")],
    )
    mini = ApiOperationFact(
        operation_key="GET:/api/x:MinimalApi.Get",
        http_method="GET",
        http_path="/api/x",
        controller="MinimalApi",
        action="Get",
        authz_policy=None,
        authz_source="unknown",
        read_only=True,
        evidence=[_ev("dotnet_roslyn", 20, "2.1.0")],
    )
    result = merge_operation_facts(
        [mini, ctrl],
        repository_id="app",
        application_id="app",
        commit_sha="abc",
    )
    assert len(result.facts) == 1
    assert result.facts[0].controller == "LoansController"
    assert result.facts[0].authz_source == "attribute"
    assert len(result.facts[0].evidence) == 2


def test_graph_distinct_uris_same_action_name() -> None:
    f1 = ApiOperationFact(
        operation_key="GET:/a:main",
        http_method="GET",
        http_path="/a",
        controller="Program",
        action="main",
        authz_policy=None,
        authz_source="unknown",
        read_only=True,
        evidence=[_ev("treesitter_node")],
    )
    f2 = ApiOperationFact(
        operation_key="GET:/b:main",
        http_method="GET",
        http_path="/b",
        controller="Program",
        action="main",
        authz_policy=None,
        authz_source="unknown",
        read_only=True,
        evidence=[_ev("treesitter_node")],
    )
    iface = RepoInterface(repository_id="app", application_id="app", commit_sha="abc")
    g, _eg = interface_to_graph(iface, [f1, f2])
    ops = [s for s, p, o in g if p == RDF.type and str(o).endswith(CLASS_API_OPERATION)]
    assert len(ops) == 2
    assert ops[0] != ops[1]
    locals_ = {str(u).rsplit("/", 1)[-1] for u in ops}
    assert eakg_operation_local_name("app", "main", "GET", "/a") in locals_
    assert eakg_operation_local_name("app", "main", "GET", "/b") in locals_
