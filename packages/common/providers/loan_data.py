"""Loan Data Provider Protocol and Implementations."""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx

from packages.common.settings import LoanApiConfig

logger = logging.getLogger(__name__)

# Common upstream field aliases → internal LoanSummary keys
_LOAN_ID_KEYS = ("loan_id", "loanId", "LoanId", "loanNumber", "loan_number", "id")
_FIRST_NAME_KEYS = (
    "borrower_first_name",
    "borrowerFirstName",
    "BorrowerFirstName",
    "firstName",
    "first_name",
    "borrower_first",
)
_LAST_NAME_KEYS = (
    "borrower_last_name",
    "borrowerLastName",
    "BorrowerLastName",
    "lastName",
    "last_name",
    "borrower_last",
)
_STATE_KEYS = (
    "state",
    "propertyState",
    "property_state",
    "PropertyRegion",
    "mailingState",
    "MailingRegion",
)
_STATUS_KEYS = ("status", "loanStatus", "loan_status", "LoanStatusDescription")
_PRODUCT_KEYS = (
    "product",
    "loanProduct",
    "loan_product",
    "productType",
    "MortgageTypeDescription",
)
_BALANCE_KEYS = (
    "current_balance_usd",
    "currentBalanceUsd",
    "currentBalance",
    "principalBalance",
    "unpaidPrincipalBalance",
    "UnpaidPrincipalBalanceAmount",
    "balance",
)
_NEXT_DUE_KEYS = (
    "next_due_date",
    "nextDueDate",
    "next_payment_due_date",
    "NextPaymentDueDate",
    "dueDate",
)
_DELINQ_KEYS = (
    "delinquency_days",
    "delinquencyDays",
    "daysDelinquent",
    "days_past_due",
    "DelinquentPaymentCount",
)
_LAST_PAY_KEYS = (
    "last_payment_date",
    "lastPaymentDate",
    "lastPaidDate",
    "LastPaymentReceivedDate",
)
_ESCROWED_KEYS = ("escrowed", "hasEscrow", "escrowIndicator", "isEscrowed", "EscrowFlag")
_FLAGS_KEYS = ("flags", "loanFlags", "alerts")


