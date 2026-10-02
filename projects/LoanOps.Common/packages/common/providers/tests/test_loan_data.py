"""Tests for loan data providers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from packages.common.providers.loan_data import (
    FixtureLoanProvider,
    JsonFileLoanProvider,
    RestApiLoanProvider,
    _apply_delinquencies,
    _merge_loan_sources,
    _normalize_escrow_breakdown,
    _normalize_loan,
    _normalize_payment_schedule,
    _normalize_search_results,
)
from packages.common.settings import LoanApiConfig


def _test_fixtures_root() -> Path:
    return Path(__file__).parent / "fixtures" / "loan_api"


def test_normalize_loan_maps_camel_case_fields() -> None:
    raw = {
        "loanId": "100245",
        "borrower": {"firstName": "Alex", "lastName": "Rivera"},
        "propertyState": "CA",
        "loanStatus": "active",
        "productType": "Conventional 30yr fixed",
        "hasEscrow": True,
        "currentBalance": 324188.42,
        "nextDueDate": "2026-06-01",
        "daysDelinquent": 0,
        "lastPaymentDate": "2026-05-01",
        "loanFlags": [],
    }
    loan = _normalize_loan(raw)
    assert loan["loan_id"] == "100245"
    assert loan["borrower_first_name"] == "Alex"
    assert loan["borrower_last_name"] == "Rivera"
    assert loan["state"] == "CA"
    assert loan["escrowed"] is True


def test_normalize_search_results_unwraps_envelope() -> None:
    payload = {
        "results": [
            {
                "loan_id": "100311",
                "borrower_first_name": "Jamie",
                "borrower_last_name": "Chen",
                "state": "TX",
                "status": "active",
                "product": "FHA",
                "escrowed": True,
                "current_balance_usd": 100.0,
                "delinquency_days": 0,
                "flags": [],
            }
        ]
    }
    loans = _normalize_search_results(payload)
    assert len(loans) == 1
    assert loans[0]["loan_id"] == "100311"


@pytest.mark.asyncio
async def test_json_file_provider_lookup_known_loan() -> None:
    provider = JsonFileLoanProvider()
    loan = await provider.get_loan("100245")
    assert loan is not None
    assert loan["borrower_first_name"] == "Alex"


def test_normalize_loan_maps_loan_services_summary() -> None:
    raw = {
        "LoanId": 1000002245,
        "LoanActiveFlag": False,
        "PaidOffFlag": False,
        "PropertyRegion": "AZ",
        "MortgageTypeDescription": "Conventional W/O PMI",
        "EscrowFlag": True,
        "UnpaidPrincipalBalanceAmount": 0.0,
        "NextPaymentDueDate": "2010-07-01T00:00:00",
        "LastPaymentReceivedDate": "2010-06-10T00:00:00",
        "DelinquentPaymentCount": 0,
        "CurrentInterestRate": 0.03328,
        "CurrentMonthlyPaymentAmount": 681.15,
        "CurrentEscrowMonthlyPaymentAmount": 284.73,
        "CurrentTotalMonthlyPaymentAmount": 965.88,
        "LoanMaturityDate": "2036-12-01T00:00:00",
        "InvestorName": "FNBN I, LLC",
        "LossMitigationTemplateDescription": "Short Sale",
        "ForeclosureStatusDescription": "Removed",
        "DelinquentAtBoardingFlag": True,
        "BorrowerSummary": [
            {
                "BorrowerOrdinal": 1,
                "BorrowerFirstName": "Gvta",
                "BorrowerLastName": "Ferdinandsen",
            }
        ],
    }
    loan = _normalize_loan(raw)
    assert loan["loan_id"] == "1000002245"
    assert loan["borrower_first_name"] == "Gvta"
    assert loan["borrower_last_name"] == "Ferdinandsen"
    assert loan["state"] == "AZ"
    assert loan["status"] == "inactive"
    assert loan["product"] == "Conventional W/O PMI"
    assert loan["escrowed"] is True
    assert loan["current_balance_usd"] == 0.0
    assert loan["next_due_date"] == "2010-07-01"
    assert loan["last_payment_date"] == "2010-06-10"
    assert loan["delinquency_days"] == 0
    assert loan["current_interest_rate"] == pytest.approx(0.03328)
    assert loan["monthly_pi_usd"] == pytest.approx(681.15)
    assert loan["monthly_escrow_usd"] == pytest.approx(284.73)
    assert loan["total_monthly_payment_usd"] == pytest.approx(965.88)
    assert loan["maturity_date"] == "2036-12-01"
    assert loan["loan_active"] is False
    assert loan["investor_name"] == "FNBN I, LLC"
    assert "loss_mitigation:Short Sale" in loan["flags"]


def test_apply_delinquencies_overrides_payment_count() -> None:
    merged = _apply_delinquencies(
        {"DelinquentPaymentCount": 0},
        [{"DelinquencyCode": "4"}],
    )
    assert merged["DelinquentPaymentCount"] == 4


def test_merge_loan_sources_injects_borrowers_and_record() -> None:
    merged = _merge_loan_sources(
        summary={"LoanId": 1000002245, "PropertyRegion": "AZ"},
        borrowers=[{"BorrowerOrdinal": 1, "BorrowerFirstName": "Gvta", "BorrowerLastName": "F"}],
        delinquencies=[{"DelinquencyCode": "4"}],
        record={"ActiveFlag": False, "UnpaidPrincipalBalanceAmount": 0.0},
        loan_id="1000002245",
    )
    loan = _normalize_loan(merged, loan_id="1000002245")
    assert loan["borrower_first_name"] == "Gvta"
    assert loan["status"] == "inactive"


def test_normalize_payment_schedule_filters_by_next_due_date() -> None:
    schedules = [
        {
            "PaymentDueMonth": "2010-06-01T00:00:00",
            "MonthlyPaymentPrincipalAmount": 100.0,
            "MonthlyPaymentInterestAmount": 50.0,
            "PendingEscrowPaymentAmount": 25.0,
            "TotalPaymentAmount": 175.0,
        },
        {
            "PaymentDueMonth": "2010-07-01T00:00:00",
            "MonthlyPaymentPrincipalAmount": 110.0,
            "MonthlyPaymentInterestAmount": 45.0,
            "PendingEscrowPaymentAmount": 25.0,
            "TotalPaymentAmount": 180.0,
        },
    ]
    result = _normalize_payment_schedule(
        "1000002245",
        schedules,
        months=2,
        next_due_date="2010-07-01",
    )
    assert len(result["schedule"]) == 1
    assert result["schedule"][0]["due_date"] == "2010-07-01"
    assert result["schedule"][0]["principal"] == 110.0


def test_normalize_escrow_breakdown_stitches_summary_and_escrows() -> None:
    summary = {
        "EscrowBalanceAmount": 0.0,
        "CurrentEscrowMonthlyPaymentAmount": 284.73,
        "MonthlyCountyTaxAmount": 122.6,
        "MonthlyHazardInsuranceAmount": 32.67,
        "NextPaymentDueDate": "2010-07-01T00:00:00",
        "MonthlyOverageShortageAmount": 129.46,
    }
    escrows = [{"LastEscrowAnalysisDate": "2010-06-21T00:00:00"}]
    result = _normalize_escrow_breakdown("1000002245", summary, escrows)
    assert result["escrow_balance_usd"] == 0.0
    assert result["monthly_escrow_usd"] == pytest.approx(284.73)
    assert result["as_of"] == "2010-06-21"
    assert "county_tax" in result["drivers"]
    assert "hazard_insurance" in result["drivers"]
    assert result["last_disbursements"] == []


@pytest.mark.asyncio
async def test_rest_api_provider_get_loan(monkeypatch: pytest.MonkeyPatch) -> None:
    config = LoanApiConfig(
        base_url="https://loanservicesapi-plaisse-dev.pnmac.com",
        api_key="test-token",
    )
    provider = RestApiLoanProvider(config)

    async def fake_summary(loan_id: str) -> dict[str, Any]:
        assert loan_id == "100245"
        return {
            "LoanId": 100245,
            "LoanActiveFlag": True,
            "PropertyRegion": "CA",
            "MortgageTypeDescription": "Conventional 30yr fixed",
            "EscrowFlag": True,
            "UnpaidPrincipalBalanceAmount": 324188.42,
            "NextPaymentDueDate": "2026-06-01T00:00:00",
            "DelinquentPaymentCount": 0,
            "LastPaymentReceivedDate": "2026-05-01T00:00:00",
        }

    async def fake_borrowers(loan_id: str) -> list[dict[str, Any]]:
        return [
            {
                "BorrowerOrdinal": 1,
                "BorrowerFirstName": "Alex",
                "BorrowerLastName": "Rivera",
            }
        ]

    async def fake_delinquencies(loan_id: str) -> list[dict[str, Any]]:
        return []

    async def fake_record(loan_id: str) -> dict[str, Any]:
        return {"ActiveFlag": True}

    monkeypatch.setattr(provider, "_fetch_summary", fake_summary)
    monkeypatch.setattr(provider, "_fetch_borrowers", fake_borrowers)
    monkeypatch.setattr(provider, "_fetch_delinquencies", fake_delinquencies)
    monkeypatch.setattr(provider, "_fetch_record", fake_record)

    loan = await provider.get_loan("100245")
    assert loan is not None
    assert loan["loan_id"] == "100245"
    assert loan["borrower_last_name"] == "Rivera"
    assert loan["status"] == "active"


@pytest.mark.asyncio
async def test_rest_api_provider_get_payment_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    config = LoanApiConfig(
        base_url="https://loanservicesapi-plaisse-dev.pnmac.com",
        api_key="test-token",
    )
    provider = RestApiLoanProvider(config)

    async def fake_summary(loan_id: str) -> dict[str, Any]:
        return {
            "LoanId": 100245,
            "LoanActiveFlag": True,
            "PropertyRegion": "CA",
            "MortgageTypeDescription": "Conventional 30yr fixed",
            "EscrowFlag": True,
            "UnpaidPrincipalBalanceAmount": 324188.42,
            "NextPaymentDueDate": "2026-06-01T00:00:00",
            "DelinquentPaymentCount": 0,
        }

    async def fake_schedules(loan_id: str) -> list[dict[str, Any]]:
        return [
            {
                "PaymentDueMonth": "2026-06-01T00:00:00",
                "MonthlyPaymentPrincipalAmount": 412.55,
                "MonthlyPaymentInterestAmount": 1180.12,
                "PendingEscrowPaymentAmount": 615.30,
                "TotalPaymentAmount": 2207.97,
            }
        ]

    monkeypatch.setattr(provider, "_fetch_summary", fake_summary)
    monkeypatch.setattr(provider, "_fetch_payment_schedules", fake_schedules)

    schedule = await provider.get_payment_schedule("100245", months=1)
    assert schedule["loan_id"] == "100245"
    assert len(schedule["schedule"]) == 1
    assert schedule["schedule"][0]["total"] == pytest.approx(2207.97)


@pytest.mark.asyncio
async def test_rest_api_provider_get_escrow_breakdown(monkeypatch: pytest.MonkeyPatch) -> None:
    config = LoanApiConfig(
        base_url="https://loanservicesapi-plaisse-dev.pnmac.com",
        api_key="test-token",
    )
    provider = RestApiLoanProvider(config)

    async def fake_summary(loan_id: str) -> dict[str, Any]:
        return {
            "LoanId": 100245,
            "LoanActiveFlag": True,
            "EscrowFlag": True,
            "EscrowBalanceAmount": 1842.10,
            "CurrentEscrowMonthlyPaymentAmount": 615.30,
            "MonthlyCountyTaxAmount": 100.0,
            "NextPaymentDueDate": "2026-06-01T00:00:00",
        }

    async def fake_escrows(loan_id: str) -> list[dict[str, Any]]:
        return [{"LastEscrowAnalysisDate": "2026-04-30T00:00:00"}]

    monkeypatch.setattr(provider, "_fetch_summary", fake_summary)
    monkeypatch.setattr(provider, "_fetch_escrows", fake_escrows)

    breakdown = await provider.get_escrow_breakdown("100245")
    assert breakdown["loan_id"] == "100245"
    assert breakdown["escrow_balance_usd"] == pytest.approx(1842.10)
    assert breakdown["monthly_escrow_usd"] == pytest.approx(615.30)


@pytest.mark.asyncio
async def test_json_file_provider_payment_schedule_for_100245() -> None:
    provider = JsonFileLoanProvider()
    schedule = await provider.get_payment_schedule("100245", months=2)
    assert schedule["loan_id"] == "100245"
    assert len(schedule["schedule"]) == 2
    assert schedule["schedule"][0]["due_date"] == "2026-06-01"


@pytest.mark.asyncio
async def test_rest_api_provider_search_by_name_unsupported() -> None:
    config = LoanApiConfig(
        base_url="https://loanservicesapi-plaisse-dev.pnmac.com",
        api_key="test-token",
    )
    provider = RestApiLoanProvider(config)
    with pytest.raises(NotImplementedError, match="not available"):
        await provider.search_by_name("Alex")


def test_rest_api_provider_requires_token() -> None:
    with pytest.raises(ValueError, match="API_KEY"):
        RestApiLoanProvider(LoanApiConfig(base_url="http://example.com", api_key=""))


@pytest.mark.asyncio
async def test_fixture_provider_get_loan_normalizes_upstream_shape() -> None:
    provider = FixtureLoanProvider(fixtures_dir=_test_fixtures_root())
    loan = await provider.get_loan("100245")
    assert loan is not None
    assert loan["loan_id"] == "100245"
    assert loan["borrower_first_name"] == "Alex"
    assert loan["borrower_last_name"] == "Rivera"
    assert loan["state"] == "CA"
    assert loan["status"] == "active"
    assert loan["escrowed"] is True
    assert loan["current_balance_usd"] == pytest.approx(324188.42)
    assert loan["next_due_date"] == "2026-06-01"
    assert loan["last_payment_date"] == "2026-05-01"
    assert loan["monthly_pi_usd"] == pytest.approx(1592.67)
    assert loan["investor_name"] == "Synthetic Investor LLC"


@pytest.mark.asyncio
async def test_fixture_provider_payment_schedule() -> None:
    provider = FixtureLoanProvider(fixtures_dir=_test_fixtures_root())
    schedule = await provider.get_payment_schedule("100245", months=2)
    assert schedule["loan_id"] == "100245"
    assert len(schedule["schedule"]) == 2
    assert schedule["schedule"][0]["due_date"] == "2026-06-01"
    assert schedule["schedule"][0]["total"] == pytest.approx(2207.97)


@pytest.mark.asyncio
async def test_fixture_provider_escrow_breakdown() -> None:
    provider = FixtureLoanProvider(fixtures_dir=_test_fixtures_root())
    breakdown = await provider.get_escrow_breakdown("100245")
    assert breakdown["loan_id"] == "100245"
    assert breakdown["monthly_escrow_usd"] == pytest.approx(615.3)
    assert breakdown["escrow_balance_usd"] == pytest.approx(1500.0)
    assert "county_tax" in breakdown["drivers"] or "hazard_insurance" in breakdown["drivers"]


@pytest.mark.asyncio
async def test_fixture_provider_search_by_name() -> None:
    provider = FixtureLoanProvider(fixtures_dir=_test_fixtures_root())
    matches = await provider.search_by_name("Alex")
    assert len(matches) == 1
    assert matches[0]["loan_id"] == "100245"
