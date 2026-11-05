"""Resolver aliases and ambiguity."""

from __future__ import annotations

from packages.api_index.records import Ambiguous, Resolved, UnifiedOperation
from packages.api_index.resolver import OperationResolver


def _op(
    *,
    app: str,
    public_id: str,
    path: str,
    eakg_key: str | None = None,
    capability_ids: list[str] | None = None,
) -> UnifiedOperation:
    np = path.lower().replace("{loan_id}", "{}").replace("{id}", "{}")
    return UnifiedOperation(
        uid=f"{app}|GET|{np}",
        public_id=public_id,
        application_id=app,
        application_label=app.title(),
        environment="local",
        method="get",
        path=path,
        normalized_path=np,
        read_only=True,
        callable=True,
        eakg_operation_key=eakg_key,
        capability_ids=capability_ids or [],
        join="suffix",
    )


def test_aliases_resolve_short_and_qualified() -> None:
    resolver = OperationResolver(
        [
            _op(
                app="loanservices",
                public_id="loanservices:getLoanSummary",
                path="/api/Loans/{loan_id}/Summary",
                eakg_key="GetLoanSummary",
                capability_ids=["get_loan_summary"],
            )
        ]
    )
    for ref in (
        "loanservices:getLoanSummary",
        "getLoanSummary",
        "GetLoanSummary",
        "get_loan_summary",
    ):
        hit = resolver.resolve(ref)
        assert isinstance(hit, Resolved)
        assert hit.public_id == "loanservices:getLoanSummary"


def test_resolve_by_openapi_path_tail_when_public_id_is_slug() -> None:
    """Agents pass GetEscrowByLoanNumber when swagger has no operationId."""
    resolver = OperationResolver(
        [
            _op(
                app="escrow",
                public_id="escrow:GET_api_escrow_getescrowbyloannumber",
                path="/api/Escrow/GetEscrowByLoanNumber",
            )
        ]
    )
    hit = resolver.resolve("GetEscrowByLoanNumber")
    assert isinstance(hit, Resolved)
    assert hit.public_id == "escrow:GET_api_escrow_getescrowbyloannumber"


def test_ambiguous_when_two_apps_share_short_name() -> None:
    resolver = OperationResolver(
        [
            _op(app="fees", public_id="fees:getFees", path="/api/fees/{id}"),
            _op(app="escrow", public_id="escrow:getFees", path="/api/escrow/fees/{id}"),
        ]
    )
    hit = resolver.resolve("getFees")
    assert isinstance(hit, Ambiguous)
    assert len(hit.candidates) == 2
    scoped = resolver.resolve("getFees", application_id="fees")
    assert isinstance(scoped, Resolved)
    assert scoped.public_id == "fees:getFees"
