"""Unit tests for MCP capability requiresPermission enforcement."""

from __future__ import annotations

import pytest
from packages.mcp_server.capability_authz import (
    allowed_permissions_for_role,
    assert_capability_permission,
    normalize_permission,
)
from packages.mcp_server.policy import PolicyError


def test_normalize_permission() -> None:
    assert normalize_permission("  Loan.Read  ") == "loan.read"


def test_enforce_false_always_allows() -> None:
    assert_capability_permission(
        required="ViewLoanPayments",
        allowed=frozenset({"loan.read"}),
        enforce=False,
    )


def test_enforce_true_matching_permission_ok() -> None:
    assert_capability_permission(
        required="loan.read",
        allowed=frozenset({"loan.read"}),
        enforce=True,
    )


def test_enforce_true_mismatch_raises_policy_error() -> None:
    with pytest.raises(PolicyError, match="viewloanpayments"):
        assert_capability_permission(
            required="ViewLoanPayments",
            allowed=frozenset({"loan.read"}),
            enforce=True,
        )


def test_empty_required_ok() -> None:
    assert_capability_permission(
        required=None,
        allowed=frozenset(),
        enforce=True,
    )
    assert_capability_permission(
        required="",
        allowed=frozenset(),
        enforce=True,
    )
    assert_capability_permission(
        required="   ",
        allowed=frozenset(),
        enforce=True,
    )


def test_configured_permissions_override_role_defaults() -> None:
    allowed = allowed_permissions_for_role("system", ["ViewLoanPayments"])
    assert allowed == frozenset({"viewloanpayments"})
    assert "loan.read" not in allowed


def test_system_dev_default_includes_loan_read() -> None:
    for role in ("system", "dev", "SYSTEM"):
        allowed = allowed_permissions_for_role(role, [])
        assert "loan.read" in allowed
        assert "*" not in allowed


def test_unknown_role_empty_defaults() -> None:
    assert allowed_permissions_for_role("rep", []) == frozenset()
