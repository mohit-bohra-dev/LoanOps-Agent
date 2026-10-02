"""Unit tests for capability-bound call_sse_api arg rewriting."""

from __future__ import annotations

import pytest
from packages.capability_kg.catalog import CapabilityRecord
from packages.mcp_server.capability_bind import apply_capability_bind, resolve_binding
from packages.mcp_server.policy import PolicyError


class _StubCatalog:
    """Minimal catalog stub implementing get_capability."""

    def __init__(self, records: dict[str, CapabilityRecord]) -> None:
        self._records = records

    def get_capability(self, capability_id: str) -> CapabilityRecord | None:
        return self._records.get(capability_id)


def _loan_summary_catalog() -> _StubCatalog:
    return _StubCatalog(
        {
            "get_loan_summary": CapabilityRecord(
                id="get_loan_summary",
                description="Get loan summary",
                operation_id="getLoanSummary",
                read_only=True,
                review_status="approved",
                permission="loan.read",
            )
        }
    )


def test_capability_id_sets_operation_id() -> None:
    catalog = _loan_summary_catalog()
    out = apply_capability_bind(
        {
            "capability_id": "get_loan_summary",
            "path_params": {"loan_id": "L-1"},
            "headers": {"x-loanops-user": "rep"},
        },
        catalog,
        require_bind=False,
    )
    assert out["operation_id"] == "getLoanSummary"
    assert out["method"] == "GET"
    assert out["path_params"] == {"loan_id": "L-1"}
    assert out["headers"] == {"x-loanops-user": "rep"}
    binding = resolve_binding(catalog, capability_id="get_loan_summary")
    assert binding is not None
    assert binding.operation_id == "getLoanSummary"


def test_mismatched_operation_id_raises_policy_error() -> None:
    catalog = _loan_summary_catalog()
    with pytest.raises(PolicyError, match="does not match capability"):
        apply_capability_bind(
            {
                "capability_id": "get_loan_summary",
                "operation_id": "getPaymentSchedules",
            },
            catalog,
            require_bind=False,
        )


def test_require_bind_without_capability_id_raises() -> None:
    catalog = _loan_summary_catalog()
    with pytest.raises(PolicyError, match="requires capability_id"):
        apply_capability_bind(
            {"operation_id": "getLoanSummary"},
            catalog,
            require_bind=True,
        )


def test_require_bind_false_operation_id_passthrough() -> None:
    catalog = _loan_summary_catalog()
    args = {
        "operation_id": "getLoanSummary",
        "path_params": {"loan_id": "L-9"},
    }
    out = apply_capability_bind(args, catalog, require_bind=False)
    assert out == args
    assert out is not args  # copy, not same object


def test_matching_operation_id_allowed() -> None:
    catalog = _loan_summary_catalog()
    out = apply_capability_bind(
        {
            "capability_id": "get_loan_summary",
            "operation_id": "getLoanSummary",
            "method": "GET",
        },
        catalog,
        require_bind=True,
    )
    assert out["operation_id"] == "getLoanSummary"
    assert out["method"] == "GET"


def test_unknown_capability_raises() -> None:
    catalog = _loan_summary_catalog()
    with pytest.raises(PolicyError, match="Unknown or unbound"):
        apply_capability_bind(
            {"capability_id": "no_such_cap"},
            catalog,
            require_bind=False,
        )


def test_non_get_method_raises() -> None:
    catalog = _loan_summary_catalog()
    with pytest.raises(PolicyError, match="must be GET"):
        apply_capability_bind(
            {"capability_id": "get_loan_summary", "method": "POST"},
            catalog,
            require_bind=False,
        )
