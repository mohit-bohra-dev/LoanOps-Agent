"""Unit tests for PNMAC requested_destination resolution."""

from __future__ import annotations

from packages.common.auth0_destination import resolve_destination


def test_dev_plaisse_subdomain() -> None:
    assert (
        resolve_destination("https://escrowapi.dev.pennymac.plaisse.com/api/x")
        == "escrowapi"
    )
    assert (
        resolve_destination("https://feesapi.dev.pennymac.plaisse.com/") == "feesapi"
    )
    assert (
        resolve_destination("https://loanservicesapi.dev.pennymac.plaisse.com/api")
        == "loanservicesapi"
    )


def test_plaisse_dev_pnmac_suffix() -> None:
    assert (
        resolve_destination(
            "https://loanservicesapi-plaisse-dev.pnmac.com/api/Loans/1/Summary"
        )
        == "loanservicesapi"
    )