def _pick(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def _unwrap_payload(payload: Any) -> Any:
    """Unwrap common API envelope shapes."""
    if not isinstance(payload, dict):
        return payload
    for key in ("data", "result", "loan", "payload", "item"):
        if key in payload:
            return payload[key]
    return payload


def _to_date_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.split("T", maxsplit=1)[0]


def _parse_date(value: Any) -> date | None:
    normalized = _to_date_str(value)
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def _primary_borrower(data: dict[str, Any]) -> dict[str, Any]:
    borrowers = data.get("BorrowerSummary")
    if not isinstance(borrowers, list) or not borrowers:
        return {}

    for item in borrowers:
        if isinstance(item, dict) and item.get("BorrowerOrdinal") == 1:
            return item
    first = borrowers[0]
    return first if isinstance(first, dict) else {}


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _as_dict_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    unwrapped = _unwrap_payload(payload)
    if isinstance(unwrapped, list):
        return [item for item in unwrapped if isinstance(item, dict)]
    if isinstance(unwrapped, dict):
        return [unwrapped]
    return []


def _apply_delinquencies(data: dict[str, Any], delinquencies: list[dict[str, Any]]) -> dict[str, Any]:
    if not delinquencies:
        return data
    result = dict(data)
    primary = delinquencies[0]
    code = primary.get("DelinquencyCode")
    if code is not None and str(code).strip().isdigit():
        count = int(str(code).strip())
        result["DelinquentPaymentCount"] = max(
            int(result.get("DelinquentPaymentCount") or 0),
            count,
        )
    return result


def _merge_loan_sources(
    *,
    summary: dict[str, Any],
    borrowers: list[dict[str, Any]],
    delinquencies: list[dict[str, Any]],
    record: dict[str, Any],
    loan_id: str,
) -> dict[str, Any]:
    merged: dict[str, Any] = {**record, **summary}
    if borrowers and not _primary_borrower(merged):
        merged["BorrowerSummary"] = borrowers
    merged = _apply_delinquencies(merged, delinquencies)
    if not merged.get("LoanId") and loan_id:
        merged["LoanId"] = loan_id
    return merged


def _derive_status(data: dict[str, Any]) -> str:
    explicit = _pick(data, _STATUS_KEYS)
    if explicit and str(explicit).strip().lower() not in {"", "unknown", "not mapped"}:
        return str(explicit).strip().lower().replace(" ", "_")

    if data.get("PaidOffFlag") is True:
        return "paid_off"
    if data.get("ChargedOffFlag") is True:
        return "charged_off"
    if data.get("LoanActiveFlag") is False or data.get("ActiveFlag") is False:
        return "inactive"
    if int(data.get("DelinquentPaymentCount") or 0) > 0:
        return "delinquent"
    if data.get("LoanActiveFlag") is True or data.get("ActiveFlag") is True:
        return "active"
    return "unknown"


def _derive_flags(data: dict[str, Any]) -> list[str]:
    flags_raw = _pick(data, _FLAGS_KEYS)
    if isinstance(flags_raw, list):
        flags = [str(flag) for flag in flags_raw if flag]
    elif flags_raw is None:
        flags = []
    else:
        flags = [str(flags_raw)]

    signal_map = {
        "DelinquentAtBoardingFlag": "delinquent_at_boarding",
        "LossMitigationTemplateDescription": "loss_mitigation",
        "ForeclosureStatusDescription": "foreclosure",
        "BankruptcyStatusDescription": "bankruptcy",
    }
    for field, prefix in signal_map.items():
        value = data.get(field)
        if value is None or str(value).strip().lower() in {"", "not mapped", "removed"}:
            continue
        flags.append(f"{prefix}:{value}")

    if int(data.get("DelinquentPaymentCount") or 0) > 0 and "delinquent" not in flags:
        flags.append("delinquent")

    return flags


def _derive_delinquency_days(data: dict[str, Any], *, status: str) -> int:
    if status in {"paid_off", "inactive", "charged_off"}:
        return 0

    delinq_raw = _pick(data, _DELINQ_KEYS)
    if delinq_raw is not None:
        count = int(delinq_raw)
        if count > 0:
            return count * 30

    due = _parse_date(_pick(data, _NEXT_DUE_KEYS))
    if due is not None and due < date.today():
        return (date.today() - due).days
    return 0


def _normalize_loan(raw: dict[str, Any], *, loan_id: str | None = None) -> dict[str, Any]:
    """Map upstream loan JSON into the internal dict used by tools_api."""
    data = raw
    borrower = data.get("borrower")
    if isinstance(borrower, dict):
        merged: dict[str, Any] = {**data, **borrower}
    else:
        merged = dict(data)

    primary_borrower = _primary_borrower(merged)
    if primary_borrower:
        merged = {**merged, **primary_borrower}

    resolved_loan_id = _pick(merged, _LOAN_ID_KEYS) or loan_id or ""
    first_name = (
        _pick(merged, _FIRST_NAME_KEYS)
        or primary_borrower.get("BorrowerFirstName")
        or ""
    )
    last_name = (
        _pick(merged, _LAST_NAME_KEYS)
        or primary_borrower.get("BorrowerLastName")
        or ""
    )
    escrowed_raw = _pick(merged, _ESCROWED_KEYS)
    status = _derive_status(merged)
    flags = _derive_flags(merged)

    balance_raw = _pick(merged, _BALANCE_KEYS)
    balance = float(balance_raw) if balance_raw is not None else 0.0
    delinquency_days = _derive_delinquency_days(merged, status=status)

    if isinstance(escrowed_raw, bool):
        escrowed = escrowed_raw
    elif isinstance(escrowed_raw, str):
        escrowed = escrowed_raw.strip().lower() in {"true", "yes", "y", "1"}
    else:
        escrowed = bool(escrowed_raw)

    investor = merged.get("InvestorName")
    loan_active_raw = merged.get("LoanActiveFlag")
    if loan_active_raw is None:
        loan_active_raw = merged.get("ActiveFlag")

    return {
        "loan_id": str(resolved_loan_id),
        "borrower_first_name": str(first_name),
        "borrower_last_name": str(last_name),
        "state": str(_pick(merged, _STATE_KEYS) or ""),
        "status": status,
        "product": str(_pick(merged, _PRODUCT_KEYS) or "unknown"),
        "escrowed": escrowed,
        "current_balance_usd": balance,
        "next_due_date": _to_date_str(_pick(merged, _NEXT_DUE_KEYS)),
        "delinquency_days": delinquency_days,
        "last_payment_date": _to_date_str(_pick(merged, _LAST_PAY_KEYS)),
        "flags": flags,
        "current_interest_rate": _optional_float(merged.get("CurrentInterestRate")),
        "monthly_pi_usd": _optional_float(merged.get("CurrentMonthlyPaymentAmount")),
        "monthly_escrow_usd": _optional_float(merged.get("CurrentEscrowMonthlyPaymentAmount")),
        "total_monthly_payment_usd": _optional_float(
            merged.get("CurrentTotalMonthlyPaymentAmount")
        ),
        "maturity_date": _to_date_str(merged.get("LoanMaturityDate")),
        "loan_active": loan_active_raw if isinstance(loan_active_raw, bool) else None,
        "investor_name": str(investor) if investor else None,
    }


def _normalize_payment_schedule(
    loan_id: str,
    schedules: list[dict[str, Any]],
    *,
    months: int,
    next_due_date: str | None,
) -> dict[str, Any]:
    due_cutoff = _parse_date(next_due_date)
    items: list[dict[str, Any]] = []
    for row in schedules:
        due = _parse_date(row.get("PaymentDueMonth"))
        if due_cutoff and due and due < due_cutoff:
            continue
        principal = float(row.get("MonthlyPaymentPrincipalAmount") or 0)
        interest = float(row.get("MonthlyPaymentInterestAmount") or 0)
        escrow = float(row.get("PendingEscrowPaymentAmount") or 0)
        total = float(row.get("TotalPaymentAmount") or principal + interest + escrow)
        due_str = _to_date_str(row.get("PaymentDueMonth"))
        if not due_str:
            continue
        items.append(
            {
                "due_date": due_str,
                "principal": principal,
                "interest": interest,
                "escrow": escrow,
                "total": total,
            }
        )
    items.sort(key=lambda item: item["due_date"])
    return {"loan_id": loan_id, "schedule": items[:months]}


def _normalize_escrow_breakdown(
    loan_id: str,
    summary: dict[str, Any],
    escrows: list[dict[str, Any]],
) -> dict[str, Any]:
    escrow_row = escrows[0] if escrows else {}
    monthly_escrow = float(summary.get("CurrentEscrowMonthlyPaymentAmount") or 0)
    balance = float(summary.get("EscrowBalanceAmount") or 0)

    over_short_raw = escrow_row.get("LastEscrowAnalysisOverShortAmount")
    if over_short_raw is None:
        over_short_raw = summary.get("MonthlyOverageShortageAmount")
    monthly_change = float(over_short_raw or 0)

    as_of = _to_date_str(escrow_row.get("LastEscrowAnalysisDate")) or ""
    change_effective = (
        _to_date_str(summary.get("PaymentScheduleDueMonth") or summary.get("NextPaymentDueDate"))
        or ""
    )

    drivers: list[str] = []
    if float(summary.get("MonthlyCountyTaxAmount") or 0) > 0:
        drivers.append("county_tax")
    if float(summary.get("MonthlyHazardInsuranceAmount") or 0) > 0:
        drivers.append("hazard_insurance")
    if float(summary.get("MonthlyMortgageInsuranceAmount") or 0) > 0:
        drivers.append("mortgage_insurance")

    analysis_date = _parse_date(escrow_row.get("LastEscrowAnalysisDate"))
    next_analysis = ""
    if analysis_date:
        next_analysis = (analysis_date + timedelta(days=365)).isoformat()

    return {
        "loan_id": loan_id,
        "as_of": as_of,
        "escrow_balance_usd": balance,
        "monthly_escrow_usd": monthly_escrow,
        "monthly_escrow_change_usd": monthly_change,
        "change_effective": change_effective,
        "drivers": drivers,
        "last_disbursements": [],
        "next_analysis_date": next_analysis,
    }


def _build_mock_payment_schedule(
    loan: dict[str, Any],
    *,
    months: int,
) -> dict[str, Any]:
    loan_id = str(loan["loan_id"])
    if loan["status"] == "paid_off" or loan.get("next_due_date") is None:
        return {"loan_id": loan_id, "schedule": []}

    if loan_id == "100245":
        schedule = [
            {
                "due_date": "2026-06-01",
                "principal": 412.55,
                "interest": 1180.12,
                "escrow": 615.30,
                "total": 2207.97,
            },
            {
                "due_date": "2026-07-01",
                "principal": 413.81,
                "interest": 1178.86,
                "escrow": 615.30,
                "total": 2207.97,
            },
            {
                "due_date": "2026-08-01",
                "principal": 415.07,
                "interest": 1177.60,
                "escrow": 615.30,
                "total": 2207.97,
            },
        ]
        return {"loan_id": loan_id, "schedule": schedule[:months]}

    from datetime import datetime

    schedule_items: list[dict[str, Any]] = []
    base_date = datetime.strptime(str(loan["next_due_date"]), "%Y-%m-%d")
    balance = float(loan["current_balance_usd"])
    interest_rate = float(loan.get("current_interest_rate") or 0.045)
    remaining_months = 360
    monthly_rate = interest_rate / 12

    if monthly_rate > 0:
        total_pi = (
            balance
            * (monthly_rate * (1 + monthly_rate) ** remaining_months)
            / ((1 + monthly_rate) ** remaining_months - 1)
        )
    else:
        total_pi = balance / remaining_months

    total_pi = round(total_pi, 2)
    escrow = float(loan.get("monthly_escrow_usd") or 615.30) if loan["escrowed"] else 0.0

    for i in range(months):
        due_date_str = (base_date + timedelta(days=30 * i)).strftime("%Y-%m-%d")
        interest = round(balance * interest_rate / 12, 2)
        principal = round(total_pi - interest, 2)
        if principal > balance:
            principal = round(balance, 2)
            total_pi = round(principal + interest, 2)
        total = round(principal + interest + escrow, 2)
        schedule_items.append(
            {
                "due_date": due_date_str,
                "principal": principal,
                "interest": interest,
                "escrow": escrow,
                "total": total,
            }
        )
        balance = round(balance - principal, 2)
        if balance <= 0:
            break

    return {"loan_id": loan_id, "schedule": schedule_items}


def _build_mock_escrow_breakdown(loan: dict[str, Any]) -> dict[str, Any]:
    loan_id = str(loan["loan_id"])
    if not loan["escrowed"]:
        return {
            "loan_id": loan_id,
            "as_of": "2026-04-30",
            "escrow_balance_usd": 0.0,
            "monthly_escrow_usd": 0.0,
            "monthly_escrow_change_usd": 0.0,
            "change_effective": "",
            "drivers": [],
            "last_disbursements": [],
            "next_analysis_date": "",
        }

    if loan_id == "100245":
        return {
            "loan_id": loan_id,
            "as_of": "2026-04-30",
            "escrow_balance_usd": 1842.10,
            "monthly_escrow_usd": 615.30,
            "monthly_escrow_change_usd": 35.12,
            "change_effective": "2026-05-01",
            "drivers": ["county_tax_reassessment", "hazard_premium"],
            "last_disbursements": [
                {"date": "2026-03-15", "type": "county_property_tax", "amount_usd": 3120.00},
                {"date": "2026-02-01", "type": "hazard_insurance", "amount_usd": 1842.00},
            ],
            "next_analysis_date": "2027-03-01",
        }

    return {
        "loan_id": loan_id,
        "as_of": "2026-04-30",
        "escrow_balance_usd": 1500.00,
        "monthly_escrow_usd": float(loan.get("monthly_escrow_usd") or 500.00),
        "monthly_escrow_change_usd": 20.00,
        "change_effective": "2026-05-01",
        "drivers": ["county_tax_reassessment"],
        "last_disbursements": [
            {"date": "2026-03-15", "type": "county_property_tax", "amount_usd": 2500.00},
            {"date": "2026-02-01", "type": "hazard_insurance", "amount_usd": 1500.00},
        ],
        "next_analysis_date": "2027-03-01",
    }


def _normalize_search_results(payload: Any) -> list[dict[str, Any]]:
    """Normalize list or envelope responses into loan dicts."""
    unwrapped = _unwrap_payload(payload)
    if isinstance(unwrapped, list):
        items = unwrapped
    elif isinstance(unwrapped, dict):
        for key in ("results", "items", "loans", "matches", "data"):
            candidate = unwrapped.get(key)
            if isinstance(candidate, list):
                items = candidate
                break
        else:
            items = [unwrapped]
    else:
        return []

    normalized: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            normalized.append(_normalize_loan(item))
    return normalized


class AbstractLoanDataProvider(ABC):
    """Protocol for fetching loan data."""

    @abstractmethod
    async def get_loan(self, loan_id: str) -> dict[str, Any] | None:
        """Fetch a specific loan by ID."""
        ...

    @abstractmethod
    async def search_by_name(self, name: str) -> list[dict[str, Any]]:
        """Search for loans by borrower name."""
        ...

    @abstractmethod
    async def get_payment_schedule(self, loan_id: str, *, months: int = 3) -> dict[str, Any]:
        """Return upcoming payment schedule as internal dict."""
        ...

    @abstractmethod
    async def get_escrow_breakdown(self, loan_id: str) -> dict[str, Any]:
        """Return escrow breakdown as internal dict."""
        ...


class JsonFileLoanProvider(AbstractLoanDataProvider):
    """Mock provider that reads from data/loans.json."""

    def __init__(self) -> None:
        self._db: dict[str, dict[str, Any]] = {}
        self._load_loans_db()

    def _load_loans_db(self) -> None:
        paths_to_try = [
            Path("data/loans.json"),
            Path(__file__).parent.parent.parent.parent / "data" / "loans.json",
        ]

        loaded = False
        for path in paths_to_try:
            if path.exists():
                try:
                    with open(path, encoding="utf-8") as f:
                        loans_list = json.load(f)
                        for loan in loans_list:
                            self._db[loan["loan_id"]] = loan
                    loaded = True
                    break
                except Exception as e:
                    logger.error(f"Error loading loans database from {path}: {e}")

        if not loaded:
            logger.warning("WARNING: Loans database (loans.json) could not be loaded!")

    async def get_loan(self, loan_id: str) -> dict[str, Any] | None:
        """Retrieve loan from the local in-memory dict."""
        clean_loan_id = loan_id.strip()
        if not self._db:
            self._load_loans_db()
        return self._db.get(clean_loan_id)

    async def search_by_name(self, name: str) -> list[dict[str, Any]]:
        """Search loan records by borrower name in the local database."""
        if not self._db:
            self._load_loans_db()

        query_tokens = [token for token in name.lower().split() if token]
        if not query_tokens:
            return []

        matches: list[dict[str, Any]] = []
        for loan in self._db.values():
            first = loan["borrower_first_name"].lower()
            last = loan["borrower_last_name"].lower()
            full = f"{first} {last}"

            if all(token in first or token in last or token in full for token in query_tokens):
                matches.append(loan)

        return matches[:10]

    async def get_payment_schedule(self, loan_id: str, *, months: int = 3) -> dict[str, Any]:
        loan = await self.get_loan(loan_id)
        if loan is None:
            return {"loan_id": loan_id.strip(), "schedule": []}
        return _build_mock_payment_schedule(loan, months=months)

    async def get_escrow_breakdown(self, loan_id: str) -> dict[str, Any]:
        loan = await self.get_loan(loan_id)
        if loan is None:
            return _build_mock_escrow_breakdown(
                {"loan_id": loan_id.strip(), "escrowed": False, "status": "unknown"}
            )
        return _build_mock_escrow_breakdown(loan)


_FIXTURE_ROOT_CANDIDATES = (
    Path("data/fixtures/loan_api"),
    Path(__file__).parent.parent.parent.parent / "data" / "fixtures" / "loan_api",
)


def loan_fixtures_dir() -> Path | None:
    """Return fixtures root if it contains at least one loan directory."""
    for path in _FIXTURE_ROOT_CANDIDATES:
        if path.is_dir() and any(path.iterdir()):
            return path
    return None


class FixtureLoanProvider(AbstractLoanDataProvider):
    """Mock provider that loads upstream-shaped JSON fixtures and normalizes them.

    Fixtures are generated by ``scripts/fixtures/generate.mjs`` (json-schema-faker)
    into ``data/fixtures/loan_api/{loan_id}/``.
    """

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        resolved = fixtures_dir or loan_fixtures_dir()
        if resolved is None:
            raise ValueError("No loan fixtures found under data/fixtures/loan_api")
        self._root = resolved
        self._cache: dict[str, dict[str, Any]] = {}

    def _loan_dir(self, loan_id: str) -> Path | None:
        path = self._root / loan_id.strip()
        return path if path.is_dir() else None

    def _read_json(self, path: Path) -> Any:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def _load_bundle(self, loan_id: str) -> dict[str, Any] | None:
        clean = loan_id.strip()
        if clean in self._cache:
            return self._cache[clean]
        loan_dir = self._loan_dir(clean)
        if loan_dir is None:
            return None

        def optional(name: str) -> Any:
            file_path = loan_dir / name
            if not file_path.exists():
                return None
            return self._read_json(file_path)

        bundle = {
            "summary": optional("summary.json") or {},
            "loan": optional("loan.json") or {},
            "borrowers": optional("borrowers.json") or [],
            "payment_schedules": optional("payment_schedules.json") or [],
            "escrows": optional("escrows.json") or [],
            "delinquencies": optional("delinquencies.json") or [],
        }
        if not bundle["summary"] and not bundle["loan"]:
            return None
        self._cache[clean] = bundle
        return bundle

    async def get_loan(self, loan_id: str) -> dict[str, Any] | None:
        bundle = self._load_bundle(loan_id)
        if bundle is None:
            return None
        borrowers = bundle["borrowers"]
        if not isinstance(borrowers, list):
            borrowers = []
        delinquencies = bundle["delinquencies"]
        if not isinstance(delinquencies, list):
            delinquencies = []
        summary = bundle["summary"] if isinstance(bundle["summary"], dict) else {}
        record = bundle["loan"] if isinstance(bundle["loan"], dict) else {}
        merged = _merge_loan_sources(
            summary=summary,
            borrowers=[b for b in borrowers if isinstance(b, dict)],
            delinquencies=[d for d in delinquencies if isinstance(d, dict)],
            record=record,
            loan_id=loan_id.strip(),
        )
        return _normalize_loan(merged, loan_id=loan_id.strip())

    async def search_by_name(self, name: str) -> list[dict[str, Any]]:
        query_tokens = [token for token in name.lower().split() if token]
        if not query_tokens:
            return []

        matches: list[dict[str, Any]] = []
        for child in sorted(self._root.iterdir()):
            if not child.is_dir():
                continue
            loan = await self.get_loan(child.name)
            if loan is None:
                continue
            first = loan["borrower_first_name"].lower()
            last = loan["borrower_last_name"].lower()
            full = f"{first} {last}"
            if all(token in first or token in last or token in full for token in query_tokens):
                matches.append(loan)
        return matches[:10]

    async def get_payment_schedule(self, loan_id: str, *, months: int = 3) -> dict[str, Any]:
        clean = loan_id.strip()
        bundle = self._load_bundle(clean)
        if bundle is None:
            return {"loan_id": clean, "schedule": []}
        summary = bundle["summary"] if isinstance(bundle["summary"], dict) else {}
        loan = _normalize_loan(summary, loan_id=clean) if summary else await self.get_loan(clean)
        if loan is None:
            return {"loan_id": clean, "schedule": []}
        schedules = bundle["payment_schedules"]
        if not isinstance(schedules, list):
            schedules = []
        return _normalize_payment_schedule(
            clean,
            [row for row in schedules if isinstance(row, dict)],
            months=months,
            next_due_date=loan.get("next_due_date"),
        )

    async def get_escrow_breakdown(self, loan_id: str) -> dict[str, Any]:
        clean = loan_id.strip()
        bundle = self._load_bundle(clean)
        if bundle is None:
            return _normalize_escrow_breakdown(clean, {}, [])
        summary = bundle["summary"] if isinstance(bundle["summary"], dict) else {}
        loan = _normalize_loan(summary, loan_id=clean) if summary else await self.get_loan(clean)
        if loan is None:
            return _normalize_escrow_breakdown(clean, {}, [])
        if not loan["escrowed"]:
            return {
                "loan_id": clean,
                "as_of": "",
                "escrow_balance_usd": 0.0,
                "monthly_escrow_usd": 0.0,
                "monthly_escrow_change_usd": 0.0,
                "change_effective": "",
                "drivers": [],
                "last_disbursements": [],
                "next_analysis_date": "",
            }
        escrows = bundle["escrows"]
        if not isinstance(escrows, list):
            escrows = []
        return _normalize_escrow_breakdown(
            clean,
            summary,
            [row for row in escrows if isinstance(row, dict)],
        )


class RestApiLoanProvider(AbstractLoanDataProvider):
    """Real provider that calls the PennyMac Loan Services REST API."""

    def __init__(self, config: LoanApiConfig) -> None:
        if not config.base_url:
            raise ValueError("DATA__LOAN_API__BASE_URL is required when DATA__LOAN_SOURCE=real")
        if not config.api_key:
            raise ValueError(
                "DATA__LOAN_API__API_KEY is required when DATA__LOAN_SOURCE=real "
                "(paste your upstream Bearer token)"
            )
        self._config = config
        base_url = config.base_url.rstrip("/")
        if base_url.startswith("http://"):
            base_url = "https://" + base_url[len("http://") :]
            logger.warning("Loan API base URL upgraded to HTTPS: %s", base_url)
        self._base_url = base_url
        self._headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, *, params: dict[str, str] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        timeout = httpx.Timeout(self._config.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers,
                params=params,
            )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()

    def _api_params(self) -> dict[str, str]:
        return {"api-version": self._config.api_version}

    def _summary_params(self) -> dict[str, str]:
        return {
            "PDMmodel": str(self._config.summary_pdm_model).lower(),
            "api-version": self._config.api_version,
        }

    def _format_path(self, template: str, loan_id: str) -> str:
        return template.format(loan_id=loan_id, LoanId=loan_id)

    async def _fetch_summary(self, loan_id: str) -> dict[str, Any] | None:
        path = self._format_path(self._config.get_loan_summary_path, loan_id)
        payload = await self._request("GET", path, params=self._summary_params())
        if payload is None:
            return None
        unwrapped = _unwrap_payload(payload)
        return unwrapped if isinstance(unwrapped, dict) else None

    async def _fetch_record(self, loan_id: str) -> dict[str, Any] | None:
        path = self._format_path(self._config.get_loan_path, loan_id)
        payload = await self._request("GET", path, params=self._api_params())
        if payload is None:
            return None
        unwrapped = _unwrap_payload(payload)
        return unwrapped if isinstance(unwrapped, dict) else None

    async def _fetch_borrowers(self, loan_id: str) -> list[dict[str, Any]]:
        path = self._format_path(self._config.get_borrower_summary_path, loan_id)
        payload = await self._request("GET", path, params=self._api_params())
        return _as_dict_list(payload)

    async def _fetch_payment_schedules(self, loan_id: str) -> list[dict[str, Any]]:
        path = self._format_path(self._config.get_payment_schedules_path, loan_id)
        payload = await self._request("GET", path, params=self._api_params())
        return _as_dict_list(payload)

    async def _fetch_escrows(self, loan_id: str) -> list[dict[str, Any]]:
        path = self._format_path(self._config.get_escrows_path, loan_id)
        payload = await self._request("GET", path, params=self._api_params())
        return _as_dict_list(payload)

    async def _fetch_delinquencies(self, loan_id: str) -> list[dict[str, Any]]:
        path = self._format_path(self._config.get_delinquencies_path, loan_id)
        payload = await self._request("GET", path, params=self._api_params())
        return _as_dict_list(payload)

    async def get_loan(self, loan_id: str) -> dict[str, Any] | None:
        clean_loan_id = loan_id.strip()
        try:
            summary, borrowers, delinquencies, record = await asyncio.gather(
                self._fetch_summary(clean_loan_id),
                self._fetch_borrowers(clean_loan_id),
                self._fetch_delinquencies(clean_loan_id),
                self._fetch_record(clean_loan_id),
            )
        except httpx.HTTPStatusError as exc:
            logger.error("Loan API get_loan failed for %s: %s", clean_loan_id, exc)
            raise
        except httpx.HTTPError as exc:
            logger.error("Loan API transport error for %s: %s", clean_loan_id, exc)
            raise

        if summary is None and record is None:
            return None

        merged = _merge_loan_sources(
            summary=summary or {},
            borrowers=borrowers,
            delinquencies=delinquencies,
            record=record or {},
            loan_id=clean_loan_id,
        )
        return _normalize_loan(merged, loan_id=clean_loan_id)

    async def get_payment_schedule(self, loan_id: str, *, months: int = 3) -> dict[str, Any]:
        clean_loan_id = loan_id.strip()
        try:
            summary, schedules = await asyncio.gather(
                self._fetch_summary(clean_loan_id),
                self._fetch_payment_schedules(clean_loan_id),
            )
        except httpx.HTTPStatusError as exc:
            logger.error("Loan API get_payment_schedule failed for %s: %s", clean_loan_id, exc)
            raise
        except httpx.HTTPError as exc:
            logger.error(
                "Loan API transport error during payment schedule for %s: %s",
                clean_loan_id,
                exc,
            )
            raise

        if summary is None:
            return {"loan_id": clean_loan_id, "schedule": []}

        loan = _normalize_loan(summary, loan_id=clean_loan_id)
        # if loan["status"] in {"paid_off", "inactive"} or loan.get("next_due_date") is None:
        #     return {"loan_id": clean_loan_id, "schedule": []}

        return _normalize_payment_schedule(
            clean_loan_id,
            schedules,
            months=months,
            next_due_date=loan.get("next_due_date"),
        )

    async def get_escrow_breakdown(self, loan_id: str) -> dict[str, Any]:
        clean_loan_id = loan_id.strip()
        try:
            summary, escrows = await asyncio.gather(
                self._fetch_summary(clean_loan_id),
                self._fetch_escrows(clean_loan_id),
            )
        except httpx.HTTPStatusError as exc:
            logger.error("Loan API get_escrow_breakdown failed for %s: %s", clean_loan_id, exc)
            raise
        except httpx.HTTPError as exc:
            logger.error(
                "Loan API transport error during escrow breakdown for %s: %s",
                clean_loan_id,
                exc,
            )
            raise

        if summary is None:
            return _normalize_escrow_breakdown(clean_loan_id, {}, escrows)

        loan = _normalize_loan(summary, loan_id=clean_loan_id)
        if not loan["escrowed"]:
            return {
                "loan_id": clean_loan_id,
                "as_of": "",
                "escrow_balance_usd": 0.0,
                "monthly_escrow_usd": 0.0,
                "monthly_escrow_change_usd": 0.0,
                "change_effective": "",
                "drivers": [],
                "last_disbursements": [],
                "next_analysis_date": "",
            }

        return _normalize_escrow_breakdown(clean_loan_id, summary, escrows)

    async def search_by_name(self, name: str) -> list[dict[str, Any]]:
        # PennyMac Loan Services API is loan-id keyed only (no borrower-name search).
        raise NotImplementedError(
            "Borrower name search is not available on the Loan Services API. "
            "Use lookup_loan with a loan_id instead."
        )
