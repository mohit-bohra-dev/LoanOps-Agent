"""Path normalize and OpenAPI↔EAKG join."""

from __future__ import annotations

from types import SimpleNamespace

from packages.api_index.records import build_operations_from_openapi, normalize_path, uid


def test_normalize_path_collapses_params_and_case() -> None:
    assert normalize_path("/api/Loans/{loan_id}/Summary") == "/api/loans/{}/summary"
    assert normalize_path("/{id:int}/Summary") == "/{}/summary"
    assert "?" not in normalize_path("/api/fees?x=1")
    assert normalize_path("\\api\\Fees\\{id}") == "/api/fees/{}"


def test_normalize_controller_token() -> None:
    assert (
        normalize_path("/[controller]/{id}/Summary", controller="LoansController")
        == "/loans/{}/summary"
    )


def test_suffix_join_matches_controller_prefix() -> None:
    doc = {
        "openapi": "3.0.3",
        "info": {"title": "Loan Services", "version": "1"},
        "paths": {
            "/api/Loans/{loan_id}/Summary": {
                "get": {
                    "operationId": "getLoanSummary",
                    "summary": "Get loan summary",
                }
            }
        },
    }
    eakg = [
        SimpleNamespace(
            http_method="get",
            http_path="/{id}/Summary",
            controller="LoansController",
            action="GetLoanSummary",
            operation_key="GetLoanSummary",
            authz_policy="LoanRead",
            authz_source="attribute",
            read_only=True,
        )
    ]
    ops = build_operations_from_openapi(
        application_id="loanservices",
        application_label="Loan Services",
        environment="local",
        document=doc,
        base_url="http://127.0.0.1:9103",
        spec_hash="abc",
        eakg_ops=eakg,
    )
    assert len(ops) == 1
    assert ops[0].join == "suffix"
    assert ops[0].public_id == "loanservices:getLoanSummary"
    assert ops[0].uid == uid("loanservices", "get", "/api/loans/{}/summary")
    assert ops[0].callable is True
    assert ops[0].code_unit == "LoansController.GetLoanSummary"
